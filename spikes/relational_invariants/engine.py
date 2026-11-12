"""Small stdlib bridge to the already-installed DuckDB CLI; no Python dependency."""

import json
import subprocess


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def execute(database, sql, *, rows=False):
    result = subprocess.run(["duckdb", "-batch", "-bail", "-json", str(database)],
                            input=sql, text=True, capture_output=True, check=True)
    return json.loads(result.stdout or "[]") if rows else None
