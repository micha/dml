"""Inspection-local copied-read reuse; original authority/lifetime guards remain."""

import threading

import daggerml as d
import pytest

from test_captured_calls import app, initial


def test_copied_reads_shared_across_native_transactions_not_top_level_calls(initial, monkeypatch):
    path, commit = initial
    calls = []
    real = d.Transaction.get_commit
    def measured(tx, oid):
        calls.append(oid)
        return real(tx, oid)
    monkeypatch.setattr(d.Transaction, "get_commit", measured)

    @app._inspection_proof
    def inspect(path, *, commit, seen=None, depth=0):
        with app._read(path) as first:
            got = first.get_commit(commit)
            assert first.get_commit(commit) is got
        with pytest.raises(d.InvalidStateError):
            first.get_commit(commit)
        with app._read(path) as second:
            assert second.get_commit(commit) is got
            with pytest.raises(AttributeError):
                second.put_commit(got.tree)
        return got

    first = inspect(path, commit=commit)
    assert calls == [commit]
    assert inspect(path, commit=commit) == first
    assert calls == [commit, commit]
    assert app._inspection_proofs.get() is None


def test_cache_hit_checks_real_transaction_abort_and_thread(initial):
    path, commit = initial
    with d.Repository(path) as repo:
        with repo.read() as tx:
            view = app._InspectionReads(tx, [{}, 0])
            view.get_commit(commit)
            errors = []
            def foreign():
                try:
                    view.get_commit(commit)
                except d.InvalidStateError as error:
                    errors.append(error)
            thread = threading.Thread(target=foreign)
            thread.start()
            thread.join()
            assert len(errors) == 1
            tx.abort()
            with pytest.raises(d.InvalidStateError):
                view.get_commit(commit)


def test_mutable_ref_values_are_never_memoized(initial, monkeypatch):
    path, commit = initial
    values = [commit, d.ObjectId(b"z" * 16)]
    calls = []
    real = d.Transaction.get_ref
    def current(tx, name):
        if name == "main":
            calls.append(name)
            return values[len(calls) - 1]
        return real(tx, name)
    monkeypatch.setattr(d.Transaction, "get_ref", current)
    with d.Repository(path) as repo, repo.read() as tx:
        view = app._InspectionReads(tx, [{}, 0])
        assert view.get_ref("main") == values[0]
        assert view.get_ref("main") == values[1]
    assert calls == ["main", "main"]


def test_failures_invalid_inputs_and_probe_errors_are_not_hidden(initial, monkeypatch):
    path, commit = initial
    missing = d.ObjectId(b"x" * 16)
    with d.Repository(path) as repo, repo.read() as tx:
        cache = [{}, 0]
        view = app._InspectionReads(tx, cache)
        for _ in range(2):
            with pytest.raises(d.NotFoundError):
                view.get_commit(missing)
        assert not cache[0]
        with pytest.raises(TypeError):
            view.get_commit("not an ID")
        with pytest.raises(ValueError):
            view.get_record("unsupported", commit)
        view.get_commit(commit)
        def broken(tx, name):
            raise d.IntegrityError("integrity_error")
        monkeypatch.setattr(d.Transaction, "get_ref", broken)
        with pytest.raises(d.IntegrityError):
            view.get_commit(commit)


def test_native_getter_changes_and_repository_paths_do_not_share_results(initial, tmp_path, monkeypatch):
    path, commit = initial
    calls = []
    real = d.Transaction.get_commit
    with d.Repository(path) as repo, repo.read() as tx:
        view = app._InspectionReads(tx, [{}, 0])
        got = view.get_commit(commit)
        def changed(tx, oid):
            calls.append(oid)
            return real(tx, oid)
        monkeypatch.setattr(d.Transaction, "get_commit", changed)
        assert view.get_commit(commit) == got
        assert calls == [commit]
    other = tmp_path / "other"
    with d.Repository(other, create=True):
        pass
    @app._inspection_proof
    def inspect(path, *, commit, seen=None, depth=0):
        with app._read(path) as tx:
            tx.get_commit(commit)
        with app._read(other) as tx:
            with pytest.raises(d.NotFoundError):
                tx.get_commit(commit)
    inspect(path, commit=commit)


