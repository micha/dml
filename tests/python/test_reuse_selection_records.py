"""Strict native S/V and public capsule authority; meaningful pre-write rejection."""

import json
from pathlib import Path
import shutil
import sys

import daggerml as d
from daggerml import exchange as ex, local, transfer
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_caller_requests import assert_file_unchanged, track_typed_puts
from test_composed_execution import producer, execute, DOUBLE
from test_exchange import exchange_runtime, literal, nested, scalar, tree, typed_oracle
from test_exchange_records import clone
from test_explicit_reuse import double
from test_records_hypothesis import run_driver
from test_reuse_selection import app, expected_file, select


@pytest.fixture
def selection(double, expected_file):
    return select(double, expected_file)


def reuse(path, commit, **changes):
    arguments = dict(
        commit=commit,
        slot="selected-double",
        binding_name="double-binding",
        inputs_name="double-inputs",
        intent_uri="urn:example:double",
        submission_ref="reuse-submission",
        ref="reused-double",
    )
    arguments.update(changes)
    return app.reuse_selected(path, **arguments)


def adopt(path, commit, fresh, **changes):
    expected = changes.get("expected_file", path.parent / "fresh-expected.json")
    if not expected.exists():
        ex.save_exchange_handle(expected, ex.ExchangeHandle(fresh[4], fresh[1]))
    arguments = dict(
        commit=commit,
        slot="selected-double",
        binding_name="double-binding",
        inputs_name="double-inputs",
        intent_uri="urn:example:double",
        expected_file=expected,
        packet=fresh[0],
        ref="adopt-fresh",
    )
    arguments.update(changes)
    return app.adopt(path, **arguments)


def changed(path, basis, dag):
    with d.Repository(path) as repository, repository.write() as tx:
        entries = tree(tx, basis)
        entries["selected-double"] = dag
        return tx.put_commit(tx.put_tree(entries), parents=(basis,))


@pytest.mark.parametrize(
    "role,mode",
    [
        ("S", "missing"),
        ("S", "extra"),
        ("S", "root"),
        ("S", "role"),
        ("S", "literal-node"),
        ("S", "subdag-node"),
        ("S", "datum-kind"),
        ("S", "F-short"),
        ("S", "F-long"),
        ("V", "missing"),
        ("V", "extra"),
        ("V", "root"),
        ("V", "subdag-node"),
        ("V", "datum-kind"),
        ("V", "oversized"),
    ],
)
def test_native_exact_fields_roots_node_datum_and_completion_bounds_before_Q(
    double, selection, role, mode
):
    path = double[0][0]
    with d.Repository(path) as repository, repository.write() as tx:
        selected = selection.dag if role == "S" else selection.validation
        fields = dict(tx.get_dag(selected).bindings)
        root = tx.get_dag(selected).root
        target = "intent" if role == "S" else "job"
        if mode == "missing":
            fields.pop(target)
        elif mode == "extra":
            fields["extra"] = literal(tx, 0)
        elif mode == "root":
            root = fields["role"] if role == "S" else fields["job"]
        elif mode == "role":
            fields["role"] = literal(tx, "wrong-role")
        elif mode == "literal-node":
            fields["attempt"] = literal(tx, "not a sub-DAG")
        elif mode == "subdag-node":
            fields[target] = tx.put_subdag(selection.result)
        elif mode == "datum-kind":
            fields[target] = literal(tx, True)
        elif mode.startswith("F-"):
            fields["completion"] = literal(tx, b"x" * (15 if mode == "F-short" else 17))
        else:
            fields["job"] = literal(tx, b"x" * 8193)
        dag = tx.put_dag(root=root, bindings=fields)
        if role == "V":
            dag = clone(tx, selection.dag, fields={"validation": tx.put_subdag(dag)})
    basis = changed(path, selection.commit, dag)
    before = (path / "data.mdb").read_bytes()
    baseline = typed_oracle(path, (basis,))
    with track_typed_puts(path, baseline) as puts:
        with pytest.raises(ValueError):
            app.inspect(path, commit=basis, slot=selection.slot)
        with pytest.raises(ValueError):
            reuse(path, basis)
    assert not puts
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize(
    "field",
    ["attempt", "result", "request", "completion", "expected", "job", "observation"],
)
def test_typed_complete_partial_swap_to_another_matching_success_rejects(
    double, selection, field
):
    path = double[0][0]
    alternate = execute(
        path, selection.commit, "alternate-double", "double-binding", "double-inputs"
    )
    saved = path.parent / "alternate-expected.json"
    ex.save_exchange_handle(saved, ex.ExchangeHandle(alternate[4], alternate[1]))
    assert alternate[2].result == selection.result
    # Result equality does not create a different result ID; construct another
    # complete typed result with equal84 but different structure for the R swap.
    with d.Repository(path) as repository, repository.write() as tx:
        if field in {"attempt", "result", "request", "completion"}:
            if field == "result":
                node = literal(tx, 84)
                other = tx.put_dag(root=node, bindings={"other-result": node})
                replacement = tx.put_subdag(other)
            elif field == "completion":
                replacement = literal(tx, alternate[2].commit.bytes)
            else:
                other = (
                    alternate[2].completion.final_attempt
                    if field == "attempt"
                    else alternate[2].request
                )
                replacement = tx.put_subdag(other)
            fields = {field: replacement}
            dag = clone(tx, selection.dag, fields=fields)
            if field == "result":
                dag = clone(tx, selection.dag, fields=fields, root=replacement)
        else:
            data = (
                saved.read_bytes()
                if field == "expected"
                else (
                    alternate[0]
                    / ("job.json" if field == "job" else "observation.json")
                ).read_bytes()
            )
            validation = clone(
                tx, selection.validation, fields={field: literal(tx, data)}
            )
            if field == "expected":
                validation = clone(
                    tx,
                    selection.validation,
                    fields={field: literal(tx, data)},
                    root=literal(tx, data),
                )
            dag = clone(
                tx, selection.dag, fields={"validation": tx.put_subdag(validation)}
            )
    basis = changed(path, alternate[2].commit, dag)
    # Export/import prove complete native closure, not a missing-Q setup rejection.
    validation = path.parent / "typed-validation"
    with d.Repository(validation, create=True):
        pass
    transfer.import_commit(validation, transfer.export_commit(path, commit=basis))
    assert typed_oracle(validation, (basis,)) == typed_oracle(path, (basis,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, d.DmlError)):
        reuse(path, basis)
    assert_file_unchanged(path / "data.mdb", before)


