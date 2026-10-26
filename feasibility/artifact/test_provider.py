#!/usr/bin/env python3
"""Real OpenTofu CLI acceptance probes; no cloud, no surrogate resource."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

BASE = Path(__file__).resolve().parent
SECRET = b'SYNTHETIC-ONLY-CONTENT-not-a-real-secret\n'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def identity(path):
    s = path.stat()
    return f'{s.st_dev}:{s.st_ino}'

def main():
    ready = json.loads((BASE / 'ready.json').read_text())
    assert digest(Path(ready['provider'])) == ready['checksums']['provider']
    runtime = BASE / 'runtime'
    run = next((runtime / f'r{i}' for i in range(1, 9) if not (runtime / f'r{i}').exists()), None)
    assert run, 'eight retained runs reached; inspect/archive manually'
    run.mkdir()
    temp = runtime / 't'
    temp.mkdir(exist_ok=True)
    env = {'PATH':os.environ['PATH'], 'HOME':str(runtime / 'home'),
           'TF_CLI_CONFIG_FILE':ready['cli_config'], 'TF_IN_AUTOMATION':'1',
           'CHECKPOINT_DISABLE':'1', 'TMPDIR':str(temp)}
    events = []
    counter = 0

    def cli(cwd, *args, expected=0, contains=None):
        nonlocal counter
        counter += 1
        p = subprocess.run([ready['tofu'], *args], cwd=cwd, env=env,
                           text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)
        logfile = run / f'{counter:03}-{args[0]}.log'
        logfile.write_text(p.stdout)
        events.append({'command':[ready['tofu'], *args], 'cwd':str(cwd), 'returncode':p.returncode,
                       'log':logfile.name})
        (run / 'commands.json').write_text(json.dumps(events, indent=2)+'\n')
        assert (p.returncode == expected if expected >= 0 else p.returncode != 0), p.stdout
        if contains:
            assert contains in p.stdout, p.stdout
        return p

    def fixture(name):
        work = run / name
        work.mkdir()
        root = work / 'files'
        root.mkdir()
        file = root / 'result'
        file.write_bytes(SECRET)
        receipt = {'path':'result', 'sha256':digest(file), 'owner':'synthetic-project',
                   'resource_id':name, 'physical':identity(file), 'root_identity':identity(root)}
        (work / 'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
        config = {
            'terraform':{'required_providers':{'immutable':{'source':ready['source'], 'version':ready['version']}}},
            'provider':{'immutable':{'root':str(root)}},
            'resource':{'immutable_artifact':{'result':{k:receipt[k] for k in ('path','sha256','owner','resource_id')}}},
            'output':{'manifest':{'value':{k:'${immutable_artifact.result.'+k+'}' for k in receipt}}}}
        def save():
            (work / 'main.tf.json').write_text(json.dumps(config, indent=2)+'\n')
        save()
        cli(work, 'init', '-input=false', '-no-color')
        return work, root, file, receipt, config, save

    def adopt(work, receipt, expected=0, contains=None):
        cli(work, 'import', '-input=false', '-no-color', 'immutable_artifact.result',
            json.dumps(receipt, separators=(',', ':')), expected=expected, contains=contains)

    checks = []
    w, root, f, r, cfg, save = fixture('life')
    before = (digest(f), identity(f), f.stat().st_mtime_ns)
    adopt(w, r)
    cli(w, 'apply', '-auto-approve', '-input=false', '-no-color')
    cli(w, 'plan', '-detailed-exitcode', '-input=false', '-no-color')
    cli(w, 'apply', '-auto-approve', '-input=false', '-no-color', contains='No changes')
    checks.append('actual CLI import + no-op plan/apply')
    manifest = json.loads(cli(w, 'output', '-json').stdout)['manifest']['value']
    assert manifest == r
    assert SECRET.decode().strip() not in json.dumps(manifest)
    (run / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    fields = cfg['resource']['immutable_artifact']['result']
    fields['metadata'] = 'retention-label-only'
    save()
    cli(w, 'plan', '-detailed-exitcode', '-input=false', '-no-color', expected=2)
    cli(w, 'apply', '-auto-approve', '-input=false', '-no-color', contains='1 changed')
    assert (digest(f), identity(f), f.stat().st_mtime_ns) == before
    checks.append('metadata update preserves bytes/inode/mtime; manifest excludes bytes')
    for key, new in [('path','other'), ('sha256','0'*64), ('owner','other-owner'), ('resource_id','other-id')]:
        old = fields[key]
        fields[key] = new
        save()
        cli(w, 'plan', '-input=false', '-no-color', expected=-1, contains='immutable field')
        fields[key] = old
    save()
    checks.append('configured path/digest/owner/id mutations rejected at plan')
    f.write_bytes(b'DELIBERATE-TAMPER\n')
    cli(w, 'plan', '-input=false', '-no-color', expected=-1, contains='mismatch')
    cli(w, 'destroy', '-auto-approve', '-refresh=false', '-input=false', '-no-color', expected=-1, contains='mismatch')
    assert f.read_bytes() == b'DELIBERATE-TAMPER\n'
    checks.append('external content mismatch blocks refresh and unrefreshed delete')
    f.write_bytes(SECRET)
    # Lose manager state, preserving a copy as evidence. Apply cannot recreate content.
    for name in ('terraform.tfstate', 'terraform.tfstate.backup'):
        p = w / name
        if p.exists():
            p.rename(w / ('lost-'+name))
    cli(w, 'plan', '-detailed-exitcode', '-input=false', '-no-color', expected=2)
    cli(w, 'apply', '-auto-approve', '-input=false', '-no-color', expected=-1, contains='adoption-only')
    assert digest(f) == r['sha256'] and identity(f) == r['physical']
    adopt(w, r)
    cli(w, 'apply', '-auto-approve', '-input=false', '-no-color')
    cli(w, 'plan', '-detailed-exitcode', '-input=false', '-no-color')
    checks.append('state loss fails creation safely; durable receipt permits re-import')
    cli(w, 'destroy', '-auto-approve', '-input=false', '-no-color')
    assert not f.exists()
    adopt(w, r, expected=-1)
    assert not f.exists()
    checks.append('retirement unlinks matching file; missing re-import cannot create')

    w, root, f, r, cfg, save = fixture('swap')
    adopt(w, r)
    cli(w, 'plan', '-destroy', '-input=false', '-no-color', '-out=destroy.plan')
    replacement = root / 'replacement'
    replacement.write_bytes(SECRET)
    replacement.replace(f)
    assert identity(f) != r['physical']
    cli(w, 'apply', '-input=false', '-no-color', 'destroy.plan', expected=-1, contains='mismatch')
    assert f.read_bytes() == SECRET
    checks.append('saved destroy plan refuses same-byte different-inode replacement')

    w, root, f, r, cfg, save = fixture('bounds')
    outside = w / 'outside'
    outside.write_bytes(SECRET)
    (root / 'link').symlink_to(outside)
    (root / 'parent').symlink_to(w, target_is_directory=True)
    os.link(outside, root / 'hardlink')
    for path in ('../outside', str(outside), 'link', 'parent/outside', 'hardlink', 'missing'):
        bad = dict(r, path=path, physical=identity(outside))
        adopt(w, bad, expected=-1)
        assert outside.read_bytes() == SECRET and f.read_bytes() == SECRET
    checks.append('CLI import rejects escape, absolute path, target/parent symlink, hardlink, missing file')
    bad = dict(r, sha256='0'*64)
    adopt(w, bad, expected=-1, contains='mismatch')
    # Root symlink is also rejected, even when resolving into a legitimate sandbox.
    (w / 'rootlink').symlink_to(root, target_is_directory=True)
    cfg['provider']['immutable']['root'] = str(w / 'rootlink')
    save()
    adopt(w, r, expected=-1)
    checks.append('wrong import digest and symlink-configured root rejected')

    w, root, f, r, cfg, save = fixture('root-swap')
    adopt(w, r)
    cli(w, 'plan', '-destroy', '-input=false', '-no-color', '-out=destroy.plan')
    root.rename(w / 'files-old')
    root.mkdir()
    f.write_bytes(SECRET)
    cli(w, 'apply', '-input=false', '-no-color', 'destroy.plan', expected=-1, contains='root mismatch')
    assert f.read_bytes() == SECRET and (w / 'files-old/result').read_bytes() == SECRET
    checks.append('saved destroy plan refuses replaced sandbox root')

    w, root, f, r, cfg, save = fixture('declarative')
    cfg['import'] = [{'to':'immutable_artifact.result', 'id':json.dumps(r, separators=(',', ':'))}]
    cfg['resource']['immutable_artifact']['result']['metadata'] = 'import-label'
    save()
    original = (digest(f), identity(f), f.stat().st_mtime_ns)
    cli(w, 'plan', '-input=false', '-no-color', '-out=import.plan')
    plan = json.loads(cli(w, 'show', '-json', 'import.plan').stdout)
    assert plan['resource_changes'][0]['change']['importing']['id'] == cfg['import'][0]['id']
    cli(w, 'apply', '-input=false', '-no-color', 'import.plan')
    cli(w, 'plan', '-detailed-exitcode', '-input=false', '-no-color')
    assert (digest(f), identity(f), f.stat().st_mtime_ns) == original
    checks.append('declarative import plus metadata reconciliation preserves bytes; subsequent no-op')

    w, root, f, r, cfg, save = fixture('crash')
    adopt(w, r)
    cli(w, 'apply', '-auto-approve', '-input=false', '-no-color')
    cli(w, 'plan', '-destroy', '-input=false', '-no-color', '-out=destroy.plan')
    log = run / 'crash-process.log'
    with log.open('w') as stream:
        p = subprocess.Popen([ready['tofu'], 'apply', '-input=false', '-no-color', 'destroy.plan'],
                             cwd=w, env=dict(env, DML_ARTIFACT_TEST_PAUSE_AFTER_UNLINK='1'),
                             stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.monotonic() + 8
        while f.exists() and p.poll() is None and time.monotonic() < deadline:
            time.sleep(.02)
        assert not f.exists(), 'did not observe unlink before crash'
        os.killpg(p.pid, signal.SIGKILL)
        p.wait(timeout=5)
    events.append({'command':[ready['tofu'], 'apply', '-input=false', '-no-color', 'destroy.plan'],
                   'cwd':str(w), 'returncode':p.returncode, 'log':log.name,
                   'fault':'SIGKILL process group after observed unlink'})
    (run / 'commands.json').write_text(json.dumps(events, indent=2)+'\n')
    assert json.loads((w / 'terraform.tfstate').read_text())['resources'], 'state unexpectedly acknowledged'
    cli(w, 'destroy', '-auto-approve', '-refresh=false', '-input=false', '-no-color')
    assert not json.loads((w / 'terraform.tfstate').read_text())['resources']
    checks.append('actual SIGKILL after unlink/before acknowledgement; old state survives, retry safely succeeds')

    # Deliberately falsify replacement safety: provider delete cannot distinguish
    # an explicit retirement from a backend-forced replacement.
    w, root, f, r, cfg, save = fixture('replace')
    adopt(w, r)
    cli(w, 'apply', '-auto-approve', '-input=false', '-no-color',
        '-replace=immutable_artifact.result', expected=-1, contains='adoption-only')
    assert not f.exists(), 'expected documented replacement counterexample'
    checks.append('COUNTEREXAMPLE: -replace deletes valid artifact then creation fails')

    result = {'status':'completed', 'run':str(run), 'cli_invocations':len(events),
              'checks':checks, 'counterexamples':['forced replacement deletes before adoption-only create fails'],
              'ready':ready}
    (run / 'results.json').write_text(json.dumps(result, indent=2)+'\n')
    (BASE / 'test-results.json').write_text(json.dumps({k:v for k,v in result.items() if k != 'ready'}, indent=2)+'\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
