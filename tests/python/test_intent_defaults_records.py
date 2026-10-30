"""Strict ordinary Idef/D native types, pinned claims and actual Q/W authority."""

from pathlib import Path
import json
import sys

import daggerml as d
from daggerml import exchange as ex, local, transfer
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_caller_requests import assert_file_unchanged, track_typed_puts
from test_composed_execution import producer, execute
from test_exchange import exchange_runtime, literal, nested, scalar, tree, typed_oracle
from test_exchange_records import clone
from test_explicit_reuse import double
from test_intent_defaults import app, define, request, inspect
from test_records_hypothesis import run_driver
from test_reuse_selection import expected_file, select


@pytest.mark.parametrize(
    "fault",
    [
        "expected-header",
        "job-header",
        "receipt-header",
        "oversized",
        "capsule-Q",
        "capsule-IO",
    ],
)
def test_present_S_V_public_header_profile_IO_errors_at_POLICY_boundary_NO_D_Q(
    double, expected_file, monkeypatch, fault
):
    path = double[0][0]
    chosen = select(double, expected_file)
    definition = define(double, commit=chosen.commit)
    with d.Repository(path) as repository, repository.write() as tx:
        fields = {}
        if fault != "capsule-IO":
            field = {
                "expected-header": "expected",
                "job-header": "job",
                "receipt-header": "observation",
                "oversized": "expected",
                "capsule-Q": "expected",
            }[fault]
            data = b"{}" if fault != "oversized" else b"x" * 8193
            if fault == "capsule-Q":
                document = json.loads(scalar(tx, chosen.validation, "expected"))
                document["expected"]["request"] = str(double[0][2][2].request)
                data = json.dumps(document).encode()
            node = literal(tx, data)
            validation = clone(
                tx,
                chosen.validation,
                fields={field: node},
                root=node if field == "expected" else None,
            )
            dag = clone(
                tx, chosen.dag, fields={"validation": tx.put_subdag(validation)}
            )
            entries = tree(tx, definition.commit)
            entries["selected-double"] = dag
            basis = tx.put_commit(tx.put_tree(entries), parents=(definition.commit,))
        else:
            basis = definition.commit
    before = (path / "data.mdb").read_bytes()
    with monkeypatch.context() as guard:
        if fault == "capsule-IO":
            guard.setattr(
                app.selection,
                "_materialize",
                lambda *a: (_ for _ in ()).throw(
                    PermissionError("private retained capsule IO")
                ),
            )
        with track_typed_puts(path, typed_oracle(path, (basis,))) as puts:
            with pytest.raises((ValueError, OSError)):
                request(path, basis, reuse_ref="no-fallback")
        assert not puts
    assert_file_unchanged(path / "data.mdb", before)
    # Same native-valid malformed S framing deliberately unused by execute default.
    execute_default = app.define(
        path,
        commit=basis,
        intent_name="double-intent",
        intent_uri="urn:example:double",
        default="execute-by-default",
        ref="execute-default",
        update=True,
    )
    fresh = request(path, execute_default.commit)
    assert fresh.decision.reason == "default-execution" and fresh.reused is None
    assert inspect(path, fresh) == fresh.decision


@pytest.mark.parametrize("phase", ["initial", "publication", "failed-completion"])
def test_PUBLIC_valid_P_U_failed84_evidence_is_NOT_policy_reuse_authority(
    double, expected_file, phase
):
    path = double[0][0]
    chosen = select(double, expected_file)
    definition = define(double, commit=chosen.commit)
    basis = definition.commit
    if phase == "failed-completion":
        with d.Repository(path) as repository, repository.write() as tx:
            entries = tree(tx, basis)
            old_binding = double[2][1].binding
            entries["double-binding"] = local.put_local_binding(
                tx,
                source=scalar(tx, old_binding, "source")
                + b"\nimport sys;sys.exit(23)\n",
                interpreter=sys.executable,
                timeout_ms=10000,
            )
            basis = tx.put_commit(tx.put_tree(entries), parents=(basis,))
    candidate = execute(
        path,
        basis,
        "noneligible",
        "double-binding",
        "double-inputs",
        phase="completion" if phase == "failed-completion" else phase,
    )
    selected = ex.read_observation(candidate[0], expected=candidate[1])
    assert selected.phase == ("completion" if phase == "failed-completion" else phase)
    if phase == "failed-completion":
        assert (
            selected.completion.outcome == "failure"
            and selected.completion.evidence == chosen.result
        )
    saved = path.parent / "independent-noneligible"
    ex.save_exchange_handle(saved, ex.ExchangeHandle(candidate[4], candidate[1]))
    with d.Repository(path) as repository, repository.write() as tx:
        headers = {
            "expected": saved.read_bytes(),
            "job": (candidate[0] / "job.json").read_bytes(),
            "observation": (candidate[0] / "observation.json").read_bytes(),
        }
        fields = {name: literal(tx, value) for name, value in headers.items()}
        validation = tx.put_dag(root=fields["expected"], bindings=fields)
        dag = clone(
            tx,
            chosen.dag,
            fields={
                "validation": tx.put_subdag(validation),
                "completion": literal(tx, selected.commit.bytes),
            },
        )
        entries = tree(tx, selected.commit)
        entries["selected-double"] = dag
        basis = tx.put_commit(tx.put_tree(entries), parents=(selected.commit,))
    before = (path / "data.mdb").read_bytes()
    with track_typed_puts(path, typed_oracle(path, (basis,))) as puts:
        with pytest.raises(ValueError, match="successful recorded F"):
            request(path, basis, reuse_ref="no-nonfinal-fallback")
    assert not puts
    assert_file_unchanged(path / "data.mdb", before)