def test_fully_coherent_alternative_selection_and_explicit_adoption_sibling_branches(
    double, selection
):
    path = double[0][0]
    old_reuse = reuse(path, selection.commit)
    before_fresh = typed_oracle(path, (old_reuse.commit,))
    fresh = execute(
        path, old_reuse.commit, "fresh-double", "double-binding", "double-inputs"
    )
    assert fresh[2].result == selection.result
    assert fresh[2].completion.final_attempt != selection.attempt
    assert (
        app.inspect(path, commit=fresh[2].commit, slot=selection.slot).attempt
        == selection.attempt
    )
    with d.Repository(path) as repository, repository.write() as tx:
        keep = tx.put_commit(
            tx.get_commit(fresh[2].commit).tree, parents=(fresh[2].commit,)
        )
        tx.create_ref("keep-old", keep)
    adopted = adopt(path, fresh[2].commit, fresh)
    assert adopted.attempt == fresh[2].completion.final_attempt
    with d.Repository(path) as repository, repository.read() as tx:
        assert (
            tx.get_commit(keep).parents
            == tx.get_commit(adopted.commit).parents
            == (fresh[2].commit,)
        )
        entries = tree(tx, fresh[2].commit)
        entries[selection.slot] = adopted.dag
        assert tree(tx, adopted.commit) == entries
        assert tree(tx, keep) == tree(tx, fresh[2].commit)
        assert nested(tx, old_reuse.dag, "attempt") == selection.attempt
        assert all(tx.get_record(*key) == raw for key, raw in before_fresh.items())
    for branch, target, suffix in (
        (keep, selection.attempt, "old"),
        (adopted.commit, adopted.attempt, "fresh"),
    ):
        got = reuse(
            path,
            branch,
            submission_ref="branch-submission-" + suffix,
            ref="branch-reuse-" + suffix,
        )
        assert got.attempt == target and got.result == selection.result
        assert got.recorded.base == branch
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="distinct attempt occurrence"):
        adopt(path, adopted.commit, fresh, ref="no-op")
    assert_file_unchanged(path / "data.mdb", before)
    # Fully coherent alternate S is a deliberately valid choice, not detectable fraud.
    saved = path.parent / "fresh-expected.json"
    coherent = select(
        double,
        saved,
        commit=fresh[2].commit,
        slot="alternate-choice",
        packet=fresh[0],
        ref="coherent",
    )
    assert (
        app.inspect(path, commit=coherent.commit, slot=coherent.slot).attempt
        == adopted.attempt
    )


