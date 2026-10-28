"""Endpoint-driven synchronous caller-Q SSH story; no Docker application dependency.

With installed runtime: python ssh_execution.py NEW_STORY HOST PORT USER KEY KNOWN_HOSTS
REMOTE_PYTHON REMOTE_ROOT. The caller owns retained transport artifacts and remote
workspace retirement. A connection error never initiates another dispatch.
"""

import json
from pathlib import Path
import sys

from daggerml import Datum, Repository
from daggerml.exchange import (
    prepare_exchange,
    record_exchange_request,
    receive_exchange,
)
from daggerml.local import put_local_binding, run_step
from daggerml.ssh import (
    SSHRemote,
    execute_ssh_exchange,
    fetch_ssh_exchange,
    stage_ssh_exchange,
)


def produce(directory, remote):
    directory = Path(directory).resolve()
    directory.mkdir()
    caller = directory / "caller.dml"
    source = Path(__file__).with_name("local_add.py").read_bytes()
    with Repository(caller, create=True) as repo, repo.write() as tx:
        nodes = {
            n: tx.put_literal(tx.put_datum(v)) for n, v in (("left", 4), ("right", 7))
        }
        inputs = tx.put_dag(root=nodes["left"], bindings=nodes)
        binding = put_local_binding(
            tx, source=source, interpreter=remote.python, timeout_ms=10000
        )
        failed = put_local_binding(
            tx,
            source=source + b"\nraise RuntimeError('after publication')",
            interpreter=remote.python,
            timeout_ms=10000,
        )
        warm_binding = put_local_binding(
            tx, source=source, interpreter=sys.executable, timeout_ms=10000
        )
        hidden = tx.put_datum("composite-only child")
        keep = tx.put_dag(
            root=tx.put_literal(
                tx.put_datum(
                    Datum.map(
                        [
                            (
                                tx.put_datum(Datum.list([hidden, hidden])),
                                tx.put_datum(Datum.set([hidden])),
                            )
                        ]
                    )
                )
            )
        )
        base = tx.put_commit(
            tx.put_tree({"binding": binding, "inputs": inputs, "keep": keep})
        )
        sentinel = tx.put_commit(tx.put_tree({"sentinel": keep}))
        tx.create_ref("main", base)
        tx.create_ref("sentinel", sentinel)
    warm = run_step(
        caller,
        head_ref="main",
        intent_uri="urn:example:prior-add",
        binding=warm_binding,
        inputs=inputs,
        scratch_dir=directory,
    )
    base = warm.final_commit
    with Repository(caller) as repo, repo.write() as tx:
        selected = dict(tx.get_tree(tx.get_commit(base).tree))
        selected["binding"] = failed
        fail_base = tx.put_commit(tx.put_tree(selected), parents=(base,))
    unused = record_exchange_request(
        caller,
        commit=base,
        binding_name="binding",
        inputs_name="inputs",
        intent_uri="urn:example:add-i64",
        ref="unstarted",
    )
    runs = []
    for index, selected in enumerate((base, base, fail_base), 1):
        recorded = record_exchange_request(
            caller,
            commit=selected,
            binding_name="binding",
            inputs_name="inputs",
            intent_uri="urn:example:add-i64",
            ref="submission-" + str(index),
        )
        workspace = directory / ("input-" + str(index))
        spec = prepare_exchange(
            caller,
            commit=recorded.commit,
            request=recorded.request,
            binding_name="binding",
            inputs_name="inputs",
            intent_uri=recorded.intent_uri,
            worker_ref="work",
            workspace=workspace,
        )
        job = stage_ssh_exchange(
            remote,
            workspace=workspace,
            expected=spec,
            control=directory / ("control-" + str(index)),
            timeout_ms=20000,
        )
        # Control remains online separately from A and already-staged input artifacts.
        offline = directory / "caller.offline"
        caller.rename(offline)
        workspace.rename(workspace.with_name(workspace.name + ".offline"))
        try:
            execute_ssh_exchange(job, timeout_ms=20000)
        finally:
            offline.rename(caller)
        packet = fetch_ssh_exchange(
            job, packet=directory / ("packet-" + str(index)), timeout_ms=20000
        )
        with Repository(caller) as repo, repo.write() as tx:
            newer = tx.put_commit(
                tx.put_tree({"later": keep}), parents=(tx.get_ref("main"),)
            )
            tx.update_ref("main", newer)
        ref = "trial-" + str(index)
        received = receive_exchange(caller, workspace=packet, expected=spec, ref=ref)
        assert (
            receive_exchange(caller, workspace=packet, expected=spec, ref=ref)
            == received
        )
        with Repository(caller) as repo, repo.read() as tx:
            assert tx.get_ref("main") == newer and tx.get_ref("sentinel") == sentinel
            assert tx.get_ref(recorded.ref) == spec.commit
            assert tx.get_ref("request-" + received.request_id) == spec.commit
        runs.append(
            {
                "commit": str(received.commit),
                "request": str(received.request),
                "request_id": received.request_id,
                "attempt_id": received.attempt_id,
                "outcome": received.outcome,
                "cleanup": received.cleanup,
                "result": None if received.result is None else str(received.result),
                "evidence": (
                    None if received.evidence is None else str(received.evidence)
                ),
            }
        )
    assert runs[0]["result"] == runs[1]["result"]
    assert runs[0]["request_id"] != runs[1]["request_id"]
    assert runs[0]["attempt_id"] != runs[1]["attempt_id"]
    assert runs[2]["outcome"] == "failure" and runs[2]["evidence"] is not None
    return {"base": str(base), "unstarted": str(unused.request), "runs": runs}


def main(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != 8:
        raise ValueError(
            "expected story, host, port, user, key, known-hosts, remote-python, remote-root"
        )
    directory, host, port, user, key, known_hosts, python, root = args
    remote = SSHRemote(host, int(port), user, key, known_hosts, python, root)
    print(json.dumps(produce(directory, remote), separators=(",", ":")))


if __name__ == "__main__":
    main()
