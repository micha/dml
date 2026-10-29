"""Example-local nonexecuting authoring for two explicitly selected recorded steps.

Packets plus independent expected selections are validation inputs, not supplied
ReceivedObservation flags. Close other native handles before calling these helpers.
Basis, subsequent Q recording, dispatch and summary are SEPARATE boundaries.
"""

import argparse
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path

import daggerml as d
from daggerml import exchange as ex, floci as f, local


@dataclass(frozen=True)
class Authored:
    commit: d.ObjectId
    dag: d.ObjectId
    ref: str


def successful(packet, expected):
    selected = ex.read_observation(packet, expected=expected)
    if expected.request is None:
        raise ValueError("example requires an independently pinned caller request")
    if (
        selected.phase != "completion"
        or selected.lifecycle != "done"
        or selected.completion is None
        or selected.completion.outcome != "success"
    ):
        raise ValueError("selected step is not a successful recorded completion")
    # Recorded cleanup failure is allowed by THIS example; never erase its history.
    return selected


def i64_root(tx, result):
    node = tx.get_node(tx.get_dag(result).root)
    if not isinstance(node, d.LiteralNode):
        raise ValueError("consumer requires a literal I64 result root")
    datum = tx.get_datum(node.datum)
    if datum.kind != "i64":
        raise ValueError("consumer requires a literal I64 result root")
    return datum.value


def consumer_basis(
    repository_path,
    *,
    producer_packet,
    producer_expected,
    remote,
    gate,
    exit_code=0,
    artifacts=b"",
    map_size=0,
):
    """Validate selected F, then atomically add only I2/C2/create-only basis ref.

    F must already have been received in A. No Q, submit, latest-ref selection,
    historical path action or inferred failure is hidden in this operation.
    """
    first = successful(producer_packet, producer_expected)
    gate = replace(remote, prefix=gate).prefix
    if type(exit_code) is not int or type(artifacts) is not bytes:
        raise TypeError("exit-code/artifacts require int/bytes")
    with d.Repository(
        repository_path, map_size=map_size
    ) as repository, repository.write() as tx:
        entries = dict(tx.get_tree(tx.get_commit(first.commit).tree))
        if "double-inputs" in entries:
            raise ValueError("consumer input name already exists")
        i64_root(tx, first.result)  # All eligibility/type reads BEFORE any A puts.
        tx.get_dag(first.completion.final_attempt)
        value = tx.put_subdag(first.result)
        fields = dict(
            value=value, producer=tx.put_subdag(first.completion.final_attempt)
        )
        fields.update(
            {
                name: tx.put_literal(tx.put_datum(item))
                for name, item in {
                    "factor": 2,
                    "endpoint": remote.endpoint,
                    "bucket": remote.bucket,
                    "gate": gate,
                    "exit-code": exit_code,
                    "artifacts": artifacts,
                }.items()
            }
        )
        inputs = tx.put_dag(root=value, bindings=fields)
        entries["double-inputs"] = inputs
        commit = tx.put_commit(tx.put_tree(entries), parents=(first.commit,))
        tx.create_ref("double-basis", commit)
        response = Authored(commit, inputs, "double-basis")  # Allocate BEFORE commit.
    return response


def input_association(tx, inputs, first):
    """Check only this example's input convention; public inspector owns roles/Q."""
    dag = tx.get_dag(inputs)
    if (
        set(dag.bindings)
        != {
            "value",
            "producer",
            "factor",
            "endpoint",
            "bucket",
            "gate",
            "exit-code",
            "artifacts",
        }
        or dag.root != dag.bindings["value"]
    ):
        raise ValueError("consumer input shape differs from example contract")
    for name, expected in (
        ("value", first.result),
        ("producer", first.completion.final_attempt),
    ):
        link = tx.get_node(dag.bindings[name])
        if not isinstance(link, d.SubDAGNode) or link.dag != expected:
            raise ValueError(
                "consumer input differs from independently selected producer"
            )
    factor = tx.get_node(dag.bindings["factor"])
    if not isinstance(factor, d.LiteralNode) or tx.get_datum(
        factor.datum
    ) != d.Datum.i64(2):
        raise ValueError("consumer factor must be literal I64 two")
    i64_root(tx, first.result)
    for name, kind in (
        ("endpoint", "string"),
        ("bucket", "string"),
        ("gate", "string"),
        ("exit-code", "i64"),
        ("artifacts", "bytes"),
    ):
        node = tx.get_node(dag.bindings[name])
        if not isinstance(node, d.LiteralNode) or tx.get_datum(node.datum).kind != kind:
            raise ValueError("consumer declared scalar has wrong type")


