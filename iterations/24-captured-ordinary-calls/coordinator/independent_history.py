"""Independent SAME-history typed/native assertions; no recording or computation."""
import base64
import hashlib
import importlib.abc
import json
from pathlib import Path
import sys

class NoTransport(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in ('urllib', 'urllib.parse'):
            return None
        if any(fullname == n or fullname.startswith(n + '.') for n in
               ('http', 'urllib', 'requests', 'httpx', 'aiohttp', 'boto3', 'botocore', 'docker',
                'daggerml.floci', 'daggerml.ssh')):
            raise RuntimeError('independent reader transport blocked')

def audit(event, args):
    if event in ('subprocess.Popen', 'os.posix_spawn', 'os.fork', 'os.forkpty', 'os.exec',
                 'os.system', 'socket.connect', 'socket.bind', 'socket.getaddrinfo'):
        raise RuntimeError('independent reader spawn/transport blocked')

sys.meta_path.insert(0, NoTransport())
sys.addaudithook(audit)
checks = 0
def check(condition, label):
    global checks
    if not condition:
        raise AssertionError(label)
    checks += 1

import subprocess
import socket
for label, action in [('spawn', lambda: subprocess.Popen([sys.executable, '-c', 'raise SystemExit(99)'])),
                      ('http', lambda: __import__('http.client')),
                      ('urllib', lambda: __import__('urllib.request')),
                      ('connect', lambda: socket.create_connection(('127.0.0.1', 1)))]:
    try:
        action()
    except RuntimeError:
        check(True, label)
    else:
        raise AssertionError('blocker failed ' + label)

root = Path('/work/repos/micha/dml/build/iteration24/acceptance/corrected/story')
source = root / 'captured-source.unavailable'
load = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
receipt = load(root / 'receipt.json')
for name, digest in receipt['sources'].items():
    check(sha(source / name) == digest, 'retained actual source ' + name)
sys.path.insert(0, str(source))
import daggerml as d
from daggerml import builtin as b, local, exchange, transfer
import captured_calls as p
import captured_call_adapter as adapter
import captured_call_session as session
import captured_call_leaf as leaf
import captured_call_funcs as logical
import composed_node_funcs as funcs

for row in receipt['installed'].values():
    check(sha(row['path']) == row['sha256'], 'installed identity')
check(str(Path(d.__file__).resolve()).startswith('/work/repos/micha/dml/build/iteration24/install/venv/'), 'isolated DML import')
check(sys.executable == receipt['interpreter'] and sha(sys.executable) == receipt['interpreter_sha256'], 'interpreter')

def forbidden(*args, **kwargs):
    raise RuntimeError('independent reader authoring/logical execution blocked')
for module, names in [(b, ('record', 'publish_callable')),
                      (local, ('run_step', 'run_request', 'retry_step', 'publish_result', 'child_context')),
                      (exchange, ('execute_exchange', 'start_exchange', 'record_exchange_request'))]:
    for name in names:
        setattr(module, name, forbidden)
adapter.execute = logical.double_sum = leaf.publish = funcs.add = funcs.double = forbidden
session.Session.__init__ = b.Recorder.__init__ = forbidden
initialize, write = d.Repository.__init__, d.Repository.write
opened = {}
targets = {root / 'caller.dml', root / 'replica.dml'}
def tracked(owner, path, **kwargs):
    initialize(owner, path, **kwargs)
    opened[id(owner)] = Path(path).resolve()
def guard_write(owner):
    if opened[id(owner)] in targets:
        raise RuntimeError('independent target write blocked')
    return write(owner)
d.Repository.__init__, d.Repository.write = tracked, guard_write
for action in [lambda: b.record(None, 'forbidden'), lambda: adapter.execute(None, None),
               lambda: logical.double_sum(None, None, None, None), lambda: b.Recorder(None, commit=None)]:
    try:
        action()
    except RuntimeError:
        check(True, 'author blocker')
    else:
        raise AssertionError('author blocker failed')

packet = load(root / 'full-history.bundle')
check(sha(root / 'full-history.bundle') == receipt['bundle_sha256'], 'complete immutable bundle')
check(packet['root'] == receipt['final'], 'bundle root')
commit = d.ObjectId.from_hex(receipt['final'])
before = {str(store): sha(store / 'data.mdb') for store in targets}
counts = []
for store in sorted(targets):
    with d.Repository(store) as repo, repo.read() as tx:
        try:
            repo.write()
        except RuntimeError:
            check(True, 'actual target write blocker')
        else:
            raise AssertionError('target write allowed')
        check(tx.get_ref('story') == commit, 'native story ref')
        for row in packet['objects']:
            check(tx.get_record(row['kind'], d.ObjectId.from_hex(row['id'])) == base64.b64decode(row['record']), 'exact typed bundle row')
        entries = dict(tx.get_tree(tx.get_commit(commit).tree))
        closure = p.inspect_closure(tx, commit, entries['outer'])
        check(closure['add']['dag'] == entries['add-A'] and closure['double']['dag'] == entries['double-A'], 'captured old leaves')
        check(closure['add']['map_binding'] == entries['map-v1'], 'captured old getter')
        check(entries['default-add'] == entries['add-B'] and entries['default-double'] == entries['double-B'], 'promoted convenience defaults')
        oq, lq, ot, lt = set(), set(), set(), set()
        for ancestor in p.history(tx, commit):
            for name, dag in p.tree(tx, ancestor).items():
                if name.startswith('outer-request-cq-'):
                    oq.add(dag)
                if name.startswith('request-q-'):
                    lq.add(dag)
                if name.startswith('outer-attempt-ca-'):
                    ot.add(b.scalar(tx, tx.get_dag(dag).root, 'string'))
                if name.startswith('attempt-a-'):
                    lt.add(b.scalar(tx, tx.get_dag(dag).root, 'string'))
        check((len(oq), len(lq), len(ot), len(lt)) == (4,6,3,5), 'ALL-parent occurrence census')
    selected = p.inspect_selection(store, commit=commit)
    descriptions, own = [], []
    for index, row in enumerate(receipt['requests']):
        request = d.ObjectId.from_hex(row['request'])
        q = p.inspect_request(store, commit=d.ObjectId.from_hex(row['submission']), request=request)
        own.append(q)
        check(q.closure == closure, 'actual pinned closure')
        final = d.ObjectId.from_hex(receipt['finals'][index])
        if index == 1:
            w = p.inspect_reuse(store, commit=final)
            check(w.selected['attempt'] == selected['attempt'], 'outer hit OLD attempt')
            check(row['satisfaction'] == receipt['finals'][index], 'own reuse satisfaction')
            descriptions.append(None)
            continue
        got = p.inspect_completion(store, commit=final)
        check(got['outcome'] == 'success' and len(got['calls']) == len(got['getters']) == 2, 'actual complete fresh outer')
        with d.Repository(store) as repo, repo.read() as tx:
            check(tx.get_datum(got['datum']) == d.Datum.i64(84), 'recorded84, no arithmetic replay')
        descriptions.append(got)
    check(own[0].inputs.datum != own[2].inputs.datum, 'swapped upstream MAP differs')
    check(descriptions[0]['attempt'] == selected['attempt'], 'no automatic outer adoption')
    with d.Repository(store) as repo, repo.read() as tx:
        old = tx.get_dag(descriptions[0]['calls'][1]).bindings
        new = tx.get_dag(descriptions[2]['calls'][1]).bindings
        check(tuple(b.link(tx, old[n]) for n in ('attempt','result')) == tuple(b.link(tx, new[n]) for n in ('attempt','result')), 'selected OLD downstream producer')
        op = tx.get_dag(b.link(tx, old['pending'])).bindings
        np = tx.get_dag(b.link(tx, new['pending'])).bindings
        check(b.link(tx, op['request']) != b.link(tx, np['request']), 'own NEW inner request')
        old_input, old_sources = p.arguments(tx, commit, b.link(tx, op['inputs']), ('x',), set())
        new_input, new_sources = p.arguments(tx, commit, b.link(tx, np['inputs']), ('x',), set())
        check(old_input.datum == new_input.datum, 'equal full downstream MAP')
        old_add = b.link(tx, tx.get_dag(descriptions[0]['calls'][0]).bindings['result'])
        new_add = b.link(tx, tx.get_dag(descriptions[2]['calls'][0]).bindings['result'])
        check(old_sources['x'].dag == old_add and new_sources['x'].dag == new_add and old_add != new_add, 'exact OLD/requested source nodes')
        check(entries[p.DOUBLE_SLOT] == b.link(tx, old['selection']), 'no automatic double adoption')
        getter_count = sum(len(g['getters']) for g in descriptions if g is not None)
        seen_attempts = set()
        for got in descriptions:
            if got is None:
                continue
            for call in got['calls']:
                cf = tx.get_dag(call).bindings
                attempt = b.link(tx, cf['attempt'])
                if attempt in seen_attempts:
                    continue
                seen_attempts.add(attempt)
                result = b.link(tx, cf['result'])
                rf = tx.get_dag(result).bindings
                trace = b.Inspector(tx, commit=commit).trace(b.link(tx, rf['trace']), request=b.link(tx, rf['request']), inputs=b.link(tx, rf['inputs']))
                getter_count += len(trace)
        check((len(seen_attempts), getter_count) == (5,14), 'separate actual getter positions')
    check(len(descriptions[0]['semantic_ids']) == 34 and len(descriptions[2]['semantic_ids']) == 50, 'actual requested/original semantic union')
    counts.append(dict(repository=str(store), outer_requests=4, leaf_requests=6, outer_attempts=3, local_attempts=5, getter_positions=getter_count))

after = {str(store): sha(store / 'data.mdb') for store in targets}
check(before == after, 'target data immutable')
custody = load(root / 'custody.json')
check(len(custody['children']) == len({r['pid'] for r in custody['children']}) == 5, 'unique recorded child population')
for row in custody['children']:
    check(row['waits'] == [dict(returned=True, exit=0)] and row['verified'] and row['absent'], 'known reaped recorded custody')
check(not (root.parent / 'launch-source').exists(), 'owned original source unavailable')
for number in (1,3,4):
    check(not (root / ('execution-' + str(number))).exists(), 'owned operational paths unavailable')
print(json.dumps(dict(independent_checks=checks, independently_authored_NONEXECUTING=True,
                      actual_typed_bundle_rows=len(packet['objects']), repositories=counts,
                      before=before, after=after, new_requests_attempts_computations=0,
                      no_historical_PID_actions=True), indent=2))
