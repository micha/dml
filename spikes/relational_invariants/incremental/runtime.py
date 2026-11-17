"""Explicit Linux/Nix review manifests; preparation never imports the native extension."""
import argparse
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = 'incremental'

from .identity import canonical, digest, exact, parse


def source_manifest(worktree):
    rows = []
    entries = subprocess.check_output(['git', '-C', str(worktree), 'ls-files', '-s', '-z'])
    names = {}
    for entry in entries.decode().split('\0'):
        if not entry:
            continue
        meta, name = entry.split('\t', 1)
        mode, _, stage = meta.split()
        if stage != '0' or mode not in ('100644', '100755'):
            raise ValueError('unmerged or unsupported source entry: ' + name)
        names[name] = mode
    # Include this newly introduced executable even before its first Git commit.
    names.setdefault('spikes/relational_invariants/incremental/runtime.py', '100644')
    for name, mode in sorted(names.items()):
        path = worktree / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('source must be a regular file: ' + name)
        raw = path.read_bytes()
        rows.append({'path': name, 'mode': mode, 'sha256': digest(raw), 'size': len(raw)})
    return rows


def store_root(path):
    path = Path(path).resolve()
    if not str(path).startswith('/nix/store/') or len(path.parts) < 4:
        raise ValueError('runtime input must be in the Nix store: ' + str(path))
    return str(Path(*path.parts[:4]))


def runtime_manifest(python, duckdb, core):
    if sys.platform != 'linux':
        raise ValueError('runtime receipts currently require Linux /proc')
    python, duckdb = Path(python).resolve(), Path(duckdb).resolve()
    roots = {store_root(python), store_root(duckdb)}
    dynamic = subprocess.check_output(['readelf', '-d', str(core)], text=True)
    libraries = []
    for line in dynamic.splitlines():
        if '(RUNPATH)' in line or '(RPATH)' in line:
            for path in re.search(r'\[(.*?)\]', line).group(1).split(':'):
                roots.add(store_root(path))
                libraries.append(str(Path(path).resolve()))
    closure = sorted(set(subprocess.check_output(
        ['nix-store', '--query', '--requisites', *sorted(roots)], text=True).splitlines()))
    return {'python': str(python), 'python_sha256': digest(python.read_bytes()),
            'duckdb': str(duckdb), 'duckdb_sha256': digest(duckdb.read_bytes()),
            'closure': closure, 'library_path': ':'.join(sorted(set(libraries))),
            'profile': 'Linux-Nix-minimal-env-I-B-fixed-hash-locale-no-network-v2',
            'machine': platform.machine()}


def review(worktree, core, python, duckdb):
    worktree, core = Path(worktree).resolve(), Path(core).resolve()
    return {'format': 'linux-nix-source-review-v1', 'sources': source_manifest(worktree),
            'core': str(core), 'core_sha256': digest(core.read_bytes()),
            'runtime': runtime_manifest(python, duckdb, core)}


def verify_runtime(runtime):
    exact(runtime, {'python', 'python_sha256', 'duckdb', 'duckdb_sha256', 'closure',
                    'library_path', 'profile', 'machine'})
    if sys.platform != 'linux' or runtime['machine'] != platform.machine():
        raise ValueError('reviewed runtime platform differs')
    for name in ('python', 'duckdb'):
        path = Path(runtime[name])
        root = store_root(path)
        if (str(path.resolve()) != str(path) or root not in runtime['closure']
                or digest(path.read_bytes()) != runtime[name + '_sha256']):
            raise ValueError('reviewed runtime executable differs: ' + name)
    if any(not Path(path).is_dir() or store_root(path) != path for path in runtime['closure']):
        raise ValueError('reviewed Nix closure is unavailable or invalid')
    for path in filter(None, runtime['library_path'].split(':')):
        if store_root(path) not in runtime['closure'] or not Path(path).is_dir():
            raise ValueError('reviewed library path is outside closure')


def read_review(path):
    result = exact(parse(Path(path).read_bytes()),
                   {'format', 'sources', 'core', 'core_sha256', 'runtime'})
    if result['format'] != 'linux-nix-source-review-v1':
        raise ValueError('unsupported review format')
    verify_runtime(result['runtime'])
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('worktree')
    parser.add_argument('output')
    parser.add_argument('--core', required=True)
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--duckdb', default=shutil.which('duckdb'))
    args = parser.parse_args()
    if not args.duckdb:
        parser.error('DuckDB is missing; enter nix develop first')
    result = review(args.worktree, args.core, args.python, args.duckdb)
    with Path(args.output).open('xb') as output:
        output.write(canonical(result))
    print('Review manifest SHA256:', digest(canonical(result)))
