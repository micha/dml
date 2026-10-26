#!/usr/bin/env python3
"""Offline counterexamples. Every effect stays under ignored runtime/sandbox.
Uses only OpenTofu's built-in terraform_data provider; never AWS or Docker.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE / 'runtime' / 'sandbox'
ROOT.mkdir(parents=True, exist_ok=True)
READY = json.loads((BASE.parent / 'tools' / 'ready.json').read_text())
TOFU = READY['executable']
results = {'python': sys.version, 'tofu': READY, 'tofu_executable_sha256': hashlib.sha256(Path(TOFU).read_bytes()).hexdigest(), 'experiments': {}}

def fresh(name):
    p = ROOT / name
    if p.exists(): shutil.rmtree(p)
    p.mkdir()
    return p

def run(p, *args, ok=True):
    env = {'PATH': os.defpath, 'HOME': str(p), 'TF_IN_AUTOMATION': '1', 'CHECKPOINT_DISABLE': '1'}
    r = subprocess.run([TOFU, *args, '-no-color'] if args[0] != 'version' else [TOFU, *args], cwd=p, env=env, text=True, capture_output=True, timeout=60)
    n = len(list(p.glob('command-*.log')))
    (p / f'command-{n:02}.log').write_text('$ ' + ' '.join([TOFU, *args]) + '\n' + r.stdout + r.stderr)
    if ok and r.returncode: raise RuntimeError(r.stdout + r.stderr)
    return r

def init(p): run(p, 'init', '-input=false')
def apply(p): run(p, 'apply', '-auto-approve', '-input=false')
def output(p): return json.loads(run(p, 'output', '-json').stdout)

# 1: actual sensitive output remains in state and structured output; copies survive.
p = fresh('erasure')
secret = 'SYNTHETIC-ONLY-project-0007'
(p / 'main.tf').write_text(f'output "private" {{\n value = "{secret}"\n sensitive = true\n}}\n')
init(p); apply(p)
state = (p / 'terraform.tfstate').read_bytes()
structured = output(p)
assert structured['private']['sensitive'] is True
assert secret.encode() in state and structured['private']['value'] == secret
(p / 'replica.tfstate.copy').write_bytes(state)
(p / 'immutable-commit.copy').write_bytes(state)
digest = hashlib.sha256(secret.encode()).hexdigest()
old_parent = hashlib.sha256(('child:' + digest).encode()).hexdigest()
tombstone_digest = hashlib.sha256(b'TOMBSTONE').hexdigest()
new_parent = hashlib.sha256(('child:' + tombstone_digest).encode()).hexdigest()
assert old_parent != new_parent
(p / 'hash-reference.json').write_text(json.dumps({'old_child': digest, 'old_parent': old_parent, 'tombstone_child': tombstone_digest, 'new_parent': new_parent}))
(p / 'main.tf').write_text('output "private" { value = "TOMBSTONE" }\n')
apply(p)
assert secret.encode() not in (p / 'terraform.tfstate').read_bytes()
survivors = [f.name for f in p.iterdir() if f.is_file() and secret.encode() in f.read_bytes()]
recovered = next(f'SYNTHETIC-ONLY-project-{i:04}' for i in range(100) if hashlib.sha256(f'SYNTHETIC-ONLY-project-{i:04}'.encode()).hexdigest() == digest)
assert recovered == secret
results['experiments']['erasure'] = {'sensitive_json_exposes_value': True, 'current_state_tombstoned': True, 'plaintext_survivors': survivors, 'low_entropy_hash_recovered_in_candidates': 100, 'rewriting_hash_child_changes_parent': True}

# 2: exact main.tf copy isn't its file dependency closure.
p = fresh('file-capture')
original = p / 'original'; regenerated = p / 'regenerated'
original.mkdir(); regenerated.mkdir()
hcl = 'output "body" { value = file("${path.module}/payload.txt") }\n'
(original / 'main.tf').write_text(hcl); (original / 'payload.txt').write_text('synthetic-dataset-v1')
(regenerated / 'main.tf').write_text(hcl)
init(original); apply(original)
init(regenerated)
r = run(regenerated, 'plan', '-input=false', ok=False)
assert r.returncode and 'payload.txt' in r.stderr
results['experiments']['file_capture'] = {'same_hcl_sha256': hashlib.sha256(hcl.encode()).hexdigest(), 'original_output': output(original)['body']['value'], 'regenerated_plan_exit': r.returncode}

# 3: removing an entire protected declaration removes its prevent_destroy gate.
p = fresh('prevent-destroy')
(p / 'main.tf').write_text('resource "terraform_data" "retained" {\n input = "artifact-binding"\n lifecycle { prevent_destroy = true }\n}\n')
init(p); apply(p)
r = run(p, 'plan', '-destroy', '-input=false', ok=False)
assert r.returncode and 'prevent_destroy' in r.stderr
(p / 'main.tf').write_text('')
r = run(p, 'plan', '-input=false')
assert '1 to destroy' in r.stdout
results['experiments']['prevent_destroy'] = {'with_declaration_destroy_exit': 1, 'removed_declaration_plan': '0 to add, 0 to change, 1 to destroy'}

# 4: cleanup shell provisioner vanishes when resource source disappears.
p = fresh('cleanup-removal')
(p / 'main.tf').write_text('''resource "terraform_data" "compute" {
 provisioner "local-exec" { command = "printf synthetic-compute > compute.txt" }
 provisioner "local-exec" {
  when = destroy
  command = "rm compute.txt"
 }
}
''')
init(p); apply(p); assert (p / 'compute.txt').exists()
(p / 'main.tf').write_text(''); apply(p)
assert (p / 'compute.txt').exists()
assert json.loads((p / 'terraform.tfstate').read_text())['resources'] == []
results['experiments']['cleanup_removal'] = {'state_empty': True, 'provisioner_created_artifact_survives_destroy': True}

# 5: two local module instances share path.module, deterministic overwrite.
p = fresh('module-path')
(p / 'child').mkdir()
(p / 'child' / 'main.tf').write_text('''variable "value" { type = string }
resource "terraform_data" "writer" {
 provisioner "local-exec" { command = "printf '${var.value}' > ${path.module}/shared.txt" }
}
output "shared_path" { value = "${path.module}/shared.txt" }
''')
(p / 'main.tf').write_text('''module "a" {\n source = "./child"\n value = "alpha"\n}
module "b" {\n source = "./child"\n value = "beta"\n depends_on = [module.a]\n}
output "paths" { value = [module.a.shared_path, module.b.shared_path] }
''')
init(p); apply(p)
paths = output(p)['paths']['value']
assert paths[0] == paths[1] and (p / paths[0]).read_text() == 'beta'
results['experiments']['module_path'] = {'two_output_paths': paths, 'final_bytes': 'beta', 'first_instance_bytes_lost': True}

# 6: unchanged regenerated source + missing state doesn't restore remote identity.
p = fresh('state-loss')
hcl = 'resource "terraform_data" "binding" { input = "same-input" }\noutput "id" { value = terraform_data.binding.id }\n'
(p / 'main.tf').write_text(hcl); init(p); apply(p)
first = output(p)['id']['value']
(p / 'observed-dml.json').write_text(json.dumps({'successful_binding_id': first}))
shutil.copyfile(p / 'terraform.tfstate', p / 'saved-state.copy')
(p / 'terraform.tfstate').unlink()
if (p / 'terraform.tfstate.backup').exists(): (p / 'terraform.tfstate.backup').unlink()
apply(p)
second = output(p)['id']['value']
assert first != second
results['experiments']['state_loss'] = {'same_hcl': True, 'first_id': first, 'second_id': second, 'historical_observation_stale_for_current_binding': True}

# 7: accounting sketches, explicitly simulations, not DML implementation.
p = fresh('history-simulation')
attempts = [{'id': 'A1', 'closure': 'agent-v1', 'bytes': 'answer-42'}, {'id': 'A2', 'closure': 'agent-v1', 'bytes': 'answer-42'}]
requests = [{'id': 'Q1', 'attempt': 'A1', 'action': 'fresh'}, {'id': 'Q2', 'attempt': 'A1', 'action': 'intentional-reuse'}, {'id': 'Q3', 'attempt': 'A2', 'action': 'fresh'}]
assert len({a['id'] for a in attempts}) == 2 and len({a['bytes'] for a in attempts}) == 1
artifact = p / 'dataset.txt'; artifact.write_text('synthetic dataset version one')
observation = {'uri': str(artifact), 'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(), 'outcome': 'success'}
artifact.write_text('out-of-band version two')
assert hashlib.sha256(artifact.read_bytes()).hexdigest() != observation['sha256']
results['experiments']['history_simulation'] = {'requests': requests, 'attempts': attempts, 'counts': {'requests': 3, 'attempts': 2, 'unique_results': 1}, 'uri_stable_but_bytes_changed': True}

# 8: source-checked cloud inference; do not mistake this for provider execution.
source = (BASE / 'runtime' / 'sources' / 'aws_s3_object.go').read_text()
assert '"metadata",' in source.split('func hasObjectContentChanges', 1)[1].split('func findObjectByBucketAndKey', 1)[0]
assert 'body = bytes.NewReader([]byte{})' in source
assert 'resourceObjectUpload(ctx, d, meta)' in source.split('func resourceObjectUpdate', 1)[1].split('func resourceObjectDelete', 1)[0]
assert 'deleteAllObjectVersions(ctx, conn, bucket, key' in source
assert '"version_id": {\n\t\t\t\t\tType:     schema.TypeString,\n\t\t\t\t\tComputed: true' in source
results['experiments']['provider_source_checks'] = {'metadata_triggers_upload': True, 'absent_body_uploads_empty_bytes': True, 'version_id_computed_not_configurable': True, 'versioned_delete_calls_all_versions': True, 'cloud_executed': False}

(BASE / 'runtime' / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
