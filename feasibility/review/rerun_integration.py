#!/usr/bin/env python3
"""Rerun inspected integration glue from copies confined to fresh review runtime."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
(HERE / 'runtime').mkdir(exist_ok=True)
ROOT = Path(tempfile.mkdtemp(prefix='i-', dir=HERE / 'runtime'))
files = ['integration/scenario.py', 'history/model.py', 'retention/model.py',
         'opentofu/closure/main.tf', 'opentofu/local-provider.lock.hcl']
hashes = {}
scenario_source = (BASE / 'integration/scenario.py').read_text()
for name in files:
    src = BASE / name
    # Short copy path only; scenario enforces its own runtime ownership.
    target_name = 'i/scenario.py' if name == 'integration/scenario.py' else name
    if name.startswith('opentofu/') and "models / 'o/closure'" in scenario_source:
        target_name = 'o/' + name.removeprefix('opentofu/')
    dst = ROOT / target_name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    hashes[name] = hashlib.sha256(src.read_bytes()).hexdigest()
(ROOT / 'i/runtime').mkdir()
tofu = BASE / 'tools/tofu'
assert hashlib.sha256(tofu.read_bytes()).hexdigest() == '949061cbb3c3d4558928ca9a459a5052b8c5e5545d17656f33316d2e3bc335f2'
cmd = [sys.executable, '-B', str(ROOT / 'i/scenario.py'), '--sandbox', str(ROOT / 'i/runtime/c'),
       '--models', str(ROOT), '--tofu', str(tofu)]
env = {k: os.environ[k] for k in ('PATH', 'SSL_CERT_FILE', 'NIX_SSL_CERT_FILE') if k in os.environ}
env.update(HOME=str(ROOT), PYTHONDONTWRITEBYTECODE='1')
p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
(ROOT / 'stdout').write_text(p.stdout)
(ROOT / 'stderr').write_text(p.stderr)
result = {'argv': cmd, 'returncode': p.returncode, 'source_sha256': hashes}
if p.returncode == 0:
    result['scenario'] = json.loads((ROOT / 'i/runtime/c/scenario.json').read_text())
(ROOT / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
(HERE / 'runtime/latest-integration.json').write_text(json.dumps({'run': str(ROOT)}) + '\n')
print(json.dumps(result, indent=2))
assert p.returncode == 0, p.stderr
