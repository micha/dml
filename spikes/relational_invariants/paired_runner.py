"""Normalize one case once, then compare independent scoped SQL verdicts."""

import hashlib
import json
from pathlib import Path
import time

from capsules import SCHEMA as CAPSULE_SCHEMA, project as project_capsules
from embedded import Batch, connect, initialize, publish
from normalizer import extract
from schema import SCHEMA
from scope_schema import SCOPE_SCHEMA


def load_rows(conn, table, columns, rows):
    fields = ', '.join(f'"{key}" {value}' for key, value in columns.items())
    conn.execute(f'CREATE TABLE {table} ({fields})')
    if rows:
        marks = ', '.join('?' for _ in columns)
        conn.executemany(f'INSERT INTO {table} VALUES ({marks})', [[row[key] for key in columns] for row in rows])


def compare(trace, output, nodeid):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    primary = [path for path in trace.roots if Path(path).name in ('caller', 'A')]
    if len(primary) != 1:
        raise AssertionError('cannot identify exactly one owned case repository: ' + repr(primary))
    repository = primary[0]
    before = hashlib.sha256((Path(repository) / 'data.mdb').read_bytes()).hexdigest()
    baseline = {'nodeid': nodeid, 'setup_seconds_instrumented': trace.setup_seconds,
                'body_seconds_instrumented': trace.body_seconds, 'setup_reads': trace.setup_reads,
                'body_reads': trace.body_reads, 'body_unique_ids': trace.body_unique,
                'host_generic_calls': trace.host_calls,
                'note': 'unchanged assertion body; HOST fixture, not child/custody assurance'}
    (output / 'baseline.json').write_text(json.dumps(baseline, indent=2) + '\n')
    (output / 'observed-scopes.json').write_text(json.dumps(trace.scopes, indent=2, default=str) + '\n')
    scopes = {table: [] for table in SCOPE_SCHEMA}
    expected = {}
    dedup = {}
    for observed in trace.scopes:
        args, kind = observed['args'], observed['kind']
        scope_id = len(expected)
        if kind == 'composition':
            row = {'scope_id': scope_id, 'commit_id': str(args['commit']),
                   'inputs_name': args['inputs_name'], 'composition_name': args['composition_name'],
                   'depth': args.get('depth', 0)}
            table = 'composition_scopes'
        elif kind == 'candidate':
            receipt, dimensions = observed['receipt'], observed['expected']
            row = {'scope_id': scope_id, 'commit_id': receipt['selected_commit'],
                   'attempt_id': receipt['attempt_id'], 'phase': receipt['phase'],
                   'request': dimensions['request'], 'binding': dimensions['binding'],
                   'inputs': dimensions['inputs'], 'intent': dimensions['intent_uri'],
                   'job_document': json.dumps(observed['job'], sort_keys=True, separators=(',', ':')),
                   'expected_document': json.dumps(observed['expected_job'], sort_keys=True, separators=(',', ':')),
                   'receipt_document': json.dumps(receipt, sort_keys=True, separators=(',', ':')),
                   'bundle_root': observed['bundle_root'], 'bundle_sha256': observed['bundle_sha256']}
            table = 'candidate_scopes'
        elif kind == 'selection':
            row = {'scope_id': scope_id, 'commit_id': str(args['commit']), 'slot': args['slot'],
                   'binding_name': args.get('binding_name'), 'inputs_name': args.get('inputs_name'),
                   'intent': args.get('intent_uri')}
            table = 'selection_scopes'
        else:
            row = {'scope_id': scope_id, 'commit_id': str(args['commit']), 'inputs_name': args['inputs_name'],
                   'composition_name': args['composition_name'], 'control': args['control'],
                   'depth': args.get('depth', 0), 'intent': args['intent'], 'binding_name': args['binding_name']}
            table = 'resolution_scopes'
        identity = (table, json.dumps({key: value for key, value in row.items() if key != 'scope_id'}, sort_keys=True))
        verdict = observed.get('action') if kind == 'resolve' and observed['accepted'] else observed['accepted']
        if identity in dedup:
            if dedup[identity] != verdict:
                raise AssertionError('same recorded scope has conflicting baseline verdicts; missing context')
            continue
        dedup[identity] = verdict
        expected[scope_id] = {'kind': kind, 'verdict': verdict, 'error': observed.get('error')}
        scopes[table].append(row)
    scopes['transition_scopes'] = [
        {'transition_id': i, 'kind': row['kind'], 'before_commit': row['before'], 'after_commit': row['after'],
         'slot': row['slot'], 'inputs': row['inputs']}
        for i, row in enumerate(trace.transitions)]
    scopes['reuse_scopes'] = [dict(reuse_id=i, **row) for i, row in enumerate(trace.reuses)]
    (output / 'scope-inputs.json').write_text(json.dumps(scopes, indent=2) + '\n')
    (output / 'original-verdicts.json').write_text(json.dumps(expected, indent=2) + '\n')
    manifest = {'repository': repository, 'roots': sorted(trace.roots[repository])}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    started = time.perf_counter()
    rows, stats = extract(manifest)
    extraction_seconds = time.perf_counter() - started
    rows = {table: rows[table] for table in SCHEMA}
    for table, entries in rows.items():
        (output / f'{table}.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in entries))
    rows['request_contexts'] = []  # New scoped profile, not the earlier fixed two-Q context checker.
    capsule_started = time.perf_counter()
    capsules = project_capsules(rows)
    projection_seconds = time.perf_counter() - capsule_started
    (output / 'capsules.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in capsules))
    database = output / 'facts.duckdb'
    started = time.perf_counter()
    initialize(database)
    with connect(database) as conn:
        publish(conn, Batch(nodeid, rows))
        load_rows(conn, 'capsules', CAPSULE_SCHEMA, capsules)
        for table, columns in SCOPE_SCHEMA.items():
            load_rows(conn, table, columns, scopes[table])
        materialize_seconds = time.perf_counter() - started
        started = time.perf_counter()
        conn.execute(Path(__file__).with_name('paired_checks.sql').read_text())
        conn.execute(Path(__file__).with_name('selection_checks.sql').read_text())
        actual = {}
        selection_faults = conn.execute('SELECT scope_id, invariant FROM s_faults ORDER BY 1,2').fetchall()
        failed_selections = {row[0] for row in selection_faults}
        for row in scopes['selection_scopes']:
            actual[row['scope_id']] = row['scope_id'] not in failed_selections
        composition_faults = conn.execute('SELECT scope_id, invariant FROM p_composition_faults ORDER BY 1,2').fetchall()
        failed_compositions = {row[0] for row in composition_faults}
        for row in scopes['composition_scopes']:
            actual[row['scope_id']] = row['scope_id'] not in failed_compositions
        for scope_id, verdict in conn.execute('SELECT scope_id, accepted FROM p_candidate_results').fetchall():
            actual[scope_id] = verdict
        for scope_id, action in conn.execute('SELECT scope_id, action FROM p_resolution_results').fetchall():
            actual[scope_id] = False if action == 'reject' else action
        transition_faults = conn.execute('SELECT * FROM p_transition_faults ORDER BY 1,2').fetchall()
        reuse_faults = conn.execute('SELECT * FROM p_reuse_faults ORDER BY 1,2').fetchall()
        checking_seconds = time.perf_counter() - started
        shared_ops = conn.execute("SELECT count(*) FROM h_roles WHERE role='builtin-operation-v1'").fetchone()[0]
    after = hashlib.sha256((Path(repository) / 'data.mdb').read_bytes()).hexdigest()
    disagreements = [{'scope_id': key, 'original': value, 'relational': actual.get(key)}
                     for key, value in expected.items() if value['verdict'] != actual.get(key)]
    result = {'baseline': baseline, 'objects': stats['unique_record_reads'], 'roots': len(manifest['roots']),
              'distinct_scopes': len(expected), 'observed_scopes_before_dedup': len(trace.scopes),
              'rejected_scopes': sum(value['verdict'] is False for value in expected.values()),
              'unique_builtin_operations': shared_ops,
              'extraction_seconds': extraction_seconds, 'projection_seconds': projection_seconds,
              'materialize_seconds': materialize_seconds,
              'query_seconds': checking_seconds,
              'relational_total_seconds': extraction_seconds + projection_seconds + materialize_seconds + checking_seconds,
              'disagreements': disagreements, 'selection_faults': selection_faults,
              'composition_faults': composition_faults,
              'transition_faults': transition_faults, 'reuse_faults': reuse_faults,
              'transitions': len(trace.transitions), 'reuses': len(trace.reuses),
              'data_unchanged': before == after}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    assert before == after, 'normalization changed native case data'
    assert not disagreements, disagreements
    assert not transition_faults, transition_faults
    assert not reuse_faults, reuse_faults
    return result
