"""Small real-repository tests and deliberate relational-oracle counterexamples."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import bootstrap

bootstrap()
import daggerml as dml
from checker import check
from engine import execute
from exerciser import exercise
from normalizer import extract, normalize


@pytest.fixture
def dataset(tmp_path):
    scenario = tmp_path / "scenario"
    manifest = exercise(scenario, checkpoints=8)
    database, stats = normalize(scenario / "manifest.json", tmp_path / "normalized")
    return manifest, database, stats


def test_valid_native_history_shared_values_distinct_sources_positions_and_fork(dataset):
    manifest, database, stats = dataset
    result = check(database)
    assert result["violations"] == []
    assert stats["unique_record_reads"] == result["inventory"]["unique_objects"]
    assert result["inventory"]["summed_per_checkpoint_objects"] > stats["unique_record_reads"] * 5
    assert result["inventory"]["unique_operation_obligations"] == 4
    assert result["inventory"]["distinct_ledger_positions"] == 6
    # 8 recordings x 3 positions; operation content and entire ledgers can repeat.
    current_positions = execute(database, """
        SELECT count(*) AS positions FROM roots r
        JOIN commits c ON c.oid = r.commit_id
        JOIN tree_entries t ON t.oid = c.tree_id AND t.name = 'trace'
        JOIN trace_positions p ON p.trace = t.dag;
    """, rows=True)[0]["positions"]
    assert current_positions == manifest["checkpoints"] * 3
    equal_sources = execute(database, """
        SELECT count(DISTINCT dag) AS sources, count(DISTINCT target) AS values
        FROM field_data f JOIN profiles p USING(dag)
        WHERE p.role = 'builtin-literal-source-v1' AND f.name = 'value';
    """, rows=True)[0]
    assert equal_sources == {"sources": 2, "values": 1}
    with dml.Repository(manifest["repository"]) as repo, repo.read() as tx:
        fork = tx.get_commit(tx.get_ref("fork"))
        assert fork.parents == (dml.ObjectId.from_hex(manifest["roots"][0]),)
        assert tx.get_ref("fork") != tx.get_ref("main")


def test_extract_reads_each_typed_record_once_without_semantic_validator(dataset, monkeypatch):
    manifest, _, stats = dataset
    from daggerml import builtin
    def forbidden(*args, **kwargs):
        raise AssertionError("normalizer called semantic validator")
    monkeypatch.setattr(builtin.Inspector, "__init__", forbidden)
    original = dml.Transaction.get_record
    reads = Counter()
    def counted(tx, kind, oid):
        reads[kind, str(oid)] += 1
        return original(tx, kind, oid)
    monkeypatch.setattr(dml.Transaction, "get_record", counted)
    datafile = Path(manifest["repository"]) / "data.mdb"
    before = hashlib.sha256(datafile.read_bytes()).hexdigest()
    _, repeated = extract(manifest)
    assert len(reads) == stats["unique_record_reads"] == repeated["unique_record_reads"]
    assert set(reads.values()) == {1}
    assert hashlib.sha256(datafile.read_bytes()).hexdigest() == before


@pytest.mark.parametrize(("mutation", "invariant"), [
    ("DELETE FROM objects WHERE kind = 'datum'", "missing_object"),
    ("DELETE FROM fields WHERE name = 'arguments'", "profile_fields"),
    ("UPDATE datums SET scalar = 'absent' WHERE kind = 'string' AND scalar = 'sample'", "source_association"),
    ("UPDATE datums SET scalar = 'dml://source/builtin/map/get/v99' WHERE kind = 'uri'", "map_get_binding"),
    ("UPDATE nodes SET target = (SELECT oid FROM datums WHERE kind = 'string' AND scalar = 'x') "
     "WHERE oid IN (SELECT node FROM fields WHERE name = 'value' AND dag IN (SELECT dag FROM operations))",
     "map_get_value"),
    ("UPDATE fields SET name = 'call-09' WHERE name = 'call-02'", "trace_positions"),
    ("DELETE FROM fields WHERE name = 'call-02'", "checkpoint_trace_count"),
    ("UPDATE nodes SET target = (SELECT dag FROM profiles WHERE role = 'builtin-binding-v1' LIMIT 1) "
     "WHERE oid IN (SELECT node FROM fields WHERE name = 'call-00')", "trace_target"),
    ("DELETE FROM roots", "empty_dataset"),
])
def test_known_relational_faults_are_detected(dataset, mutation, invariant):
    _, database, _ = dataset
    assert check(database)["violations"] == []
    execute(database, mutation)
    result = check(database)
    assert invariant in {row["invariant"] for row in result["violations"]}
    assert all(row["subject"] for row in result["violations"])


def test_semantically_wrong_result_in_actual_repository_is_detected(tmp_path):
    scenario = tmp_path / "wrong-result"
    manifest = exercise(scenario, checkpoints=2)
    with dml.Repository(manifest["repository"]) as repo, repo.write() as tx:
        old = dml.ObjectId.from_hex(manifest["roots"][-1])
        entries = dict(tx.get_tree(tx.get_commit(old).tree))
        trace = tx.get_dag(entries["trace"])
        calls = dict(trace.bindings)
        operation = tx.get_dag(tx.get_node(calls["call-00"]).dag)
        fields = dict(operation.bindings)
        # Public native authoring accepts structural data, not builtin semantic correctness.
        fields["value"] = tx.put_literal(tx.put_datum(43))
        bad = tx.put_dag(root=fields["value"], bindings=fields)
        calls["call-00"] = tx.put_subdag(bad)
        entries["trace"] = tx.put_dag(root=trace.root, bindings=calls)
        commit = tx.put_commit(tx.put_tree(entries), parents=(old,))
        tx.create_ref("bad-result", commit)
    manifest["roots"].append(str(commit))
    (scenario / "manifest.json").write_text(json.dumps(manifest))
    database, _ = normalize(scenario / "manifest.json", tmp_path / "bad-normalized")
    result = check(database)
    assert {row["subject"] for row in result["violations"] if row["invariant"] == "map_get_value"} == {str(bad)}


def test_missing_repository_root_fails_extraction_not_empty_success(tmp_path):
    scenario = tmp_path / "missing"
    manifest = exercise(scenario, checkpoints=2)
    manifest["roots"].append("f" * 32)
    (scenario / "manifest.json").write_text(json.dumps(manifest))
    output = tmp_path / "failed-extraction"
    with pytest.raises(dml.NotFoundError):
        normalize(scenario / "manifest.json", output)
    assert (output / "extraction-error.txt").exists()
    assert not (output / "facts.duckdb").exists()


def test_checker_runs_with_original_repository_unavailable(dataset):
    manifest, database, _ = dataset
    repository = Path(manifest["repository"])
    retired = repository.with_name("unavailable-original")
    repository.rename(retired)
    try:
        result = subprocess.run([sys.executable, str(Path(__file__).with_name("run.py")),
                                 "check", str(database)], capture_output=True, text=True, check=True)
        assert json.loads(result.stdout)["violations"] == []
    finally:
        retired.rename(repository)


@pytest.mark.parametrize("checkpoints", [2, 32])
def test_more_checkpoints_add_context_not_duplicate_semantic_obligations(tmp_path, checkpoints):
    scenario = tmp_path / "scaled"
    exercise(scenario, checkpoints=checkpoints)
    database, _ = normalize(scenario / "manifest.json", tmp_path / "scaled-normalized")
    result = check(database)
    assert result["violations"] == []
    assert result["inventory"]["unique_operation_obligations"] == 4
    assert result["inventory"]["distinct_ledger_positions"] == 6
