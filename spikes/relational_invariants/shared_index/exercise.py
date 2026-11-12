"""One batch repository, no refs; immutable P0/index/description/context publications."""

import hashlib
import json
from pathlib import Path
import platform
import sys

import daggerml as dml
from daggerml import builtin

from incremental.identity import canonical

INDEX = 'shared-exercise-index-v1'
RUN = 'shared-exercise-run-v1'
DESCRIPTION = 'shared-exercise-description-v1'
CONTEXT = 'shared-exercise-context-v1'
OBSERVATIONS = 'shared-exercise-observations-v1'
OCCURRENCE = 'shared-exercise-occurrence-v1'
LIMITS = {'cases': 16, 'roots': 3, 'getters': 6, 'trace_positions': 16,
          'arguments': 16, 'builtin_reached': 64, 'extract_objects': 10000}
DEFAULT_CASES = [
    {'label': 'normal42', 'value': 42, 'fault': False},
    {'label': 'equal42-fresh', 'value': 42, 'fault': False},
    {'label': 'wrong-result43', 'value': 42, 'fault': True},
    {'label': 'normal43', 'value': 43, 'fault': False},
]


def literal(tx, value):
    return tx.put_literal(tx.put_datum(value))


def id_list(tx, ids):
    return tx.put_literal(tx.put_datum(dml.Datum.list([tx.put_datum(oid.bytes) for oid in ids])))


def role_dag(tx, role, fields):
    nodes = {'role': literal(tx, role), **fields}
    return tx.put_dag(root=nodes['role'], bindings=nodes)


def index(tx, entries):
    return role_dag(tx, INDEX, {name: tx.put_subdag(description) for name, description in entries.items()})


def captures():
    paths = {'builtin': Path(builtin.__file__), 'python_api': Path(dml.__file__),
             'native_core': Path(dml._core.__file__), 'exerciser': Path(__file__),
             'python': Path(sys.executable).resolve()}
    return {'files': {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()},
            'python_version': sys.version.split()[0], 'system': platform.system(), 'machine': platform.machine(),
            'profile': 'trusted-local-map-get-v1; declared capture, not hermeticity'}


def validate_cases(cases):
    if type(cases) is not list or not 0 <= len(cases) <= LIMITS['cases']:
        raise ValueError('case count/type exceeds profile')
    names = set()
    for case in cases:
        if type(case) is not dict or set(case) != {'label', 'value', 'fault'}:
            raise ValueError('case fields differ')
        if type(case['label']) is not str or not case['label'] or case['label'] in names:
            raise ValueError('case labels must be unique nonempty strings')
        if type(case['value']) is not int or not -(2**63) <= case['value'] < 2**63 or type(case['fault']) is not bool:
            raise ValueError('case requires I64 value/exact bool fault')
        if case['fault'] and case['value'] == 2**63-1:
            raise ValueError('wrong-result successor exceeds I64')
        names.add(case['label'])


def fixture(tx, cases):
    entries, sources = {}, {}
    for number, value in enumerate(sorted({case['value'] for case in cases})):
        key = tx.put_datum('x')
        contents = tx.put_datum(dml.Datum.map([(key, tx.put_datum(value))]))
        node = tx.put_literal(contents)
        pair = []
        for side in ('a', 'b'):
            source = tx.put_dag(root=node, bindings={'sample': node, 'origin': literal(tx, 'source-' + side)})
            entries[f'value-{number}-{side}'] = source
            pair.append(source)
        sources[value] = pair
    bindings = [builtin.put_binding(tx, source_uri=f'dml://source/builtin/map/get/v{v}') for v in (1, 2)]
    entries.update(zip(('v1', 'v2'), bindings))
    base = tx.put_commit(tx.put_tree(entries))
    return base, entries, sources, bindings


