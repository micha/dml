#!/usr/bin/env python3
"""Independent adversarial checks; synthetic files only in fresh review runtime."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
(HERE / 'runtime').mkdir(exist_ok=True)
ROOT = Path(tempfile.mkdtemp(prefix='x-', dir=HERE / 'runtime'))
(ROOT / 't').mkdir()
ENV = {'PATH': os.environ['PATH'], 'HOME': str(ROOT), 'TMPDIR': str(ROOT / 't'),
       'TF_IN_AUTOMATION': '1', 'CHECKPOINT_DISABLE': '1', 'TF_INPUT': '0',
       'TF_CLI_CONFIG_FILE': str(ROOT / 'tofurc')}
(ROOT / 'tofurc').write_text('')
TOFU = STUDY / 'tools/tofu'
assert hashlib.sha256(TOFU.read_bytes()).hexdigest() == '949061cbb3c3d4558928ca9a459a5052b8c5e5545d17656f33316d2e3bc335f2'
results = {'runtime': str(ROOT), 'commands': [], 'checks': {}}

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

ret = load('review_retention', STUDY / 'retention/model.py')
# A new dependent can reintroduce a withdrawn prerequisite before physical disposal.
m = ret.Manager(ROOT / 'withdrawn')
m.add('compute', 'provisioned')
m.excise({'compute'}, set())
assert m.plan().victims == {'compute'}
m.add('new-result', 'adopted', deps={'compute'})
m.publish('A', 'new-history', datums=['new-result'])
assert 'compute' in m.retained() and 'compute' not in m.plan().victims
assert not m.available('new-result')
m.assert_safety()  # Current invariants do not reject this lifecycle deadlock.
results['checks']['adoption_after_excision'] = {
    'evidence': 'executed simulation', 'new_reference_accepted': True,
    'excised_compute_re_retained': True, 'new_result_available': False,
    'invariants_passed': True, 'interpretation': 'missing withdrawal/publication policy, not approved design violation'}

# Existing resource identities are not immutable through the model add API.
m = ret.Manager(ROOT / 'identity')
m.add('bucket', 'external')
m.add('bucket', 'provisioned')
m.reserve(m.plan()); m.destroy_reserved(); m.assert_safety()
assert 'bucket' in m.deleted
results['checks']['identity_re_registration'] = {
    'evidence': 'executed simulation', 'original_external_identity_deleted': True,
    'invariants_passed': True, 'interpretation': 'fixture API overwrites ownership; reject duplicate identities in a hardened model'}

# Two head names are independent retention roots, even when pointing to one commit.
m = ret.Manager(ROOT / 'heads')
m.add('object', 'adopted'); m.publish('A', 'a', datums=['object'])
m.move_head('A', 'alias-head', 'a'); m.move_head('A', 'main', None)
assert not m.plan().victims
m.add_export('alias-export', {'object'}); m.move_head('A', 'alias-head', None)
assert not m.plan().victims
results['checks']['head_export_aliases'] = {'evidence': 'executed simulation', 'retained': True}

def cli(d, *args, expected=0):
    cmd = [str(TOFU), '-chdir=' + str(d), *args]
    p = subprocess.run(cmd, env=ENV, capture_output=True, text=True, timeout=60)
    n = len(results['commands'])
    (ROOT / f'{n}.stdout').write_text(p.stdout)
    (ROOT / f'{n}.stderr').write_text(p.stderr)
    results['commands'].append({'argv': cmd, 'returncode': p.returncode, 'log': n})
    assert p.returncode == expected, (cmd, p.stderr)
    return p.stdout

def directory(name):
    d = ROOT / name; d.mkdir(); return d

# A queued saved destroy plan ignores subsequently restored/strengthened HCL.
d = directory('queue')
marker = d / 'synthetic-compute'
original = f'''resource "terraform_data" "compute" {{
  input = "old-binding"
  provisioner "local-exec" {{ command = "printf synthetic > {marker}" }}
  provisioner "local-exec" {{
    when = destroy
    command = "rm {marker}"
  }}
}}
'''
(d / 'main.tf').write_text(original)
cli(d, 'init', '-input=false', '-no-color')
cli(d, 'apply', '-auto-approve', '-input=false', '-no-color')
assert marker.exists()
cli(d, 'plan', '-destroy', '-out=queued.tfplan', '-input=false', '-no-color')
(d / 'main.tf').write_text(original.replace('old-binding', 'new-retention-decision').replace(
    '  input =', '  lifecycle { prevent_destroy = true }\n  input ='))
cli(d, 'apply', '-input=false', '-no-color', 'queued.tfplan')
assert not marker.exists()
state = json.loads(cli(d, 'state', 'pull'))
assert not state['resources']
results['checks']['queued_stale_plan'] = {
    'evidence': 'actual OpenTofu 1.13.2, built-in provider and sandbox provisioner',
    'changed_hcl_prevent_destroy_ignored_by_saved_plan': True, 'sandbox_compute_deleted': True,
    'state_resources': len(state['resources']), 'state_serial': state['serial']}

# Output A and state B can be paired by an independently polling consumer.
d = directory('observe')
def config(version):
    return f'''resource "terraform_data" "binding" {{
  input = "{version}"
  triggers_replace = "{version}"
}}
output "binding" {{ value = {{ id = terraform_data.binding.id, value = terraform_data.binding.output }} }}
'''
(d / 'main.tf').write_text(config('v1'))
cli(d, 'init', '-input=false', '-no-color'); cli(d, 'apply', '-auto-approve', '-input=false', '-no-color')
a = json.loads(cli(d, 'output', '-json'))['binding']['value']
sa = json.loads(cli(d, 'state', 'pull'))
(d / 'main.tf').write_text(config('v2'))
cli(d, 'apply', '-auto-approve', '-input=false', '-no-color')
sb = json.loads(cli(d, 'state', 'pull'))
b = sb['outputs']['binding']['value']
assert a['id'] != b['id'] and sa['lineage'] == sb['lineage'] and sa['serial'] < sb['serial']
results['checks']['output_state_race'] = {
    'evidence': 'actual CLI, sequentially scheduled interleaving, no concurrent processes',
    'output_A': a, 'state_B_output': b, 'lineage': sb['lineage'],
    'serial_A': sa['serial'], 'serial_B': sb['serial'], 'identity_mismatch': True}
cli(d, 'destroy', '-auto-approve', '-input=false', '-no-color')
results['status'] = 'passed'
(ROOT / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
(HERE / 'runtime/latest-adversarial.json').write_text(json.dumps({'run': str(ROOT)}) + '\n')
print(json.dumps(results, indent=2))
