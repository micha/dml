"""Fixed foreground E/P/C wrappers, explicit imports and retained true receipts."""

import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = 'incremental'

from .identity import canonical, digest, parse


def load_dml(package, *, name='daggerml'):
    package = Path(package).resolve()
    if name in sys.modules:
        if Path(sys.modules[name].__file__).resolve() != package / '__init__.py':
            raise ValueError('recorder/candidate import alias differs')
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, package / '__init__.py',
                                                submodule_search_locations=[str(package)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_transfer(dml):
    import importlib
    return importlib.import_module(dml.__name__ + '.transfer')


def runtime_receipt(pins, *, dml=None):
    """Loaded immutable library files, not an invented reproducible-build receipt."""
    allowed = pins['runtime']['closure']
    libraries = {}
    for line in Path('/proc/self/maps').read_text().splitlines():
        fields = line.split()
        if len(fields) < 6 or not fields[-1].startswith('/'):
            continue
        path = Path(fields[-1]).resolve()
        if '.so' not in path.name:
            continue
        if dml is not None and path == Path(dml._core.__file__).resolve():
            continue
        if not any(str(path).startswith(prefix + '/') for prefix in allowed):
            raise ValueError('loaded library outside pinned immutable runtime')
        libraries[str(path)] = digest(path.read_bytes())
    receipt = {'python': str(Path(sys.executable).resolve()), 'libraries': libraries,
               'runtime': pins['runtime_digest'], 'package': None, 'core': None}
    if receipt['python'] != pins['runtime']['python']:
        raise ValueError('actual interpreter differs')
    if dml is not None:
        receipt['package'] = str(Path(dml.__file__).resolve())
        receipt['core'] = digest(Path(dml._core.__file__).read_bytes())
        if receipt['core'] != pins['core_sha256']:
            raise ValueError('actual core differs')
    return receipt


def _wrong_result(dml, manifest):
    """Same public authoring operation as the retained original negative; not a codec."""
    with dml.Repository(manifest['repository']) as repo, repo.write() as tx:
        old = dml.ObjectId.from_hex(manifest['roots'][-1])
        entries = dict(tx.get_tree(tx.get_commit(old).tree))
        trace = tx.get_dag(entries['trace'])
        calls = dict(trace.bindings)
        operation = tx.get_dag(tx.get_node(calls['call-00']).dag)
        fields = dict(operation.bindings)
        fields['value'] = tx.put_literal(tx.put_datum(43))
        bad = tx.put_dag(root=fields['value'], bindings=fields)
        calls['call-00'] = tx.put_subdag(bad)
        entries['trace'] = tx.put_dag(root=trace.root, bindings=calls)
        commit = tx.put_commit(tx.put_tree(entries), parents=(old,))
        tx.create_ref('bad-result', commit)
    manifest['roots'].append(str(commit))
    return str(bad)


def execute(request):
    pins = parse(Path(request['pins']).read_bytes())
    output = Path(request['output'])
    stage = request['stage']
    children = []
    original_popen = subprocess.Popen
    allowance = {'E': 0, 'P': 1, 'C': 3}[stage]

    def pinned_cli(command, *args, **kwargs):
        if (type(command) is not list or command[0] != 'duckdb' or len(children) >= allowance):
            raise ValueError('stage child outside finite pinned DuckDB allowlist')
        command = [pins['runtime']['duckdb'], *command[1:]]
        child = original_popen(command, *args, **kwargs)
        children.append((child, command))
        return child

    def forbidden_network(*args, **kwargs):
        raise ValueError('stage cannot activate network')

    subprocess.Popen = pinned_cli
    socket.socket.connect = forbidden_network
    socket.create_connection = forbidden_network
    result = {'stage': stage, 'producer': request['producer'], 'key': request['key'],
              'process': {'pid': os.getpid(), 'parent': os.getppid(), 'group': os.getpgrp()},
              'variant': request['variant']}
    if stage == 'E':
        dml = load_dml(Path(pins['root']) / ('candidate-' + request['candidate']) /
                       'python/daggerml/daggerml')
        sys.path.insert(0, str(Path(pins['root']) / 'exercise'))
        from exerciser import exercise
        manifest = exercise(output / 'scenario', checkpoints=2)
        result['bad_subject'] = _wrong_result(dml, manifest) if request['variant'] == 'wrong' else None
        if len(manifest['roots']) > 4:
            raise ValueError('root bound exceeded')
        transfer = load_transfer(dml)
        bundles = []
        for i, root in enumerate(manifest['roots']):
            bundle = transfer.export_commit(manifest['repository'], commit=dml.ObjectId.from_hex(root))
            name = f'root-{i}.bundle'
            (output / name).write_bytes(bundle)
            bundles.append({'path': name, 'root': root, 'sha256': digest(bundle)})
        # Live scenario database is NOT an artifact. Keep it in an owned working sibling.
        working = output.parent / (output.name + '.native-working')
        (output / 'scenario').rename(working)
        portable = {'roots': manifest['roots'], 'checkpoints': 2, 'expected_trace_positions': 3,
                    'bundles': bundles, 'bad_subject': result['bad_subject']}
        (output / 'evidence.json').write_bytes(canonical(portable))
        result['loaded'] = runtime_receipt(pins, dml=dml)
        result['source'] = digest((Path(pins['root']) / 'exercise/exerciser.py').read_bytes())
        result['working'] = str(working)
    elif stage == 'P':
        dml = load_dml(Path(pins['root']) / 'controller/daggerml')
        transfer = load_transfer(dml)
        upstream = Path(request['upstream'])
        evidence = parse((upstream / 'evidence.json').read_bytes())
        if not 1 <= len(evidence['roots']) <= 4 or len(evidence['bundles']) != len(evidence['roots']):
            raise ValueError('root inventory differs')
        working = output.parent / (output.name + '.native-working')
        with dml.Repository(working, create=True):
            pass
        for i, (root, item) in enumerate(zip(evidence['roots'], evidence['bundles'])):
            if item['path'] != f'root-{i}.bundle' or item['root'] != root:
                raise ValueError('root/bundle boundary differs')
            raw = (upstream / item['path']).read_bytes()
            if digest(raw) != item['sha256']:
                raise ValueError('portable evidence bytes differ')
            imported = transfer.import_commit(working, raw, ref=f'root-{i}')
            if str(imported.commit) != root:
                raise ValueError('imported root differs')
        payload = Path(pins['root']) / request['variant']
        sys.path.insert(0, str(payload))
        from normalizer import normalize
        manifest = {'repository': str(working), 'roots': evidence['roots'], 'expected_trace_positions': 3}
        (output / 'roots.json').write_bytes(canonical({'roots': evidence['roots'], 'expected_trace_positions': 3}))
        # Input manifest with local working path is outside immutable output/key boundary.
        manifest_path = output.parent / (output.name + '.input.json')
        manifest_path.write_bytes(canonical(manifest))
        normalize(manifest_path, output / 'facts')
        result['loaded'] = runtime_receipt(pins, dml=dml)
        result['source'] = digest((payload / 'normalizer.py').read_bytes())
        result['working'] = str(working)
    elif stage == 'C':
        payload = Path(pins['root']) / request['variant']
        sys.path.insert(0, str(payload))
        from checker import check
        upstream = Path(request['upstream']) / 'facts/facts.duckdb'
        before = digest(upstream.read_bytes())
        scratch = output.parent / (output.name + '.scratch.duckdb')
        scratch.write_bytes(upstream.read_bytes())
        checked = check(scratch)
        # Timing is observation text, not a floating computational argument.
        checked['checker_seconds_reported'] = str(checked.pop('checker_seconds'))
        if digest(upstream.read_bytes()) != before:
            raise ValueError('checker changed projection artifact')
        (output / 'verdict.json').write_bytes(canonical(checked))
        result['loaded'] = runtime_receipt(pins)
        result['source'] = digest((payload / 'checker.py').read_bytes())
        result['scratch'] = str(scratch)
        result['violations'] = checked['violations']
    else:
        raise ValueError('unsupported stage')
    if len(children) != allowance or any(child.returncode != 0 for child, _ in children):
        raise ValueError('stage CLI ownership/actual completion differs')
    result['children'] = [{'pid': child.pid, 'command': command, 'wait_exit': child.returncode}
                          for child, command in children]
    (output / 'receipt.json').write_bytes(canonical(result))
    return 1 if stage == 'C' and result['violations'] else 0


def main():
    request = parse(Path(sys.argv[1]).read_bytes())
    raise SystemExit(execute(request))


if __name__ == '__main__':
    main()
