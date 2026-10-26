#!/usr/bin/env python3
"""Real CLI lab: fresh ignored sandbox per run; no external resource targets.
Run: python3 feasibility/opentofu/probe.py [--tofu /absolute/path/to/tofu]
No cleanup traversals: each run is retained under runtime/run-*.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / 'tools'
parser = argparse.ArgumentParser()
parser.add_argument('--tofu', default=str(TOOLS / 'tofu'))
args = parser.parse_args()
TOFU = str(Path(args.tofu).resolve())
RUNTIME = HERE / 'runtime'
RUNTIME.mkdir(exist_ok=True)
RUN = Path(tempfile.mkdtemp(prefix='run-', dir=RUNTIME)).resolve()
# Do not inherit deployment credentials or user OpenTofu CLI configuration.
ENV = {k: os.environ[k] for k in ('PATH', 'SSL_CERT_FILE', 'NIX_SSL_CERT_FILE') if k in os.environ}
ENV.update(HOME=str(RUN / 'home'), XDG_CONFIG_HOME=str(RUN / 'home/config'),
           XDG_DATA_HOME=str(RUN / 'home/data'), TMPDIR=str(RUN / 'tmp'),
           TF_IN_AUTOMATION='1', CHECKPOINT_DISABLE='1', TF_INPUT='0',
           TF_CLI_CONFIG_FILE=str(RUN / 'tofurc'))
for d in ('home', 'tmp', 'cache'): (RUN / d).mkdir()
(RUN / 'tofurc').write_text(f'plugin_cache_dir = "{RUN / "cache"}"\n')
RESULT = {'runtime': str(RUN), 'commands': [], 'probes': {}}
COUNTER = 0
REQ = '''terraform {
  required_providers {
    local = { source = "hashicorp/local", version = "= 2.5.3" }
  }
}
'''

def write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def cli(d, *argv, expect=0):
    global COUNTER
    COUNTER += 1
    cmd = [TOFU, f'-chdir={d}', *argv]
    r = subprocess.run(cmd, env=ENV, text=True, capture_output=True, timeout=120)
    stem = f'{COUNTER:03d}-{argv[0]}'
    write(RUN / 'logs' / (stem + '.stdout'), r.stdout)
    write(RUN / 'logs' / (stem + '.stderr'), r.stderr)
    RESULT['commands'].append({'argv': cmd, 'returncode': r.returncode, 'log': stem})
    assert r.returncode in ([expect] if isinstance(expect, int) else expect), (cmd, r.returncode, r.stdout, r.stderr)
    return r

def directory(name, hcl):
    d = RUN / name
    write(d / 'main.tf', hcl)
    if 'source = "hashicorp/local"' in hcl:
        shutil.copyfile(HERE / 'local-provider.lock.hcl', d / '.terraform.lock.hcl')
    return d

def init(d):
    cli(d, 'init', '-input=false', '-no-color', '-lockfile=readonly')
    cli(d, 'validate', '-no-color')

def plan(d, name, *extra):
    cli(d, 'plan', '-input=false', '-no-color', '-detailed-exitcode', f'-out={name}.tfplan', *extra, expect=[0, 2])
    j = json.loads(cli(d, 'show', '-json', f'{name}.tfplan').stdout)
    write(d / f'{name}.json', json.dumps(j, indent=2))
    return j

def actions(j):
    return {r['address']: r['change']['actions'] for r in j.get('resource_changes', [])}

def changes(j):
    return {r['address']: r['change'] for r in j.get('resource_changes', [])}

def apply(d, name): cli(d, 'apply', '-input=false', '-no-color', f'{name}.tfplan')
def outputs(d): return json.loads(cli(d, 'output', '-json').stdout)
def note(name, data):
    RESULT['probes'][name] = data
    write(RUN / 'results.json', json.dumps(RESULT, indent=2))

RESULT['version'] = json.loads(cli(RUN, 'version', '-json').stdout)

def root(keys=('a','b'), providers=True):
    return REQ + '''provider "local" { alias = "lab" }
resource "terraform_data" "shared" { input = "shared-authority-surrogate" }
module "installation" {
  source = "./material"
  for_each = toset(KEYS)
  directory = "DIRECTORY"
  label = each.key
  shared_id = terraform_data.shared.id
  PROVIDERS
}
output "bindings" { value = { for k, m in module.installation : k => m.binding } }
'''.replace('KEYS', json.dumps(list(keys))).replace('DIRECTORY', str(RUN / 'composition/artifacts')).replace('PROVIDERS', 'providers = { local.bound = local.lab }' if providers else '')

# 1: composition, unknown outputs, stable addresses and deliberate renaming.
d = directory('composition', root())
shutil.copytree(HERE / 'closure', d / 'material')
init(d)
p = plan(d, 'initial')
initial = actions(p)
assert all(a == ['create'] for a in initial.values()) and len(initial) == 5
unknown = p['output_changes']['bindings']['after_unknown']
assert unknown
apply(d, 'initial')
o1 = outputs(d)['bindings']['value']
assert o1['a']['occurrence_id'] != o1['b']['occurrence_id']
p = plan(d, 'repeat'); assert all(a == ['no-op'] for a in actions(p).values())
apply(d, 'repeat'); assert outputs(d)['bindings']['value'] == o1
write(d / 'main.tf', root(('b','a')))
p = plan(d, 'regenerated'); assert all(a == ['no-op'] for a in actions(p).values())
write(d / 'main.tf', root(providers=False))
r = cli(d, 'validate', '-no-color', expect=1)
assert 'provider' in (r.stderr + r.stdout).lower()
write(d / 'main.tf', root(('renamed','b')))
renamed = actions(plan(d, 'renamed'))
assert renamed['module.installation["a"].local_file.artifact'] == ['delete']
assert renamed['module.installation["renamed"].local_file.artifact'] == ['create']
write(d / 'main.tf', root())
note('composition', {'initial_actions': initial, 'unknown_bindings': unknown, 'outputs': o1,
                     'regeneration_actions': actions(p), 'rename_actions': renamed,
                     'missing_alias_error': (r.stderr + r.stdout).strip(),
                     'material_sha256': hashlib.sha256((d / 'material/main.tf').read_bytes()).hexdigest()})

# 2: local_file is not importable; unmanaged pre-existing content is overwritten by create.
adopted = RUN / 'local-adoption/artifact.txt'
hcl = REQ + f'''resource "local_file" "adopted" {{
  filename = "{adopted}"
  content = "configuration-content"
  file_permission = "0600"
}}
output "path" {{ value = local_file.adopted.filename }}
'''
a = directory('local-adoption', hcl)
write(adopted, 'execution-created-content')
init(a)
r = cli(a, 'import', '-input=false', '-no-color', 'local_file.adopted', str(adopted), expect=1)
assert 'import' in (r.stderr + r.stdout).lower()
assert adopted.read_text() == 'execution-created-content'
pj = plan(a, 'after-failed-import'); assert actions(pj)['local_file.adopted'] == ['create']
apply(a, 'after-failed-import'); assert adopted.read_text() == 'configuration-content'
note('local_adoption', {'import_error': (r.stderr + r.stdout).strip(), 'actions': actions(pj),
                         'before': 'execution-created-content', 'after': adopted.read_text(),
                         'warning': 'Applying configuration after unsupported adoption overwrote the artifact.'})
cli(a, 'destroy', '-input=false', '-auto-approve', '-no-color')
assert not adopted.exists()

# 3: CLI vs declarative import using terraform_data, explicitly state-only surrogate.
base = '''resource "terraform_data" "adopted" { input = "resolved-input" }
output "binding" { value = { id = terraform_data.adopted.id, value = terraform_data.adopted.output } }
'''
i = directory('cli-import', base); init(i)
cli(i, 'import', '-input=false', '-no-color', 'terraform_data.adopted', 'execution-42')
pre = outputs(i)
assert pre['binding']['value'] == {'id': 'execution-42', 'value': None}
state = json.loads(cli(i, 'show', '-json').stdout)
assert state['values']['root_module']['resources'][0]['values']['id'] == 'execution-42'
pj = plan(i, 'reconcile'); assert actions(pj)['terraform_data.adopted'] == ['update']
apply(i, 'reconcile'); post = outputs(i)
assert post['binding']['value']['id'] == 'execution-42' and post['binding']['value']['value'] == 'resolved-input'
i2 = directory('declarative-import', base + '''import {
  to = terraform_data.adopted
  id = "execution-43"
}
'''); init(i2)
pj2 = plan(i2, 'import')
change = changes(pj2)['terraform_data.adopted']
assert change['importing']['id'] == 'execution-43'
assert change['actions'] == ['update']
apply(i2, 'import'); post2 = outputs(i2)
assert post2['binding']['value']['id'] == 'execution-43'
pj3 = plan(i2, 'repeat'); assert actions(pj3)['terraform_data.adopted'] == ['no-op']
note('surrogate_import', {'surrogate': True, 'cli_outputs_immediately_after_import': pre,
                          'cli_import_state': state['values']['root_module']['resources'][0]['values'],
                          'cli_reconciliation_actions': actions(pj), 'cli_outputs_after_apply': post,
                          'declarative_change': change, 'declarative_outputs': post2,
                          'repeat_actions': actions(pj3)})
for z in (i,i2): cli(z, 'destroy', '-input=false', '-auto-approve', '-no-color')

# 4: lost configuration with intact state vs genuinely lost state.
l = directory('loss', REQ + f'''resource "local_file" "artifact" {{
  filename = "{RUN / 'loss/artifact.txt'}"
  content = "desired-by-config"
  file_permission = "0600"
}}
resource "terraform_data" "identity" {{ input = "fixed" }}
output "identity" {{ value = terraform_data.identity.id }}
'''); original = (l / 'main.tf').read_text()
init(l); plan(l, 'initial'); apply(l, 'initial'); old_id = outputs(l)['identity']['value']
write(l / 'main.tf', REQ)
missing = actions(plan(l, 'missing-config')); assert all(a == ['delete'] for a in missing.values())
write(l / 'main.tf', original)
regen = actions(plan(l, 'regenerated')); assert all(a == ['no-op'] for a in regen.values())
# Move state aside ONLY within this new lab directory. Do not use state rm on external resources.
(l / 'terraform.tfstate').rename(l / 'lost-state.saved.json')
if (l / 'terraform.tfstate.backup').exists(): (l / 'terraform.tfstate.backup').rename(l / 'lost-backup.saved.json')
write(l / 'artifact.txt', 'execution-result-do-not-overwrite')
lost = actions(plan(l, 'lost-state')); assert all(a == ['create'] for a in lost.values())
apply(l, 'lost-state'); new_id = outputs(l)['identity']['value']
assert old_id != new_id and (l / 'artifact.txt').read_text() == 'desired-by-config'
note('loss', {'missing_configuration_actions': missing, 'regenerated_actions': regen,
              'lost_state_actions': lost, 'old_surrogate_id': old_id, 'new_surrogate_id': new_id,
              'overwritten_content': 'execution-result-do-not-overwrite', 'after': (l / 'artifact.txt').read_text()})
cli(l, 'destroy', '-input=false', '-auto-approve', '-no-color')

# 5: selective removal retains shared resource; destruction events expose actual ordering.
write(d / 'main.tf', root(('b',)))
rem = plan(d, 'remove-a'); acts = actions(rem)
assert acts['module.installation["a"].local_file.artifact'] == ['delete']
assert acts['module.installation["a"].terraform_data.binding'] == ['delete']
assert acts['terraform_data.shared'] == ['no-op']
assert all(v == ['no-op'] for k,v in acts.items() if '["b"]' in k)
cli(d, 'apply', '-input=false', '-json', 'remove-a.tfplan')
assert not (d / 'artifacts/a.txt').exists() and (d / 'artifacts/b.txt').exists()
pj = plan(d, 'destroy-all', '-destroy')
r = cli(d, 'apply', '-input=false', '-json', 'destroy-all.tfplan')
events = [json.loads(line) for line in r.stdout.splitlines()]
completed = [e['hook']['resource']['addr'] for e in events if e.get('type') == 'apply_complete']
assert completed.index('module.installation["b"].local_file.artifact') < completed.index('module.installation["b"].terraform_data.binding') < completed.index('terraform_data.shared')
note('removal', {'remove_one_actions': acts, 'destroy_all_actions': actions(pj), 'destroy_completion_order': completed})

# 6: an alias absent from regenerated config blocks destruction of orphaned resources.
x = directory('provider-cleanup', REQ + f'''provider "local" {{ alias = "cleanup" }}
resource "local_file" "artifact" {{
  provider = local.cleanup
  filename = "{RUN / 'provider-cleanup/artifact.txt'}"
  content = "safe-sandbox-only"
  file_permission = "0600"
}}
'''); init(x); plan(x,'initial'); apply(x,'initial')
write(x / 'main.tf', REQ)
r = cli(x, 'plan', '-destroy', '-input=false', '-no-color', expect=1)
assert 'Provider configuration not present' in r.stderr + r.stdout
write(x / 'main.tf', REQ + 'provider "local" { alias = "cleanup" }\n')
pj = plan(x, 'restored-provider', '-destroy'); assert actions(pj)['local_file.artifact'] == ['delete']
apply(x,'restored-provider')
note('provider_cleanup', {'missing_provider_error': (r.stderr + r.stdout).strip(), 'restored_provider_actions': actions(pj)})

# 7: benign code is deployed, not run by this plan; removing HCL can erase cleanup behavior.
pdir = RUN / 'provisioner'
marker = pdir / 'created.txt'; cleanup = pdir / 'cleanup.txt'
provision = f'''resource "terraform_data" "hook" {{
  count = COUNT
  provisioner "local-exec" {{ command = "printf created > {marker}" }}
  provisioner "local-exec" {{
    when = destroy
    command = "printf cleaned >> {cleanup}"
  }}
}}
'''
s = directory('provisioner', provision.replace('COUNT','1')); init(s)
plan(s,'initial'); assert not marker.exists()
apply(s,'initial'); assert marker.read_text() == 'created'
write(s / 'main.tf','')
removed = actions(plan(s,'removed')); apply(s,'removed'); assert not cleanup.exists()
write(s / 'main.tf',provision.replace('COUNT','1')); plan(s,'recreate'); apply(s,'recreate')
write(s / 'main.tf',provision.replace('COUNT','0')); zero = actions(plan(s,'zero')); apply(s,'zero')
assert cleanup.read_text() == 'cleaned'
note('provisioners', {'marker_absent_after_plan': True, 'marker_after_apply': marker.read_text(),
                     'removed_block_actions': removed, 'removed_block_skipped_cleanup': True,
                     'count_zero_actions': zero, 'count_zero_cleanup': cleanup.read_text()})

locks = {}
for lock in RUN.rglob('.terraform.lock.hcl'):
    locks[str(lock.relative_to(RUN))] = lock.read_text()
RESULT['provider_locks'] = locks
RESULT['status'] = 'passed'
write(RUN / 'results.json', json.dumps(RESULT, indent=2))
# Condensed, non-sensitive facts tracked separately from raw logs/state.
condensed = {k:v for k,v in RESULT.items() if k not in ('commands','provider_locks')}
condensed['command_count'] = len(RESULT['commands'])
condensed['provider'] = 'registry.opentofu.org/hashicorp/local 2.5.3'
write(HERE / 'evidence.json', json.dumps(condensed, indent=2))
write(RUNTIME / 'latest.json', json.dumps({'runtime':str(RUN)}, indent=2))
print(json.dumps({'status':RESULT['status'],'runtime':str(RUN),'probes':list(RESULT['probes'])},indent=2))
