"""New grouped evidence/index profiles; actual controller links never become fake native edges."""
from pathlib import Path

from incremental.identity import canonical, digest, parse
from incremental.records import read_record

INDEX = 'per-exercise-batch-index-v1'
ENTRY = 'per-exercise-batch-entry-v1'
RUN = 'per-exercise-batch-run-v1'
GROUP = 'per-exercise-controller-batch-v1'


def check_result(attempt, produced, reference, artifact, result):
    if (reference != {'name': result['name'], 'sha256': result['digest']} or produced['key'] != result['key']
            or artifact['stage'] != result['stage'] or result['outcome'] != str(attempt['outcome'])):
        raise ValueError('result artifact/key/stage/outcome differs')


ENTRY_KINDS = {'requested': 'bytes', 'request': 'bytes', 'terminal': 'bytes', 'outcome': 'bytes',
               'E-key': 'string', 'E-artifact': 'string', 'fresh': 'bool',
               'producer-description': 'subdag', 'producer-run': 'subdag',
               'target': 'bytes', 'producer-publication': 'bytes'}


def read_fields(tx, dml, oid, role, kinds):
    dag = tx.get_dag(oid)
    if set(dag.bindings) != {'role', *kinds} or dag.root != dag.bindings['role']:
        raise ValueError('new batch role/root/shape differs')
    data = {}
    for name, kind in {'role': 'string', **kinds}.items():
        node = tx.get_node(dag.bindings[name])
        if kind == 'subdag':
            if not isinstance(node, dml.SubDAGNode):
                raise ValueError('batch native SubDAG field kind differs')
            tx.get_dag(node.dag)
            data[name] = node.dag
        else:
            if not isinstance(node, dml.LiteralNode):
                raise ValueError('batch native literal field kind differs')
            datum = tx.get_datum(node.datum)
            if datum.kind != kind:
                raise ValueError('batch native datum kind differs')
            data[name] = datum.value
    if data.pop('role') != role:
        raise ValueError('new batch role differs')
    return data


def authority(store, result, spec):
    dml = store.dml
    terminal = dml.ObjectId.from_hex(result['terminal'])
    attempt, produced, outcome, reference, artifact = store.terminal(terminal)
    check_result(attempt, produced, reference, artifact, result)
    with dml.Repository(store.path) as repo, repo.read() as tx:
        requested = read_record(tx, dml, dml.ObjectId.from_hex(result['request']), 'request')
        if requested['inputs'] != produced['inputs'] or outcome['status'] != 'success':
            raise ValueError('requested/produced computation differs')
        context = parse(requested['inputs'])['context']
        if {name: context[name] for name in spec} != spec:
            raise ValueError('request case context differs')
        if result['fresh']:
            if str(attempt['request']) != result['request'] or result['satisfaction'] is not None:
                raise ValueError('fresh request belongs to other producer')
        else:
            satisfaction = read_record(tx, dml, dml.ObjectId.from_hex(result['satisfaction']), 'satisfaction')
            if (str(satisfaction['request']) != result['request'] or satisfaction['attempt'] != terminal
                    or satisfaction['outcome'] != attempt['outcome'] or str(attempt['request']) == result['request']):
                raise ValueError('reuse satisfaction/old producer differs')
    return attempt, requested, outcome


def publish(controller, cases, pool, number):
    from daggerml import transfer
    from shared_index.exercise import literal, role_dag
    dml = controller.store.dml
    occurrence = controller.store.reserve()
    directory = controller.directory / 'batches' / f'batch-{number}'
    directory.mkdir(parents=True, exist_ok=False)
    specs = [row['spec'] for row in cases]
    admitted = []
    for row in cases:
        for stage in ('E', 'P', 'C'):
            authority(controller.store, row[stage], row['spec'])
        evidence = parse((controller.artifacts / row['E']['name'] / 'evidence.json').read_bytes())
        if evidence['spec'] != row['spec']:
            raise ValueError('producer/request input mismatch')
        admitted.append(evidence)
    entries = {}
    publications = []
    with dml.Repository(controller.evidence) as repo, repo.write() as tx:
        run = role_dag(tx, RUN, {'occurrence': literal(tx, occurrence),
            'requested': literal(tx, canonical(specs)), 'profile': literal(tx, 'per-exercise-v1')})
        previous = tx.put_commit(tx.put_tree({'exercise-index': role_dag(tx, INDEX, {}), 'exercise-run': run}))
        publications.append(str(previous))
        for number_, (row, evidence) in enumerate(zip(cases, admitted), 1):
            e = row['E']
            # Explicit BYTES foreign IDs; original producer links are native SubDAGs.
            entry = role_dag(tx, ENTRY, {'requested': literal(tx, canonical(row['spec'])),
                'request': literal(tx, bytes.fromhex(e['request'])),
                'terminal': literal(tx, bytes.fromhex(e['terminal'])),
                'outcome': literal(tx, bytes.fromhex(e['outcome'])), 'E-key': literal(tx, e['key']),
                'E-artifact': literal(tx, e['digest']), 'fresh': literal(tx, e['fresh']),
                'producer-description': tx.put_subdag(dml.ObjectId.from_hex(evidence['description'])),
                'producer-run': tx.put_subdag(dml.ObjectId.from_hex(evidence['producer_run'])),
                'target': literal(tx, bytes.fromhex(evidence['target'])),
                'producer-publication': literal(tx, bytes.fromhex(evidence['publication']))})
            entries[f'case-{number_:03d}'] = tx.put_subdag(entry)
            index = role_dag(tx, INDEX, entries)
            previous = tx.put_commit(tx.put_tree({'exercise-index': index, 'exercise-run': run}),
                                     parents=(previous, dml.ObjectId.from_hex(evidence['target'])))
            publications.append(str(previous))
    bundle = transfer.export_commit(controller.evidence, commit=previous)
    (directory / 'publication.bundle').write_bytes(bundle)
    document = {'occurrence': occurrence, 'publication': str(previous), 'chain': publications,
                'bundle_sha256': digest(bundle), 'cases': cases, 'pool': pool}
    (directory / 'group.json').write_bytes(canonical(document))
    inspect(controller, document)
    record_group(controller, document)
    return document


