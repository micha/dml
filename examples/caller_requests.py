"""Record caller Q before launch; finite owner and fresh clients retain exact Q/T.

With installed runtime, outside checkout:
  python /path/to/examples/caller_requests.py NEW_STORY_DIRECTORY
No detached lifetime promise: this application retains its live WorkerLaunch.
"""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from daggerml import Datum, NotFoundError, ObjectId, Repository
from daggerml.exchange import (
    ExchangeHandle,
    load_exchange_handle,
    observe_exchange,
    prepare_exchange,
    record_exchange_request,
    receive_observation,
    save_exchange_handle,
    start_exchange,
)
from daggerml.local import put_local_binding, run_step


def describe(observation):
    snapshot = observation.snapshot
    return {
        "phase": observation.phase,
        "lifecycle": observation.lifecycle,
        "commit": None if snapshot is None else str(snapshot.commit),
        "request_id": None if snapshot is None else snapshot.request_id,
        "attempt_id": None if snapshot is None else snapshot.attempt_id,
    }


def client(args):
    # subprocess.run owns/reaps this finite short-lived client; it owns no worker.
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode != 0:
        raise RuntimeError("example client failed")
    return json.loads(result.stdout)


def poll(saved, directory, phase):
    deadline, index = time.monotonic() + 15, 0
    while time.monotonic() < deadline:
        packet = directory / (phase + "-" + str(index))
        got = client(["--observe", str(saved), str(packet)])
        if got["phase"] == phase:
            return got, packet
        if got["phase"] not in ("bootstrap", "initial", "publication"):
            raise RuntimeError("finite demonstration missed requested phase")
        index += 1
        time.sleep(0.02)
    raise TimeoutError("finite observation deadline expired")


def receive(path, packet, saved, ref):
    # Expected is caller-owned saved selection, never inferred from packet/B.
    expected = load_exchange_handle(saved).expected
    got = receive_observation(path, packet=packet, expected=expected, ref=ref)
    assert receive_observation(path, packet=packet, expected=expected, ref=ref) == got
    return {
        "phase": got.phase,
        "lifecycle": got.lifecycle,
        "commit": str(got.commit),
        "request_id": got.request_id,
        "attempt_id": got.attempt_id,
        "result": None if got.result is None else str(got.result),
        "outcome": None if got.completion is None else got.completion.outcome,
        "cleanup": None if got.completion is None else got.completion.cleanup,
    }


