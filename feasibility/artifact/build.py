#!/usr/bin/env python3
"""Build pinned modules with scoped caches and package a filesystem mirror."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

BASE = Path(__file__).resolve().parent
GO = Path('/nix/store/h3rc4y3szd0391wryw9hslrijdvni030-go-1.26.8/bin/go')
TOFU = BASE.parent / 'tools/tofu'
TOFU_SHA = '949061cbb3c3d4558928ca9a459a5052b8c5e5545d17656f33316d2e3bc335f2'
SOURCE = 'dml.invalid/feasibility/immutable'
VERSION = '0.1.0'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    assert sha(TOFU) == TOFU_SHA, 'unexpected shared tofu executable'
    assert subprocess.check_output([GO, 'version'], text=True).strip() == 'go version go1.26.8 linux/amd64'
    runtime = BASE / 'runtime'
    runtime.mkdir(exist_ok=True)
    # Exclude nested module caches from the parent module package traversal.
    (runtime / 'go.mod').write_text('module example.invalid/runtime-cache\n\ngo 1.26.8\n')
    for name in ('tmp', 'home', 'build-cache', 'gopath', 'modules'):
        (runtime / name).mkdir(exist_ok=True)
    env = {'PATH':os.environ['PATH'], 'HOME':str(runtime / 'home'),
           'GOTOOLCHAIN':'local', 'GOPATH':str(runtime / 'gopath'),
           'GOMODCACHE':str(runtime / 'modules'), 'GOCACHE':str(runtime / 'build-cache'),
           'GOTMPDIR':str(runtime / 'tmp')}
    binary = BASE / 'tools' / f'terraform-provider-immutable_v{VERSION}'
    binary.parent.mkdir(exist_ok=True)
    with (runtime / 'rebuild.log').open('w') as log:
        for args in (['mod', 'verify'], ['build', '-trimpath', '-o', str(binary)]):
            subprocess.run([GO, *args], cwd=BASE, env=env, stdout=log, stderr=log, check=True, timeout=240)
    mirror = BASE / 'tools/mirror' / SOURCE / VERSION / 'linux_amd64'
    mirror.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binary, mirror / binary.name)
    config = BASE / 'tools/provider.tfrc'
    config.write_text('provider_installation {\n filesystem_mirror {\n  path = '+json.dumps(str(BASE / 'tools/mirror'))+'\n  include = ["'+SOURCE+'"]\n }\n}\n')
    ready = {'tofu':str(TOFU), 'compiler':str(GO), 'provider':str(binary),
             'mirror':str(BASE / 'tools/mirror'), 'cli_config':str(config),
             'source':SOURCE, 'version':VERSION, 'sdk':'v2.38.2',
             'tofu_version':'1.13.2', 'compiler_version':'1.26.8',
             'checksums':{'tofu':sha(TOFU), 'compiler':sha(GO), 'provider':sha(binary),
                          'go.mod':sha(BASE / 'go.mod'), 'go.sum':sha(BASE / 'go.sum')}}
    temp = BASE / 'ready.json.tmp'
    temp.write_text(json.dumps(ready, indent=2)+'\n')
    temp.replace(BASE / 'ready.json')
    print(json.dumps(ready, indent=2))

if __name__ == '__main__':
    main()
