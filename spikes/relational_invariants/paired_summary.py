"""Summarize retained paired-case evidence without rerunning any test or repository."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

from embedded import object_signatures


def case_paths(directory):
    return sorted({path.resolve() for path in Path(directory).glob('cases/*/comparison/result.json')})


def summarize(directory, expected_cases=12):
    directory = Path(directory)
    paths = case_paths(directory)
    results = [json.loads(path.read_text()) for path in paths]
    assert len(results) == expected_cases and len({row['baseline']['nodeid'] for row in results}) == expected_cases
    counts = {key: sum(row[key] for row in results) for key in
              ('objects', 'distinct_scopes', 'observed_scopes_before_dedup', 'rejected_scopes', 'transitions', 'reuses')}
    counts['setup_reads'] = sum(row['baseline']['setup_reads'] for row in results)
    counts['body_reads'] = sum(row['baseline']['body_reads'] for row in results)
    times = {'setup_seconds_instrumented': sum(row['baseline']['setup_seconds_instrumented'] for row in results),
             'body_seconds_instrumented': sum(row['baseline']['body_seconds_instrumented'] for row in results),
             'extraction_seconds': sum(row['extraction_seconds'] for row in results),
             'projection_seconds': sum(row.get('projection_seconds', 0) for row in results),
             'materialize_seconds': sum(row['materialize_seconds'] for row in results),
             'query_seconds': sum(row['query_seconds'] for row in results),
             'relational_total_seconds': sum(row['relational_total_seconds'] for row in results)}
    registry = {}
    for result_path in paths:
        path = result_path.with_name('objects.jsonl')
        rows = {table.stem: [json.loads(line) for line in table.read_text().splitlines()]
                for table in path.parent.glob('*.jsonl')}
        for row in object_signatures(rows):
            key = row['kind'], row['oid']
            if key in registry:
                assert registry[key] == row['fingerprint'], 'same object ID differs across collected cases'
            registry[key] = row['fingerprint']
    root = Path(__file__).resolve().parents[2]
    files = ['test_composed_node_calls.py', 'test_reuse_selection_records.py', 'test_intent_scoped_edges.py',
             'test_composed_execution.py', 'test_explicit_reuse.py', 'test_reuse_selection.py',
             'test_intent_scoped_reuse.py', 'test_implementation_selection.py', 'test_exchange.py']
    source_hashes = {}
    for name in files:
        relative = 'tests/python/' + name
        current = (root / relative).read_bytes()
        original = subprocess.run(['git', '-C', str(root), 'show', 'HEAD:' + relative],
                                  capture_output=True, check=True).stdout
        assert original == current, 'existing source changed: ' + relative
        source_hashes[relative] = hashlib.sha256(current).hexdigest()
    assert all(not row['disagreements'] and not row['transition_faults'] and not row['reuse_faults']
               and row['data_unchanged'] for row in results)
    summary = {'cases': results, 'counts': counts, 'times': times,
               'cross_case_distinct_objects': len(registry),
               'shared_object_fact_signatures_agree': True, 'unchanged_original_source_sha256': source_hashes,
               'qualification': 'HOST fixture; partial SQL assertion map; single instrumented timings, not equivalent-work suite speedup'}
    (directory / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    summary = summarize(sys.argv[1], int(sys.argv[2]) if len(sys.argv)>2 else 12)
    print(json.dumps({key: value for key, value in summary.items() if key != 'cases'}, indent=2))