def produce(directory):
    directory = Path(directory).resolve()
    directory.mkdir()
    caller = directory / "caller.dml"
    gates = directory / "gates"
    gates.mkdir()
    with Repository(caller, create=True) as repo, repo.write() as tx:
        inputs = {
            n: tx.put_literal(tx.put_datum(v)) for n, v in (("left", 4), ("right", 7))
        }
        inputs["gate"] = tx.put_literal(tx.put_datum(str(gates)))
        inputs = tx.put_dag(root=inputs["left"], bindings=inputs)
        source = Path(__file__).with_name("local_slow_add.py").read_bytes()
        binding = put_local_binding(
            tx, source=source, interpreter=sys.executable, timeout_ms=40000
        )
        failed = put_local_binding(
            tx,
            source=source + b"\nraise RuntimeError('after publication')",
            interpreter=sys.executable,
            timeout_ms=40000,
        )
        hidden = tx.put_datum("composite-only retained child")
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
        commit = tx.put_commit(
            tx.put_tree({"binding": binding, "inputs": inputs, "keep": keep})
        )
        fail_commit = tx.put_commit(
            tx.put_tree({"binding": failed, "inputs": inputs, "keep": keep}),
            parents=(commit,),
        )
        sentinel = tx.put_commit(tx.put_tree({"sentinel": keep}))
        tx.create_ref("main", commit)
        tx.create_ref("sentinel", sentinel)
    # Real unrelated prior Q/T/publication history in C, not fake prefix names.
    with Repository(caller) as repo, repo.write() as tx:
        warm_binding = put_local_binding(
            tx,
            source=Path(__file__).with_name("local_add.py").read_bytes(),
            interpreter=sys.executable,
            timeout_ms=10000,
        )
    warm = run_step(
        caller,
        head_ref="main",
        intent_uri="urn:example:prior-add",
        binding=warm_binding,
        inputs=inputs,
        scratch_dir=directory,
    )
    commit = warm.final_commit
    with Repository(caller) as repo, repo.write() as tx:
        selected_tree = dict(tx.get_tree(tx.get_commit(commit).tree))
        selected_tree["binding"] = failed
        fail_commit = tx.put_commit(tx.put_tree(selected_tree), parents=(commit,))
    manifest = {
        "base": str(commit),
        "sentinel": str(sentinel),
        "runs": [],
        "submissions": [],
        "prior_request_ref": "request-" + warm.request_id,
        "prior_request_target": str(warm.context.pre_dispatch),
        "prior_attempt_ref": warm.context.publication_ref,
    }
    with Repository(caller) as repo, repo.read() as tx:
        manifest["prior_attempt_target"] = str(tx.get_ref(warm.context.publication_ref))
    for index, selected in enumerate((commit, commit, fail_commit), 1):
        for phase in ("initial", "publication"):
            (gates / (phase + "-release")).unlink(missing_ok=True)
        workspace = directory / ("workspace-" + str(index))
        recorded = record_exchange_request(
            caller,
            commit=selected,
            binding_name="binding",
            inputs_name="inputs",
            intent_uri="urn:example:add-i64",
            ref="submission-" + str(index),
        )
        # Q exists with two refs BEFORE workspace/worker/attempt exists.
        with Repository(caller) as repo, repo.read() as tx:
            assert tx.get_ref(recorded.ref) == recorded.commit
            assert tx.get_ref("request-" + recorded.request_id) == recorded.commit
            assert tx.get_commit(recorded.commit).parents == (selected,)
        manifest["submissions"].append(
            {
                "commit": str(recorded.commit),
                "request": str(recorded.request),
                "request_id": recorded.request_id,
                "ref": recorded.ref,
            }
        )
        spec = prepare_exchange(
            caller,
            commit=recorded.commit,
            request=recorded.request,
            binding_name="binding",
            inputs_name="inputs",
            intent_uri="urn:example:add-i64",
            worker_ref="work",
            workspace=workspace,
        )
        saved = directory / ("handle-" + str(index) + ".json")
        h = ExchangeHandle(workspace, spec)
        save_exchange_handle(saved, h)
        observers = directory / ("observations-" + str(index))
        observers.mkdir()
        offline = directory / "caller.offline"
        caller.rename(offline)
        launch = None
        try:
            launch = start_exchange(h)  # this application is the sole live owner
            packets, snapshots = [], []
            for phase in ("initial", "publication", "completion"):
                got, packet = poll(saved, observers, phase)
                snapshots.append(got)
                packets.append(packet)
                if phase != "completion":
                    (gates / (phase + "-release")).touch()
            assert launch.wait(timeout=15) == 0
        finally:
            # Cooperative owned gates are normal example input, not a runtime
            # hook. Release them on errors before waiting; never signal the worker
            # while its child might still run. Hard owner loss remains unsupported.
            for phase in ("initial", "publication"):
                (gates / (phase + "-release")).touch()
            if launch is not None:
                launch.wait(timeout=20)
            offline.rename(caller)
        assert len({s["request_id"] for s in snapshots}) == 1
        assert snapshots[0]["request_id"] == recorded.request_id
        # Original synchronous receipt is unnecessary after known worker reaping.
        (workspace / "completion.json").unlink()
        assert (
            client(["--observe", str(saved), str(observers / "receipt-loss")])["phase"]
            == "completion"
        )
        assert len({s["attempt_id"] for s in snapshots}) == 1
        if index == 1:
            with Repository(caller) as repo, repo.write() as tx:
                newer = tx.put_commit(tx.put_tree({"later": keep}), parents=(commit,))
                tx.update_ref("main", newer)
                manifest["main"] = str(newer)
        # Packets alone suffice; B offline before any receive. Paths in saved
        # handle/history are inert during receipt and never cleanup authority.
        (workspace / "worker.dml").rename(workspace / "worker.offline")
        returned = []
        for phase, packet in zip(("initial", "publication", "completion"), packets):
            copied = directory / ("packet-" + str(index) + "-" + phase)
            shutil.copytree(packet, copied)
            ref = "trial-" + str(index) + "-" + phase
            got = client(["--receive", str(caller), str(copied), str(saved), ref])
            got["ref"] = ref
            returned.append(got)
        assert returned[-1]["outcome"] == ("failure" if index == 3 else "success")
        manifest["runs"].append(returned)
    unstarted = record_exchange_request(
        caller,
        commit=commit,
        binding_name="binding",
        inputs_name="inputs",
        intent_uri="urn:example:add-i64",
        ref="submission-unstarted",
    )
    manifest["unstarted"] = {
        "commit": str(unstarted.commit),
        "request": str(unstarted.request),
        "request_id": unstarted.request_id,
        "ref": unstarted.ref,
    }
    assert manifest["runs"][0][-1]["result"] == manifest["runs"][1][-1]["result"]
    assert len({run[-1]["attempt_id"] for run in manifest["runs"]}) == 3
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def inspect(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    with Repository(directory / "caller.dml") as repo, repo.read() as tx:
        assert str(tx.get_ref("main")) == manifest["main"]
        assert str(tx.get_ref("sentinel")) == manifest["sentinel"]
        assert (
            str(tx.get_ref(manifest["prior_request_ref"]))
            == manifest["prior_request_target"]
        )
        assert (
            str(tx.get_ref(manifest["prior_attempt_ref"]))
            == manifest["prior_attempt_target"]
        )
        for submission in manifest["submissions"] + [manifest["unstarted"]]:
            cq = ObjectId.from_hex(submission["commit"])
            q = ObjectId.from_hex(submission["request"])
            assert tx.get_ref(submission["ref"]) == cq
            assert tx.get_ref("request-" + submission["request_id"]) == cq
            tree = tx.get_tree(tx.get_commit(cq).tree)
            assert tree["request-" + submission["request_id"]] == q
        for run in manifest["runs"]:
            for got in run:
                assert str(tx.get_ref(got["ref"])) == got["commit"]
                snapshot = dict(
                    tx.get_tree(tx.get_commit(ObjectId.from_hex(got["commit"])).tree)
                )
                attempt = tx.get_dag(snapshot["attempt-" + got["attempt_id"]])
                assert ("status" in attempt.bindings) == (got["phase"] == "completion")
                for ref in ("work", "attempt-" + got["attempt_id"]):
                    try:
                        tx.get_ref(ref)
                    except NotFoundError:
                        pass
                    else:
                        raise AssertionError("worker refs were copied")
    return manifest


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) == 3 and args[0] == "--observe":
        print(
            json.dumps(
                describe(
                    observe_exchange(load_exchange_handle(args[1]), packet=args[2])
                )
            )
        )
    elif len(args) == 5 and args[0] == "--receive":
        print(json.dumps(receive(args[1], args[2], args[3], args[4])))
    elif len(args) == 2 and args[0] == "--inspect":
        print(json.dumps(inspect(args[1])))
    elif len(args) == 1:
        produce(args[0])
        print(json.dumps(inspect(args[0])))
    else:
        raise SystemExit("usage: caller_requests.py NEW_STORY_DIRECTORY")


if __name__ == "__main__":
    main()
