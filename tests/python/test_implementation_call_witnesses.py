"""Exactly FOUR precise native witness/producer corruptions, ONE existing HOST seed.

TWO HOST publication assertions + source spawn blocker, not independent OS census.
Existing parent-first public typed/header rewrite only; no private codec/flags/hooks.
"""

import sys

import daggerml as d
from daggerml import builtin as b, exchange as ex, local
import pytest

from captured_call_rewrite import rewrite
from test_exchange_records import clone
from test_implementation_calls import p, adapter, host as host_fixture


@pytest.fixture(scope="module")
def seed(tmp_path_factory):
    root = tmp_path_factory.mktemp("witness-native-seed")
    path = root / "caller.dml"
    commit = p.initialize(path, sys.executable)
    commit = p.prepare_arguments(path, commit=commit, values={"a": 13, "b": 29}, inputs_name="inputs", ref="inputs")
    with pytest.MonkeyPatch.context() as patch:
        publications = host_fixture.__wrapped__(patch)  # Reuse EXACT existing labelled HOST publisher/blocker.
        original = local._execute
        def second_failed(context, source, interpreter, timeout):
            observed = original(context, source, interpreter, timeout)
            if len(publications) == 2:
                return local._Observation(7, "child-exit", "HOST double nonzero AFTER native publication", observed.stdout, observed.stderr)
            return observed
        patch.setattr(local, "_execute", second_failed)
        q = p.record_request(path, commit=commit, ref="seed-outer")
        final = adapter.execute(path, q, workspace=root / "HOST-two")
        got = p.inspect_completion(path, commit=final)
        assert len(publications) == 2 and got["outcome"] == "failure" and len(got["calls"]) == 2
    with d.Repository(path) as repo, repo.read() as tx:
        add, failure = (tx.get_dag(dag).bindings for dag in got["calls"])
        add_slot = b.scalar(tx, add["selection-slot"], "string")
        add_q = b.link(tx, tx.get_dag(b.link(tx, add["pending"])).bindings["request"])
        failed_q = b.link(tx, tx.get_dag(b.link(tx, failure["pending"])).bindings["request"])
        witness = b.link(tx, failure["witness"])
        b_binding = p.leaf.inspect(tx, p.tree(tx, final)["add-B"], *p.leaf.sources())["binding"]
    selected, returned = p.inspect_leaf_success(path, commit=final, slot=add_slot)
    received = p.inspect_failed_witness(path, final, witness, failed_q)
    assert returned.value == d.Datum.i64(42) and received.completion.outcome == "failure"
    with d.Repository(path) as repo, repo.read() as tx:
        trace = b.link(tx, tx.get_dag(selected.result).bindings["trace"])
    return dict(path=path, final=final, add_slot=add_slot, add_q=add_q, failed_q=failed_q,
                witness=witness, selection=selected, trace=trace, b_binding=b_binding)


def retain_variant(seed, tx, witness, name):
    entries = p.tree(tx, seed["final"])
    entries[name] = witness
    return tx.put_commit(tx.put_tree(entries), parents=(seed["final"],))


def test_failed_witness_wrong_REAL_add_Q_refused_BEFORE_public_packet_stage(seed, monkeypatch):
    path = seed["path"]
    with d.Repository(path) as repo, repo.write() as tx:
        wrong = clone(tx, seed["witness"], fields={"request": tx.put_subdag(seed["add_q"])})
        commit = retain_variant(seed, tx, wrong, "wrong-witness-owner")
    baseline = (path / "data.mdb").read_bytes()
    def forbidden(*a, **k):
        pytest.fail("wrong witness owner MUST reject BEFORE public framing/scratch")
    monkeypatch.setattr(ex, "load_exchange_handle", forbidden)
    monkeypatch.setattr(ex, "read_observation", forbidden)
    monkeypatch.setattr(p.tempfile, "TemporaryDirectory", forbidden)
    with pytest.raises(ValueError, match="failed leaf witness owner/retention differs"):
        p.inspect_failed_witness(path, commit, wrong, seed["failed_q"])
    assert (path / "data.mdb").read_bytes() == baseline


def test_failed_witness_header8193_refused_BEFORE_scratch_loader(seed, monkeypatch):
    assert ex.MAX_DESCRIPTOR_BYTES == 8192
    path = seed["path"]
    with d.Repository(path) as repo, repo.write() as tx:
        wrong = clone(tx, seed["witness"], fields={"expected": b.literal(tx, b"x" * 8193)})
        commit = retain_variant(seed, tx, wrong, "oversized-native-witness")
        # Positive owner/retention control: NOT an earlier mismatched-native witness failure.
        completion, headers = p.inspect_failure(tx, commit, wrong, seed["failed_q"])
        assert len(headers[0]) == 8193 and completion == p.oid(tx, tx.get_dag(wrong).bindings["completion"])
    baseline = (path / "data.mdb").read_bytes()
    def forbidden(*a, **k):
        pytest.fail("header byte cap MUST reject BEFORE scratch/public loader")
    monkeypatch.setattr(ex, "load_exchange_handle", forbidden)
    monkeypatch.setattr(p.tempfile, "TemporaryDirectory", forbidden)
    with pytest.raises(ValueError, match="failure framing exceeds public profile"):
        p.inspect_failed_witness(path, commit, wrong, seed["failed_q"])
    assert (path / "data.mdb").read_bytes() == baseline


def test_public_valid_ORIGINAL_add_D_realB_binding_exact_B_E_refusal(seed, tmp_path):
    changed = []
    def corrupt(read, write, old, fields, root):
        original = read.get_dag(old).bindings
        if ("role" in original and b.scalar(read, original["role"], "string") == p.LEAF_D_ROLE
            and b.scalar(read, original["slot"], "i64") == 0):
            fields["binding"] = write.put_subdag(seed["b_binding"])
            changed.append(old)
        return fields, root
    path = tmp_path / "binding-poison.dml"
    commit, mapping = rewrite(seed["path"], path, seed["final"], corrupt)
    assert changed
    public = p.selection.inspect(path, commit=commit, slot=seed["add_slot"])
    assert public.binding == seed["selection"].binding and public.request == seed["selection"].request
    assert public.result == seed["selection"].result  # PUBLIC completed S/F still valid, not fake flags.
    baseline = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="ORIGINAL exact leaf B/E differs"):
        p.inspect_leaf_success(path, commit=commit, slot=seed["add_slot"])
    assert (path / "data.mdb").read_bytes() == baseline


def test_public_valid_returned_shape_removed_actual_add_getter_position(seed, tmp_path):
    changed = []
    def corrupt(read, write, old, fields, root):
        if old == seed["trace"]:
            assert "call-01" in fields
            del fields["call-01"]
            changed.append(old)
        return fields, root
    path = tmp_path / "getter-poison.dml"
    commit, mapping = rewrite(seed["path"], path, seed["final"], corrupt)
    assert changed == [seed["trace"]]
    public = p.selection.inspect(path, commit=commit, slot=seed["add_slot"])
    with d.Repository(path) as repo, repo.read() as tx:
        inspector = b.Inspector(tx, commit=commit)
        returned = inspector.node(public.result)
        fields = tx.get_dag(public.result).bindings
        trace = inspector.trace(b.link(tx, fields["trace"]), request=public.request, inputs=public.inputs)
        assert returned.value == d.Datum.i64(42) and len(trace) == 1
    baseline = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="ORIGINAL getter positions differ"):
        p.inspect_leaf_success(path, commit=commit, slot=seed["add_slot"])
    assert (path / "data.mdb").read_bytes() == baseline