@pytest.mark.parametrize("phase", ["initial", "publication"])
def test_nonfinal_packets_never_select_or_adopt(
    double, expected_file, selection, phase
):
    path = double[0][0]
    progress = execute(
        path,
        selection.commit,
        "nonfinal",
        "double-binding",
        "double-inputs",
        phase=phase,
    )
    saved = path.parent / "nonfinal-expected.json"
    ex.save_exchange_handle(saved, ex.ExchangeHandle(progress[4], progress[1]))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="successful recorded F"):
        select(
            double,
            saved,
            commit=progress[2].commit,
            packet=progress[0],
            slot="new-choice",
            ref="nonfinal",
        )
    with pytest.raises(ValueError, match="successful recorded F"):
        adopt(path, progress[2].commit, progress, expected_file=saved)
    assert_file_unchanged(path / "data.mdb", before)


def test_failed_F_evidence_84_and_cleanup_success_policy(
    double, selection, monkeypatch
):
    path = double[0][0]
    with d.Repository(path) as repository, repository.write() as tx:
        entries = tree(tx, selection.commit)
        entries["double-binding"] = local.put_local_binding(
            tx,
            source=DOUBLE + b"\nimport sys;sys.exit(23)\n",
            interpreter=sys.executable,
            timeout_ms=10000,
        )
        base = tx.put_commit(tx.put_tree(entries), parents=(selection.commit,))
    failed = execute(path, base, "failed-double", "double-binding", "double-inputs")
    assert failed[2].completion.evidence == selection.result
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="successful recorded F"):
        adopt(path, failed[2].commit, failed)
    assert_file_unchanged(path / "data.mdb", before)
    original = shutil.rmtree

    def denied(path, *a, **k):
        if Path(path).name.startswith("dml-local-"):
            raise PermissionError("private known cleanup failure")
        return original(path, *a, **k)

    with monkeypatch.context() as guard:
        guard.setattr(shutil, "rmtree", denied)
        fresh = execute(
            path, selection.commit, "cleanup-double", "double-binding", "double-inputs"
        )
    try:
        assert (
            fresh[2].completion.cleanup == "failed"
            and fresh[2].completion.outcome == "success"
        )
        got = adopt(
            path, fresh[2].commit, fresh, expected_file=path.parent / "cleanup-expected"
        )
        assert (
            app.inspect(path, commit=got.commit, slot=got.slot).attempt
            == fresh[2].completion.final_attempt
        )
    finally:
        original(fresh[3].context.scratch)


@pytest.mark.parametrize("damage", ["missing", "corrupt"])
def test_genuine_damaged_composite_only_basis_rejects_inspect_reuse_and_adopt(
    double, selection, damage
):
    path = double[0][0]
    with d.Repository(path) as repository, repository.write() as tx:
        leaf = tx.put_datum("deep-composite-child")
        raw = tx.get_record("datum", leaf)
        composite = tx.put_datum(d.Datum.list([tx.put_datum(d.Datum.list([leaf]))]))
        entries = tree(tx, selection.commit)
        entries["composite"] = tx.put_dag(root=tx.put_literal(composite))
        basis = tx.put_commit(tx.put_tree(entries), parents=(selection.commit,))
    if damage == "missing":
        run_driver("raw-delete", str(path), "objects/datums/" + str(leaf))
    else:
        run_driver(
            "raw-write", str(path), "objects/datums/" + str(leaf), data=raw[:-1] + b"X"
        )
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(d.DmlError):
        app.inspect(path, commit=basis, slot=selection.slot)
    with pytest.raises(d.DmlError):
        reuse(path, basis)
    with pytest.raises(d.DmlError):
        adopt(path, basis, double[2])
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize(
    "role,field",
    [
        ("S", n)
        for n in (
            "role",
            "intent",
            "binding",
            "inputs",
            "request",
            "attempt",
            "result",
            "completion",
            "validation",
        )
    ]
    + [("V", n) for n in ("expected", "job", "observation")],
)
@pytest.mark.parametrize("mode", ["missing", "wrong-node-or-datum"])
def test_EVERY_native_selection_validation_field_required_and_typed(
    double, selection, role, field, mode
):
    path = double[0][0]
    with d.Repository(path) as repository, repository.write() as tx:
        target = selection.dag if role == "S" else selection.validation
        fields = dict(tx.get_dag(target).bindings)
        if mode == "missing":
            fields.pop(field)
        else:
            # All scalar fields must be correctly typed literals; all DAG links
            # must be sub-DAG nodes. Exact root handling is tested independently.
            scalar_field = role == "V" or field in {"role", "intent", "completion"}
            fields[field] = (
                literal(tx, 1) if scalar_field else literal(tx, b"not a DAG")
            )
        root = tx.get_dag(target).root
        if field in fields and field == ("result" if role == "S" else "expected"):
            root = fields[field]
        dag = tx.put_dag(root=root, bindings=fields)
        if role == "V":
            dag = clone(tx, selection.dag, fields={"validation": tx.put_subdag(dag)})
    basis = changed(path, selection.commit, dag)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        reuse(path, basis)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("field", ["intent", "binding", "inputs"])
