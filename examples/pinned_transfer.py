"""Copy two recorded additions without executing imported source.

With an installed runtime, from outside the checkout:
  python /path/to/examples/pinned_transfer.py /fresh/parent/story
The caller-owned story directory must not exist; its parent must exist.
"""

import base64
import json
from pathlib import Path
import subprocess
import sys

from daggerml import NotFoundError, ObjectId, Repository
from daggerml.local import put_local_binding, run_step
from daggerml.transfer import export_commit, import_commit


def scalar(tx, dag, name):
    return tx.get_datum(tx.get_node(tx.lookup_node(dag, name)).datum).value


def nested(tx, dag, name):
    return tx.get_node(tx.lookup_node(dag, name)).dag


def produce(directory):
    """Create/export A and save independent ordinary-history assertions."""
    directory = Path(directory).resolve()
    directory.mkdir()
    source = directory / "source.dml"
    with Repository(source, create=True) as repo, repo.write() as tx:
        nodes = {
            name: tx.put_literal(tx.put_datum(value)) for name, value in [("left", 4), ("right", 7)]
        }
        inputs = tx.put_dag(root=nodes["left"], bindings=nodes)
        binding = put_local_binding(
            tx,
            source=Path(__file__).with_name("local_add.py").read_bytes(),
            interpreter=sys.executable,
            timeout_ms=10000,
        )
        tx.create_ref("main", tx.put_commit(tx.put_tree({"inputs": inputs})))
    runs = [
        run_step(
            source,
            head_ref="main",
            intent_uri="urn:example:add-i64",
            binding=binding,
            inputs=inputs,
            scratch_dir=directory,
        )
        for _ in range(2)
    ]
    assert runs[0].request_id != runs[1].request_id
    assert runs[0].attempt_id != runs[1].attempt_id
    assert runs[0].result == runs[1].result
    assert all(run.outcome == "success" and run.cleanup == "ok" for run in runs)
    root = runs[-1].final_commit
    bundle = export_commit(source, commit=root)
    with Repository(source) as repo, repo.write() as tx:
        unrelated = tx.put_datum("unrelated source branch sentinel")
        other = tx.put_commit(tx.put_tree({"other": tx.put_dag(root=tx.put_literal(unrelated))}))
        tx.create_ref("other", other)
        tx.update_ref("main", other)
    assert export_commit(source, commit=root) == bundle
    manifest = {"root": str(root), "unrelated": str(unrelated), "runs": []}
    with Repository(source) as repo, repo.read() as tx:
        # Save exact original bytes through reads, not transfer's insertion results.
        for row in json.loads(bundle)["objects"]:
            assert tx.get_record(row["kind"], ObjectId.from_hex(row["id"])) == base64.b64decode(
                row["record"]
            )
        for run in runs:
            manifest["runs"].append(
                {
                    "request": str(run.context.request),
                    "attempt": str(run.context.attempt),
                    "request_id": run.request_id,
                    "attempt_id": run.attempt_id,
                    "final_attempt": str(run.final_attempt),
                    "pre": str(run.context.pre_dispatch),
                    "final": str(run.final_commit),
                    "result": str(run.result),
                    "publication": str(tx.get_ref(run.context.publication_ref)),
                    "publication_ref": run.context.publication_ref,
                }
            )
    # Caller-owned ordinary file writes are not atomic filesystem publication.
    (directory / "bundle.json").write_bytes(bundle)
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    dest = directory / "destination.dml"
    with Repository(dest, create=True) as repo, repo.write() as tx:
        keep = tx.put_commit(tx.put_tree({}))
        tx.create_ref("keep", keep)
    manifest["keep"] = str(keep)
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return directory


def receive(directory):
    """Fresh importer needs only bundle and initialized B, never A."""
    directory = Path(directory)
    bundle = (directory / "bundle.json").read_bytes()
    dest = directory / "destination.dml"
    received = import_commit(dest, bundle, ref="received")
    assert import_commit(dest, bundle, ref="received") == received
    assert import_commit(dest, bundle).commit == received.commit
    assert export_commit(dest, commit=received.commit) == bundle
    return received


def inspect(directory):
    """Ordinary reads validate occurrences, parent order, values, bytes and absent refs."""
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    with Repository(directory / "destination.dml") as repo, repo.read() as tx:
        assert str(tx.get_ref("received")) == manifest["root"]
        assert str(tx.get_ref("keep")) == manifest["keep"]
        for row in json.loads((directory / "bundle.json").read_bytes())["objects"]:
            assert tx.get_record(row["kind"], ObjectId.from_hex(row["id"])) == base64.b64decode(
                row["record"]
            )
        for run in manifest["runs"]:
            oid = lambda name: ObjectId.from_hex(run[name])
            assert tx.get_commit(oid("final")).parents == (oid("pre"), oid("publication"))
            for name, value in [
                ("request", run["request_id"]),
                ("attempt", run["attempt_id"]),
                ("final_attempt", run["attempt_id"]),
            ]:
                assert tx.get_datum(tx.get_node(tx.get_dag(oid(name)).root).datum).value == value
            assert "status" not in tx.get_dag(oid("attempt")).bindings
            assert scalar(tx, oid("final_attempt"), "status") == "done"
            assert nested(tx, oid("final_attempt"), "request") == oid("request")
            outcome = nested(tx, oid("final_attempt"), "outcome")
            assert nested(tx, outcome, "result") == oid("result")
            assert scalar(tx, oid("result"), "result") == 11
            assert scalar(tx, nested(tx, oid("final_attempt"), "cleanup"), "disposition") == "ok"
            for ref in (run["publication_ref"], "request-" + run["request_id"]):
                try:
                    tx.get_ref(ref)
                except NotFoundError:
                    pass
                else:
                    raise AssertionError("source refs were copied")
        for kind, oid in [("datum", ObjectId.from_hex(manifest["unrelated"]))]:
            try:
                tx.get_record(kind, oid)
            except NotFoundError:
                pass
            else:
                raise AssertionError("unrelated source object was copied")
        try:
            tx.get_ref("main")
        except NotFoundError:
            pass
        else:
            raise AssertionError("source main was inferred")
    return manifest


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) == 2 and args[0] == "--receive":
        receive(args[1])
    elif len(args) == 2 and args[0] == "--inspect":
        print(json.dumps(inspect(args[1]), sort_keys=True))
    elif len(args) == 1:
        directory = produce(args[0])
        for mode in ("--receive", "--inspect"):
            subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), mode, str(directory)],
                check=True,
                timeout=30,
            )
    else:
        raise SystemExit("usage: pinned_transfer.py NEW_STORY_DIRECTORY")


if __name__ == "__main__":
    main()
