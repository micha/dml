"""Public native composition/selection tests; no Docker/default fixture startup."""

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys

import daggerml as d
from daggerml import exchange as ex, floci as f, local
import pytest

from test_exchange import ROOT, exchange_runtime, literal, typed_oracle, tree, nested
from test_caller_requests import assert_file_unchanged

spec = importlib.util.spec_from_file_location(
    "composed_example", ROOT / "examples/composed_execution.py"
)
example = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = example
spec.loader.exec_module(example)

ADD = (ROOT / "examples/local_add.py").read_bytes()
DOUBLE = b"""import daggerml as d
from daggerml.local import child_context,publish_result
c=child_context()
with d.Repository(c.repository_path) as r,r.read() as t:
 value=t.get_node(t.lookup_node(c.inputs,'value'))
 root=t.get_node(t.get_dag(value.dag).root)
 answer=t.get_datum(root.datum).value*2
with d.Repository(c.repository_path) as r,r.write() as t:
 n=t.put_literal(t.put_datum(answer));publish_result(t,c,t.put_dag(root=n,bindings={'result':n}))
"""
REMOTE = f.FlociRemote(
    "http://floci:4566",
    "dml-local",
    "example/scope",
    "local",
    "installed:1",
    "sha256:" + "1" * 64,
    "/opt/dml/bin/python",
)


def execute(
    path, base, label, binding="add-binding", inputs="add-inputs", phase="completion"
):
    recorded = ex.record_exchange_request(
        path,
        commit=base,
        binding_name=binding,
        inputs_name=inputs,
        intent_uri=(
            "urn:example:double" if inputs == "double-inputs" else "urn:example:add"
        ),
        ref="submission-" + label,
    )
    workspace = path.parent / ("input-" + label)
    expected = ex.prepare_exchange(
        path,
        commit=recorded.commit,
        request=recorded.request,
        binding_name=binding,
        inputs_name=inputs,
        intent_uri=recorded.intent_uri,
        worker_ref="work",
        workspace=workspace,
    )
    run = ex.execute_exchange(workspace)
    if phase != "completion":
        with d.Repository(workspace / "worker.dml") as repo, repo.write() as tx:
            tx.update_ref("work", run.context.pre_dispatch)
            if phase == "initial":
                tx.update_ref(run.context.publication_ref, run.context.pre_dispatch)
    packet = path.parent / ("packet-" + label)
    observation = ex.observe_exchange(
        ex.ExchangeHandle(workspace, expected), packet=packet
    )
    received = ex.receive_observation(
        path, packet=packet, expected=expected, ref="received-" + label
    )
    return packet, expected, received, run, workspace


@pytest.fixture
def producer(tmp_path, exchange_runtime):
    import shutil

    for name in ("floci.py", "floci_http.py", "floci_worker.py"):
        shutil.copyfile(
            ROOT / "python/daggerml/daggerml" / name,
            exchange_runtime / "daggerml" / name,
        )
    path = tmp_path / "A"
    with d.Repository(path, create=True) as repo, repo.write() as tx:
        fields = {"left": literal(tx, 13), "right": literal(tx, 29)}
        inputs = tx.put_dag(root=fields["left"], bindings=fields)
        add = local.put_local_binding(
            tx, source=ADD, interpreter=sys.executable, timeout_ms=10000
        )
        double = local.put_local_binding(
            tx, source=DOUBLE, interpreter=sys.executable, timeout_ms=10000
        )
        base = tx.put_commit(
            tx.put_tree(
                {"add-binding": add, "double-binding": double, "add-inputs": inputs}
            )
        )
        tx.create_ref("main", base)
    return path, base, execute(path, base, "a")


def basis(producer, **kwargs):
    path, _, first = producer
    return example.consumer_basis(
        path,
        producer_packet=first[0],
        producer_expected=first[1],
        remote=REMOTE,
        gate="gates/double",
        **kwargs,
    )


def summary(producer, second, **kwargs):
    return example.experiment_summary(
        producer[0],
        producer_packet=producer[2][0],
        producer_expected=producer[2][1],
        consumer_packet=second[0],
        consumer_expected=second[1],
        **kwargs,
    )