def inspect(controller, document):
    from .capsules import read
    from .profiles import LABELS
    dml = controller.store.dml
    if [row['spec']['label'] for row in document['cases']] != list(LABELS):
        raise ValueError('group scenarios/order differ')
    authorities = []
    for row in document['cases']:
        for stage in ('E', 'P', 'C'):
            authority(controller.store, row[stage], row['spec'])
        capsule = read(controller.artifacts / row['P']['name'] / 'capsule.json')
        evidence = parse((controller.artifacts / row['E']['name'] / 'evidence.json').read_bytes())
        if (capsule['publication'] != evidence['publication']
                or capsule['case']['description'] != evidence['description']):
            raise ValueError('projection/exercise authority differs')
        authorities.append(evidence)
    with dml.Repository(controller.evidence) as repo, repo.read() as tx:
        def fields(oid, role, names):
            kinds = (ENTRY_KINDS if role == ENTRY else
                     {'occurrence': 'string', 'requested': 'bytes', 'profile': 'string'} if role == RUN else
                     {name: 'subdag' for name in names})
            if set(kinds) != set(names):
                raise ValueError('new batch owning schema differs')
            return read_fields(tx, dml, oid, role, kinds)
        current = dml.ObjectId.from_hex(document['publication'])
        chain = []
        expected_run = None
        for count in range(3, -1, -1):
            chain.append(str(current))
            commit = tx.get_commit(current)
            tree = dict(tx.get_tree(commit.tree))
            if set(tree) != {'exercise-index', 'exercise-run'}:
                raise ValueError('batch tree shape differs')
            if expected_run is None:
                expected_run = tree['exercise-run']
            if tree['exercise-run'] != expected_run:
                raise ValueError('batch run changed within publication chain')
            run = fields(expected_run, RUN, {'occurrence', 'requested', 'profile'})
            if run != {'occurrence': document['occurrence'],
                       'requested': canonical([row['spec'] for row in document['cases']]),
                       'profile': 'per-exercise-v1'}:
                raise ValueError('batch requested context differs')
            names = {f'case-{i:03d}' for i in range(1, count + 1)}
            entries = fields(tree['exercise-index'], INDEX, names)
            for i in range(1, count + 1):
                row, evidence = document['cases'][i - 1], authorities[i - 1]
                entry = fields(entries[f'case-{i:03d}'], ENTRY,
                    {'requested', 'request', 'terminal', 'outcome', 'E-key', 'E-artifact', 'fresh',
                     'producer-description', 'producer-run', 'target', 'producer-publication'})
                e = row['E']
                wanted = {'requested': canonical(row['spec']), 'request': bytes.fromhex(e['request']),
                    'terminal': bytes.fromhex(e['terminal']), 'outcome': bytes.fromhex(e['outcome']),
                    'E-key': e['key'], 'E-artifact': e['digest'], 'fresh': e['fresh'],
                    'producer-description': dml.ObjectId.from_hex(evidence['description']),
                    'producer-run': dml.ObjectId.from_hex(evidence['producer_run']),
                    'target': bytes.fromhex(evidence['target']),
                    'producer-publication': bytes.fromhex(evidence['publication'])}
                if entry != wanted:
                    raise ValueError('current request versus OLD producer entry differs')
            if count == 0:
                if commit.parents:
                    raise ValueError('empty batch P0 is not parentless')
            else:
                if len(commit.parents) != 2 or str(commit.parents[1]) != authorities[count - 1]['target']:
                    raise ValueError('ordered publication parent differs')
                current = commit.parents[0]
        if list(reversed(chain)) != document['chain']:
            raise ValueError('batch chain handle differs')
    return True


def record_group(controller, document):
    from shared_index.exercise import literal, role_dag
    dml = controller.store.dml
    basis = controller.store.head()
    with dml.Repository(controller.store.path) as repo, repo.write() as tx:
        if tx.get_ref('main') != basis:
            raise ValueError('stale grouping basis')
        ledger = {}
        for number, row in enumerate(document['cases'], 1):
            fields = {'requested': literal(tx, canonical(row['spec'])),
                      'fresh': literal(tx, canonical({s: row[s]['fresh'] for s in ('E', 'P', 'C')}))}
            for stage in ('E', 'P', 'C'):
                for name, key in [('Q', 'request'), ('T', 'terminal'), ('O', 'outcome')]:
                    fields[stage + '-' + name] = tx.put_subdag(dml.ObjectId.from_hex(row[stage][key]))
            child = role_dag(tx, 'per-exercise-controller-case-v1', fields)
            ledger[f'case-{number:03d}'] = tx.put_subdag(child)
        group = role_dag(tx, GROUP, {'occurrence': literal(tx, document['occurrence']),
            'cases': tx.put_subdag(role_dag(tx, 'per-exercise-controller-cases-v1', ledger)),
            'evidence-publication': literal(tx, bytes.fromhex(document['publication'])),
            'evidence-artifact': literal(tx, canonical({'bundle_sha256': document['bundle_sha256']})),
            'materialization': literal(tx, canonical(document['pool'])), 'state': literal(tx, 'complete')})
        entries = dict(tx.get_tree(tx.get_commit(basis).tree))
        entries['latest-batch'] = group
        tx.update_ref('main', tx.put_commit(tx.put_tree(entries), parents=(basis,)))
