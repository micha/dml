"""Spike-only ordinary DAG events and serialized, branch-local explicit selection."""

from pathlib import Path

from .artifacts import admit
from .identity import canonical, digest, exact, key as stage_key, parse, sha

ROLES = {
    'request': {'occurrence': 'string', 'stage': 'string', 'key': 'string', 'control': 'string',
                'inputs': 'bytes', 'basis': 'bytes'},
    'attempt': {'occurrence': 'string', 'request': 'link', 'state': 'string', 'outcome': 'optional'},
    'outcome': {'attempt-occurrence': 'string', 'status': 'string', 'artifacts': 'bytes',
                'exit': 'i64', 'diagnostics': 'bytes'},
    'satisfaction': {'request': 'link', 'attempt': 'link', 'outcome': 'link'},
    'selection': {'stage': 'string', 'key': 'string', 'attempt': 'link', 'outcome': 'link'},
    'allocator': {'store-namespace': 'string', 'next-run': 'i64', 'next-event': 'i64'},
}


def write_record(tx, role, fields):
    exact(fields, ROLES[role])
    nodes = {'role': tx.put_literal(tx.put_datum('spike-incremental-' + role + '-v1'))}
    for name, kind in ROLES[role].items():
        value = fields[name]
        nodes[name] = (tx.put_subdag(value) if kind == 'link' or kind == 'optional' and value is not None
                       else tx.put_literal(tx.put_datum(value)))
    return tx.put_dag(root=nodes['role'], bindings=nodes)


def read_record(tx, dml, oid, role):
    dag = tx.get_dag(oid)
    exact(dict(dag.bindings), set(ROLES[role]) | {'role'})
    if dag.root != dag.bindings['role']:
        raise ValueError('record root differs')
    result = {}
    for name in dag.bindings:
        node = tx.get_node(dag.bindings[name])
        kind = 'string' if name == 'role' else ROLES[role][name]
        if kind in ('link', 'optional') and isinstance(node, dml.SubDAGNode):
            result[name] = node.dag
        elif isinstance(node, dml.LiteralNode):
            value = tx.get_datum(node.datum)
            expected = 'null' if kind == 'optional' else kind
            if value.kind != expected:
                raise ValueError('record field native kind differs')
            result[name] = value.value
        else:
            raise ValueError('record link kind differs')
    if result.pop('role') != 'spike-incremental-' + role + '-v1':
        raise ValueError('record role differs')
    return result