def test_selected_earlier_equal_result_witness_and_summary(producer):
    path, base, first = producer
    later = execute(path, base, "b")
    assert first[2].result == later[2].result
    assert first[2].completion.final_attempt != later[2].completion.final_attempt
    with d.Repository(path) as repo, repo.write() as tx:
        tx.create_ref("latest", later[2].commit)
    old = typed_oracle(path, (first[2].commit, later[2].commit))
    authored = basis(producer)
    with d.Repository(path) as repo, repo.write() as tx:
        fields = dict(tx.get_dag(authored.dag).bindings)
        assert nested(tx, authored.dag, "value") == first[2].result
        assert nested(tx, authored.dag, "producer") == first[2].completion.final_attempt
        fields["producer"] = tx.put_subdag(later[2].completion.final_attempt)
        alternate = tx.put_dag(root=fields["value"], bindings=fields)
        assert alternate != authored.dag
        assert tx.get_commit(authored.commit).parents == (first[2].commit,)
        expected = tree(tx, first[2].commit)
        expected["double-inputs"] = authored.dag
        assert tree(tx, authored.commit) == expected
    from daggerml import transfer

    alternate_path = path.parent / "alternate-A"
    with d.Repository(alternate_path, create=True):
        pass
    transfer.import_commit(
        alternate_path, transfer.export_commit(path, commit=later[2].commit)
    )
    alternate_basis = example.consumer_basis(
        alternate_path,
        producer_packet=later[0],
        producer_expected=later[1],
        remote=REMOTE,
        gate="gates/double",
    )
    assert alternate_basis.dag != authored.dag
    second = execute(path, authored.commit, "double", "double-binding", "double-inputs")
    got = summary(producer, second)
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_ref("main") == base and tx.get_ref("latest") == later[2].commit
        assert tx.get_commit(got.commit).parents == (second[2].commit,)
        assert nested(tx, got.dag, "add") == first[2].completion.final_attempt
        assert nested(tx, got.dag, "double") == second[2].completion.final_attempt
        dag = tx.get_dag(got.dag)
        assert dag.root == dag.bindings["result"]
        assert nested(tx, got.dag, "result") == second[2].result
        assert example.i64_root(tx, second[2].result) == 84
        for key, raw in old.items():
            assert tx.get_record(*key) == raw
    # Alternate valid producer is allowed as explicit choice, NOT silently interchangeable.
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="independently selected"):
        example.experiment_summary(
            path,
            producer_packet=later[0],
            producer_expected=later[1],
            consumer_packet=second[0],
            consumer_expected=second[1],
        )
    assert_file_unchanged(path / "data.mdb", before)


@pytest.mark.parametrize("phase", ["initial", "publication"])
def test_progress_cannot_create_basis(producer, phase):
    path, base, _ = producer
    progress = execute(path, base, phase, phase=phase)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="successful recorded"):
        example.consumer_basis(
            path,
            producer_packet=progress[0],
            producer_expected=progress[1],
            remote=REMOTE,
            gate="gates/double",
        )
    assert_file_unchanged(path / "data.mdb", before)
    assert not (path.parent / "input-double").exists()


def test_wrong_expected_valid_matching_packet_rejects_before_authoring(producer):
    path, base, first = producer
    later = execute(path, base, "b")
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ex.ExchangeError):
        example.consumer_basis(
            path,
            producer_packet=later[0],
            producer_expected=first[1],
            remote=REMOTE,
            gate="gates/double",
        )
    assert_file_unchanged(path / "data.mdb", before)


def test_no_received_dataclass_authority_and_absent_packet(producer):
    path, base, first = producer
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(TypeError):
        example.consumer_basis(
            path,
            producer_packet=replace(first[2], lifecycle="done"),
            producer_expected=first[1],
            remote=REMOTE,
            gate="gates/double",
        )
    with pytest.raises(FileNotFoundError):
        example.consumer_basis(
            path,
            producer_packet=path.parent / "unknown",
            producer_expected=first[1],
            remote=REMOTE,
            gate="gates/double",
        )
    assert_file_unchanged(path / "data.mdb", before)


