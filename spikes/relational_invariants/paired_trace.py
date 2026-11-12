"""Test-only observation/counters around unchanged existing assertion bodies."""

from collections import Counter, defaultdict
from contextlib import redirect_stderr, redirect_stdout
from functools import wraps
import hashlib
import inspect
import io
from pathlib import Path
import sys
import time
from unittest.mock import patch
import weakref

import daggerml as dml
from daggerml import local


class Trace:
    def __init__(self, monkeypatch, directory):
        self.directory = Path(directory)
        self.owners, self.transactions = weakref.WeakKeyDictionary(), weakref.WeakKeyDictionary()
        self.pending, self.pending_refs = weakref.WeakKeyDictionary(), weakref.WeakKeyDictionary()
        self.roots, self.refs = defaultdict(set), defaultdict(dict)
        self.reads = Counter()
        self.scopes, self.transitions, self.reuses = [], [], []
        self.host_calls = 0
        self.body_started = None
        self.setup_started = time.perf_counter()
        self._instrument(monkeypatch)

    def _instrument(self, monkeypatch):
        init, read, write = dml.Repository.__init__, dml.Repository.read, dml.Repository.write
        get, put, rawput = dml.Transaction.get_record, dml.Transaction.put_commit, dml.Transaction.put_record
        commit = dml.Transaction.commit
        create, update = dml.Transaction.create_ref, dml.Transaction.update_ref
        def owner_init(owner, path, **kwargs):
            init(owner, path, **kwargs)
            self.owners[owner] = str(Path(path).resolve())
        def transaction(method):
            @wraps(method)
            def run(owner):
                tx = method(owner)
                self.transactions[tx] = self.owners[owner]
                return tx
            return run
        def record(tx, kind, oid):
            self.reads[kind, str(oid)] += 1
            return get(tx, kind, oid)
        def put_commit(tx, *args, **kwargs):
            oid = put(tx, *args, **kwargs)
            self.pending.setdefault(tx, []).append(str(oid))
            return oid
        def put_record(tx, kind, raw):
            oid = rawput(tx, kind, raw)
            if kind == 'commit':
                self.pending.setdefault(tx, []).append(str(oid))
            return oid
        def ref(method):
            @wraps(method)
            def run(tx, name, oid):
                result = method(tx, name, oid)
                self.pending_refs.setdefault(tx, []).append((name, str(oid)))
                return result
            return run
        def committed(tx):
            result = commit(tx)
            path = self.transactions[tx]
            self.roots[path].update(self.pending.pop(tx, ()))
            self.refs[path].update(self.pending_refs.pop(tx, ()))
            return result
        monkeypatch.setattr(dml.Repository, '__init__', owner_init)
        monkeypatch.setattr(dml.Repository, 'read', transaction(read))
        monkeypatch.setattr(dml.Repository, 'write', transaction(write))
        monkeypatch.setattr(dml.Transaction, 'get_record', record)
        monkeypatch.setattr(dml.Transaction, 'put_commit', put_commit)
        monkeypatch.setattr(dml.Transaction, 'put_record', put_record)
        monkeypatch.setattr(dml.Transaction, 'commit', committed)
        monkeypatch.setattr(dml.Transaction, 'create_ref', ref(create))
        monkeypatch.setattr(dml.Transaction, 'update_ref', ref(update))

    def begin_body(self):
        self.setup_seconds = time.perf_counter() - self.setup_started
        self.setup_reads = sum(self.reads.values())
        self.reads.clear()
        self.body_started = time.perf_counter()

    def end_body(self):
        self.body_seconds = time.perf_counter() - self.body_started
        self.body_reads = sum(self.reads.values())
        self.body_unique = len(self.reads)

    def scope(self, monkeypatch, module, name, kind):
        original = getattr(module, name)
        signature = inspect.signature(original)
        @wraps(original)
        def observed(*args, **kwargs):
            bound = dict(signature.bind(*args, **kwargs).arguments)
            row = {'kind': kind, 'args': bound}
            if kind == 'candidate':
                import json
                packet = Path(bound['packet'])
                row['receipt'] = json.loads((packet / 'observation.json').read_text())
                row['job'] = json.loads((packet / 'job.json').read_text())
                bundle = (packet / 'snapshot.bundle').read_bytes()
                row['bundle_root'] = json.loads(bundle)['root']
                row['bundle_sha256'] = hashlib.sha256(bundle).hexdigest()
                expected = bound['expected']
                row['expected_job'] = {'format': 'daggerml-local-exchange-job-v2',
                    'token': expected.token, 'commit': str(expected.commit),
                    'binding_name': expected.binding_name, 'inputs_name': expected.inputs_name,
                    'binding': str(expected.binding), 'inputs': str(expected.inputs),
                    'intent_uri': expected.intent_uri, 'worker_ref': expected.worker_ref,
                    'request': None if expected.request is None else str(expected.request)}
                row['expected'] = {key: str(getattr(expected, key)) for key in
                                   ('request', 'binding', 'inputs', 'intent_uri')}
            try:
                result = original(*args, **kwargs)
            except (ValueError, KeyError, TypeError) as error:
                row.update(accepted=False, error=type(error).__name__ + ': ' + str(error))
                self.scopes.append(row)
                raise
            row.update(accepted=True, action=result[-2] if kind == 'resolve' else None)
            self.scopes.append(row)
            return result
        monkeypatch.setattr(module, name, observed)

    def transition(self, monkeypatch, module, name, kind):
        original = getattr(module, name)
        signature = inspect.signature(original)
        @wraps(original)
        def observed(*args, **kwargs):
            bound = dict(signature.bind(*args, **kwargs).arguments)
            before = str(bound['commit'])
            try:
                result = original(*args, **kwargs)
            except (ValueError, KeyError, TypeError):
                raise  # Rejected operation remains covered by existing assertions/scopes.
            self.transitions.append({'kind': kind, 'before': before, 'after': str(result.commit),
                                     'slot': bound.get('slot', bound.get('table_name')),
                                     'inputs': str(bound.get('inputs', '')),
                                     'selection_slot': bound.get('selection_slot', '')})
            return result
        monkeypatch.setattr(module, name, observed)

    def reuse(self, monkeypatch, module, name):
        original = getattr(module, name)
        @wraps(original)
        def observed(*args, **kwargs):
            result = original(*args, **kwargs)
            recorded = result.recorded
            satisfaction = result.reused if hasattr(result, 'reused') else result
            if satisfaction is not None:
                selected = result.decision.selected if hasattr(result, 'decision') else None
                if selected is not None and hasattr(selected, 'selected'):
                    selected = selected.selected
                self.reuses.append({'submission': str(recorded.commit), 'request': str(recorded.request),
                                    'satisfaction': str(satisfaction.commit),
                                    'selection': str(selected.dag) if selected else '',
                                    'basis': str(recorded.base), 'slot': kwargs.get('slot', '')})
            return result
        monkeypatch.setattr(module, name, observed)

    def host_execute(self, context, source, interpreter, timeout):
        """Trusted fixed generic test sources only, not a sandbox or child proof."""
        from test_composed_execution import ADD, DOUBLE
        allowed = (ADD, DOUBLE, DOUBLE + b'\nimport sys;sys.exit(23)\n',
                   DOUBLE + b'\n# Distinct captured implementation B\n')
        if source not in allowed:
            raise AssertionError('HOST seam refuses source outside selected fixed tests')
        self.host_calls += 1
        stdout, stderr, code = io.StringIO(), io.StringIO(), 0
        argv = ['HOST-entry', context.repository_path, str(context.pre_dispatch),
                context.attempt_id, context.publication_ref]
        with patch.object(sys, 'argv', argv), redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                exec(compile(source, 'HOST-selected-existing-source', 'exec'), {'__name__': '__main__'})
            except SystemExit as exit:
                code = 0 if exit.code is None else exit.code
                if type(code) is not int:
                    raise AssertionError('unsupported HOST exit code')
        out, err = stdout.getvalue().encode(), stderr.getvalue().encode()
        return local._Observation(code, 'child-exit' if code else None, 'HOST observation' if code else '',
                                  (out, len(out)), (err, len(err)))
