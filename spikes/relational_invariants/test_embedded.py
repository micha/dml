"""Embedded transaction/concurrency controls using collected facts only."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from embedded import check_snapshot, collected_batches, connect, initialize, publish

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "build/relational-spike/retained-requests-v1"


@pytest.fixture
def state(tmp_path):
    database = tmp_path / "facts.duckdb"
    first, second = collected_batches(EVIDENCE)
    initialize(database)
    with connect(database) as conn:
        assert publish(conn, first)
        before = check_snapshot(conn)
    return database, first, second, before


def test_actual_thread_overlap_atomic_marker_and_stable_read_snapshot(tmp_path):
    result = subprocess.run([sys.executable, str(Path(__file__).with_name("concurrency_probe.py")),
                             str(EVIDENCE), str(tmp_path / "overlap")],
                            capture_output=True, text=True, timeout=60, check=True)
    observations = json.loads(result.stdout)
    assert observations["duckdb_version"] == "1.5.2"
    assert observations["writer_joined"] and not observations["dml_imported"]
    old = observations["observations"]["initial"]
    assert old["objects"] == 368
    for stage in ("partial_facts_uncommitted", "complete_batch_and_marker_uncommitted",
                  "reader_snapshot_after_writer_commit"):
        assert observations["observations"][stage] == old
    fresh = observations["observations"]["fresh_reader_after_commit"]
    assert fresh == observations["observations"]["reopened_after_clean_close"]
    assert fresh["objects"] == 473 and fresh["contexts"] == 2 and not fresh["violations"]


def test_writer_failure_before_barrier_surfaces_root_error_and_joins(tmp_path, monkeypatch):
    import concurrency_probe
    first, second = collected_batches(EVIDENCE)
    second = deepcopy(second)
    second.rows["objects"].append(deepcopy(second.rows["objects"][0]))
    monkeypatch.setattr(concurrency_probe, 'collected_batches', lambda _: (first, second))
    output = tmp_path / "failed-probe"
    with pytest.raises(ValueError, match="duplicate incoming fact keys"):
        concurrency_probe.probe(EVIDENCE, output)
    assert "duplicate incoming fact keys" in (output / "failure.txt").read_text()
    with connect(output / "facts.duckdb") as conn:
        assert check_snapshot(conn)["batches"] == ["request-4"]
        assert check_snapshot(conn)["objects"] == 368


@pytest.mark.parametrize("failure_stage", ["objects", "request_contexts", "marker"])
def test_partial_batch_or_marker_failure_rolls_back_every_fact(state, failure_stage):
    database, _, second, before = state
    with connect(database) as writer, connect(database) as reader:
        def fail(table, conn):
            if table == failure_stage:
                # Independent connection cannot see any staged partial publication.
                assert check_snapshot(reader) == before
                raise RuntimeError("deliberate publication failure")
        with pytest.raises(RuntimeError, match="deliberate publication failure"):
            publish(writer, second, fail)
        assert check_snapshot(reader) == before
        assert writer.execute("SELECT count(*) FROM object_signatures").fetchone()[0] == 368


def test_identical_replay_is_inert_and_overlap_deduplicates(state):
    database, first, second, before = state
    with connect(database) as conn:
        assert not publish(conn, first)
        assert check_snapshot(conn) == before
        assert publish(conn, second)
        after = check_snapshot(conn)
        assert after["objects"] == 473 and after["roots"] == 4 and after["contexts"] == 2
        assert not publish(conn, second)
        assert check_snapshot(conn) == after
        assert conn.execute("SELECT count(*) FROM object_signatures").fetchone()[0] == 473


def test_changed_batch_identity_rejected(state):
    database, first, _, before = state
    bad = deepcopy(first)
    bad.rows["datums"][0]["scalar"] = "changed"
    with connect(database) as conn:
        with pytest.raises(ValueError, match="batch identity reused"):
            publish(conn, bad)
        assert check_snapshot(conn) == before


@pytest.mark.parametrize("fault", ["changed-scalar", "missing-relationship", "duplicate-key", "root-disagreement", "missing-target"])
def test_inconsistent_immutable_facts_are_not_silently_ignored(state, fault):
    database, first, second, before = state
    bad = deepcopy(second)
    bad.name = "fault-" + fault
    if fault == "changed-scalar":
        shared = next(row for row in bad.rows["datums"] if row["kind"] == 'i64' and row["scalar"] == '42')
        shared["scalar"] = "43"
        message = "conflicting immutable facts in object_signatures"
    elif fault == "missing-relationship":
        shared_dag = first.rows["fields"][0]["dag"]
        bad.rows["fields"] = [row for row in bad.rows["fields"]
                              if not (row["dag"] == shared_dag and row["name"] == first.rows["fields"][0]["name"])]
        message = "conflicting immutable facts in object_signatures"
    elif fault == "duplicate-key":
        bad.rows["objects"].append(deepcopy(bad.rows["objects"][0]))
        message = "duplicate incoming fact keys in objects"
    elif fault == "root-disagreement":
        bad.rows["roots"].append({**first.rows["roots"][0], "commit_id": "f" * 32})
        message = "conflicting immutable facts in roots"
    else:
        previous = {(row["kind"], row["oid"]) for row in first.rows["objects"]}
        owner = next(row for row in second.rows["objects"] if (row["kind"], row["oid"]) not in previous)
        bad.rows["edges"].append({"src_kind": owner["kind"], "src": owner["oid"],
                                  "label": "deliberate-missing", "dst_kind": "datum", "dst": "f" * 32})
        message = "missing typed edge targets"
    with connect(database) as conn:
        with pytest.raises(ValueError, match=message):
            publish(conn, bad)
        assert check_snapshot(conn) == before


def test_marker_means_loaded_not_semantically_valid(state):
    database, _, _, _ = state
    with connect(database) as conn:
        # A checker still evaluates rules after publication; marker is not a proof.
        conn.execute("DELETE FROM fields WHERE name='validation' AND dag IN "
                     "(SELECT dag FROM h_selections)")
        result = check_snapshot(conn)
        assert result["batches"] == ["request-4"]
        assert 'profile_shape' in {row[0] for row in result["violations"]}


def test_unpublished_database_is_idle_not_validated(tmp_path):
    database = tmp_path / "idle.duckdb"
    initialize(database)
    with connect(database) as conn:
        assert check_snapshot(conn) == {"batches": [], "objects": 0, "contexts": 0, "roots": 0, "violations": []}


def test_unknown_batch_tables_rejected_instead_of_dropped(state):
    database, _, second, before = state
    bad = deepcopy(second)
    bad.rows["unexpected"] = []
    with connect(database) as conn:
        with pytest.raises(ValueError, match="batch table set differs"):
            publish(conn, bad)
        assert check_snapshot(conn) == before


def test_unknown_fact_columns_rejected_instead_of_dropped(state):
    database, _, second, before = state
    bad = deepcopy(second)
    bad.rows["request_contexts"][0]["unexpected"] = "must not disappear"
    with connect(database) as conn:
        with pytest.raises(ValueError, match="unexpected fact columns"):
            publish(conn, bad)
        assert check_snapshot(conn) == before


def test_committed_facts_without_marker_are_not_silent_idle(tmp_path):
    database = tmp_path / "orphan.duckdb"
    initialize(database)
    with connect(database) as conn:
        conn.execute("INSERT INTO objects VALUES ('datum', 'deliberate-orphan')")
        result = check_snapshot(conn)
        assert result["batches"] == []
        assert result["violations"][0][0] == 'unpublished_facts'


def test_separate_writer_connections_can_commit_disjoint_appends(tmp_path):
    database = tmp_path / "appends.duckdb"
    with connect(database) as first, connect(database) as second:
        first.execute("CREATE TABLE items(id INTEGER PRIMARY KEY)")
        first.execute("BEGIN;")
        second.execute("BEGIN;")
        first.execute("INSERT INTO items VALUES (1)")
        second.execute("INSERT INTO items VALUES (2)")
        second.execute("COMMIT;")
        first.execute("COMMIT;")
        assert first.execute("SELECT id FROM items ORDER BY id").fetchall() == [(1,), (2,)]


def test_same_row_conflict_aborts_losing_transaction_without_retry(tmp_path):
    database = tmp_path / "conflict.duckdb"
    with connect(database) as first, connect(database) as second:
        first.execute("CREATE TABLE counters(id INTEGER PRIMARY KEY, value INTEGER)")
        first.execute("INSERT INTO counters VALUES (1,0)")
        first.execute("BEGIN;")
        second.execute("BEGIN;")
        assert second.execute("SELECT value FROM counters").fetchone() == (0,)
        first.execute("UPDATE counters SET value=1 WHERE id=1")
        with pytest.raises(duckdb.TransactionException, match="Conflict"):
            second.execute("UPDATE counters SET value=2 WHERE id=1")
        second.execute("ROLLBACK;")
        first.execute("COMMIT;")
        assert second.execute("SELECT value FROM counters").fetchone() == (1,)


def test_snapshot_isolation_does_not_enforce_cross_row_invariant(tmp_path):
    database = tmp_path / "write-skew.duckdb"
    with connect(database) as first, connect(database) as second:
        first.execute("CREATE TABLE available(id INTEGER PRIMARY KEY, enabled INTEGER)")
        first.execute("INSERT INTO available VALUES (1,1), (2,1)")
        first.execute("BEGIN;")
        second.execute("BEGIN;")
        assert first.execute("SELECT sum(enabled) FROM available").fetchone() == (2,)
        assert second.execute("SELECT sum(enabled) FROM available").fetchone() == (2,)
        first.execute("UPDATE available SET enabled=0 WHERE id=1")
        second.execute("UPDATE available SET enabled=0 WHERE id=2")
        first.execute("COMMIT;")
        second.execute("COMMIT;")
        # Both transactions commit: 'at least one enabled' requires extra coordination.
        assert first.execute("SELECT sum(enabled) FROM available").fetchone() == (0,)
