#!/usr/bin/env python3
"""Read-only PRIOR synthetic Iteration10 packet replay; NEVER dispatches or executes source.
Use reviewed installed Python, with PYTHONPATH unset. prepare/validate operate only in new study sandboxes.
"""
import base64
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

import daggerml as d
from daggerml import exchange as ex, transfer

ROOT = Path(__file__).resolve().parent
DML = ROOT.parents[2] / 'dml'
SOURCE = Path('/tmp/dml-iteration10-independent-story')
FILES = ('job.json', 'observation.json', 'snapshot.bundle')
WHEELS = {'daggerml-0.1.0-cp313-abi3-linux_x86_64.whl': '767d1032c73f335588f47053cefe4b6f023adf7242ed8975940071aed6394385',
          'daggerml_cli-0.1.0-py3-none-any.whl': 'f9f277c8287df8321056d44341c5ad8cac665febcfb81de3e54bab8216374983'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def typed(path, root):
    # Independent public breadth-first oracle, not transfer's traversal/helper.
    found = {}
    todo = [('commit', root)]
    with d.Repository(path) as repository, repository.read() as tx:
        while todo:
            kind, oid = todo.pop(0)
            if (kind, oid) in found:
                continue
            found[kind, oid] = tx.get_record(kind, oid)
            if kind == 'commit':
                value = tx.get_commit(oid)
                todo += [('tree', value.tree)] + [('commit', p) for p in value.parents]
            elif kind == 'tree':
                todo += [('dag', v) for v in tx.get_tree(oid).values()]
            elif kind == 'dag':
                value = tx.get_dag(oid)
                todo += [('node', value.root)] + [('node', n) for n in value.bindings.values()]
            elif kind == 'node':
                value = tx.get_node(oid)
                todo += [('datum', value.datum)] if isinstance(value, d.LiteralNode) else [('dag', value.dag)]
            else:
                value = tx.get_datum(oid)
                if value.kind in ('list', 'set'):
                    todo += [('datum', n) for n in value.value]
                elif value.kind == 'map':
                    todo += [('datum', n) for pair in value.value for n in pair]
    return found


def installed_provenance():
    site = Path(d.__file__).resolve().parent.parent
    verified = []
    assert '/python/daggerml/' not in str(site)
    for filename, expected in WHEELS.items():
        path = DML / 'build/iteration10-owned/dist' / filename
        assert digest(path.read_bytes()) == expected
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.startswith(('daggerml/', 'daggerml_cli/')) and not name.endswith('/'):
                    data = archive.read(name)
                    assert (site / name).read_bytes() == data
                    # Every maintained package Python byte also agrees with read-only published checkout.
                    source = DML / 'python' / ('daggerml-cli' if name.startswith('daggerml_cli/') else 'daggerml') / name
                    if name.endswith('.py'):
                        assert source.read_bytes() == data
                    verified.append({'file': name, 'sha256': digest(data)})
    return {'python': sys.executable, 'package': str(site), 'artifacts': verified, 'wheels': WHEELS}


def prepare(sandbox):
    sandbox.mkdir(exist_ok=False)
    provenance = installed_provenance()
    assert json.loads((SOURCE / 'summary.json').read_bytes())['checks'] == 178
    provenance['prior_summary_sha256'] = digest((SOURCE / 'summary.json').read_bytes())
    provenance['prior_driver_sha256'] = digest(Path('/tmp/dml-iteration10-independent.py').read_bytes())
    rows = []
    for trial in (0, 1, 2):
        # Independent caller selection, NOT incoming packet's expected claims or serialized SSH keys.
        expected = ex.read_exchange_spec(SOURCE / ('input-' + str(trial) + '.offline'))
        ex.save_exchange_handle(sandbox / ('expected-' + str(trial) + '.json'), ex.ExchangeHandle(sandbox / 'inert', expected))
        for phase in ('initial', 'publication', 'completion'):
            label = str(trial) + '-' + phase + '-0'
            original = SOURCE / label
            selected = sandbox / 'selected' / label
            selected.mkdir(parents=True)
            hashes = {}
            for filename in FILES:
                data = (original / filename).read_bytes()
                assert len(data) <= 1048576
                (selected / filename).write_bytes(data)
                hashes[filename] = {'bytes': len(data), 'sha256': digest(data)}
            inspected = ex.read_observation(selected, expected=expected)
            assert inspected.phase == phase
            if phase == 'completion':
                assert inspected.completion.outcome == ('failure' if trial == 2 else 'success')
                assert inspected.completion.exit_code == (23 if trial == 2 else 0)
            rows.append({'label': label, 'trial': trial, 'phase': phase, 'files': hashes,
                         'commit': str(inspected.commit), 'Q': str(expected.request),
                         'Cq': str(expected.commit), 'source': str(original)})
    (sandbox / 'selection.json').write_text(json.dumps({'provenance': provenance, 'packets': rows}, indent=2))
    print(json.dumps({'stage': 'prepare', 'packets': len(rows), 'verified_artifacts': len(provenance['artifacts'])}))


def validate(sandbox):
    installed_provenance()
    selection = json.loads((sandbox / 'selection.json').read_bytes())
    caller = sandbox / 'A.dml'
    with d.Repository(caller, create=True) as repository, repository.write() as tx:
        value = tx.put_literal(tx.put_datum('new-study-sentinel'))
        keep = tx.put_dag(root=value)
        sentinel = tx.put_commit(tx.put_tree({'sentinel': keep}))
        main = tx.put_commit(tx.put_tree({'independently-advanced': keep}), parents=(sentinel,))
        tx.create_ref('main', main)
        tx.create_ref('sentinel', sentinel)
    fixed_refs = {'main': main, 'sentinel': sentinel}
    # Seed exact old submissions/reservations in this NEW A, with no execution/recording new Q.
    for trial in (0, 1, 2):
        expected = ex.load_exchange_handle(sandbox / ('expected-' + str(trial) + '.json')).expected
        initial = sandbox / 'selected' / (str(trial) + '-initial-0')
        transfer.import_commit(caller, (initial / 'snapshot.bundle').read_bytes())
        got = ex.read_observation(initial, expected=expected)
        with d.Repository(caller) as repository, repository.write() as tx:
            for ref in ('submission-' + str(trial), 'request-' + got.request_id):
                tx.create_ref(ref, expected.commit)
                fixed_refs[ref] = expected.commit
    old = {}
    for root in set(fixed_refs.values()):
        old.update(typed(caller, root))
    reports = []
    for row in selection['packets']:
        label = row['label']
        original = sandbox / 'selected' / label
        fetched = sandbox / 'fetched' / label
        for filename in FILES:
            data = (fetched / filename).read_bytes()
            assert data == (original / filename).read_bytes()
            assert digest(data) == row['files'][filename]['sha256']
        expected = ex.load_exchange_handle(sandbox / ('expected-' + str(row['trial']) + '.json')).expected
        got = ex.read_observation(fetched, expected=expected)
        assert got.commit == d.ObjectId.from_hex(row['commit']) and got.request == expected.request
        assert got.phase == row['phase']
        assert got.lifecycle == ('done' if row['phase'] == 'completion' else 'working')
        bundle = (original / 'snapshot.bundle').read_bytes()
        validation = sandbox / ('oracle-' + label)
        with d.Repository(validation, create=True):
            pass
        transfer.import_commit(validation, bundle)
        oracle = typed(validation, got.commit)
        raw_rows = {(r['kind'], d.ObjectId.from_hex(r['id'])): base64.b64decode(r['record'], validate=True)
                    for r in json.loads(bundle)['objects']}
        assert oracle == raw_rows
        received = ex.receive_observation(caller, packet=fetched, expected=expected, ref='return-' + label)
        assert received.commit == got.commit
        assert ex.receive_observation(caller, packet=fetched, expected=expected, ref='return-' + label) == received
        assert typed(caller, got.commit) == oracle
        with d.Repository(caller) as repository, repository.read() as tx:
            assert all(tx.get_ref(ref) == value for ref, value in fixed_refs.items())
            assert all(tx.get_record(kind, oid) == value for (kind, oid), value in old.items())
            for ref in ('worker', 'attempt-' + got.attempt_id):
                try:
                    tx.get_ref(ref)
                except d.NotFoundError:
                    pass
                else:
                    raise AssertionError('copied operational B ref')
        reports.append({'label': label, 'objects': len(oracle), 'phase': got.phase,
                        'lifecycle': got.lifecycle, 'request_id': got.request_id, 'attempt_id': got.attempt_id})
    before = (caller / 'data.mdb').read_bytes()
    expected = ex.load_exchange_handle(sandbox / 'expected-0.json').expected
    malformed = sandbox / 'wrong-phase'
    shutil.copytree(sandbox / 'fetched/0-completion-0', malformed)
    receipt = json.loads((malformed / 'observation.json').read_bytes())
    receipt['phase'] = 'initial'
    (malformed / 'observation.json').write_text(json.dumps(receipt))
    wrong_q = sandbox / 'wrong-matching-Q'
    shutil.copytree(sandbox / 'fetched/1-completion-0', wrong_q)
    (wrong_q / 'job.json').write_bytes((sandbox / 'fetched/0-completion-0/job.json').read_bytes())
    receipt = json.loads((wrong_q / 'observation.json').read_bytes())
    receipt.update(token=expected.token, commit=str(expected.commit))
    (wrong_q / 'observation.json').write_text(json.dumps(receipt))
    rejected = []
    for candidate in (malformed, wrong_q):
        for operation in ('inspect', 'receive'):
            try:
                if operation == 'inspect':
                    ex.read_observation(candidate, expected=expected)
                else:
                    ex.receive_observation(caller, packet=candidate, expected=expected, ref='wrong')
            except (ex.ExchangeError, d.NotFoundError) as error:
                assert (caller / 'data.mdb').read_bytes() == before
                rejected.append(candidate.name + ':' + operation + ':' + type(error).__name__)
            else:
                raise AssertionError('wrong history accepted')
    try:
        ex.receive_observation(caller, packet=sandbox / 'fetched/0-completion-0', expected=expected, ref='return-0-initial-0')
    except transfer.RefConflictError:
        assert (caller / 'data.mdb').read_bytes() == before
        rejected.append('P-ref-to-F')
    else:
        raise AssertionError('implicit return ref advance')
    (sandbox / 'replay-result.json').write_text(json.dumps({'prior_execution_replay_only': True,
                'packets': reports, 'whole_file_equality': True, 'all_typed_packed_parent_equality': True,
                'unchanged_refs': list(fixed_refs), 'rejected': rejected}, indent=2))
    print(json.dumps({'stage': 'validate', 'packets': len(reports), 'rejections': len(rejected), 'prior_execution_replay_only': True}))


if __name__ == '__main__':
    operation, path = sys.argv[1:]
    if operation not in {'prepare', 'validate'}:
        raise ValueError('unsupported nonexecuting operation')
    globals()[operation](Path(path).resolve())
