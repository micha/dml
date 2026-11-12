"""SQL-only checks over a materialized dataset; imports no DML code."""

from pathlib import Path
import time

from engine import execute

CHECKS = Path(__file__).with_name("checks.sql")


def check(database):
    started = time.perf_counter()
    execute(database, CHECKS.read_text())
    violations = execute(database, "SELECT * FROM violations ORDER BY invariant, subject, detail;", rows=True)
    inventory = execute(database, """
        WITH RECURSIVE reached(checkpoint, kind, oid) AS (
            SELECT checkpoint, 'commit', commit_id FROM roots
            UNION
            SELECT r.checkpoint, e.dst_kind, e.dst FROM reached r
            JOIN edges e ON e.src_kind = r.kind AND e.src = r.oid
        )
        SELECT (SELECT count(*) FROM objects) AS unique_objects,
               count(*) AS summed_per_checkpoint_objects,
               (SELECT count(*) FROM operations) AS unique_operation_obligations,
               (SELECT count(*) FROM trace_positions) AS distinct_ledger_positions,
               (SELECT count(*) FROM reached r JOIN trace_positions t ON t.trace = r.oid
                 WHERE r.kind = 'dag') AS checkpoint_trace_position_memberships
        FROM reached;
    """, rows=True)[0]
    return {"violations": violations, "inventory": inventory,
            "checker_seconds": time.perf_counter() - started}
