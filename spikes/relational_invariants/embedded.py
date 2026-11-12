"""One embedded DB owner: immutable batch publication and snapshot SQL checking.

Uses only collected facts, never DML repositories. This is spike tooling, not an
installed runtime or a full replacement for the existing validators.
"""

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import duckdb

from schema import CONTEXT_COLUMNS, KEYS, SCHEMA

TABLES = {**SCHEMA, "request_contexts": CONTEXT_COLUMNS,
          "object_signatures": {"kind": "VARCHAR", "oid": "VARCHAR", "fingerprint": "VARCHAR"}}
OWNERS = {"datums": ("datum", "oid"), "map_entries": ("datum", "oid"),
          "nodes": ("node", "oid"), "dags": ("dag", "oid"), "fields": ("dag", "dag"),
          "tree_entries": ("tree", "oid"), "commits": ("commit", "oid")}


@dataclass
class Batch:
    name: str
    rows: dict


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def signature(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def object_signatures(rows):
    descriptions = defaultdict(list)
    for table, entries in rows.items():
        if table in OWNERS:
            kind, column = OWNERS[table]
            for row in entries:
                descriptions[kind, row[column]].append([table, row])
        elif table == "edges":
            for row in entries:
                descriptions[row["src_kind"], row["src"]].append([table, row])
    identities = {(row["kind"], row["oid"]) for row in rows["objects"]}
    if set(descriptions) - identities:
        raise ValueError("decoded facts have no declared owning object")
    return [{"kind": kind, "oid": oid, "fingerprint": signature(sorted(descriptions[kind, oid], key=canonical))}
            for kind, oid in sorted(identities)]


def collected_batches(evidence):
    """Partition already-collected history into complete overlapping4/6 batches."""
    evidence = Path(evidence)
    facts = {table: [json.loads(line) for line in (evidence / "normalized" / f"{table}.jsonl").read_text().splitlines()]
             for table in SCHEMA}
    contexts = json.loads((evidence / "request-contexts.json").read_text())
    adjacency = defaultdict(list)
    for row in facts["edges"]:
        adjacency[row["src_kind"], row["src"]].append((row["dst_kind"], row["dst"]))
    batches = []
    for context in sorted(contexts, key=lambda row: row["number"]):
        roots = {context["commit"], context["satisfaction"]}
        pending, reached = [("commit", root) for root in roots], set()
        while pending:
            identity = pending.pop()
            if identity not in reached:
                reached.add(identity)
                pending.extend(adjacency[identity])
        rows = {}
        for table, entries in facts.items():
            if table == "objects":
                rows[table] = [row for row in entries if (row["kind"], row["oid"]) in reached]
            elif table == "roots":
                rows[table] = [row for row in entries if row["commit_id"] in roots]
            elif table == "edges":
                rows[table] = [row for row in entries if (row["src_kind"], row["src"]) in reached]
            else:
                kind, column = OWNERS[table]
                rows[table] = [row for row in entries if (kind, row[column]) in reached]
        rows["request_contexts"] = [{key: context[key] for key in CONTEXT_COLUMNS}]
        batches.append(Batch(f"request-{context['number']}", rows))
    return batches


def connect(database):
    # Separate connections per thread; all share the same database configuration.
    return duckdb.connect(str(database), config={"threads": 2})


def initialize(database):
    if Path(database).exists():
        raise FileExistsError("use a NEW spike database")
    with connect(database) as conn:
        for table, columns in TABLES.items():
            fields = ", ".join(f'"{name}" {kind}' for name, kind in columns.items())
            keys = ", ".join(f'"{name}"' for name in KEYS[table])
            conn.execute(f"CREATE TABLE {table} ({fields}, PRIMARY KEY ({keys}));")
        conn.execute("CREATE TABLE published_batches (name VARCHAR PRIMARY KEY, fingerprint VARCHAR NOT NULL);")
        conn.execute(Path(__file__).with_name("reuse_checks.sql").read_text())


def insert_immutable(conn, table, rows):
    columns = TABLES[table]
    if any(set(row) != set(columns) for row in rows):
        raise ValueError(f"unexpected fact columns for {table}")
    projections = ", ".join(f"CAST(json_extract_string(value, '$.{name}') AS {kind}) AS \"{name}\""
                            for name, kind in columns.items())
    stage = "stage_" + table
    conn.execute(f"CREATE OR REPLACE TEMP TABLE {stage} AS SELECT {projections} FROM json_each(?);",
                 [canonical(rows)])
    keys = ", ".join(f'"{key}"' for key in KEYS[table])
    if conn.execute(f"SELECT count(*) FROM (SELECT {keys} FROM {stage} GROUP BY {keys} HAVING count(*) > 1);").fetchone()[0]:
        raise ValueError(f"duplicate incoming fact keys in {table}")
    equality = " AND ".join(f's."{key}" IS NOT DISTINCT FROM t."{key}"' for key in KEYS[table])
    disagreement = " OR ".join(f's."{key}" IS DISTINCT FROM t."{key}"' for key in columns)
    if conn.execute(f"SELECT count(*) FROM {stage} s JOIN {table} t ON {equality} WHERE {disagreement};").fetchone()[0]:
        raise ValueError(f"conflicting immutable facts in {table}")
    conn.execute(f"INSERT INTO {table} SELECT * FROM {stage} ON CONFLICT DO NOTHING;")


def publish(conn, batch, hook=None):
    """Commit all supplied facts+contexts+marker atomically. ONE normalizer writer.

    Identical batch replay is inert; changed replay or immutable disagreement fails.
    No automatic retry. A marker means fully loaded, NOT semantically valid.
    """
    if set(batch.rows) != {*SCHEMA, "request_contexts"}:
        raise ValueError("batch table set differs from this spike profile")
    payload = {table: sorted(rows, key=canonical) for table, rows in batch.rows.items()}
    fingerprint = signature(payload)
    conn.execute("BEGIN;")
    try:
        old = conn.execute("SELECT fingerprint FROM published_batches WHERE name=?", [batch.name]).fetchone()
        if old is not None:
            if old[0] != fingerprint:
                raise ValueError("batch identity reused with different facts")
            conn.execute("COMMIT;")
            return False
        # Whole-object signatures also catch missing/additional relationships in a
        # duplicate object, not merely disagreements for present individual keys.
        insert_immutable(conn, "object_signatures", object_signatures(batch.rows))
        for table in (*SCHEMA, "request_contexts"):
            insert_immutable(conn, table, batch.rows[table])
            if hook is not None:
                hook(table, conn)
        missing = conn.execute("""
            SELECT count(*) FROM edges e LEFT JOIN objects o
              ON o.kind=e.dst_kind AND o.oid=e.dst WHERE o.oid IS NULL;
        """).fetchone()[0]
        if missing:
            raise ValueError("batch contains missing typed edge targets")
        conn.execute("INSERT INTO published_batches VALUES (?, ?)", [batch.name, fingerprint])
        if hook is not None:
            hook("marker", conn)
        conn.execute("COMMIT;")
        return True
    except BaseException:
        conn.execute("ROLLBACK;")
        raise


def snapshot(conn):
    """Caller owns a read transaction spanning ALL queries for a consistent verdict."""
    batches = [row[0] for row in conn.execute("SELECT name FROM published_batches ORDER BY name").fetchall()]
    counts = {"objects": conn.execute("SELECT count(*) FROM objects").fetchone()[0],
              "contexts": conn.execute("SELECT count(*) FROM request_contexts").fetchone()[0],
              "roots": conn.execute("SELECT count(*) FROM roots").fetchone()[0]}
    if batches:
        violations = conn.execute("SELECT * FROM reuse_violations ORDER BY invariant, subject, detail").fetchall()
    elif any(conn.execute(f"SELECT EXISTS(SELECT 1 FROM {table})").fetchone()[0] for table in TABLES):
        violations = [("unpublished_facts", "database", "committed facts without a publication marker")]
    else:
        violations = []  # Truly empty owner is idle, not a semantic validation pass.
    return {"batches": batches, **counts, "violations": [list(row) for row in violations]}


def check_snapshot(conn):
    conn.execute("BEGIN;")
    try:
        result = snapshot(conn)
        conn.execute("COMMIT;")
        return result
    except BaseException:
        conn.execute("ROLLBACK;")
        raise