def replace_definition(double, definition, dag):
    path = double[0][0]
    with d.Repository(path) as repository, repository.write() as tx:
        entries = tree(tx, definition.commit)
        entries[definition.name] = dag
        return tx.put_commit(tx.put_tree(entries), parents=(definition.commit,))


@pytest.mark.parametrize("field", ["role", "intent", "default"])
@pytest.mark.parametrize("fault", ["missing", "wrong-type", "subdag"])
def test_every_Idef_field_exact_type_required_before_D_Q(double, field, fault):
    path = double[0][0]
    definition = define(double)
    with d.Repository(path) as repository, repository.write() as tx:
        fields = dict(tx.get_dag(definition.dag).bindings)
        root = tx.get_dag(definition.dag).root
        if fault == "missing":
            fields.pop(field)
        else:
            fields[field] = (
                tx.put_subdag(double[2][2].result)
                if fault == "subdag"
                else literal(tx, True)
            )
            if field == "intent":
                root = fields[field]
        dag = tx.put_dag(root=root, bindings=fields)
    basis = replace_definition(double, definition, dag)
    before = (path / "data.mdb").read_bytes()
    with track_typed_puts(path, typed_oracle(path, (basis,))) as puts:
        with pytest.raises(ValueError):
            request(path, basis)
    assert not puts
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("fault", ["root", "extra", "role", "default"])
def test_Idef_root_extra_role_unknown_policy_never_implicit_default(double, fault):
    path = double[0][0]
    definition = define(double)
    with d.Repository(path) as repository, repository.write() as tx:
        fields = dict(tx.get_dag(definition.dag).bindings)
        root = fields["role"] if fault == "root" else fields["intent"]
        if fault != "root":
            fields["extra" if fault == "extra" else fault] = literal(tx, "unknown")
        dag = tx.put_dag(root=root, bindings=fields)
    basis = replace_definition(double, definition, dag)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        request(path, basis)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize(
    "field",
    [
        "role",
        "intent-definition",
        "binding",
        "inputs",
        "intent-name",
        "binding-name",
        "inputs-name",
        "selection-slot",
        "override",
        "action",
        "reason",
    ],
)
@pytest.mark.parametrize("fault", ["missing", "wrong-node-type"])
def test_every_D_field_required_typed_and_root_checked_by_pinned_reader(
    double, field, fault
):
    path = double[0][0]
    definition = define(double)
    got = request(path, definition.commit)
    with d.Repository(path) as repository, repository.write() as tx:
        fields = dict(tx.get_dag(got.decision.dag).bindings)
        root = tx.get_dag(got.decision.dag).root
        if fault == "missing":
            fields.pop(field)
        else:
            fields[field] = literal(tx, True)
            if field == "intent-definition":
                root = fields[field]
        dag = tx.put_dag(root=root, bindings=fields)
        entries = tree(tx, definition.commit)
        entries[got.decision.name] = dag
        fake = tx.put_commit(tx.put_tree(entries), parents=(definition.commit,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        app.inspect_decision(path, commit=fake, decision_name=got.decision.name)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize(
    "field",
    [
        "role",
        "action",
        "reason",
        "override",
        "intent-name",
        "binding-name",
        "inputs-name",
        "selection-slot",
        "intent-definition",
        "binding",
        "inputs",
        "selection",
        "extra",
        "root",
    ],
)
def test_typed_complete_partial_D_claims_against_exact_parent_not_flags(
    double, expected_file, field
):
    path = double[0][0]
    chosen = select(double, expected_file)
    definition = define(double, commit=chosen.commit)
    got = request(path, definition.commit, reuse_ref="reused")
    with d.Repository(path) as repository, repository.write() as tx:
        values = {
            "role": "other",
            "action": "execute-fresh",
            "reason": "default-no-selection",
            "override": "fresh",
            "intent-name": "add-binding",
            "binding-name": "add-binding",
            "inputs-name": "add-inputs",
            "selection-slot": "missing",
            "extra": "extra",
        }
        if field in ("intent-definition", "binding", "inputs", "selection"):
            replacement = tx.put_subdag(double[2][2].result)
        else:
            replacement = literal(tx, values.get(field, "not-root"))
        dag = clone(
            tx,
            got.decision.dag,
            fields={} if field == "root" else {field: replacement},
            root=replacement if field in ("root", "intent-definition") else None,
        )
        entries = tree(tx, definition.commit)
        entries[got.decision.name] = dag
        fake = tx.put_commit(tx.put_tree(entries), parents=(definition.commit,))
    copied = path.parent / "typed-copy"
    with d.Repository(copied, create=True):
        pass
    transfer.import_commit(copied, transfer.export_commit(path, commit=fake))
    assert typed_oracle(copied, (fake,)) == typed_oracle(path, (fake,))
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, KeyError)):
        app.inspect_decision(path, commit=fake, decision_name=got.decision.name)
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize(
    "fault",
    [
        "root",
        "role",
        "intent",
        "binding",
        "inputs",
        "extra",
        "no-Q",
        "unrelated",
        "parent",
        "two-parents",
        "wrong-Q",
    ],
)
def test_public_exact_typed_Q_and_submission_ancestry_reader(double, fault):
    path = double[0][0]
    definition = define(double)
    got = request(path, definition.commit)
    with d.Repository(path) as repository, repository.write() as tx:
        q = got.recorded.request
        cdec = got.decision.commit
        fields, root = {}, None
        if fault == "root":
            root = literal(tx, "q-" + "a" * 32)
        elif fault in ("role", "intent", "binding", "inputs", "extra"):
            value = d.Datum.uri("urn:wrong") if fault == "intent" else "wrong"
            fields[fault] = (
                tx.put_subdag(double[2][2].result)
                if fault in ("binding", "inputs")
                else literal(tx, value)
            )
        q = clone(tx, q, fields=fields, root=root)
        entries = tree(tx, cdec)
        if fault != "no-Q":
            entries["request-" + got.recorded.request_id] = q
        if fault == "unrelated":
            entries["unrelated"] = double[2][2].result
        parents = (
            (definition.commit,)
            if fault == "parent"
            else (cdec, definition.commit) if fault == "two-parents" else (cdec,)
        )
        cq = tx.put_commit(tx.put_tree(entries), parents=parents)
    if fault == "wrong-Q":
        q = double[2][
            2
        ].request  # Present, fully typed, from another valid producing Q.
    transfer.export_commit(path, commit=cq)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises((ValueError, KeyError)):
        app.inspect_request(path, commit=cq, request=q, decision_name=got.decision.name)
    assert_file_unchanged(path / "data.mdb", before)
    assert inspect(path, got) == got.decision


