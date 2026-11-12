"""Pure harness guards, not native scenario or predicate assurance."""

from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import bootstrap
bootstrap()
from paired_runner import compare
from paired_summary import case_paths


def test_conflicting_same_scope_verdicts_cannot_be_silently_deduplicated(tmp_path):
    # Synthetic file sufficient for the pre-extraction guard; never opened as LMDB.
    repository = tmp_path / 'caller'
    repository.mkdir()
    (repository / 'data.mdb').write_bytes(b'pure orchestration guard')
    scope = {'kind': 'composition', 'args': {'commit': '1' * 32, 'inputs_name': 'inputs',
                                           'composition_name': 'C', 'depth': 0}}
    trace = SimpleNamespace(roots={str(repository): {'1' * 32}}, setup_seconds=0,
                            body_seconds=0, setup_reads=0, body_reads=0, body_unique=0,
                            host_calls=0, transitions=[], reuses=[],
                            scopes=[dict(scope, accepted=True), dict(scope, accepted=False)])
    with pytest.raises(AssertionError, match='conflicting baseline verdicts'):
        compare(trace, tmp_path / 'report', 'synthetic-guard')
    assert not (tmp_path / 'report' / 'facts.duckdb').exists()


def test_pytest_current_symlink_does_not_double_count_case_artifacts(tmp_path):
    case = tmp_path / 'cases' / 'case0'
    (case / 'comparison').mkdir(parents=True)
    result = case / 'comparison' / 'result.json'
    result.write_text('{}')
    (case.parent / 'casecurrent').symlink_to(case, target_is_directory=True)
    assert case_paths(tmp_path) == [result.resolve()]
