"""Fact schemas shared by collection and independent checkers; no DML imports."""

SCHEMA = {
    "objects": {"kind": "VARCHAR", "oid": "VARCHAR"},
    "roots": {"checkpoint": "INTEGER", "commit_id": "VARCHAR", "expected_positions": "INTEGER"},
    "edges": {"src_kind": "VARCHAR", "src": "VARCHAR", "label": "VARCHAR",
              "dst_kind": "VARCHAR", "dst": "VARCHAR"},
    "datums": {"oid": "VARCHAR", "kind": "VARCHAR", "scalar": "VARCHAR"},
    "map_entries": {"oid": "VARCHAR", "position": "INTEGER", "key_id": "VARCHAR", "value_id": "VARCHAR"},
    "nodes": {"oid": "VARCHAR", "kind": "VARCHAR", "target": "VARCHAR"},
    "dags": {"oid": "VARCHAR", "root": "VARCHAR"},
    "fields": {"dag": "VARCHAR", "name": "VARCHAR", "node": "VARCHAR"},
    "tree_entries": {"oid": "VARCHAR", "name": "VARCHAR", "dag": "VARCHAR"},
    "commits": {"oid": "VARCHAR", "tree_id": "VARCHAR"},
}
CONTEXT_COLUMNS = {"number": "INTEGER", "commit": "VARCHAR", "request": "VARCHAR",
                   "request_id": "VARCHAR", "decision": "VARCHAR", "satisfaction": "VARCHAR",
                   "inputs": "VARCHAR"}

KEYS = {
    "objects": ("kind", "oid"), "roots": ("checkpoint",),
    "edges": ("src_kind", "src", "label", "dst_kind", "dst"),
    "datums": ("oid",), "map_entries": ("oid", "position"), "nodes": ("oid",),
    "dags": ("oid",), "fields": ("dag", "name"), "tree_entries": ("oid", "name"),
    "commits": ("oid",), "request_contexts": ("number",),
    "object_signatures": ("kind", "oid"),
}
