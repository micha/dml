"""Check real Python export rows against fixture expectations and the Quint rules."""

import argparse
import base64
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from shutil import copyfile
import subprocess
from unittest.mock import patch

import daggerml as dml
from daggerml import transfer


RULES = Path(__file__).with_name("export_walk_rules.qnt")
RULE_NAMES = ("orderedSubset", "completeAndUnique", "exactOrder")
Key = tuple[str, str]
Rows = tuple[Key, ...]
Verdicts = tuple[bool, bool, bool]


@dataclass(frozen=True)
class Fixture:
    keys: dict[str, Key]
    edges: dict[Key, Rows]
    records: dict[Key, bytes]
    orders: dict[str, Rows]


@dataclass(frozen=True)
class Observation:
    root: Key
    expected: Rows
    rows: Rows
    verdicts: Verdicts


def build_fixture(path: Path) -> Fixture:
    keys = {}
    records = {}
    with dml.Repository(path, create=True) as repo, repo.write() as tx:
        def save(label, kind, object_id):
            key = (kind, str(object_id))
            assert label not in keys and key not in records
            keys[label] = key
            records[key] = tx.get_record(kind, object_id)
            return object_id

        def datum(label, value):
            return save(label, "datum", tx.put_datum(value))

        def literal(label, value):
            return save(label, "node", tx.put_literal(value))

        shared = datum("shared", 42)
        list_only = datum("list-only", "list payload")
        sequence = datum("list", dml.Datum.list([list_only, shared, list_only]))
        main_node = literal("main-node", sequence)
        other_node = literal("other-node", shared)
        other_dag = save("other-dag", "dag", tx.put_dag(root=other_node))
        backlink = save("subdag", "node", tx.put_subdag(other_dag))
        main_dag = save("main-dag", "dag", tx.put_dag(root=main_node, bindings={"nested": backlink}))
        # Supply non-canonical tree entry order; export visits 'a' before 'z'.
        top_tree = save("top-tree", "tree", tx.put_tree([("z", other_dag), ("a", main_dag)]))
        base_tree = save("base-tree", "tree", tx.put_tree({}))
        base = save("base", "commit", tx.put_commit(base_tree))
        left = save("left", "commit", tx.put_commit(base_tree, parents=[base]))

        set_ids = sorted((shared, datum("set-a", 71), datum("set-b", 83)), key=str)
        collection = datum("set", dml.Datum.set(reversed(set_ids)))
        map_key = datum("map-key", "key payload")
        mapping = datum("map", dml.Datum.map([(map_key, collection)]))
        right_node = literal("right-node", mapping)
        right_dag = save("right-dag", "dag", tx.put_dag(root=right_node))
        right_tree = save("right-tree", "tree", tx.put_tree({"right": right_dag}))
        right = save("right", "commit", tx.put_commit(right_tree, parents=[base]))
        root_lr = save("left-first", "commit", tx.put_commit(top_tree, parents=[left, right]))
        root_rl = save("right-first", "commit", tx.put_commit(top_tree, parents=[right, left]))
        datum("unrelated", "not in either pinned closure")
        tx.create_ref("main", root_lr)
        tx.create_ref("other", root_rl)

    set_labels = tuple(sorted(("shared", "set-a", "set-b"), key=lambda label: keys[label][1]))
    # Designed adjacency, not traversal output or a readback of transfer._edges.
    links = {
        "left-first": ("top-tree", "left", "right"), "right-first": ("top-tree", "right", "left"),
        "top-tree": ("main-dag", "other-dag"), "main-dag": ("main-node", "subdag"),
        "main-node": ("list",), "list": ("list-only", "shared", "list-only"),
        "subdag": ("other-dag",), "other-dag": ("other-node",), "other-node": ("shared",),
        "left": ("base-tree", "base"), "base": ("base-tree",),
        "right": ("right-tree", "base"), "right-tree": ("right-dag",), "right-dag": ("right-node",),
        "right-node": ("map",), "map": ("map-key", "set"), "set": set_labels,
    }
    edges = {key: tuple(keys[child] for child in links.get(label, ())) for label, key in keys.items()}
    # Hand-listed output sections. Do not walk `links` to derive these expectations.
    top = ("list-only", "shared", "list", "main-node", "other-node", "other-dag", "subdag", "main-dag", "top-tree")
    right_rows = ("map-key", *sorted(("set-a", "set-b"), key=lambda label: keys[label][1]),
                  "set", "map", "right-node", "right-dag", "right-tree")
    orders = {
        "left-first": top + ("base-tree", "base", "left") + right_rows + ("right", "left-first"),
        "right-first": top + right_rows + ("base-tree", "base", "right", "left", "right-first"),
    }
    expected = {name: tuple(keys[label] for label in order) for name, order in orders.items()}
    return Fixture(keys, edges, records, expected)


def expected_bundle(root: Key, rows: Rows, records: dict[Key, bytes]) -> bytes:
    objects = [{"kind": kind, "id": oid, "record": base64.b64encode(records[kind, oid]).decode("ascii")}
               for kind, oid in rows]
    return json.dumps({"format": "daggerml-commit-bundle-v1", "root": root[1], "objects": objects},
                      separators=(",", ":")).encode("utf-8")