def make_case(repo, base, entries, sources, bindings, context, occurrence, spec):
    roots, results = [base], []
    marker = None
    for step in range(2):
        with repo.write() as tx:
            marker = role_dag(tx, OCCURRENCE, {'occurrence': literal(tx, occurrence)})
            with builtin.Recorder(tx, commit=base) as recorder:
                left, right = [recorder.source(source, 'sample') for source in sources]
                key = recorder.literal('x')
                for source in (left, left, right):
                    args = recorder.arguments({'map': source, 'key': key})
                    returned = recorder.call(builtin.MAP_GET, bindings[step], args)
                    if returned.value.kind != 'i64' or returned.value.value != spec['value']:
                        raise ValueError('actual builtin return differs from fixture value')
                    results.append(returned.value.value)
                trace = recorder.trace()
            case_entries = {**entries, 'trace': trace, 'exercise-context': context, 'exercise-occurrence': marker}
            bad = None
            if step == 1 and spec['fault']:
                ledger = tx.get_dag(trace)
                calls = dict(ledger.bindings)
                operation = tx.get_dag(tx.get_node(calls['call-00']).dag)
                fields = dict(operation.bindings)
                fields['value'] = literal(tx, spec['value'] + 1)
                bad = tx.put_dag(root=fields['value'], bindings=fields)
                calls['call-00'] = tx.put_subdag(bad)
                case_entries['trace'] = tx.put_dag(root=ledger.root, bindings=calls)
            checkpoint = tx.put_commit(tx.put_tree(case_entries), parents=(base,))
            roots.append(checkpoint)
    with repo.write() as tx:
        # One exercise target retains BOTH independent checkpoint tips and their common fixture.
        target = tx.put_commit(tx.put_tree(case_entries), parents=tuple(roots[1:]))
    return target, roots, results, bad


def publication(tx, previous, target, run, entries):
    """No mutation of old index/commit, no ref. Called inside caller-owned write batch."""
    latest_index = index(tx, entries)
    tree = tx.put_tree({'exercise-index': latest_index, 'exercise-run': run})
    return tx.put_commit(tree, parents=(previous, target))


def exercise(directory, *, namespace, cases=None):
    cases = DEFAULT_CASES if cases is None else cases
    validate_cases(cases)
    if type(namespace) is not str or not namespace:
        raise ValueError('explicit actual run namespace required')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    repository = directory / 'repository'
    publications, descriptors = [], {}
    captured = captures()
    with dml.Repository(repository, create=True) as repo:
        with repo.write() as tx:
            run = role_dag(tx, RUN, {'namespace': literal(tx, namespace), 'scenarios': literal(tx, canonical(cases)),
                                    'captures': literal(tx, canonical(captured)), 'limits': literal(tx, canonical(LIMITS))})
            empty = index(tx, {})
            previous = tx.put_commit(tx.put_tree({'exercise-index': empty, 'exercise-run': run}))
            base, entries, source_pairs, bindings = fixture(tx, cases)
        publications.append(str(previous))
        (directory / 'publication-000.json').write_bytes(canonical({'publication': str(previous)}))
        for number, spec in enumerate(cases, 1):
            occurrence = f'{namespace}/exercise-{number}'
            with repo.write() as tx:
                context = role_dag(tx, CONTEXT, {
                    'scenario': literal(tx, 'builtin-map-get'), 'parameters': literal(tx, canonical({'value': spec['value']})),
                    'captures': literal(tx, canonical(captured)), 'limits': literal(tx, canonical(LIMITS)),
                    'expectations': literal(tx, canonical({'positions': [None, 3, 3],
                        'outcome': 'reject' if spec['fault'] else 'accept',
                        'invariant': 'map_get_value' if spec['fault'] else None})),
                    'fixture': literal(tx, base.bytes), 'sources': id_list(tx, source_pairs[spec['value']]),
                })
            target, roots, results, bad = make_case(repo, base, entries, source_pairs[spec['value']], bindings,
                                                    context, occurrence, spec)
            with repo.write() as tx:
                observations = role_dag(tx, OBSERVATIONS, {
                    'calls': literal(tx, len(results)), 'returns': literal(tx, canonical(results)),
                    'errors': literal(tx, canonical([])), 'bad-operation': literal(tx, None if bad is None else bad.bytes),
                })
                description = role_dag(tx, DESCRIPTION, {
                    'label': literal(tx, spec['label']), 'occurrence': literal(tx, occurrence),
                    'target': literal(tx, target.bytes), 'roots': id_list(tx, roots),
                    'context': tx.put_subdag(context), 'observations': tx.put_subdag(observations),
                })
                descriptors[f'case-{number:03d}'] = description
                previous = publication(tx, previous, target, run, descriptors)
            publications.append(str(previous))
            (directory / f'publication-{number:03d}.json').write_bytes(canonical({'publication': str(previous)}))
    handle = {'repository': str(repository.resolve()), 'publication': str(previous),
              'publication_chain': publications, 'namespace': namespace,
              'note': 'external retrieval handles only; case context is authoritative in indexed DML DAGs'}
    (directory / 'handle.json').write_bytes(canonical(handle))
    return handle