def test_create_only_repeat_rejects(producer):
    authored = basis(producer)
    before = (producer[0] / "data.mdb").read_bytes()
    with pytest.raises(d.InvalidStateError):
        basis(producer)
    assert_file_unchanged(producer[0] / "data.mdb", before)


def changed_binding(producer, source, label, name="add-binding"):
    path, base, _ = producer
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, base)
        entries[name] = local.put_local_binding(
            tx, source=source, interpreter=sys.executable, timeout_ms=10000
        )
        selected = tx.put_commit(tx.put_tree(entries), parents=(base,))
    return selected


@pytest.mark.parametrize("kind", ["failure", "bool", "string", "subdag"])
def test_producer_failure_evidence_or_unsuitable_success_no_downstream(producer, kind):
    path, base, _ = producer
    if kind == "failure":
        source = ADD + b"\nimport sys;sys.exit(23)\n"
    else:
        source = ADD.replace(
            b"sum(values)",
            {"bool": b"True", "string": b"'42'", "subdag": b"sum(values)"}[kind],
        )
        if kind == "subdag":
            source = source.replace(
                b'result = tx.put_dag(root=node, bindings={"result": node})',
                b"result = tx.put_dag(root=tx.put_subdag(tx.put_dag(root=node)))",
            )
    selected = changed_binding(producer, source, kind)
    first = execute(path, selected, kind)
    if kind == "failure":
        assert (
            first[2].completion.outcome == "failure"
            and first[2].completion.evidence is not None
        )
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        example.consumer_basis(
            path,
            producer_packet=first[0],
            producer_expected=first[1],
            remote=REMOTE,
            gate="gates/double",
        )
    assert_file_unchanged(path / "data.mdb", before)
    with d.Repository(path) as repo, repo.read() as tx:
        with pytest.raises(d.NotFoundError):
            tx.get_ref("double-basis")


@pytest.mark.parametrize(
    "field",
    [
        "producer",
        "value",
        "factor",
        "factor-type",
        "witness-type",
        "endpoint-type",
        "root",
        "fields",
    ],
)
def test_valid_consumer_packet_bad_selected_input_rejects_even_same_84(producer, field):
    path, base, first = producer
    later = execute(path, base, "b")
    authored = basis(producer)
    with d.Repository(path) as repo, repo.write() as tx:
        fields = dict(tx.get_dag(authored.dag).bindings)
        if field == "producer":
            fields["producer"] = tx.put_subdag(later[2].completion.final_attempt)
        elif field == "value":
            root = literal(tx, 42)
            fields["value"] = tx.put_subdag(
                tx.put_dag(root=root, bindings={"extra": root})
            )
        elif field == "factor":
            fields["factor"] = literal(tx, 3)
        elif field == "factor-type":
            fields["factor"] = literal(tx, True)
        elif field == "witness-type":
            fields["producer"] = literal(tx, "wrong witness type")
        elif field == "endpoint-type":
            fields["endpoint"] = literal(tx, 42)
        elif field == "fields":
            fields["extra"] = literal(tx, 0)
        inputs = tx.put_dag(
            root=fields["factor"] if field == "root" else fields["value"],
            bindings=fields,
        )
        entries = tree(tx, authored.commit)
        entries["double-inputs"] = inputs
        changed = tx.put_commit(tx.put_tree(entries), parents=(first[2].commit,))
    second = execute(path, changed, "double", "double-binding", "double-inputs")
    assert second[2].completion.outcome == "success"
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError):
        summary(producer, second)
    assert_file_unchanged(path / "data.mdb", before)


def test_consumer_failure_retains_evidence_without_success_summary(producer):
    path, _, _ = producer
    selected = changed_binding(
        producer,
        DOUBLE + b"\nimport sys;sys.exit(23)\n",
        "failing-double",
        name="double-binding",
    )
    first = execute(path, selected, "producer-for-consumer-failure")
    selected_producer = (path, selected, first)
    authored = basis(selected_producer)
    second = execute(path, authored.commit, "double", "double-binding", "double-inputs")
    assert (
        second[2].completion.outcome == "failure"
        and second[2].completion.evidence is not None
    )
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="successful recorded"):
        summary(selected_producer, second)
    assert_file_unchanged(path / "data.mdb", before)