def faulted_export(repo: Path, commit: dml.ObjectId, *, first_parent_only: bool) -> bytes:
    unmodified_edges = transfer._edges
    altered = False

    def altered_edges(tx, kind, object_id):
        nonlocal altered
        edges = unmodified_edges(tx, kind, object_id)
        if (kind, object_id) != ("commit", commit):
            return edges
        assert not altered and tuple(kind for kind, _ in edges) == ("tree", "commit", "commit")
        altered = True
        return edges[:2] if first_parent_only else (edges[0], edges[2], edges[1])

    with patch.object(transfer, "_edges", altered_edges):
        bundle = transfer.export_commit(repo, commit=commit)
    assert altered, "Negative control did not reach the merge root"
    return bundle


def observations(fixture: Fixture, repo: Path, out: Path) -> tuple[list[Observation], dict]:
    cases, summary = [], {}
    for label, expected in fixture.orders.items():
        root = fixture.keys[label]
        commit = dml.ObjectId(bytes.fromhex(root[1]))
        for mode, verdicts in (("baseline", (True, True, True)), ("first-parent", (True, False, False)),
                               ("swapped-parents", (True, True, False))):
            if mode == "baseline":
                bundle = transfer.export_commit(repo, commit=commit)
            else:
                bundle = faulted_export(repo, commit, first_parent_only=mode == "first-parent")
            document = json.loads(bundle)
            assert document["root"] == root[1]
            rows = tuple((obj["kind"], obj["id"]) for obj in document["objects"])
            if mode == "baseline":
                assert bundle == expected_bundle(root, expected, fixture.records), label
            assert all(base64.b64decode(obj["record"], validate=True) == fixture.records[key]
                       for obj, key in zip(document["objects"], rows, strict=True))
            case = f"{label}-{mode}"
            (out / f"{case}.json").write_bytes(bundle)
            cases.append(Observation(root, expected, rows, verdicts))
            summary[case] = {"rows": len(rows), "sha256": sha256(bundle).hexdigest(),
                             "missing": sorted(set(expected) - set(rows))}
    return cases, summary


def quint_key(key: Key) -> str:
    kind, oid = key
    return f"({json.dumps(kind)}, {json.dumps(oid)})"


def quint_rows(rows: Rows) -> str:
    return "List(" + ", ".join(map(quint_key, rows)) + ")"


def check_quint(quint: Path, out: Path, graph: dict[Key, Rows], cases: list[Observation]) -> list[Verdicts]:
    copyfile(RULES, out / RULES.name)
    edges = ",\n    ".join(f"{quint_key(key)} -> {quint_rows(children)}" for key, children in graph.items())
    conditions = []
    for case in cases:
        root_expr = quint_key(case.root)
        expected_expr, actual_expr = quint_rows(case.expected), quint_rows(case.rows)
        conditions.append(f"(orderedSubset(graph, {root_expr}, {actual_expr}),\n"
                          f"     completeAndUnique(graph, {root_expr}, {actual_expr}),\n"
                          f"     exactOrder({expected_expr}, {actual_expr}))")
    verdicts = ",\n    ".join(conditions)
    model = out / "export_baseline_observations.qnt"
    model.write_text(f'''module export_baseline_observations {{
  import export_walk_rules.* from "./export_walk_rules"
  pure val graph: Graph = Map(
    {edges}
  )
  var verdicts: List[(bool, bool, bool)]
  action init = verdicts' = List(
    {verdicts}
  )
  action step = verdicts' = verdicts
}}
''', encoding="utf-8")
    report = out / "verdicts.itf.json"
    subprocess.run([quint, "run", model, "--backend=typescript", "--seed=1", "--max-samples=1",
                    "--max-steps=0", "--verbosity=0", f"--out-itf={report}"], check=True, timeout=30)
    trace = json.loads(report.read_text(encoding="utf-8"))
    assert trace["#meta"]["status"] == "ok" and trace["vars"] == ["verdicts"], trace["#meta"]
    state, = trace["states"]
    actual = [tuple(item["#tup"]) for item in state["verdicts"]]
    assert len(actual) == len(cases), "Wrong number of Quint verdict tuples"
    for index, (verdicts, case) in enumerate(zip(actual, cases, strict=True)):
        assert all(type(verdict) is bool for verdict in verdicts), f"Case {index}: non-boolean verdicts {verdicts}"
        assert verdicts == case.verdicts, f"Case {index} ({case.root}): got {verdicts}, expected {case.verdicts}"
    return actual


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="New working directory with existing parent")
    args = parser.parse_args()
    if not __debug__:
        parser.error("Run without optimizations to keep the checks enabled")
    out, quint = args.out.resolve(), args.quint.absolute()
    version = subprocess.run([quint, "--version"], capture_output=True, text=True, check=True, timeout=10)
    if version.stdout.strip() != "0.33.1":
        parser.error(f"Expected Quint 0.33.1, got {version.stdout.strip()!r}")
    out.mkdir(mode=0o700)
    repo = out / "source.dml"
    fixture = build_fixture(repo)
    cases, summary = observations(fixture, repo, out)
    for case, verdict in zip(summary, check_quint(quint, out, fixture.edges, cases), strict=True):
        summary[case]["verdicts"] = dict(zip(RULE_NAMES, verdict, strict=True))
    result = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    (out / "summary.json").write_text(result, encoding="utf-8")
    print(result, end="")


if __name__ == "__main__":
    main()
