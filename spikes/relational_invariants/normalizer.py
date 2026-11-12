"""Decode unique typed native objects; leave builtin semantic rules to SQL."""

from collections import defaultdict
import json
from pathlib import Path
import time

import daggerml as dml

from engine import execute, quote
from schema import SCHEMA


def extract(manifest):
    started = time.perf_counter()
    rows = defaultdict(list)
    roots = [dml.ObjectId.from_hex(value) for value in manifest["roots"]]
    rows["roots"] = [{"checkpoint": i, "commit_id": str(root),
                      "expected_positions": None if i == 0 else manifest.get("expected_trace_positions")}
                     for i, root in enumerate(roots)]
    pending = [("commit", root) for root in roots]
    seen = set()
    references = 0
    with dml.Repository(manifest["repository"]) as repo, repo.read() as tx:
        while pending:
            kind, oid = pending.pop()
            if (kind, oid) in seen:
                continue
            if len(seen) >= 10000:
                raise ValueError("spike extraction bound exceeded")
            seen.add((kind, oid))
            identity = str(oid)
            # Each public getter performs one native record read + decode.
            got = getattr(tx, "get_" + kind)(oid)
            rows["objects"].append({"kind": kind, "oid": identity})

            def edge(label, target_kind, target):
                nonlocal references
                references += 1
                rows["edges"].append({"src_kind": kind, "src": identity, "label": label,
                                      "dst_kind": target_kind, "dst": str(target)})
                pending.append((target_kind, target))

            if kind == "commit":
                rows["commits"].append({"oid": identity, "tree_id": str(got.tree)})
                edge("tree", "tree", got.tree)
                for i, parent in enumerate(got.parents):
                    edge(f"parent-{i}", "commit", parent)
            elif kind == "tree":
                for name, dag in got.entries:
                    rows["tree_entries"].append({"oid": identity, "name": name, "dag": str(dag)})
                    edge(name, "dag", dag)
            elif kind == "dag":
                rows["dags"].append({"oid": identity, "root": str(got.root)})
                edge("root", "node", got.root)
                for name, node in got.bindings.items():
                    rows["fields"].append({"dag": identity, "name": name, "node": str(node)})
                    edge("field:" + name, "node", node)
            elif kind == "node":
                literal = isinstance(got, dml.LiteralNode)
                target = got.datum if literal else got.dag
                rows["nodes"].append({"oid": identity, "kind": "literal" if literal else "subdag",
                                      "target": str(target)})
                edge("target", "datum" if literal else "dag", target)
            else:
                scalar = None
                if got.kind not in ("list", "set", "map", "null"):
                    scalar = got.value.hex() if got.kind == "bytes" else str(got.value)
                rows["datums"].append({"oid": identity, "kind": got.kind, "scalar": scalar})
                if got.kind == "map":
                    for i, (key, value) in enumerate(got.value):
                        rows["map_entries"].append({"oid": identity, "position": i,
                                                    "key_id": str(key), "value_id": str(value)})
                        edge(f"key-{i}", "datum", key)
                        edge(f"value-{i}", "datum", value)
                elif got.kind in ("list", "set"):
                    for i, child in enumerate(got.value):
                        edge(f"item-{i}", "datum", child)
    stats = {"unique_record_reads": len(seen), "reference_edges": references,
             "roots": len(roots), "extraction_seconds": time.perf_counter() - started}
    return rows, stats


def normalize(manifest_path, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    try:
        rows, stats = extract(json.loads(Path(manifest_path).read_text()))
    except Exception as error:
        (directory / "extraction-error.txt").write_text(repr(error) + "\n")
        raise
    sql = ["BEGIN TRANSACTION;"]
    for table, columns in SCHEMA.items():
        definition = ", ".join(f'"{key}" {value}' for key, value in columns.items())
        sql.append(f"CREATE TABLE {table} ({definition});")
        path = directory / f"{table}.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows[table]))
        if rows[table]:
            column_spec = ", ".join(f"{quote(key)}: {quote(value)}" for key, value in columns.items())
            sql.append(f"INSERT INTO {table} SELECT * FROM read_json({quote(path.resolve())}, "
                       f"format='newline_delimited', columns={{{column_spec}}});")
    sql.extend(["CREATE UNIQUE INDEX object_identity ON objects(kind, oid);",
                "CREATE UNIQUE INDEX field_identity ON fields(dag, name);", "COMMIT;"])
    load = "\n".join(sql)
    (directory / "load.sql").write_text(load + "\n")
    database = directory / "facts.duckdb"
    execute(database, load)
    stats["normalize_seconds"] = time.perf_counter() - started
    stats["table_rows"] = {table: len(rows[table]) for table in SCHEMA}
    (directory / "stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    return database, stats