def test_complete_valid_S_computation_claim_swap_rejected_against_public_fields(
    double, selection, field
):
    path = double[0][0]
    with d.Repository(path) as repository, repository.write() as tx:
        value = (
            literal(tx, d.Datum.uri("urn:other:intent"))
            if field == "intent"
            else tx.put_subdag(
                tree(tx, double[2][2].commit)[
                    "add-binding" if field == "binding" else "add-inputs"
                ]
            )
        )
        dag = clone(tx, selection.dag, fields={field: value})
    basis = changed(path, selection.commit, dag)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="PUBLIC validated"):
        reuse(path, basis)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize(
    "field,value",
    [
        ("token", "0" * 32),
        ("commit", "0" * 32),
        ("selected_commit", "0" * 32),
        ("pre_dispatch", "0" * 32),
        ("request_id", "q-" + "0" * 32),
        ("attempt_id", "a-" + "0" * 32),
        ("phase", "initial"),
    ],
)
def test_partial_stored_V_receipt_claim_swap_public_inspector_rejects(
    double, selection, field, value
):
    path = double[0][0]
    with d.Repository(path) as repository, repository.write() as tx:
        document = json.loads(scalar(tx, selection.validation, "observation"))
        document[field] = value
        validation = clone(
            tx,
            selection.validation,
            fields={"observation": literal(tx, json.dumps(document).encode())},
        )
        dag = clone(tx, selection.dag, fields={"validation": tx.put_subdag(validation)})
    basis = changed(path, selection.commit, dag)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ex.ExchangeError, d.DmlError)):
        reuse(path, basis)
    assert_file_unchanged(path / "data.mdb", before)


def test_deep_wrong_T_to_other_matching_Q_uses_same_public_rejection_before_selection(
    double, expected_file, monkeypatch
):
    # Reuse the existing exact-Cq/retained-Q typed-complete wrong-T history builder,
    # NOT its authoring operation. The intercepted public candidate is our select;
    # its original native completeness/association and no-write assertions remain.
    import test_explicit_reuse_selection as previous

    calls = []

    def selecting(path, **arguments):
        calls.append(True)
        return app.select(
            path,
            commit=arguments["commit"],
            slot="selected-double",
            binding_name=arguments["binding_name"],
            inputs_name=arguments["inputs_name"],
            intent_uri=arguments["intent_uri"],
            packet=arguments["historical_packet"],
            expected_file=expected_file,
            ref="wrong-Q-choice",
        )

    monkeypatch.setattr(previous.app, "reuse_attempt", selecting)
    previous.test_complete_wrong_t_to_matching_q_packet_rejected_by_public_authority(
        double
    )
    assert calls == [True]