def experiment_summary(
    repository_path,
    *,
    producer_packet,
    producer_expected,
    consumer_packet,
    consumer_expected,
    map_size=0,
):
    """Validate both exact selections/association, then publish ordinary E/S/ref."""
    first = successful(producer_packet, producer_expected)
    second = successful(consumer_packet, consumer_expected)
    if (
        consumer_expected.binding_name != "double-binding"
        or consumer_expected.inputs_name != "double-inputs"
    ):
        raise ValueError("consumer must select the declared double binding/inputs")
    with d.Repository(
        repository_path, map_size=map_size
    ) as repository, repository.write() as tx:
        entries = dict(tx.get_tree(tx.get_commit(second.commit).tree))
        if "experiment" in entries:
            raise ValueError("summary tree name already exists")
        input_association(tx, consumer_expected.inputs, first)
        # Public inspector checked exact Q2. Its submission parent must be THIS
        # pinned producer's basis, preserving the entire producer tree plus I2.
        basis = tx.get_commit(consumer_expected.commit).parents[0]
        basis_description = tx.get_commit(basis)
        basis_entries = dict(tx.get_tree(basis_description.tree))
        producer_entries = dict(tx.get_tree(tx.get_commit(first.commit).tree))
        if (
            basis_description.parents != (first.commit,)
            or "double-inputs" in producer_entries
            or basis_entries.pop("double-inputs", None) != consumer_expected.inputs
            or basis_entries != producer_entries
        ):
            raise ValueError("consumer basis differs from selected producer history")
        i64_root(tx, second.result)
        result = tx.put_subdag(second.result)
        summary = tx.put_dag(
            root=result,
            bindings={
                "add": tx.put_subdag(first.completion.final_attempt),
                "double": tx.put_subdag(second.completion.final_attempt),
                "result": result,
            },
        )
        entries["experiment"] = summary
        commit = tx.put_commit(tx.put_tree(entries), parents=(second.commit,))
        tx.create_ref("experiment-result", commit)
        response = Authored(commit, summary, "experiment-result")
    return response


def initialize(repository_path, *, remote, add_source, double_source, gate):
    """Predeclare both trusted bindings and add inputs; never request/dispatch."""
    gate = replace(remote, prefix=gate).prefix
    with d.Repository(
        repository_path, create=True
    ) as repository, repository.write() as tx:
        fields = {
            name: tx.put_literal(tx.put_datum(value))
            for name, value in {
                "left": 13,
                "right": 29,
                "endpoint": remote.endpoint,
                "bucket": remote.bucket,
                "gate": gate,
                "exit-code": 0,
            }.items()
        }
        inputs = tx.put_dag(root=fields["left"], bindings=fields)
        entries = {"add-inputs": inputs}
        for name, source in (
            ("add-binding", add_source),
            ("double-binding", double_source),
        ):
            entries[name] = local.put_local_binding(
                tx,
                source=Path(source).read_bytes(),
                interpreter=remote.python,
                timeout_ms=360000,
            )
        commit = tx.put_commit(tx.put_tree(entries))
        tx.create_ref("main", commit)
        tx.create_ref("sentinel", commit)
    return commit


