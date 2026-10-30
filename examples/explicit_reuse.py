"""Example-local explicit historical-attempt reuse; never dispatches or imports HTTP.

Independent historical packet/expected supplies OLD T/result authority. This operation
records its own NEW Q, then separately publishes ordinary W. A W failure can leave Q
pending; missing response can leave complete W. No fallback, resume or cache discovery.
"""

import argparse
from dataclasses import dataclass
import json

import daggerml as d
from daggerml import exchange as ex, transfer


@dataclass(frozen=True)
class Reused:
    recorded: ex.RecordedRequest
    commit: d.ObjectId
    dag: d.ObjectId
    ref: str
    attempt: d.ObjectId
    result: d.ObjectId


def reuse_attempt(
    repository_path,
    *,
    commit,
    binding_name,
    inputs_name,
    intent_uri,
    historical_packet,
    historical_expected,
    submission_ref,
    ref,
    map_size=0,
):
    """Validate/match BEFORE new Q; publish Q and W in SEPARATE transactions.

    Require successful F already reachable through any parent of pinned C. Recorded
    cleanup failure is permitted by this example policy, never repaired/reclassified.
    Only the public inspector owns historical roles. No incoming RecordedRequest or
    ReceivedObservation description is accepted as authoring authority.
    """
    selected = ex.read_observation(historical_packet, expected=historical_expected)
    if historical_expected.request is None:
        raise ValueError("reuse requires independently pinned historical Cq/Q")
    if (
        selected.phase != "completion"
        or selected.lifecycle != "done"
        or selected.completion is None
        or selected.completion.outcome != "success"
        or selected.result is None
    ):
        raise ValueError("reuse requires a successful recorded completion")
    with d.Repository(repository_path) as repository, repository.read() as tx:
        entries = tx.get_tree(tx.get_commit(commit).tree)
        binding, inputs = entries[binding_name], entries[inputs_name]
        if (intent_uri, binding, inputs) != (
            historical_expected.intent_uri,
            historical_expected.binding,
            historical_expected.inputs,
        ):
            raise ValueError("reuse intent/binding/full inputs differ")
        pending, seen = [commit], set()
        while pending:
            current = pending.pop()
            if current not in seen:
                seen.add(current)
                pending.extend(tx.get_commit(current).parents)
        if selected.commit not in seen:
            raise ValueError("historical F is not in basis all-parent history")
    # Public complete typed closure validation also rejects missing/corrupt composite
    # descendants in A BEFORE Q. The existing bounded transfer profile applies.
    transfer.export_commit(repository_path, commit=commit)
    recorded = ex.record_exchange_request(
        repository_path,
        commit=commit,
        binding_name=binding_name,
        inputs_name=inputs_name,
        intent_uri=intent_uri,
        ref=submission_ref,
        map_size=map_size,
    )
    if (recorded.intent_uri, recorded.binding, recorded.inputs) != (
        historical_expected.intent_uri,
        historical_expected.binding,
        historical_expected.inputs,
    ):
        raise ValueError("actual newly recorded request selection differs")
    with d.Repository(
        repository_path, map_size=map_size
    ) as repository, repository.write() as tx:
        entries = dict(tx.get_tree(tx.get_commit(recorded.commit).tree))
        name = "reuse-" + recorded.request_id
        if name in entries:
            raise ValueError("reuse tree name already exists")
        result = tx.put_subdag(selected.result)
        association = tx.put_dag(
            root=result,
            bindings={
                "role": tx.put_literal(tx.put_datum("example-explicit-reuse-v1")),
                "request": tx.put_subdag(recorded.request),
                "attempt": tx.put_subdag(selected.completion.final_attempt),
                "result": result,
            },
        )
        entries[name] = association
        reused = tx.put_commit(tx.put_tree(entries), parents=(recorded.commit,))
        tx.create_ref(ref, reused)
        response = Reused(
            recorded,
            reused,
            association,
            ref,
            selected.completion.final_attempt,
            selected.result,
        )  # Allocate BEFORE W storage commit.
    return response


def main(argv=None):
    """One finite offline reuse action; expected file is independently caller-owned."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "repository",
        "commit",
        "binding",
        "inputs",
        "intent",
        "expected",
        "packet",
        "submission_ref",
        "ref",
    ):
        parser.add_argument(name)
    args = parser.parse_args(argv)
    got = reuse_attempt(
        args.repository,
        commit=d.ObjectId.from_hex(args.commit),
        binding_name=args.binding,
        inputs_name=args.inputs,
        intent_uri=args.intent,
        historical_expected=ex.load_exchange_handle(args.expected).expected,
        historical_packet=args.packet,
        submission_ref=args.submission_ref,
        ref=args.ref,
    )
    print(
        json.dumps(
            dict(
                mode="reuse",
                commit=str(got.commit),
                association=str(got.dag),
                ref=got.ref,
                request=str(got.recorded.request),
                request_id=got.recorded.request_id,
                request_commit=str(got.recorded.commit),
                attempt=str(got.attempt),
                result=str(got.result),
            )
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
