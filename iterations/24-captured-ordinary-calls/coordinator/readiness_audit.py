"""Coordinator STATIC readiness audit; no DML import/build/test/reader/computation."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

repo = Path('/work/repos/micha/dml')
root = repo / 'build/iteration24'
evidence = root / 'readiness/final'
load = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
submission = load(evidence / 'submission.json')
for field, filename in [('source_manifest_sha256', 'source.json'),
                        ('copies_manifest_sha256', 'copies.json'),
                        ('coverage_sha256', 'coverage.json'),
                        ('matrix_sha256', 'line-matrix.json')]:
    assert sha(evidence / filename) == submission[field], field
sources = load(evidence / 'source.json')
assert len(sources) == submission['source_paths'] == 31
for name, digest in sources.items():
    assert sha(repo / name) == digest, name
changed = subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain', '--untracked-files=all'], text=True)
assert {line[3:] for line in changed.splitlines()} == set(sources), 'actual changed surface differs'
assert subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip() == submission['head'] == '965cec450356e5f776b68bc311fa4d7eaf690519'
assert not subprocess.check_output(['git', '-C', str(repo), 'diff', '--cached', '--name-only'], text=True).strip()
subprocess.run(['git', '-C', str(repo), 'diff', '--check'], check=True)
copies = load(evidence / 'copies.json')
assert len(copies) == 10
for name, row in copies.items():
    assert Path(row['copy']) == root / 'acceptance/launch-source' / name
    assert sha(row['source']) == sha(row['copy']) == row['sha256'], name
metadata = load(evidence / 'metadata/readiness.json')
assert metadata['metadata_only'] and metadata['semantic_input_union'] == 10
assert metadata['sources'] == {name: row['sha256'] for name, row in copies.items()}
assert metadata['required_prelaunch_review']['declaration_NOT_installed_receipt']
assert metadata['required_prelaunch_review']['authority_limit'] == 8
assert metadata['required_prelaunch_review']['semantic_limit'] == 64
install = load(root / 'install/manifest.json')
assert len(install['artifacts']) == 15
for name, row in install['artifacts'].items():
    assert sha(row['installed']) == sha(row.get('source', row.get('compiled'))) == row['sha256'], name
assert sha(install['interpreter']) == metadata['interpreter_sha256'] == install['interpreter_sha256']
assert metadata['interpreter'] == install['interpreter']
assert Path(metadata['prefix']) == root / 'install/venv'
for row in metadata['installed'].values():
    assert Path(metadata['prefix']) in Path(row['path']).parents
    assert sha(row['path']) == row['sha256']
for name, row in metadata['helpers'].items():
    assert row['path'] == copies[name]['copy'] and row['sha256'] == copies[name]['sha256']
for mode in ['controller-controls', 'reader-controls', 'metadata']:
    assert (evidence / (mode + '.exit')).read_text().strip() == '0', mode
    assert not (evidence / (mode + '.err')).read_bytes(), mode
    command = (evidence / (mode + '.command')).read_text()
    assert 'env -u PYTHONPATH -u PYTHONHOME ' + install['interpreter'] + ' -I ' in command
    assert ' run ' not in command
controller = load(evidence / 'controller-controls.log')
reader = load(evidence / 'reader-controls.log')
assert controller['blockers'] == ['spawn', 'connect', 'urllib-transport']
assert reader['blockers'] == ['spawn', 'http', 'urllib-transport', 'connect']
assert reader['author_blockers'] == ['target-write', 'record', 'dispatch', 'logical', 'recorder']
assert reader['blocker_first'] and reader['nonexecuting']
coverage = load(evidence / 'coverage.json')
assert coverage['totals']['num_statements'] == coverage['totals']['covered_lines'] == 1144
assert coverage['totals']['missing_lines'] == 0 and coverage['totals']['excluded_lines'] == 1
for name, row in coverage['files'].items():
    assert not row['missing_lines'], name
    assert row['excluded_lines'] == ([124] if name.endswith('/captured_calls.py') else []), name
exclusion = root / 'readiness/exclusion124'
a = (exclusion / 'captured_calls.before.py').read_bytes()
b = (repo / 'examples/captured_calls.py').read_bytes()
assert b == (exclusion / 'captured_calls.after.py').read_bytes()
assert ast.dump(ast.parse(a), include_attributes=True) == ast.dump(ast.parse(b), include_attributes=True)
assert b == a.replace(b'raise ValueError("captured dependency not retained")\n', b'raise ValueError("captured dependency not retained")  # pragma: no cover\n', 1)
proof = load(root / 'native-proof/current/proof.json')
assert len(set(proof['original_semantic_ids'])) == 34
assert len(set(proof['aggregate_semantic_ids'])) == 50
assert set(proof['original_semantic_ids']) <= set(proof['aggregate_semantic_ids'])
assert all(row['bound'] == row['prior'] + row['count'] <= 64 for row in proof['reservations'])
assert proof['HOST_only'] and proof['OS_computational_children'] == 0
assert proof['HOST_publications'] == 3 and proof['no_double_Q_or_second_ordinary_position']
for name, digest in proof['source'].items():
    assert sha(root / 'native-proof/current' / name) == digest
    actual = a if name == 'captured_calls.py' else (repo / 'examples' / name).read_bytes()
    assert hashlib.sha256(actual).hexdigest() == digest
xml = ET.parse(root / 'focused-v23/pytest.xml')
assert (len(list(xml.iter('testcase'))), len(list(xml.iter('failure'))), len(list(xml.iter('error'))), len(list(xml.iter('skipped')))) == (5, 0, 0, 0)
assert (root / 'focused-v23/exit').read_text().strip() == '0'
assert not (root / 'acceptance/story').exists()
result = dict(static_audit='PASS', current_changed_paths=31, exact_copied_sources=10,
              installed_artifacts=15, worker_metadata_control_exits=[0,0,0],
              worker_v23_cases=5, cumulative_informative_retained_statements=1144,
              approved_excluded_raise=124, source_AST_with_locations_equal=True,
              old_proof_pre_marker_qualified=True, story_absent=True,
              independently_executed_DML_tests_builds_readers_computations=0,
              not_implementation_acceptance=True)
print(json.dumps(result, indent=2))