def test_record_byte_and_entry_caps_limit_memory_not_validity(initial, monkeypatch):
    path, commit = initial
    with d.Repository(path) as repo, repo.write() as tx:
        payload = tx.put_datum(b"copied payload budget")
    with d.Repository(path) as repo, repo.read() as tx:
        cache = [{}, 0]
        view = app._InspectionReads(tx, cache)
        monkeypatch.setattr(app.transfer, "MAX_PACKED_BYTES", 1)
        assert view.get_record("commit", commit)
        assert view.get_datum(payload).value == b"copied payload budget"
        assert not cache[0]
        monkeypatch.setattr(app.transfer, "MAX_OBJECTS", 0)
        assert view.get_commit(commit)
        assert not cache[0]


def test_public_snapshot_checks_revalidate_changed_limits_and_functions(initial, monkeypatch):
    path, commit = initial
    calls = []
    def exported(path, *, commit):
        calls.append(commit)
        return b"not retained in memo"
    monkeypatch.setattr(app.transfer, "export_commit", exported)
    @app._inspection_proof
    def inspect(path, *, commit, seen=None, depth=0):
        app._validated_snapshot(path, commit)
        app._validated_snapshot(path, commit)
        assert calls == [commit]
        monkeypatch.setattr(app.transfer, "MAX_OBJECTS", 1)
        app._validated_snapshot(path, commit)
        assert calls == [commit, commit]
        def refused(*a, **k):
            raise ValueError("refused snapshot")
        monkeypatch.setattr(app.transfer, "export_commit", refused)
        for _ in range(2):
            with pytest.raises(ValueError, match="refused"):
                app._validated_snapshot(path, commit)
    inspect(path, commit=commit)


def test_inspectors_preserve_seen_and_active_state_and_do_not_cross_transactions(initial):
    path, commit = initial
    @app._inspection_proof
    def inspect(path, *, commit, seen=None, depth=0):
        with app._read(path) as tx:
            first = app._inspector(tx, commit)
            first.seen.add(commit)
            assert app._inspector(tx, commit) is first
            assert first.seen == {commit}
            first.active.add(commit)
            second = app._inspector(tx, commit)
            assert second is not first and first.active == {commit}
            first.active.remove(commit)
        with app._read(path) as tx:
            third = app._inspector(tx, commit)
            assert third is not first and not third.seen
    inspect(path, commit=commit)


def test_recursive_proofs_recheck_changed_authority_and_semantic_bounds(tmp_path, monkeypatch):
    calls = []
    @app._inspection_proof
    def child(path, *, commit, seen=None, depth=0):
        calls.append(commit)
        return commit
    @app._inspection_proof
    def parent(path, *, commit, seen=None, depth=0):
        child(path, commit=commit)
        child(path, commit=commit)
        assert calls == [commit]
        monkeypatch.setattr(app.b, "MAX_RECORDS", 63)
        child(path, commit=commit)
        monkeypatch.setattr(app, "MAX_AUTHORITY_DEPTH", 7)
        child(path, commit=commit)
        monkeypatch.setattr(app.transfer, "MAX_OBJECTS", 1)
        child(path, commit=commit)
        assert calls == [commit] * 4
    parent(tmp_path, commit="pinned")
    assert app._inspection_proofs.get() is None


def test_lookup_and_typed_record_views_use_public_data(initial):
    path, commit = initial
    with d.Repository(path) as repo, repo.read() as tx:
        view = app._InspectionReads(tx, [{}, 0])
        tree = view.get_tree(view.get_commit(commit).tree)
        dag = tree["outer"]
        got = view.get_dag(dag)
        node = view.lookup_node(dag, "role")
        assert view.lookup_node(dag, "role") == node
        assert view.get_node(node) == tx.get_node(node)
        assert view.get_datum(view.get_node(node).datum) == tx.get_datum(tx.get_node(node).datum)
        assert view.get_record("dag", dag) == tx.get_record("dag", dag)
        assert got.bindings["role"] == node
        with pytest.raises(TypeError):
            view.lookup_node(dag, 1)