def main(argv=None):
    """Finite explicit modes; provisioning/gate release/poll order remain caller policy."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    init = commands.add_parser("init")
    for name in ("repository", "config", "add_source", "double_source"):
        init.add_argument(name, type=Path)
    init.add_argument("gate")
    basis = commands.add_parser("basis")
    for name in ("repository", "producer_saved", "producer_packet", "config"):
        basis.add_argument(name, type=Path)
    basis.add_argument("gate")
    request = commands.add_parser("request")
    for name in ("repository", "step", "config"):
        request.add_argument(name, type=Path)
    for name in ("commit", "binding", "inputs", "intent", "ref"):
        request.add_argument(name)
    submit = commands.add_parser("submit")
    submit.add_argument("step", type=Path)
    observe = commands.add_parser("observe")
    observe.add_argument("saved", type=Path)
    observe.add_argument("packet", type=Path)
    summary = commands.add_parser("summary")
    for name in (
        "repository",
        "producer_saved",
        "producer_packet",
        "consumer_saved",
        "consumer_packet",
    ):
        summary.add_argument(name, type=Path)
    args = parser.parse_args(argv)
    if args.mode in ("init", "basis", "request", "submit"):
        config = args.step / "remote.json" if args.mode == "submit" else args.config
        with open(config, "rb") as stream:
            data = stream.read(8193)
        if len(data) > 8192:
            raise ValueError("example configuration exceeds profile")
        remote = f.FlociRemote(**json.loads(data))
    if args.mode == "init":
        result = {
            "commit": str(
                initialize(
                    args.repository,
                    remote=remote,
                    add_source=args.add_source,
                    double_source=args.double_source,
                    gate=args.gate,
                )
            )
        }
    elif args.mode == "basis":
        authored = consumer_basis(
            args.repository,
            producer_packet=args.producer_packet,
            producer_expected=f.load_floci_job(args.producer_saved).expected,
            remote=remote,
            gate=args.gate,
        )
        result = {
            "commit": str(authored.commit),
            "inputs": str(authored.dag),
            "ref": authored.ref,
        }
    elif args.mode == "request":
        # Deliberate separate Q transaction; later file failure does NOT erase Q.
        recorded = ex.record_exchange_request(
            args.repository,
            commit=d.ObjectId.from_hex(args.commit),
            binding_name=args.binding,
            inputs_name=args.inputs,
            intent_uri=args.intent,
            ref=args.ref,
        )
        args.step.mkdir()
        expected = ex.prepare_exchange(
            args.repository,
            commit=recorded.commit,
            request=recorded.request,
            binding_name=args.binding,
            inputs_name=args.inputs,
            intent_uri=args.intent,
            worker_ref="work",
            workspace=args.step / "input",
        )
        (args.step / "remote.json").write_text(
            json.dumps(asdict(remote)), encoding="utf-8"
        )
        result = {"commit": str(expected.commit), "request": str(expected.request)}
    elif args.mode == "submit":
        expected = ex.read_exchange_spec(args.step / "input")
        staged = f.stage_floci_exchange(
            remote,
            workspace=args.step / "input",
            expected=expected,
            control=args.step / "control",
            timeout_ms=30000,
        )
        job = f.submit_floci_exchange(staged, timeout_ms=10000)
        f.save_floci_job(args.step / "saved", job)
        result = {"job_id": job.job_id}
    elif args.mode == "observe":
        observed = f.observe_floci_job(
            f.load_floci_job(args.saved), packet=args.packet, timeout_ms=10000
        )
        result = {
            "phase": observed.phase,
            "lifecycle": observed.lifecycle,
            "job_id": observed.job_id,
        }
    else:
        authored = experiment_summary(
            args.repository,
            producer_packet=args.producer_packet,
            producer_expected=f.load_floci_job(args.producer_saved).expected,
            consumer_packet=args.consumer_packet,
            consumer_expected=f.load_floci_job(args.consumer_saved).expected,
        )
        result = {
            "commit": str(authored.commit),
            "summary": str(authored.dag),
            "ref": authored.ref,
        }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
