"""Inspection-owned readonly capabilities/lifetime and actual getter source/type contract."""

import threading

import daggerml as d
from daggerml import builtin as b
import pytest

from test_implementation_calls import initial, p


def test_inspection_copied_reads_NEVER_grant_writer_or_stale_owner_state(initial):
    path, commit = initial
    with d.Repository(path) as repo, repo.read() as tx:
        view = p._InspectionReads(tx, [{}, 0])
        with pytest.raises(AttributeError):
            view.write()
        one = view.get_commit(commit)
        assert view.get_commit(commit) == one
        failures = []
        def wrong_thread():
            try:
                view.get_commit(commit)
            except d.InvalidStateError:
                failures.append(True)
        thread = threading.Thread(target=wrong_thread)
        thread.start()
        thread.join()
        assert failures == [True]
        tx.abort()
        with pytest.raises(d.InvalidStateError):
            view.get_commit(commit)
        view._open = False
        with pytest.raises(d.InvalidStateError, match="ended"):
            view.get_commit(commit)


def test_native_occurrence_name_parent_tree_and_I64_input_contracts(initial):
    path, commit = initial
    with pytest.raises(ValueError, match="name"):
        p.name("space forbidden")
    with pytest.raises(ValueError, match="depth"):
        p.authority_depth(True)
    with d.Repository(path) as repo, repo.write() as tx:
        entries = p.tree(tx, commit)
        for occurrence in ("not-an-occurrence", "ia-" + "f" * 32):
            dag = p.event(tx, p.Q_ROLE, occurrence)
            with pytest.raises(ValueError, match="root"):
                p.occurrence(tx, dag, p.Q_ROLE, "iq-", ())
        wrong = p.event(tx, "wrong-role", "iq-" + "f" * 32)
        with pytest.raises(ValueError, match="role"):
            p.occurrence(tx, wrong, p.Q_ROLE, "iq-", ())
        with pytest.raises(ValueError, match="parent"):
            p.single_delta(tx, tx.get_commit(commit).parents[0], ("additional",))
        with pytest.raises(ValueError, match="absent-name"):
            p.single_delta(tx, commit, ("additional",))
    with pytest.raises(ValueError, match="a,b"):
        p.prepare_arguments(path, commit=commit, values={"x": 1}, inputs_name="bad", ref="bad")
    with pytest.raises(ValueError, match="absent"):
        p.prepare_source_arguments(path, commit=commit, values={"a": 1, "b": 2}, inputs_name="inputs", ref="bad")
    with pytest.raises(ValueError, match="a,b"):
        p.prepare_source_arguments(path, commit=commit, values={}, inputs_name="bad", ref="bad")
    with pytest.raises(ValueError, match="exists"):
        p.prepare_arguments(path, commit=commit, values={"a": 1, "b": 2}, inputs_name="inputs", ref="bad")


def test_valid_native_getter_wrong_source_binding_order_or_kind_is_not_own_getter(initial):
    path, commit = initial
    with d.Repository(path) as repo, repo.write() as tx:
        entries = p.tree(tx, commit)
        with b.Recorder(tx, commit=commit) as recorder:
            inputs = recorder.load(entries["inputs"])
            first_args = recorder.arguments({"map": inputs, "key": recorder.literal("a")})
            getter = recorder.dag(recorder.call(b.MAP_GET, entries["map-v1"], first_args))
            entries["getter"] = getter
            new = tx.put_commit(tx.put_tree(entries), parents=(commit,))
    with d.Repository(path) as repo, repo.read() as tx:
        assert p.inspect_getter(tx, new, getter, entries["inputs"], "a", entries["map-v1"], set()).value == d.Datum.i64(13)
        with pytest.raises(ValueError, match="source/binding"):
            p.inspect_getter(tx, new, getter, entries["inputs"], "a", entries["map-v2"], set())
        with pytest.raises(ValueError, match="order/I64"):
            p.inspect_getter(tx, new, getter, entries["inputs"], "b", entries["map-v1"], set())
    with d.Repository(path) as repo, repo.write() as tx:
        with b.Recorder(tx, commit=new) as recorder:
            boolean = recorder.arguments({"a": recorder.literal(True), "b": recorder.literal(29)})
            boolean_dag = recorder.dag(boolean)
            more = dict(entries, **{"bool-inputs": boolean_dag})
            last = tx.put_commit(tx.put_tree(more), parents=(new,))
    with d.Repository(path) as repo, repo.read() as tx:
        with pytest.raises(ValueError, match="I64"):
            p.arguments(tx, last, boolean_dag, ("a", "b"), set())
