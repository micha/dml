"""SQL-only retained-history checker; no DML imports or repository access."""

import json
from pathlib import Path
import sys
import time

from engine import execute, quote
from schema import CONTEXT_COLUMNS


def check_reuse(database, contexts=None):
    started = time.perf_counter()
    if contexts is not None:
        spec = ", ".join(f"{quote(key)}: {quote(kind)}" for key, kind in CONTEXT_COLUMNS.items())
        execute(database, "CREATE TABLE request_contexts AS SELECT * FROM "
                f"read_json({quote(Path(contexts).resolve())}, format='array', columns={{{spec}}}); "
                "CREATE UNIQUE INDEX context_number ON request_contexts(number);")
    execute(database, Path(__file__).with_name("reuse_checks.sql").read_text())
    violations = execute(database, "SELECT * FROM reuse_violations ORDER BY invariant, subject, detail;", rows=True)
    answers = execute(database, """
        SELECT c.number, c.action, c.actual_inputs AS requested_inputs, v.value_id AS requested_value,
               s.request AS selected_request, s.attempt AS selected_attempt,
               s.result AS selected_result, s.inputs AS selected_inputs
        FROM h_contexts c LEFT JOIN h_values v ON v.dag = c.actual_inputs
        LEFT JOIN h_selections s ON s.dag = c.selection ORDER BY c.number;
    """, rows=True)
    provenance = execute(database, """
        SELECT c.number, requested.source AS requested_upstream_result,
               producing.source AS producing_upstream_result,
               requested.value_id AS requested_upstream_value,
               producing.value_id AS producing_upstream_value
        FROM h_contexts c JOIN h_selections s ON s.dag = c.selection
        JOIN h_arguments requested ON requested.arguments = c.actual_inputs AND requested.key_name = 'x'
        JOIN h_arguments producing ON producing.arguments = s.inputs AND producing.key_name = 'x'
        ORDER BY c.number;
    """, rows=True)
    inventory = execute(database, """
        SELECT (SELECT count(*) FROM objects) AS unique_objects,
               (SELECT count(*) FROM h_reached) AS summed_per_root_objects,
               (SELECT count(*) FROM h_contexts) AS reuse_contexts,
               (SELECT count(*) FROM h_selections) AS selection_obligations,
               (SELECT count(*) FROM h_requests) AS distinct_request_dags,
               (SELECT count(DISTINCT occurrence) FROM h_attempts) AS attempt_occurrences,
               (SELECT count(*) FROM h_roles WHERE role = 'builtin-operation-v1') AS unique_builtin_operations,
               (SELECT count(*) FROM h_roles WHERE role = 'example-node-composition-v1') AS composition_obligations,
               (SELECT count(*) FROM h_trace_positions) AS retained_trace_positions;
    """, rows=True)[0]
    return {"violations": violations, "answers": answers, "provenance": provenance, "inventory": inventory,
            "checker_seconds": time.perf_counter() - started}


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit("usage: reuse_checker.py DATABASE [INITIAL_CONTEXTS_JSON]")
    result = check_reuse(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["violations"]))
