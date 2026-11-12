"""Retained-history oracle controls; no original repository reads or computation."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import ROOT, bootstrap
bootstrap()
import daggerml as dml
from daggerml import transfer
from engine import execute, quote
from normalizer import SCHEMA, normalize
from reuse_checker import check_reuse

EVIDENCE = ROOT / "build/relational-spike/retained-requests-v1"


@pytest.fixture
def history_database(tmp_path):
    database = tmp_path / "history.duckdb"
    sql = ["BEGIN;"]
    for table, columns in SCHEMA.items():
        spec = ", ".join(f"{quote(k)}: {quote(v)}" for k, v in columns.items())
        definition = ", ".join(f'"{k}" {v}' for k, v in columns.items())
        sql.append(f"CREATE TABLE {table} ({definition});")
        path = EVIDENCE / "normalized" / f"{table}.jsonl"
        if path.stat().st_size:
            sql.append(f"INSERT INTO {table} SELECT * FROM read_json({quote(path)}, "
                       f"format='newline_delimited', columns={{{spec}}});")
    sql.append("COMMIT;")
    execute(database, "\n".join(sql))
    result = check_reuse(database, EVIDENCE / "request-contexts.json")
    assert result["violations"] == []
    return database, result


def test_exact_same_473_objects_and_both_baseline_answers(history_database):
    database, result = history_database
    baseline = json.loads((EVIDENCE / "baseline.json").read_text())
    actual = execute(database, "SELECT kind, oid FROM objects", rows=True)
    assert {(r["kind"], r["oid"]) for r in actual} == {
        (r["kind"], r["oid"]) for r in baseline["record_counts"]}
    assert result["answers"] == baseline["answers"]
    assert len(actual) == 473
    assert baseline["record_reads"] == 54628
    assert result["inventory"]["distinct_request_dags"] == 6
    assert result["inventory"]["attempt_occurrences"] == 4
    assert result["inventory"]["reuse_contexts"] == 2
    assert result["inventory"]["retained_trace_positions"] == 7
    assert all(r["requested_upstream_value"] == r["producing_upstream_value"]
               and r["requested_upstream_result"] != r["producing_upstream_result"]
               for r in result["provenance"])
    assert len({r["requested_upstream_result"] for r in result["provenance"]}) == 2
    assert len({r["producing_upstream_result"] for r in result["provenance"]}) == 1


@pytest.mark.parametrize(("mutation", "invariant"), [
    ("UPDATE fields SET node = (SELECT oid FROM nodes WHERE kind='subdag' AND target="
     "(SELECT s.request FROM h_selections s JOIN h_contexts c ON c.selection=s.dag LIMIT 1) LIMIT 1) "
     "WHERE dag IN (SELECT satisfaction_dag FROM h_contexts) AND name='request'", "reuse_association"),
    ("UPDATE fields SET node = (SELECT n.oid FROM nodes n JOIN h_attempts a ON a.dag=n.target "
     "WHERE n.kind='subdag' AND a.status='done' AND a.dag NOT IN "
     "(SELECT satisfied_attempt FROM h_contexts) LIMIT 1) "
     "WHERE dag IN (SELECT satisfaction_dag FROM h_contexts) AND name='attempt'", "reuse_association"),
    ("UPDATE fields SET node = (SELECT oid FROM nodes WHERE kind='subdag' AND target="
     "(SELECT actual_inputs FROM h_contexts WHERE number=4) LIMIT 1) "
     "WHERE name='request' AND dag IN (SELECT dag FROM h_attempts WHERE status='done')", "successful_selection"),
    ("UPDATE fields SET node = (SELECT oid FROM nodes WHERE kind='subdag' AND target="
     "(SELECT request FROM h_contexts WHERE number=4) LIMIT 1) "
     "WHERE name='request' AND dag IN (SELECT dag FROM h_attempts WHERE status='done')", "reuse_new_attempt"),
    ("UPDATE datums SET scalar='ffffffffffffffffffffffffffffffff' WHERE oid IN "
     "(SELECT f.target FROM h_fields f JOIN h_contexts c ON c.selection=f.dag WHERE f.name='completion')",
     "completion_retention"),
    ("UPDATE fields SET node=(SELECT oid FROM nodes WHERE kind='subdag' AND target="
     "(SELECT a.source FROM h_arguments a JOIN h_selections s ON s.inputs=a.arguments "
     "JOIN h_contexts c ON c.selection=s.dag WHERE a.key_name='x' LIMIT 1) LIMIT 1) "
     "WHERE name='source' AND dag IN (SELECT a.entry FROM h_arguments a JOIN h_contexts c "
     "ON c.actual_inputs=a.arguments WHERE c.number=4 AND a.key_name='x')", "composition_provenance"),
    ("UPDATE fields SET node=(SELECT oid FROM nodes WHERE kind='literal' AND target="
     "(SELECT oid FROM datums WHERE kind='string' AND scalar='x') LIMIT 1) "
     "WHERE name='value' AND dag IN (SELECT dag FROM h_operations)", "map_get_value"),
    ("DELETE FROM fields WHERE name='call-01'", "trace_count"),
    ("INSERT INTO tree_entries SELECT c.tree_id, 'unexpected-addition', h.selection FROM h_contexts h "
     "JOIN commits c ON c.oid=h.satisfaction WHERE h.number=4", "satisfaction_tree_delta"),
    ("DELETE FROM fields WHERE name='validation' AND dag IN (SELECT dag FROM h_selections)", "profile_shape"),
    ("DELETE FROM roots WHERE commit_id IN (SELECT satisfaction FROM request_contexts WHERE number=6)",
     "context_available"),
    ("DELETE FROM request_contexts", "empty_contexts"),
])
def test_independent_reuse_oracle_faults(history_database, mutation, invariant):
    database, _ = history_database
    execute(database, mutation)
    result = check_reuse(database)
    assert invariant in {row["invariant"] for row in result["violations"]}


def test_checker_has_no_repository_dependency_and_failure_exit(history_database):
    database, _ = history_database
    script = Path(__file__).with_name("reuse_checker.py")
    positive = subprocess.run([sys.executable, str(script), str(database)],
                              capture_output=True, text=True, check=True)
    assert json.loads(positive.stdout)["violations"] == []
    execute(database, "DELETE FROM request_contexts;")
    negative = subprocess.run([sys.executable, str(script), str(database)], capture_output=True, text=True)
    assert negative.returncode == 1
    assert json.loads(negative.stdout)["violations"][0]["invariant"] == "empty_contexts"


def test_equal_value_wrong_actual_producer_rejected_by_both_systems(tmp_path, monkeypatch):
    # Only public import into an OWN new case store. No LMDB/lockfile copying.
    repository = tmp_path / "case.dml"
    with dml.Repository(repository, create=True):
        pass
    bundle = (EVIDENCE / "test-fixture.bundle").read_bytes()
    imported = transfer.import_commit(repository, bundle, ref="retained")
    assert imported.object_count == 473
    manifest = json.loads((EVIDENCE / "manifest.json").read_text())
    contexts = json.loads((EVIDENCE / "request-contexts.json").read_text())
    fourth = next(row for row in contexts if row["number"] == 4)
    sys.path.insert(0, str(ROOT / "examples"))
    import composed_node_calls as calls
    with dml.Repository(repository) as repo, repo.write() as tx:
        # Existing composition4 chooses successful producer3. Change only its input
        # source to OLD producer1, which also returned42: MAP VALUE stays identical.
        base = dml.ObjectId.from_hex(fourth["basis"])
        entries = dict(tx.get_tree(tx.get_commit(base).tree))
        original_composition = tx.get_dag(dml.ObjectId.from_hex(fourth["composition"]))
        original_inputs = tx.get_dag(dml.ObjectId.from_hex(fourth["inputs"]))
        ledger = tx.get_dag(tx.get_node(original_inputs.bindings["entries"]).dag)
        row = tx.get_dag(tx.get_node(ledger.bindings["arg-00"]).dag)
        old_selection = tx.get_dag(entries["producer-add-1"])
        old_result = tx.get_node(old_selection.bindings["result"]).dag
        expected_result = tx.get_node(original_composition.bindings["result"]).dag
        assert old_result != expected_result
        old_value = tx.get_node(tx.get_dag(old_result).bindings["value"]).datum
        expected_value = tx.get_node(tx.get_dag(expected_result).bindings["value"]).datum
        assert old_value == expected_value
        new_row = tx.put_dag(root=row.root, bindings={**row.bindings, "source": tx.put_subdag(old_result)})
        new_ledger = tx.put_dag(root=ledger.root, bindings={**ledger.bindings, "arg-00": tx.put_subdag(new_row)})
        new_inputs = tx.put_dag(root=original_inputs.root,
                               bindings={**original_inputs.bindings, "entries": tx.put_subdag(new_ledger)})
        new_composition = tx.put_dag(root=original_composition.root,
            bindings={**original_composition.bindings, "arguments": tx.put_subdag(new_inputs)})
        # Correct two-entry parent/tree framing, but wrong exact source relationship.
        parent = tx.get_commit(base).parents[0]
        parent_entries = dict(tx.get_tree(tx.get_commit(parent).tree))
        bad = tx.put_commit(tx.put_tree({**parent_entries, "bad-inputs": new_inputs,
                                        "bad-composition": new_composition}), parents=(parent,))
        tx.create_ref("bad", bad)
    def no_launch(*args, **kwargs):
        raise AssertionError("native metadata control must not launch")
    with monkeypatch.context() as blocked:
        blocked.setattr(subprocess, "Popen", no_launch)
        with pytest.raises(ValueError, match="exact OUTER selected R source"):
            calls.inspect_composition(repository, commit=bad,
                                      inputs_name="bad-inputs", composition_name="bad-composition")
    manifest["repository"] = str(repository)
    manifest["roots"].append(str(bad))
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    database, _ = normalize(manifest_path, tmp_path / "normalized")
    result = check_reuse(database, EVIDENCE / "request-contexts.json")
    assert {r["subject"] for r in result["violations"]
            if r["invariant"] == "composition_provenance"} == {str(new_composition)}
    # Equal computational argument VALUE survives; exact source provenance does not.
    assert not any(r["subject"] == str(new_inputs) and r["invariant"] == 'argument_sources'
                   for r in result["violations"])
