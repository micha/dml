#!/usr/bin/env python3
"""Real sandbox file installation -> history model -> simulated adoption/retention.
Only a NEW directory beneath integration/runtime/ is accepted. No cloud APIs.
Called by run-all with its byte-identical model/fixture copies.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sandbox', type=Path, required=True)
    p.add_argument('--models', type=Path, required=True)
    p.add_argument('--tofu', type=Path, required=True)
    args = p.parse_args()
    sandbox = args.sandbox.resolve()
    if not sandbox.is_relative_to((HERE / 'runtime').resolve()) or sandbox.exists():
        raise SystemExit('Sandbox must be a new directory beneath integration/runtime/')
    sandbox.mkdir(parents=True)
    models = args.models.resolve()
    h = load('cross_history', models / 'history/model.py')
    r = load('cross_retention', models / 'retention/model.py')
    live = sandbox / 'live'
    live.mkdir()
    (sandbox / 'home').mkdir()
    (sandbox / 'tmp').mkdir()
    (sandbox / 'tofurc').write_text('')
    env = {k: os.environ[k] for k in ('PATH', 'SSL_CERT_FILE', 'NIX_SSL_CERT_FILE') if k in os.environ}
    env.update(HOME=str(sandbox / 'home'), TMPDIR=str(sandbox / 'tmp'),
               TF_CLI_CONFIG_FILE=str(sandbox / 'tofurc'), TF_IN_AUTOMATION='1', CHECKPOINT_DISABLE='1')
    commands = []
    def cli(*argv, expect=(0,)):
        cmd = [str(args.tofu.resolve()), f'-chdir={live}', *argv]
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)
        stem = f'{len(commands):02}-{argv[0]}'
        (sandbox / (stem + '.stdout')).write_text(proc.stdout)
        (sandbox / (stem + '.stderr')).write_text(proc.stderr)
        commands.append({'argv': cmd, 'returncode': proc.returncode})
        assert proc.returncode in expect, (cmd, proc.stdout, proc.stderr)
        return proc.stdout

    shutil.copytree(models / 'o/closure', live / 'material')
    shutil.copyfile(models / 'o/local-provider.lock.hcl', live / '.terraform.lock.hcl')
    providers = '''terraform {
  required_providers {
    local = { source = "hashicorp/local", version = "= 2.5.3" }
  }
}
provider "local" { alias = "lab" }
'''
    (live / 'main.tf').write_text(providers + f'''module "compute" {{
  source = "./material"
  directory = "{sandbox / 'installed'}"
  label = "worker"
  shared_id = "external-authority-surrogate"
  providers = {{ local.bound = local.lab }}
}}
output "binding" {{ value = module.compute.binding }}
''')
    cli('init', '-input=false', '-no-color', '-lockfile=readonly')
    cli('apply', '-input=false', '-auto-approve', '-no-color')
    exported = json.loads(cli('output', '-json'))['binding']['value']
    descriptor = Path(exported['filename'])
    assert descriptor.is_relative_to(sandbox) and descriptor.read_text() == 'worker'
    assert hashlib.sha256(descriptor.read_bytes()).hexdigest() == exported['sha256']
    store = h.Store(sandbox / 'dag')
    repo = h.Repo(store, sandbox / 'heads.json')
    ids = h.IDs('integration')
    # Local arithmetic is genuinely executed. The installed file is a descriptor,
    # not provisioned compute capacity, and the execution adapter is modeled glue.
    code = 'import json,sys; print(sum(json.loads(sys.argv[1])))'
    impl = store.put('artifact', {'python_code_sha256': hashlib.sha256(code.encode()).hexdigest()})
    adapter = store.put('artifact', {'mode': 'bounded local subprocess; informative integration glue'})
    description = store.put('installation-description', {'execution_config': {'python': sys.version.split()[0]}},
        {'implementation': impl, 'adapter': adapter, 'hcl': store.put('hcl', (live / 'main.tf').read_text())})
    installed, closure = h.install(store, ids, description, exported, {'observed_by': 'real OpenTofu output -json'})
    bound = h.binding(store, 'intent:sum', closure, store.put('datum', [4, 7]))
    repo.append('main', [h.event(store, ids, installed, 'installation-observed')])
    attempts, requests, results = [], [], []
    def execute():
        q = h.request(store, ids, bound)
        a = h.attempt(store, ids, q)
        repo.append('main', [h.event(store, ids, a, 'registered')])
        proc = subprocess.run([sys.executable, '-c', code, '[4,7]'], env=env, text=True, capture_output=True, timeout=10)
        assert proc.returncode == 0
        value = json.loads(proc.stdout)
        assert value == 11
        result = store.put('datum', value)
        repo.append('main', [h.event(store, ids, a, 'done',
            {'status': 'done', 'computation': 'success', 'cleanup': 'no temporary compute allocated'}, {'result': result})])
        attempts.append(a); requests.append(q); results.append(result)
        return a, result
    a1, result = execute()
    repo.append('main', selections={bound: a1})
    q2 = h.request(store, ids, bound)
    requests.append(q2)
    assert h.choose(repo, repo.heads['main'], bound, True) == a1
    repo.append('main', [h.event(store, ids, q2, 'reuse', refs={'actual_attempt': a1, 'result': result})])
    a2, same_result = execute()
    assert len(set(requests)) == 3 and len(set(attempts)) == 2 and result == same_result
    assert h.choose(repo, repo.heads['main'], bound, True) == a1  # Fresh is not adoption.
    research_before_retirement = repo.heads['main']
    artifact = sandbox / 'execution-result.txt'
    artifact.write_text('11\n')

    # Explicit mapping seam: exported resource-set identities into the retention
    # model. Fake .object files stand in for adoption/state/disposal obligations.
    manager = r.Manager(sandbox / 'retention-simulation')
    manager.add('bucket', 'external')
    manager.add('identity', 'provisioned')
    manager.add('compute', 'provisioned')
    manager.add('result', 'adopted', deps={'bucket'}, container='bucket', cleaner='identity', registered=False)
    manager.start_adoption('result', 'identity')
    manager.publish('A', 'a0', datums=['compute', 'result'])
    manager.publish('A', 'a1', parents=['a0'], datums=[])
    manager.publish('B', 'b0', datums=['compute', 'result'])
    assert not manager.plan().victims
    assert 'compute' in manager.history('A')
    mapping = {'compute': exported, 'result': {'local_copy': str(artifact), 'dag_result': result},
               'A:a0': {'history_commit': research_before_retirement}}
    store_mapping = store.put('retention-export', {'mapping': mapping, 'simulation': True})
    repo.append('main', [h.event(store, ids, installed, 'pending-adoption', refs={'manifest': store_mapping})])
    manager.excise({'compute'}, {'A', 'B'})
    manager.reserve(manager.plan())
    assert manager.reserved == {'compute'}
    # Apply real removal only after the model's authorized reservation. This is
    # sequential demonstration, NOT a production approval/fencing protocol.
    (live / 'main.tf').write_text(providers)
    cli('plan', '-input=false', '-no-color', '-detailed-exitcode', '-out=retire.tfplan', expect=(2,))
    planned = json.loads(cli('show', '-json', 'retire.tfplan'))
    actions = {v['address']: v['change']['actions'] for v in planned['resource_changes']}
    assert len(actions) == 2 and all(action == ['delete'] for action in actions.values())
    cli('apply', '-input=false', '-no-color', 'retire.tfplan')
    assert not descriptor.exists()
    manager.destroy_reserved()
    resource = store.get(closure)['refs']['resource']
    repo.append('main', [h.event(store, ids, resource, 'resource-retired',
        {'real_descriptor_absent': True, 'compute_capacity_provisioned': False, 'authorized_model_consumers': ['A', 'B']})])
    assert result in store.walk(repo.heads['main'])
    assert h.choose(repo, repo.heads['main'], bound, True) == a1 and manager.available('result')
    assert not manager.available('compute')
    manager.move_head('A', 'main', None)
    assert manager.history('B') == {'compute', 'result'} and not manager.plan().victims
    manager.move_head('B', 'main', None)
    assert not manager.plan().victims  # Pending adoption protects identity/target.
    manager.reconcile('result', fail=True)
    assert manager.obligations['result'].failures == 1 and artifact.exists()
    manager.reconcile('result')  # Simulated external registration/deletion.
    artifact.unlink()  # Actual controlled-copy cleanup, not provider adoption.
    manager.reserve(manager.plan())
    manager.destroy_reserved()
    manager.assert_safety()
    assert manager.deleted == {'compute', 'result', 'identity'}
    assert (manager.sandbox / 'bucket.object').exists()
    # Research history still contains scalar 11; GC above concerns exported
    # resource roots, NOT physical erasure of the history DAG.
    summary = {'status': 'passed', 'installation_outputs': exported,
        'requests': len(set(requests)), 'attempts': len(set(attempts)), 'result_roots': len(set(results)),
        'selected_attempt_unchanged_by_fresh': True, 'reuse_after_compute_retirement': True,
        'history_result_still_reachable': result in store.walk(repo.heads['main']),
        'real_local_file_destroyed': not descriptor.exists(), 'retirement_plan_actions': actions,
        'adoption': 'simulated pending obligation -> registration -> failed cleanup -> confirmed absence',
        'disposal_failure_count': 1, 'model_deleted': sorted(manager.deleted),
        'controlled_result_copy_deleted': not artifact.exists(), 'external_bucket_simulation_survives': True,
        'mapping': mapping, 'tofu_commands': len(commands),
        'boundaries': ['OpenTofu provisions a real file plus state-only binding surrogate, not compute capacity.',
            'Retention roots are explicit exports into a separate model, not inferred from DML nodes.',
            'Adoption, repository fencing and external disposal are simulations.',
            'Local arithmetic and controlled-file removal are real; no AWS, DML C or erasure claim.']}
    (sandbox / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    (sandbox / 'scenario.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
