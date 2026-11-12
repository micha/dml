"""Owned fixed E/P/C actor, exact finite pinned CLI allowance and source receipts."""
from pathlib import Path
import importlib.util
import os
import socket
import subprocess
import sys


def execute(job):
    root = Path(job['pin_root'])
    sys.path[:0] = [str(root / 'base/controller/code'), str(root / 'code'), str(root / 'common')]
    from incremental.identity import canonical, digest, parse
    from incremental.stages import load_dml
    from per_exercise.capsules import admit
    pins = parse((root / 'pins.json').read_bytes())
    stage, out = job['stage'], Path(job['output'])
    package = (root / 'base' / ('candidate-' + job['candidate']) / 'python/daggerml/daggerml'
               if stage == 'E' else root / 'base/controller/daggerml')
    dml = load_dml(package)
    original = subprocess.Popen
    children = []
    cap = 1 if stage == 'C' else 0

    def cli(command, *args, **kwargs):
        if (type(command) is not list or command[0] not in ('duckdb', pins['runtime']['duckdb'])
                or len(children) >= cap):
            raise ValueError('actor child outside exact pinned allowance')
        command = [pins['runtime']['duckdb'], *command[1:]]
        child = original(command, *args, **kwargs)
        children.append((child, command))
        return child

    def forbidden(*args, **kwargs):
        raise ValueError('stage cannot activate network/native store in C')

    subprocess.Popen = cli
    socket.socket.connect = forbidden
    socket.create_connection = forbidden
    source = root / 'code/per_exercise/evidence.py'
    if stage == 'E':
        from per_exercise.evidence import produce
        produce(dml, job['repository'], job['spec'], job['producer'], out)
    else:
        source = root / 'payloads' / job['variant'] / ('project.py' if stage == 'P' else 'predicate.py')
        spec = importlib.util.spec_from_file_location('_per_exercise_payload', source)
        payload = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(payload)
        if stage == 'P':
            payload.project(dml, job['upstream'], job['repository'], out, job['spec'])
        elif stage == 'C':
            pool = job['pool']
            admit(pool['directory'], pool['identity'], pool['inputs'], pool['digest'])
            dml.Repository = forbidden
            agreement = payload.check(job['upstream'], Path(pool['directory']) / 'pool.duckdb', out, job['spec'])
        else:
            raise ValueError('unknown stage')
    if len(children) != cap or any(p.returncode != 0 for p, _ in children):
        raise ValueError('actor CLI count/exit differs')
    libraries = {}
    for line in Path('/proc/self/maps').read_text().splitlines():
        fields = line.split()
        if len(fields) < 6 or not fields[-1].startswith('/') or '.so' not in fields[-1]:
            continue
        path = Path(fields[-1]).resolve()
        if path == Path(dml._core.__file__).resolve():
            continue
        if not any(str(path).startswith(prefix + '/') for prefix in pins['runtime']['closure']):
            raise ValueError('loaded library outside declared closure')
        libraries[str(path)] = digest(path.read_bytes())
    receipt = {'stage': stage, 'key': job['key'], 'producer': job['producer'], 'spec': job['spec'],
        'source': digest(source.read_bytes()), 'package': str(Path(dml.__file__).resolve()),
        'core': digest(Path(dml._core.__file__).read_bytes()), 'python': str(Path(sys.executable).resolve()),
        'runtime': pins['runtime_digest'], 'libraries': libraries,
        'process': {'pid': os.getpid(), 'parent': os.getppid(), 'group': os.getpgrp()},
        'children': [{'pid': p.pid, 'command': command, 'wait_exit': p.returncode} for p, command in children]}
    (out / 'receipt.json').write_bytes(canonical(receipt))
    return 1 if stage == 'C' and not agreement else 0


if __name__ == '__main__':
    import json
    raise SystemExit(execute(json.loads(Path(sys.argv[1]).read_bytes())))
