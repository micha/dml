"""Check one poisoned transaction recipe against live and stored graph evidence."""

import argparse
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
from shutil import which
import subprocess
import sys
from tempfile import TemporaryDirectory

import daggerml as dml
import generated_transactions as generated

from transaction_binding import Batch
from transaction_graph import load_batch, save_batch


INITIAL = "a"
REQUESTS = (("update_ref", "b"), ("create_ref", "a"))
FINISH = "commit"
REF = "transaction-evidence"
EXPECTED = {"commitClean": "unexercised", "commitPoisoned": "pass", "continuity": "pass",
            "explicitAbort": "unexercised", "freshMarker": "pass", "stepEffects": "pass"}


def checked_verdicts(batch: Batch) -> dict[str, str]:
    counts = generated.check(INITIAL, REQUESTS, FINISH, batch)
    verdicts = generated.verdicts(batch.evidence)
    assert verdicts == EXPECTED, verdicts
    assert counts == Counter(verdicts.items()), counts
    return verdicts


def load(path: Path, root: dml.ObjectId) -> Batch:
    return load_batch(path, root, initial=INITIAL, requests=REQUESTS, finish=FINISH)


def fresh_process(path: Path, root: dml.ObjectId, live: Batch, empty_bin: Path) -> None:
    # The child receives only a path and independently pinned root; JSON is a
    # comparison report sent back to the parent, never part of the stored graph.
    env = {"PATH": str(empty_bin)}
    if "PYTHONPATH" in os.environ:
        env["PYTHONPATH"] = os.environ["PYTHONPATH"]
    result = subprocess.run(
        [sys.executable, "-B", str(Path(__file__).resolve()), "--reopen", str(path), str(root)],
        capture_output=True, text=True, env=env, timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(f"Fresh graph reader failed ({result.returncode}):\n{result.stdout}{result.stderr}")
    expected = {"batch": asdict(live), "verdicts": EXPECTED}
    assert json.loads(result.stdout) == json.loads(json.dumps(expected)), result.stdout


def map_entries(tx: dml.Transaction, object_id: dml.ObjectId) -> dict[str, dml.ObjectId]:
    datum = tx.get_datum(object_id)
    assert datum.kind == "map", datum
    entries = {}
    for key, value in datum.value:
        name = tx.get_datum(key)
        assert name.kind == "string" and name.value not in entries, name
        entries[name.value] = value
    return entries


def put_entries(tx: dml.Transaction, fields: dict[str, dml.ObjectId]) -> dml.ObjectId:
    return tx.put_datum(dml.Datum.map((tx.put_datum(key), value) for key, value in fields.items()))


def read_entries(tx: dml.Transaction, root: dml.ObjectId) -> dict[str, dml.ObjectId]:
    assert tx.get_ref(REF) == root
    commit = tx.get_commit(root)
    assert commit.parents == ()
    tree = tx.get_tree(commit.tree)
    assert tuple(tree) == ("evidence",)
    dag = tx.get_dag(tree["evidence"])
    assert not dag.bindings
    node = tx.get_node(dag.root)
    assert isinstance(node, dml.LiteralNode), node
    fields = map_entries(tx, node.datum)
    assert fields.keys() == {"schema", "initial", "requests", "finish", "requested_ids", "evidence"}, fields
    assert tx.get_datum(fields["requests"]).kind == "list"
    assert tx.get_datum(fields["requested_ids"]).kind == "list"
    return fields


def reroot(
    tx: dml.Transaction, fields: dict[str, dml.ObjectId], *, parents: tuple[dml.ObjectId, ...] = (),
) -> dml.ObjectId:
    node = tx.put_literal(put_entries(tx, fields))
    dag = tx.put_dag(root=node)
    root = tx.put_commit(tx.put_tree({"evidence": dag}), parents=parents)
    tx.update_ref(REF, root)
    return root


def expect_invalid(message: str, check: Callable[[], object]) -> None:
    try:
        check()
    except ValueError as error:
        assert message in str(error), error
        return
    raise AssertionError(f"Expected the graph adapter to reject: {message}")


def check_controls(path: Path, root: dml.ObjectId, live: Batch) -> None:
    for initial, requests, finish in (("b", REQUESTS, FINISH), (INITIAL, REQUESTS[::-1], FINISH),
                                      (INITIAL, REQUESTS, "abort")):
        expect_invalid("another exercise", lambda: load_batch(path, root, initial=initial,
                                                               requests=requests, finish=finish))

    # The writer must reject malformed evidence before creating any repository.
    missing = {name: value for name, value in live.evidence.items() if name != "after"}
    invalid_path = path.with_name("incomplete")
    expect_invalid("complete transaction evidence",
                   lambda: save_batch(invalid_path, replace(live, evidence=missing)))
    assert not invalid_path.exists()

    # Bypass the adapter's encoder: build malformed evidence with public native
    # writes and pass each graph's actual root pin to the read-side guard.
    with dml.Repository(path) as repo, repo.write() as tx:
        fields = read_entries(tx, root)
        evidence = map_entries(tx, fields["evidence"])
        incomplete = {name: value for name, value in evidence.items() if name != "after"}
        incomplete_root = reroot(tx, {**fields, "evidence": put_entries(tx, incomplete)})
    assert incomplete_root != root
    expect_invalid("complete transaction evidence", lambda: load(path, incomplete_root))
    with dml.Repository(path) as repo, repo.write() as tx:
        schema_root = reroot(tx, {**fields, "schema": tx.put_datum("unknown-version")})
    expect_invalid("supported schema", lambda: load(path, schema_root))
    with dml.Repository(path) as repo, repo.write() as tx:
        parented_root = reroot(tx, fields, parents=(root,))
    expect_invalid("parentless commit", lambda: load(path, parented_root))

    with dml.Repository(path) as repo, repo.write() as tx:
        # Keep all other evidence, including the actual poisoned outcome. Change
        # only the post-rollback snapshot to publish the first update and marker.
        steps = tx.get_datum(evidence["steps"])
        assert steps.kind == "list" and len(steps.value) == 2, steps
        update = map_entries(tx, steps.value[0])
        published = {**evidence, "after": update["after"], "markerAfter": evidence["markerStaged"]}
        wrong_root = reroot(tx, {**fields, "evidence": put_entries(tx, published)})
    assert wrong_root not in (root, incomplete_root)
    expect_invalid("ref does not match the expected root", lambda: load(path, root))
    wrong = load(path, wrong_root)
    wrong_evidence = {**live.evidence, "after": live.evidence["steps"][0]["after"], "markerAfter": True}
    assert wrong == replace(live, evidence=wrong_evidence)
    assert generated.verdicts(wrong.evidence) == {**EXPECTED, "commitPoisoned": "violation"}
    try:
        generated.check(INITIAL, REQUESTS, FINISH, wrong)
    except generated.RuleViolation as error:
        assert error.rule == "commitPoisoned", error
    else:
        raise AssertionError("The stored wrong publication did not violate commitPoisoned")
    print("controls: save/load incomplete evidence, unknown schema, parented commit, mismatched recipe and "
          "stale pin rejected; stored wrong publication violated commitPoisoned")


def check_graph() -> None:
    live = generated.execute(INITIAL, REQUESTS, FINISH)
    verdicts = checked_verdicts(live)
    with TemporaryDirectory(prefix="quint-transaction-graph-") as tmp:
        path = Path(tmp) / "evidence"
        empty_bin = Path(tmp) / "empty-bin"
        empty_bin.mkdir()
        root = save_batch(path, live)
        reopened = load(path, root)
        assert reopened == live, reopened
        assert checked_verdicts(reopened) == verdicts
        fresh_process(path, root, live, empty_bin)
        print(f"round trip: native root {root}, reopened batch and all six verdicts agree, "
              f"including in a fresh Python process with no Quint/Node/npm on PATH: {verdicts}", flush=True)
        check_controls(path, root, live)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reopen", nargs=2, metavar=("REPO", "ROOT"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.reopen is None:
        check_graph()
        return
    if any(which(tool) is not None for tool in ("quint", "node", "npm")):
        raise RuntimeError("The graph reader requires a tool-free PATH")
    path, root = args.reopen
    batch = load(Path(path), dml.ObjectId.from_hex(root))
    print(json.dumps({"batch": asdict(batch), "verdicts": checked_verdicts(batch)}))


if __name__ == "__main__":
    main()
