"""One step in independent local B, explicitly returned to A without adoption.

With an installed runtime, outside the checkout:
  python /path/to/examples/repository_execution.py /fresh/parent/story
The caller-owned story directory must not exist. --worker is a small synchronous
example driver, not a new dml CLI command or process-tree supervisor.
"""

from dataclasses import asdict
import json
from pathlib import Path
import shutil
import subprocess
import sys

from daggerml import NotFoundError, ObjectId, Repository
from daggerml.exchange import (
    ExchangeSpec,
    execute_exchange,
    prepare_exchange,
    receive_exchange,
)
from daggerml.local import put_local_binding


def save_expected(file, spec):
    values = asdict(spec)
    for name in ("commit", "binding", "inputs"):
        values[name] = str(getattr(spec, name))
    file.write_text(json.dumps(values), encoding="utf-8")


def load_expected(file):
    # Caller-owned input supplied independently, not inferred from worker receipt.
    values = json.loads(file.read_text(encoding="utf-8"))
    for name in ("commit", "binding", "inputs"):
        values[name] = ObjectId.from_hex(values[name])
    return ExchangeSpec(**values)


def scalar(tx, dag, name):
    return tx.get_datum(tx.get_node(tx.lookup_node(dag, name)).datum).value


def nested(tx, dag, name):
    return tx.get_node(tx.lookup_node(dag, name)).dag


def supervise(args):
    """Finite direct-worker ownership. Does not promise child/descendant cleanup."""
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), *args], stdin=subprocess.DEVNULL
    )
    try:
        if process.wait(timeout=30) != 0:
            raise RuntimeError("example worker/receiver failed")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def receive(path, workspace, expected_file, ref):
    received = receive_exchange(
        path, workspace=workspace, expected=load_expected(expected_file), ref=ref
    )
    assert (
        receive_exchange(
            path, workspace=workspace, expected=load_expected(expected_file), ref=ref
        )
        == received
    )
    return received


def produce(directory):
    directory = Path(directory).resolve()
    directory.mkdir()
    caller = directory / "caller.dml"
    with Repository(caller, create=True) as repo, repo.write() as tx:
        nodes = {
            name: tx.put_literal(tx.put_datum(value))
            for name, value in (("left", 4), ("right", 7))
        }
        inputs = tx.put_dag(root=nodes["left"], bindings=nodes)
        source = Path(__file__).with_name("local_add.py").read_bytes()
        binding = put_local_binding(
            tx, source=source, interpreter=sys.executable, timeout_ms=10000
        )
        failed_binding = put_local_binding(
            tx,
            source=b"raise RuntimeError('deliberate failure')",
            interpreter=sys.executable,
            timeout_ms=10000,
        )
        keep = tx.put_dag(
            root=tx.put_literal(tx.put_datum("unrelated retained research"))
        )
        base_tree = {"binding": binding, "inputs": inputs, "keep": keep}
        commit = tx.put_commit(tx.put_tree(base_tree))
        failure_commit = tx.put_commit(
            tx.put_tree(dict(base_tree, binding=failed_binding)), parents=(commit,)
        )
        sentinel = tx.put_commit(tx.put_tree({"sentinel": keep}))
        tx.create_ref("main", commit)
        tx.create_ref("sentinel", sentinel)
    manifest = {
        "base": str(commit),
        "sentinel": str(sentinel),
        "keep": str(keep),
        "runs": [],
    }
    for index, selected in enumerate((commit, commit, failure_commit), 1):
        workspace = directory / ("workspace-" + str(index))
        spec = prepare_exchange(
            caller,
            commit=selected,
            binding_name="binding",
            inputs_name="inputs",
            intent_uri="urn:example:add-i64",
            worker_ref="work",
            workspace=workspace,
        )
        expected_file = directory / ("expected-" + str(index) + ".json")
        save_expected(expected_file, spec)
        # Functional separation, not access control: worker arguments contain no A path.
        offline = directory / "caller.offline"
        caller.rename(offline)
        try:
            supervise(["--worker", str(workspace)])
        finally:
            offline.rename(caller)
        with Repository(caller) as repo, repo.read() as tx:
            assert str(tx.get_ref("main")) == manifest.get("main", manifest["base"])
        # Caller independently advances main after pinning first input.
        if index == 1:
            with Repository(caller) as repo, repo.write() as tx:
                later = tx.put_commit(tx.put_tree({"later": keep}), parents=(commit,))
                tx.update_ref("main", later)
                manifest["main"] = str(later)
        packet = directory / ("packet-" + str(index))
        packet.mkdir()
        for name in ("job.json", "completion.json", "output.bundle"):
            shutil.copyfile(workspace / name, packet / name)
        (workspace / "worker.dml").rename(workspace / "worker.offline")
        ref = "trial-" + str(index)
        supervise(["--receive", str(caller), str(packet), str(expected_file), ref])
        returned = receive(caller, packet, expected_file, ref)
        assert returned.outcome == ("failure" if index == 3 else "success")
        manifest["runs"].append(
            {
                "ref": ref,
                "final": str(returned.commit),
                "pre": str(returned.pre_dispatch),
                "request_id": returned.request_id,
                "attempt_id": returned.attempt_id,
                "request": str(returned.request),
                "initial_attempt": str(returned.initial_attempt),
                "final_attempt": str(returned.final_attempt),
                "outcome": returned.outcome,
                "result": None if returned.result is None else str(returned.result),
                "cleanup": returned.cleanup,
            }
        )
    assert manifest["runs"][0]["result"] == manifest["runs"][1]["result"]
    assert len({run["request_id"] for run in manifest["runs"]}) == 3
    assert len({run["attempt_id"] for run in manifest["runs"]}) == 3
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return directory