def test_public_valid_later_description_of_SAME_occurrence_is_not_fresh_adoption(
    double, expected_file, selection
):
    path = double[0][0]
    original = ex.read_observation(double[2][0], expected=double[2][1])
    with d.Repository(path) as repository, repository.write() as tx:
        # Ordinary public authoring of another coherent final report, NOT fresh
        # execution: P/Q/attempt occurrence/result are exactly unchanged.
        cleanup = clone(
            tx,
            original.completion.cleanup_dag,
            fields={"detail": literal(tx, "later cleanup description")},
        )
        attempt = clone(
            tx,
            original.completion.final_attempt,
            fields={"cleanup": tx.put_subdag(cleanup)},
        )
        entries = tree(tx, original.commit)
        entries["attempt-" + original.attempt_id] = attempt
        final = tx.put_commit(
            tx.put_tree(entries), parents=tx.get_commit(original.commit).parents
        )
        both = tx.put_commit(
            tx.get_commit(selection.commit).tree, parents=(selection.commit, final)
        )
    packet = path.parent / "same-occurrence-later-F"
    shutil.copytree(double[2][0], packet)
    (packet / "snapshot.bundle").write_bytes(transfer.export_commit(path, commit=final))
    receipt = json.loads((packet / "observation.json").read_bytes())
    receipt["selected_commit"] = str(final)
    (packet / "observation.json").write_text(json.dumps(receipt), encoding="utf-8")
    later = ex.read_observation(packet, expected=double[2][1])
    assert later.phase == "completion" and later.lifecycle == "done"
    assert later.completion.outcome == "success"
    assert later.commit != original.commit
    assert later.completion.final_attempt != original.completion.final_attempt
    assert later.pre_dispatch == original.pre_dispatch
    assert later.request == original.request
    assert later.attempt_id == original.attempt_id
    assert later.result == original.result
    baseline = typed_oracle(path, (both,))
    before = (path / "data.mdb").read_bytes()
    candidate = (packet, double[2][1], later, double[2][3], double[2][4])
    with track_typed_puts(path, baseline) as puts:
        with pytest.raises(ValueError, match="distinct attempt occurrence"):
            adopt(path, both, candidate, expected_file=expected_file)
    assert not puts
    assert_file_unchanged(path / "data.mdb", before)
    assert typed_oracle(path, (both,)) == baseline
    with d.Repository(path) as repository, repository.read() as tx:
        assert tx.get_ref("selection-old") == selection.commit
        with pytest.raises(d.NotFoundError):
            tx.get_ref("adopt-fresh")
    # A genuinely distinct request/attempt occurrence still qualifies, even with
    # this alternate report retained in a nonfirst supporting parent.
    fresh = execute(path, both, "distinct-fresh", "double-binding", "double-inputs")
    assert fresh[2].attempt_id != original.attempt_id
    got = adopt(
        path, fresh[2].commit, fresh, expected_file=path.parent / "distinct-expected"
    )
    assert got.attempt == fresh[2].completion.final_attempt
    assert got.attempt_id == fresh[2].attempt_id


def test_adoption_matching_new_basis_but_different_old_choice_rejects(
    double, selection
):
    path = double[0][0]
    with d.Repository(path) as repository, repository.write() as tx:
        entries = tree(tx, selection.commit)
        binding = double[2][1].binding
        entries["double-binding"] = local.put_local_binding(
            tx,
            source=scalar(tx, binding, "source")
            + b"\n# deliberate different full binding\n",
            interpreter=sys.executable,
            timeout_ms=10000,
        )
        basis = tx.put_commit(tx.put_tree(entries), parents=(selection.commit,))
    fresh = execute(path, basis, "different-binding", "double-binding", "double-inputs")
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="existing selection"):
        adopt(path, fresh[2].commit, fresh)
    assert_file_unchanged(path / "data.mdb", before)


def test_internal_publisher_defensive_slot_check_does_not_put(
    double, expected_file, selection
):
    path = double[0][0]
    headers, expected, selected = app._capture(double[2][0], expected_file)
    before = (path / "data.mdb").read_bytes()
    for commit, replacement in ((selection.commit, False), (double[2][2].commit, True)):
        with track_typed_puts(path, typed_oracle(path, (commit,))) as puts:
            with pytest.raises(ValueError, match="slot must"):
                app._publish(
                    path,
                    commit,
                    "selected-double",
                    "invalid-slot",
                    headers,
                    expected,
                    selected,
                    replace=replacement,
                )
        assert not puts
    assert_file_unchanged(path / "data.mdb", before)


def test_disconnected_stored_S_F_and_absent_slot_never_resolve_fallback(
    double, selection
):
    path = double[0][0]
    with d.Repository(path) as repository, repository.write() as tx:
        disconnected = tx.put_commit(tx.get_commit(selection.commit).tree)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="ALL-parent"):
        reuse(path, disconnected)
    with pytest.raises(KeyError):
        reuse(path, double[2][2].commit)
    assert_file_unchanged(path / "data.mdb", before)