@pytest.mark.parametrize(
    "fault", ["request", "attempt", "result", "role", "root", "extra", "parent", "tree"]
)
def test_W_exact_original_four_fields_selected_T_R_and_actual_own_Q(
    double, expected_file, fault
):
    path = double[0][0]
    chosen = select(double, expected_file)
    definition = define(double, commit=chosen.commit)
    got = request(path, definition.commit, reuse_ref="reused")
    with d.Repository(path) as repository, repository.write() as tx:
        fields, root = {}, None
        if fault in ("request", "attempt", "result"):
            fields[fault] = tx.put_subdag(
                chosen.request
                if fault == "request"
                else (
                    double[0][2][2].completion.final_attempt
                    if fault == "attempt"
                    else double[0][2][2].result
                )
            )
        elif fault in ("role", "extra"):
            fields[fault] = literal(tx, "wrong")
        elif fault == "root":
            root = literal(tx, "wrong")
        w = clone(tx, got.reused.dag, fields=fields, root=root)
        entries = tree(tx, got.recorded.commit)
        entries["reuse-" + got.recorded.request_id] = w
        if fault == "tree":
            entries["extra"] = chosen.result
        fake = tx.put_commit(
            tx.put_tree(entries),
            parents=(definition.commit if fault == "parent" else got.recorded.commit,),
        )
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        app.inspect_request(
            path,
            commit=got.recorded.commit,
            request=got.recorded.request,
            decision_name=got.decision.name,
            satisfaction_commit=fake,
        )
    assert_file_unchanged(path / "data.mdb", before)