def inspect(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    with Repository(directory / "caller.dml") as repo, repo.read() as tx:
        assert str(tx.get_ref("main")) == manifest["main"]
        assert str(tx.get_ref("sentinel")) == manifest["sentinel"]
        for run in manifest["runs"]:
            oid = lambda key: ObjectId.from_hex(run[key])
            assert tx.get_ref(run["ref"]) == oid("final")
            parents = tx.get_commit(oid("final")).parents
            assert parents[0] == oid("pre") and len(parents) == (
                1 if run["outcome"] == "failure" else 2
            )
            assert "status" not in tx.get_dag(oid("initial_attempt")).bindings
            assert scalar(tx, oid("final_attempt"), "status") == "done"
            assert nested(tx, oid("final_attempt"), "request") == oid("request")
            assert (
                scalar(tx, nested(tx, oid("final_attempt"), "cleanup"), "disposition")
                == run["cleanup"]
            )
            assert (
                str(dict(tx.get_tree(tx.get_commit(oid("final")).tree))["keep"])
                == manifest["keep"]
            )
            outcome = nested(tx, oid("final_attempt"), "outcome")
            if run["result"] is not None:
                assert nested(tx, outcome, "result") == oid("result")
                assert scalar(tx, oid("result"), "result") == 11
            else:
                assert scalar(tx, outcome, "reason") == "child-exit"
            for ref in (
                "work",
                "request-" + run["request_id"],
                "attempt-" + run["attempt_id"],
            ):
                try:
                    tx.get_ref(ref)
                except NotFoundError:
                    pass
                else:
                    raise AssertionError("worker refs were copied")
    return manifest


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) == 2 and args[0] == "--worker":
        execute_exchange(args[1])
    elif len(args) == 5 and args[0] == "--receive":
        receive(args[1], Path(args[2]), Path(args[3]), args[4])
    elif len(args) == 2 and args[0] == "--inspect":
        print(json.dumps(inspect(args[1]), sort_keys=True))
    elif len(args) == 1:
        directory = produce(args[0])
        supervise(["--inspect", str(directory)])
        print(json.dumps(inspect(directory), sort_keys=True))
    else:
        raise SystemExit("usage: repository_execution.py NEW_STORY_DIRECTORY")


if __name__ == "__main__":
    main()