class Store:
    """One serialized owner; copied IDs only cross short transaction boundaries."""

    def __init__(self, dml, path, artifact_root, namespace, *, create=False):
        self.dml, self.path = dml, Path(path)
        self.artifact_root, self.namespace = Path(artifact_root), namespace
        if type(namespace) is not str or not namespace:
            raise ValueError('explicit store namespace required')
        if create:
            with dml.Repository(self.path, create=True) as repo, repo.write() as tx:
                empty = tx.put_commit(tx.put_tree({}))
                allocator = write_record(tx, 'allocator', {'store-namespace': namespace,
                    'next-run': 0, 'next-event': 0})
                state = tx.put_commit(tx.put_tree({'allocator': allocator}))
                tx.create_ref('main', empty)
                tx.create_ref('allocator', state)
        with dml.Repository(self.path) as repo, repo.read() as tx:
            allocator = self._allocator(tx)[1]
            if allocator['store-namespace'] != namespace:
                raise ValueError('controller store namespace differs')
        self.run = self.reserve(run=True)

    def _allocator(self, tx):
        basis = tx.get_ref('allocator')
        entries = dict(tx.get_tree(tx.get_commit(basis).tree))
        exact(entries, {'allocator'})
        state = read_record(tx, self.dml, entries['allocator'], 'allocator')
        if state['next-run'] < 0 or state['next-event'] < 0:
            raise ValueError('allocator counter invalid')
        return basis, state

    def reserve(self, *, run=False):
        with self.dml.Repository(self.path) as repo, repo.write() as tx:
            basis, state = self._allocator(tx)
            field = 'next-run' if run else 'next-event'
            number = state[field]
            state[field] += 1
            record = write_record(tx, 'allocator', state)
            commit = tx.put_commit(tx.put_tree({'allocator': record}), parents=(basis,))
            tx.update_ref('allocator', commit)
        return (self.namespace + '/run-' + str(number) if run
                else self.run + '/event-' + str(number))

    def head(self, branch='main'):
        with self.dml.Repository(self.path) as repo, repo.read() as tx:
            return tx.get_ref(branch)

    def fork(self, name, basis):
        with self.dml.Repository(self.path) as repo, repo.write() as tx:
            tx.get_commit(basis)
            tx.create_ref(name, basis)

    def _publish(self, role, fields, branch, expected, *, slot=None):
        with self.dml.Repository(self.path) as repo, repo.write() as tx:
            basis = tx.get_ref(branch)
            if basis != expected:
                raise ValueError('stale publication basis')
            entries = dict(tx.get_tree(tx.get_commit(basis).tree))
            record = write_record(tx, role, fields)
            entries['latest-event'] = record
            if slot:
                entries[slot] = record
            if len([name for name in entries if name.startswith('sel-')]) > 16:
                raise ValueError('controller selector bound exceeded')
            commit = tx.put_commit(tx.put_tree(entries), parents=(basis,))
            tx.update_ref(branch, commit)
        return record, commit

    def request(self, envelope, control, *, branch='main', expected=None):
        if control not in ('reuse', 'fresh'):
            raise ValueError('unsupported request control')
        key = stage_key(envelope)
        expected = self.head(branch) if expected is None else expected
        occurrence = self.reserve()
        fields = {'occurrence': occurrence, 'stage': envelope['stage'], 'key': key,
                  'control': control, 'inputs': canonical(envelope), 'basis': expected.bytes}
        request, commit = self._publish('request', fields, branch, expected)
        return request, commit

    def begin(self, request, *, branch='main'):
        with self.dml.Repository(self.path) as repo, repo.read() as tx:
            entries = dict(tx.get_tree(tx.get_commit(tx.get_ref(branch)).tree))
            if entries.get('latest-event') != request:
                raise ValueError('request is not this branch pending event')
            read_record(tx, self.dml, request, 'request')
        occurrence = self.reserve()
        record, commit = self._publish('attempt', {'occurrence': occurrence, 'request': request,
            'state': 'running', 'outcome': None}, branch, self.head(branch))
        return record, occurrence, commit

    def finish(self, initial, artifact_name, artifact_digest, *, branch='main'):
        artifact = admit(self.artifact_root, artifact_name, expected_digest=artifact_digest)
        with self.dml.Repository(self.path) as repo, repo.read() as tx:
            basis = tx.get_ref(branch)
            if dict(tx.get_tree(tx.get_commit(basis).tree)).get('latest-event') != initial:
                raise ValueError('initial attempt is not this branch pending event')
            attempt = read_record(tx, self.dml, initial, 'attempt')
            request = read_record(tx, self.dml, attempt['request'], 'request')
        if attempt['state'] != 'running' or attempt['outcome'] is not None:
            raise ValueError('attempt is not initial unknown')
        envelope = parse(request['inputs'])
        if (artifact['producer'] != attempt['occurrence'] or artifact['key'] != request['key']
                or artifact['stage'] != request['stage'] or artifact['dependencies'] != envelope['dependencies']):
            raise ValueError('artifact producer/request/dependencies disagree')
        fields = {'attempt-occurrence': attempt['occurrence'], 'status': artifact['status'],
                  'artifacts': canonical({'name': artifact_name, 'sha256': sha(artifact_digest)}),
                  'exit': artifact['exit'], 'diagnostics': canonical({'historical': True})}
        with self.dml.Repository(self.path) as repo, repo.write() as tx:
            if tx.get_ref(branch) != basis:
                raise ValueError('stale publication basis')
            entries = dict(tx.get_tree(tx.get_commit(basis).tree))
            outcome = write_record(tx, 'outcome', fields)
            terminal = write_record(tx, 'attempt', {**attempt, 'state': 'done', 'outcome': outcome})
            entries['latest-event'] = terminal
            commit = tx.put_commit(tx.put_tree(entries), parents=(basis,))
            tx.update_ref(branch, commit)
        return terminal, commit

    def terminal(self, terminal):
        with self.dml.Repository(self.path) as repo, repo.read() as tx:
            attempt = read_record(tx, self.dml, terminal, 'attempt')
            if attempt['state'] != 'done' or attempt['outcome'] is None:
                raise ValueError('unknown attempt cannot supply selected success')
            request = read_record(tx, self.dml, attempt['request'], 'request')
            outcome = read_record(tx, self.dml, attempt['outcome'], 'outcome')
        envelope = parse(request['inputs'])
        if stage_key(envelope) != request['key'] or envelope['stage'] != request['stage']:
            raise ValueError('stored request key differs')
        if outcome['attempt-occurrence'] != attempt['occurrence']:
            raise ValueError('terminal outcome belongs to another occurrence')
        reference = exact(parse(outcome['artifacts']), {'name', 'sha256'})
        artifact = admit(self.artifact_root, reference['name'], expected_digest=reference['sha256'])
        if (artifact['producer'] != attempt['occurrence'] or artifact['key'] != request['key']
                or artifact['stage'] != request['stage'] or artifact['dependencies'] != envelope['dependencies']
                or artifact['status'] != outcome['status'] or artifact['exit'] != outcome['exit']):
            raise ValueError('selected artifact authority disagrees')
        return attempt, request, outcome, reference, artifact

    @staticmethod
    def slot(stage, key):
        if stage not in ('E', 'P', 'C'):
            raise ValueError('unsupported selection stage')
        return 'sel-' + stage + '-' + sha(key)

    def adopt(self, terminal, *, branch='main', expected=None):
        expected = self.head(branch) if expected is None else expected
        attempt, request, outcome, _, _ = self.terminal(terminal)
        if outcome['status'] != 'success' or outcome['exit'] != 0:
            raise ValueError('non-success attempt cannot be adopted')
        return self._publish('selection', {'stage': request['stage'], 'key': request['key'],
            'attempt': terminal, 'outcome': attempt['outcome']}, branch, expected,
            slot=self.slot(request['stage'], request['key']))

    def selected(self, envelope, *, branch='main'):
        key = stage_key(envelope)
        slot = self.slot(envelope['stage'], key)
        with self.dml.Repository(self.path) as repo, repo.read() as tx:
            entries = dict(tx.get_tree(tx.get_commit(tx.get_ref(branch)).tree))
            if slot not in entries:
                return None  # Only known-slot absence is a miss.
            selection = read_record(tx, self.dml, entries[slot], 'selection')
        attempt, request, outcome, _, _ = self.terminal(selection['attempt'])
        if (selection['stage'] != envelope['stage'] or selection['key'] != key
                or request['inputs'] != canonical(envelope) or selection['outcome'] != attempt['outcome']):
            raise ValueError('selected computation/links disagree')
        if outcome['status'] != 'success' or outcome['exit'] != 0:
            raise ValueError('non-success selection cannot satisfy request')
        return selection['attempt']

    def reuse(self, request, *, branch='main'):
        with self.dml.Repository(self.path) as repo, repo.read() as tx:
            basis = tx.get_ref(branch)
            if dict(tx.get_tree(tx.get_commit(basis).tree)).get('latest-event') != request:
                raise ValueError('request is not this branch pending event')
            requested = read_record(tx, self.dml, request, 'request')
        if requested['control'] != 'reuse':
            raise ValueError('fresh request cannot reuse')
        terminal = self.selected(parse(requested['inputs']), branch=branch)
        if terminal is None:
            return None
        attempt = self.terminal(terminal)[0]
        satisfaction, commit = self._publish('satisfaction', {'request': request,
            'attempt': terminal, 'outcome': attempt['outcome']}, branch, basis)
        return terminal, satisfaction, commit
