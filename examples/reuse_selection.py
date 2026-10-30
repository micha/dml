"""Example-local durable selection; ordinary S/V, existing PUBLIC validation only.

No discovery/default/dispatch or historical-path action. Close other native handles
before calling. Selection storage, Q/W, files and service are separate boundaries.
"""

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import re
import tempfile

import daggerml as d
from daggerml import exchange as ex, transfer

from explicit_reuse import reuse_attempt


@dataclass(frozen=True)
class Selection:
    commit: d.ObjectId
    dag: d.ObjectId
    validation: d.ObjectId
    slot: str
    completion: d.ObjectId
    request: d.ObjectId
    attempt: d.ObjectId
    result: d.ObjectId
    intent_uri: str
    binding: d.ObjectId
    inputs: d.ObjectId
    attempt_id: str  # Owning public occurrence, not a new native S field.


def _name(name):
    if (
        type(name) is not str
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", name) is None
    ):
        raise ValueError("explicit name outside native profile")
    return name


def _bounded(path, limit):
    with open(path, "rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("selection file exceeds owning profile")
    return data


def _successful(packet, expected):
    selected = ex.read_observation(packet, expected=expected)
    if expected.request is None:
        raise ValueError("selection requires independent caller Cq/Q")
    if (
        selected.phase != "completion"
        or selected.lifecycle != "done"
        or selected.completion is None
        or selected.completion.outcome != "success"
        or selected.result is None
    ):
        raise ValueError("selection requires successful recorded F")
    return selected


def _materialize(path, headers, bundle):
    for name, data in zip(
        ("expected.json", "job.json", "observation.json", "snapshot.bundle"),
        (*headers, bundle),
    ):
        (path / name).write_bytes(data)
    expected = ex.load_exchange_handle(path / "expected.json").expected
    # Serialized workspace is inert. NEVER observe/start that loaded handle.
    return expected, _successful(path, expected)


def _capture(packet, expected_file):
    """Capture FIRST; the same immutable copies validate and later populate V."""
    headers = (
        _bounded(expected_file, ex.MAX_DESCRIPTOR_BYTES),
        _bounded(Path(packet) / "job.json", ex.MAX_DESCRIPTOR_BYTES),
        _bounded(Path(packet) / "observation.json", ex.MAX_DESCRIPTOR_BYTES),
    )
    bundle = _bounded(Path(packet) / "snapshot.bundle", transfer.MAX_BUNDLE_BYTES)
    with tempfile.TemporaryDirectory(prefix="dml-selection-capture-") as scratch:
        expected, selected = _materialize(Path(scratch), headers, bundle)
    # ALL validation/projection scratch disposed BEFORE authoring A.
    return headers, expected, selected


def _history(repository_path, commit, completion):
    with d.Repository(repository_path) as repository, repository.read() as tx:
        pending, seen = [commit], set()
        while pending:
            current = pending.pop()
            if current not in seen:
                seen.add(current)
                pending.extend(tx.get_commit(current).parents)
        if completion not in seen:
            raise ValueError("F not retained by basis ALL-parent history")
    # Complete typed native closure/profile, including composite-only descendants.
    transfer.export_commit(repository_path, commit=commit)


def _match(repository_path, commit, binding_name, inputs_name, intent_uri, expected):
    with d.Repository(repository_path) as repository, repository.read() as tx:
        entries = dict(tx.get_tree(tx.get_commit(commit).tree))
        if (intent_uri, entries[binding_name], entries[inputs_name]) != (
            expected.intent_uri,
            expected.binding,
            expected.inputs,
        ):
            raise ValueError("selection intent/binding/full inputs differ")
    return entries


def _publish(
    repository_path,
    commit,
    slot,
    ref,
    headers,
    expected,
    selected,
    *,
    replace=False,
    map_size=0,
):
    with d.Repository(
        repository_path, map_size=map_size
    ) as repository, repository.write() as tx:
        entries = dict(tx.get_tree(tx.get_commit(commit).tree))
        if (slot in entries) != replace:
            raise ValueError(
                "selection slot must be present for adoption, absent for select"
            )
        fields = {
            name: tx.put_literal(tx.put_datum(data))
            for name, data in zip(("expected", "job", "observation"), headers)
        }
        validation = tx.put_dag(root=fields["expected"], bindings=fields)
        result = tx.put_subdag(selected.result)
        fields = {
            "role": tx.put_literal(tx.put_datum("example-reuse-selection-v1")),
            "intent": tx.put_literal(tx.put_datum(d.Datum.uri(expected.intent_uri))),
            "binding": tx.put_subdag(expected.binding),
            "inputs": tx.put_subdag(expected.inputs),
            "request": tx.put_subdag(selected.request),
            "attempt": tx.put_subdag(selected.completion.final_attempt),
            "result": result,
            "completion": tx.put_literal(tx.put_datum(selected.commit.bytes)),
            "validation": tx.put_subdag(validation),
        }
        dag = tx.put_dag(root=result, bindings=fields)
        entries[slot] = dag
        authored = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref(ref, authored)
        response = Selection(
            authored,
            dag,
            validation,
            slot,
            selected.commit,
            selected.request,
            selected.completion.final_attempt,
            selected.result,
            expected.intent_uri,
            expected.binding,
            expected.inputs,
            selected.attempt_id,
        )
    return response


def select(
    repository_path,
    *,
    commit,
    slot,
    binding_name,
    inputs_name,
    intent_uri,
    packet,
    expected_file,
    ref,
    map_size=0,
):
    """No Q/T/job. One atomic S/V/tree/commit/create-only ref, response precommit."""
    _name(slot)
    _name(ref)
    headers, expected, selected = _capture(packet, expected_file)
    entries = _match(
        repository_path, commit, binding_name, inputs_name, intent_uri, expected
    )
    if slot in entries:
        raise ValueError("selection slot already exists")
    _history(repository_path, commit, selected.commit)
    return _publish(
        repository_path,
        commit,
        slot,
        ref,
        headers,
        expected,
        selected,
        map_size=map_size,
    )


def _scalar(tx, node, kind):
    node = tx.get_node(node)
    if not isinstance(node, d.LiteralNode):
        raise ValueError("selection field must be literal")
    datum = tx.get_datum(node.datum)
    if datum.kind != kind:
        raise ValueError("selection scalar type differs")
    return datum.value


def _subdag(tx, node):
    node = tx.get_node(node)
    if not isinstance(node, d.SubDAGNode):
        raise ValueError("selection field must be sub-DAG")
    tx.get_dag(node.dag)
    return node.dag


@contextmanager
def _projection(repository_path, commit, slot):
    _name(slot)
    with d.Repository(repository_path) as repository, repository.read() as tx:
        dag = tx.get_tree(tx.get_commit(commit).tree)[slot]
        description = tx.get_dag(dag)
        if (
            set(description.bindings)
            != {
                "role",
                "intent",
                "binding",
                "inputs",
                "request",
                "attempt",
                "result",
                "completion",
                "validation",
            }
            or description.root != description.bindings["result"]
        ):
            raise ValueError("selection shape/root differs")
        fields = description.bindings
        if _scalar(tx, fields["role"], "string") != "example-reuse-selection-v1":
            raise ValueError("selection role differs")
        intent = _scalar(tx, fields["intent"], "uri")
        links = {
            name: _subdag(tx, fields[name])
            for name in (
                "binding",
                "inputs",
                "request",
                "attempt",
                "result",
                "validation",
            )
        }
        completion = d.ObjectId(_scalar(tx, fields["completion"], "bytes"))
        validation = tx.get_dag(links["validation"])
        if (
            set(validation.bindings) != {"expected", "job", "observation"}
            or validation.root != validation.bindings["expected"]
        ):
            raise ValueError("validation shape/root differs")
        headers = tuple(
            _scalar(tx, validation.bindings[name], "bytes")
            for name in ("expected", "job", "observation")
        )
        if any(len(data) > ex.MAX_DESCRIPTOR_BYTES for data in headers):
            raise ValueError("stored validation exceeds owning profile")
    _history(repository_path, commit, completion)
    bundle = transfer.export_commit(repository_path, commit=completion)
    with tempfile.TemporaryDirectory(prefix="dml-selection-projection-") as scratch:
        path = Path(scratch)
        expected, selected = _materialize(path, headers, bundle)
        if (
            intent,
            links["binding"],
            links["inputs"],
            links["request"],
            links["attempt"],
            links["result"],
            completion,
        ) != (
            expected.intent_uri,
            expected.binding,
            expected.inputs,
            selected.request,
            selected.completion.final_attempt,
            selected.result,
            selected.commit,
        ):
            raise ValueError("stored selection differs from PUBLIC validated fields")
        response = Selection(
            commit,
            dag,
            links["validation"],
            slot,
            completion,
            selected.request,
            selected.completion.final_attempt,
            selected.result,
            expected.intent_uri,
            expected.binding,
            expected.inputs,
            selected.attempt_id,
        )
        yield response, path, expected


def inspect(repository_path, *, commit, slot):
    """Pinned repository alone supplies revalidation; creates NO DML records/refs."""
    with _projection(repository_path, commit, slot) as (response, _, __):
        pass
    return response


def reuse_selected(
    repository_path,
    *,
    commit,
    slot,
    binding_name,
    inputs_name,
    intent_uri,
    submission_ref,
    ref,
    map_size=0,
):
    """Revalidate THAT pinned S, match BEFORE Q, delegate unchanged separate Q/W.

    Projection files live through delegation. Their late cleanup failure can leave
    published Q/W; this is NOT a whole-operation rollback or retry permission.
    """
    with _projection(repository_path, commit, slot) as (_, packet, expected):
        _match(repository_path, commit, binding_name, inputs_name, intent_uri, expected)
        response = reuse_attempt(
            repository_path,
            commit=commit,
            binding_name=binding_name,
            inputs_name=inputs_name,
            intent_uri=intent_uri,
            historical_packet=packet,
            historical_expected=expected,
            submission_ref=submission_ref,
            ref=ref,
            map_size=map_size,
        )
    return response


def adopt(
    repository_path,
    *,
    commit,
    slot,
    binding_name,
    inputs_name,
    intent_uri,
    packet,
    expected_file,
    ref,
    map_size=0,
):
    """Revalidate both successful histories; replace only the slot in NEW C/S/V."""
    _name(ref)
    previous = inspect(repository_path, commit=commit, slot=slot)
    headers, expected, selected = _capture(packet, expected_file)
    _match(repository_path, commit, binding_name, inputs_name, intent_uri, expected)
    if (previous.intent_uri, previous.binding, previous.inputs) != (
        expected.intent_uri,
        expected.binding,
        expected.inputs,
    ):
        raise ValueError(
            "adoption intent/binding/full inputs differ from existing selection"
        )
    if previous.attempt_id == selected.attempt_id:
        raise ValueError("adoption requires a distinct attempt occurrence")
    _history(repository_path, commit, selected.commit)
    return _publish(
        repository_path,
        commit,
        slot,
        ref,
        headers,
        expected,
        selected,
        replace=True,
        map_size=map_size,
    )


def main(argv=None):
    """Finite offline explicit actions; fresh execution uses existing separate modes."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    for mode in ("select", "inspect", "reuse-selected", "adopt"):
        command = commands.add_parser(mode)
        for name in ("repository", "commit", "slot"):
            command.add_argument(name)
        if mode != "inspect":
            for name in ("binding", "inputs", "intent"):
                command.add_argument(name)
            if mode in ("select", "adopt"):
                command.add_argument("expected")
                command.add_argument("packet")
            else:
                command.add_argument("submission_ref")
            command.add_argument("ref")
    args = parser.parse_args(argv)
    keywords = dict(commit=d.ObjectId.from_hex(args.commit), slot=args.slot)
    if args.mode != "inspect":
        keywords.update(
            binding_name=args.binding,
            inputs_name=args.inputs,
            intent_uri=args.intent,
            ref=args.ref,
        )
    if args.mode in ("select", "adopt"):
        keywords.update(expected_file=args.expected, packet=args.packet)
        got = (select if args.mode == "select" else adopt)(args.repository, **keywords)
    elif args.mode == "inspect":
        got = inspect(args.repository, **keywords)
    else:
        got = reuse_selected(
            args.repository, submission_ref=args.submission_ref, **keywords
        )
    result = dict(
        mode=args.mode,
        commit=str(got.commit),
        attempt=str(got.attempt),
        result=str(got.result),
    )
    if args.mode == "reuse-selected":
        result.update(
            association=str(got.dag),
            request=str(got.recorded.request),
            request_id=got.recorded.request_id,
            request_commit=str(got.recorded.commit),
        )
    else:
        result.update(
            selection=str(got.dag),
            validation=str(got.validation),
            completion=str(got.completion),
            attempt_id=got.attempt_id,
            request=str(got.request),
            slot=got.slot,
        )
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
