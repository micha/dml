#!/usr/bin/env python3
"""Review copies only: all writes below a newly allocated review/runtime directory."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
(HERE / 'runtime').mkdir(exist_ok=True)
RUN = Path(tempfile.mkdtemp(prefix='r-', dir=HERE / 'runtime'))
TOFU = STUDY / 'tools/tofu'
assert hashlib.sha256(TOFU.read_bytes()).hexdigest() == '949061cbb3c3d4558928ca9a459a5052b8c5e5545d17656f33316d2e3bc335f2'
ENV = {'PATH': os.environ['PATH'], 'PYTHONDONTWRITEBYTECODE': '1', 'HOME': str(RUN)}
for k in ('SSL_CERT_FILE', 'NIX_SSL_CERT_FILE'):
    if k in os.environ:
        ENV[k] = os.environ[k]
results = {'run': str(RUN), 'python': sys.version, 'commands': [], 'input_sha256': {}}

def copy(group, names):
    # Shorten copy names, not test semantics: Go plugin Unix sockets have path limits.
    dest = RUN / {'history': 'h', 'retention': 'r', 'opentofu': 'o', 'adversarial': 'a'}[group]
    dest.mkdir()
    for name in names:
        source = STUDY / group / name
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        results['input_sha256'][group + '/' + name] = hashlib.sha256(source.read_bytes()).hexdigest()
    return dest

def run(cwd, args):
    p = subprocess.run(args, cwd=cwd, env=ENV, capture_output=True, text=True, timeout=600)
    stem = str(len(results['commands']))
    (RUN / (stem + '.stdout')).write_text(p.stdout)
    (RUN / (stem + '.stderr')).write_text(p.stderr)
    row = {'cwd': str(cwd), 'argv': args, 'returncode': p.returncode, 'log': stem}
    count = re.search(r'Ran (\d+) tests', p.stderr)
    if count:
        row['tests_run'] = int(count.group(1))
    results['commands'].append(row)
    assert p.returncode == 0, (args, p.stderr[-3000:])

try:
    h = copy('history', ['model.py', 'test_model.py', 'run_scenarios.py', 'scenario-results.json'])
    run(h, [sys.executable, '-B', '-m', 'unittest', '-v'])
    r = copy('retention', ['model.py', 'test_model.py'])
    run(r, [sys.executable, '-B', 'test_model.py'])
    o = copy('opentofu', ['probe.py', 'local-provider.lock.hcl', 'closure/main.tf'])
    # Disclosed harness-only adaptation after reproduced Unix socket bind failure.
    # Provider versions, HCL, dependencies and assertions remain unchanged.
    (o / 't').mkdir()
    probe = o / 'probe.py'
    text = probe.read_text()
    assert text.count("TMPDIR=str(RUN / 'tmp')") == 1
    probe.write_text(text.replace("TMPDIR=str(RUN / 'tmp')", "TMPDIR=str(HERE / 't')"))
    results['adaptation'] = {'file': 'probe.py', 'change': 'sandbox TMPDIR shortened to copy-local t',
                             'sha256': hashlib.sha256(probe.read_bytes()).hexdigest()}
    run(o, [sys.executable, '-B', 'probe.py', '--tofu', str(TOFU)])
    a = copy('adversarial', ['experiments.py', 'runtime/sources/aws_s3_object.go'])
    (RUN / 'tools').mkdir()
    shutil.copyfile(STUDY / 'tools/ready.json', RUN / 'tools/ready.json')
    run(a, [sys.executable, '-B', 'experiments.py'])
    results['counts'] = {'history_tests': results['commands'][0]['tests_run'],
                         'history_scenarios': len(json.loads((h / 'scenario-results.json').read_text())['scenarios']),
                         'retention_tests': results['commands'][1]['tests_run'], 'lab_probes': 7,
                         'lab_commands': json.loads((o / 'evidence.json').read_text())['command_count'],
                         'adversarial_cases': len(json.loads((a / 'runtime/results.json').read_text())['experiments'])}
    results['status'] = 'passed'
finally:
    (RUN / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    (HERE / 'runtime/latest-rerun.json').write_text(json.dumps({'run': str(RUN)}) + '\n')
    print(json.dumps(results, indent=2))
