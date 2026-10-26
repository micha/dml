#!/usr/bin/env python3
"""Provision only the official, pinned Linux amd64 CLI into ignored ../tools.
No Nix profile, OS installation, retry loop, credentials, or cloud API access.
"""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import urllib.request
import zipfile

VERSION = '1.13.2'
SHA256 = '723bebb0df8411daff1e5fc3862e28ff5581fe5634087f4c29a9aa41d78208b5'
TOOLS = Path(__file__).resolve().parent.parent / 'tools'
assert platform.system() == 'Linux' and platform.machine() == 'x86_64'
TOOLS.mkdir(exist_ok=True)
NAME = f'tofu_{VERSION}_linux_amd64.zip'
BASE = f'https://github.com/opentofu/opentofu/releases/download/v{VERSION}'

def fetch(name):
    path = TOOLS / name
    if not path.exists():
        with urllib.request.urlopen(f'{BASE}/{name}', timeout=120) as response:
            data = response.read(80 * 1024 * 1024 + 1)
        assert len(data) <= 80 * 1024 * 1024, 'download exceeds bound'
        temporary = path.with_name(path.name + '.tmp')
        temporary.write_bytes(data)
        temporary.replace(path)
    return path

archive = fetch(NAME)
sums = fetch(f'tofu_{VERSION}_SHA256SUMS')
published = next(line.split()[0] for line in sums.read_text().splitlines() if line.split()[-1] == NAME)
actual = hashlib.sha256(archive.read_bytes()).hexdigest()
assert published == SHA256 == actual, 'release checksum mismatch'
# Extract only the expected executable, not arbitrary paths from the archive.
with zipfile.ZipFile(archive) as z:
    binary = z.read('tofu')
exe = TOOLS / 'tofu'
exe.write_bytes(binary)
exe.chmod(0o755)
version = json.loads(subprocess.check_output([str(exe), 'version', '-json'], text=True))
assert version['terraform_version'] == VERSION
ready = {'executable':str(exe), 'version':VERSION, 'sha256':actual,
         'source':f'official release v{VERSION}'}
tmp = TOOLS / 'ready.json.tmp'
tmp.write_text(json.dumps(ready,indent=2)+'\n')
tmp.replace(TOOLS / 'ready.json')
print(json.dumps(ready, indent=2))