def test_basis_input_type_and_tree_collisions(producer):
    path, _, first = producer
    for kwargs in ({"exit_code": True}, {"artifacts": "not-bytes"}):
        with pytest.raises(TypeError):
            basis(producer, **kwargs)
    authored = basis(producer)
    second = execute(path, authored.commit, "double", "double-binding", "double-inputs")
    # A valid successful second step is unsuitable as a fresh producer because
    # its snapshot already contains the example-local double-inputs name.
    with pytest.raises(ValueError, match="already exists"):
        example.consumer_basis(
            path,
            producer_packet=second[0],
            producer_expected=second[1],
            remote=REMOTE,
            gate="gates/double",
        )


def test_success_cleanup_failure_allowed_without_reclassification(
    producer, monkeypatch
):
    import shutil

    path, base, _ = producer
    original = shutil.rmtree

    def denied(path, *a, **k):
        if Path(path).name.startswith("dml-local-"):
            raise PermissionError("private owned cleanup failure")
        return original(path, *a, **k)

    with monkeypatch.context() as guard:
        guard.setattr(shutil, "rmtree", denied)
        first = execute(path, base, "cleanup")
    try:
        assert (
            first[2].completion.outcome == "success"
            and first[2].completion.cleanup == "failed"
        )
        authored = basis((path, base, first))
        with d.Repository(path) as repo, repo.read() as tx:
            assert (
                nested(tx, authored.dag, "producer")
                == first[2].completion.final_attempt
            )
    finally:
        original(first[3].context.scratch)


def test_wrong_basis_ancestry_rejects_and_summary_name_collision(producer):
    path, base, first = producer
    authored = basis(producer)
    with d.Repository(path) as repo, repo.write() as tx:
        bad = tx.put_commit(
            tx.get_commit(authored.commit).tree, parents=(first[2].commit, base)
        )
    second = execute(path, bad, "double", "double-binding", "double-inputs")
    with pytest.raises(ValueError, match="basis differs"):
        summary(producer, second)
    # Separate valid chain to exercise create-only summary repeat late ref rollback.
    third = execute(
        path, authored.commit, "double-good", "double-binding", "double-inputs"
    )
    summary(producer, third)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(d.InvalidStateError):
        summary(producer, third)
    assert_file_unchanged(path / "data.mdb", before)
    # Existing experiment entry in a still-valid consumer basis passes through
    # public execution but must not be overwritten by summary authoring.
    with d.Repository(path) as repo, repo.write() as tx:
        entries = tree(tx, authored.commit)
        entries["experiment"] = first[2].result
        collision = tx.put_commit(tx.put_tree(entries), parents=(first[2].commit,))
    fourth = execute(path, collision, "collision", "double-binding", "double-inputs")
    with pytest.raises(ValueError, match="summary tree name"):
        summary(producer, fourth)


def test_example_requires_pinned_caller_q_not_fresh_q_mode(producer):
    path, base, _ = producer
    workspace = path.parent / "fresh-q-mode"
    expected = ex.prepare_exchange(
        path,
        commit=base,
        binding_name="add-binding",
        inputs_name="add-inputs",
        intent_uri="urn:example:add",
        worker_ref="work",
        workspace=workspace,
    )
    ex.execute_exchange(workspace)
    packet = path.parent / "fresh-q-packet"
    ex.observe_exchange(ex.ExchangeHandle(workspace, expected), packet=packet)
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="pinned caller request"):
        example.consumer_basis(
            path,
            producer_packet=packet,
            producer_expected=expected,
            remote=REMOTE,
            gate="gates/double",
        )
    assert_file_unchanged(path / "data.mdb", before)


def test_summary_cannot_substitute_other_named_binding_selection(producer):
    path, base, first = producer
    before = (path / "data.mdb").read_bytes()
    with pytest.raises(ValueError, match="declared double"):
        summary(producer, first)
    assert_file_unchanged(path / "data.mdb", before)
