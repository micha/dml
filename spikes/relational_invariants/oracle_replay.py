"""Replay SAME collected cases: isolated vs shared/materialized SQL oracle.

No DML imports, repository access, source execution or original-test rerun.
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
import time

from capsules import SCHEMA as CAPSULE_SCHEMA, project as project_capsules
from embedded import OWNERS, connect, object_signatures
from schema import CONTEXT_COLUMNS, KEYS, SCHEMA
from scope_schema import SCOPE_SCHEMA

HERE = Path(__file__).resolve().parent
FACTS = {name: columns for name, columns in SCHEMA.items() if name != 'roots'}
PROJECTIONS = {
    'h_fields': 'dag', 'h_roles': 'dag', 'h_values': 'dag', 'h_requests': 'dag',
    'h_attempts': 'dag', 'h_arguments': 'arguments', 'h_expected_arguments': 'arguments',
    'h_operations': 'dag', 'h_trace_positions': 'trace', 'h_selections': 'dag', 'h_field_sets': 'dag',
}


@dataclass
class Case:
    name: str
    facts: dict
    scopes: dict
    expected: dict


def cases_from(directory):
    paths = sorted({p.resolve() for p in Path(directory).glob('cases/*/comparison/result.json')})
    cases = []
    for path in paths:
        result = json.loads(path.read_text())
        facts = {name: [json.loads(line) for line in (path.parent / f'{name}.jsonl').read_text().splitlines()]
                 for name in SCHEMA}
        scopes = json.loads((path.parent / 'scope-inputs.json').read_text())
        expected = json.loads((path.parent / 'original-verdicts.json').read_text())
        cases.append(Case(result['baseline']['nodeid'], facts, scopes, expected))
    if len(cases) != 44 or len({case.name for case in cases}) != 44:
        raise ValueError('expected exactly44 distinct retained case datasets')
    return cases


def create_table(conn, name, columns):
    conn.execute(f'CREATE TABLE {name} (' + ', '.join(f'"{key}" {kind}' for key, kind in columns.items()) + ')')


def replace_rows(conn, name, columns, rows):
    conn.execute(f'DELETE FROM {name}')
    if rows:
        projection = ', '.join(f"CAST(json_extract_string(value, '$.{key}') AS {kind}) AS \"{key}\""
                               for key, kind in columns.items())
        conn.execute(f'INSERT INTO {name} SELECT {projection} FROM json_each(?)',
                     [json.dumps(rows, sort_keys=True, separators=(',', ':'))])


def rule_definitions(conn):
    for name in ('reuse_checks.sql', 'paired_checks.sql', 'selection_checks.sql'):
        conn.execute((HERE / name).read_text())


def scope_verdicts(conn, case):
    failed_compositions = {row[0] for row in conn.execute('SELECT scope_id FROM p_composition_faults').fetchall()}
    failed_selections = {row[0] for row in conn.execute('SELECT scope_id FROM s_faults').fetchall()}
    actual = {str(row['scope_id']): row['scope_id'] not in failed_compositions
              for row in case.scopes['composition_scopes']}
    actual.update({str(row['scope_id']): row['scope_id'] not in failed_selections
                   for row in case.scopes['selection_scopes']})
    actual.update({str(key): value for key, value in conn.execute('SELECT scope_id, accepted FROM p_candidate_results').fetchall()})
    actual.update({str(key): False if value == 'reject' else value
                   for key, value in conn.execute('SELECT scope_id, action FROM p_resolution_results').fetchall()})
    return {'actual': actual,
            'disagreements': [key for key, value in case.expected.items() if actual.get(key) != value['verdict']],
            'transition_faults': conn.execute('SELECT * FROM p_transition_faults').fetchall(),
            'reuse_faults': conn.execute('SELECT * FROM p_reuse_faults').fetchall()}


def empty_context_tables(conn):
    create_table(conn, 'roots', SCHEMA['roots'])
    create_table(conn, 'request_contexts', CONTEXT_COLUMNS)
    for name, columns in SCOPE_SCHEMA.items():
        create_table(conn, name, columns)


def immutable_pool(cases):
    tables = {name: {} for name in FACTS}
    signatures = {}
    for case in cases:
        for row in object_signatures(case.facts):
            key = row['kind'], row['oid']
            if key in signatures and signatures[key] != row['fingerprint']:
                raise ValueError('same immutable object differs between cases')
            signatures[key] = row['fingerprint']
        for name in FACTS:
            for row in case.facts[name]:
                key = tuple(row[column] for column in KEYS[name])
                if key in tables[name] and tables[name][key] != row:
                    raise ValueError('same immutable fact key differs between cases: ' + name)
                tables[name][key] = row
    return {name: list(rows.values()) for name, rows in tables.items()}, signatures


class SharedOracle:
    def __init__(self, conn, cases, *, materialize_scopes=False):
        self.conn = conn
        self.materialize_scopes = materialize_scopes
        sql = '\n'.join((HERE/name).read_text() for name in ('paired_checks.sql','selection_checks.sql'))
        self.scope_definitions = {}
        for statement, name in re.findall(r'(CREATE OR REPLACE VIEW (\w+)\s+AS\s+.*?;)', sql, flags=re.S):
            self.scope_definitions[name] = statement
        required = {'p_compositions','s_targets','s_headers','p_table_rows','p_reuse_choices'}
        if not required.issubset(self.scope_definitions):
            raise ValueError('scope SQL definitions missing from fixed rule sources')
        self.facts, self.signatures = immutable_pool(cases)
        for name, columns in FACTS.items():
            create_table(conn, name, columns)
            replace_rows(conn, name, columns, self.facts[name])
        empty_context_tables(conn)
        create_table(conn, 'capsules', CAPSULE_SCHEMA)
        replace_rows(conn, 'capsules', CAPSULE_SCHEMA, project_capsules(self.facts))
        rule_definitions(conn)
        # These are immutable structural projections, NOT cached successful authority
        # verdicts. Ancestry is filtered on BOTH available endpoints below.
        for name in (*PROJECTIONS, 'h_ancestry'):
            conn.execute(f'CREATE TABLE global_{name} AS SELECT * FROM {name}')
            conn.execute(f'CREATE OR REPLACE VIEW {name} AS SELECT * FROM global_{name}')
        create_table(conn, 'active_objects', SCHEMA['objects'])
        for name, columns in FACTS.items():
            conn.execute(f'ALTER TABLE {name} RENAME TO global_{name}')
            if name == 'objects':
                condition = "o.kind=t.kind AND o.oid=t.oid"
            elif name == 'edges':
                condition = "o.kind=t.src_kind AND o.oid=t.src"
            else:
                kind, column = OWNERS[name]
                condition = f"o.kind='{kind}' AND o.oid=t.{column}"
            conn.execute(f'CREATE VIEW {name} AS SELECT t.* FROM global_{name} t JOIN active_objects o ON {condition}')
        conn.execute('ALTER TABLE capsules RENAME TO global_capsules')
        conn.execute("CREATE VIEW capsules AS SELECT t.* FROM global_capsules t JOIN active_objects o ON o.kind='dag' AND o.oid=t.dag")
        for name, column in PROJECTIONS.items():
            conn.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT t.* FROM global_{name} t "
                         f"JOIN active_objects o ON o.kind='dag' AND o.oid=t.{column}")
        conn.execute("CREATE OR REPLACE VIEW h_ancestry AS SELECT t.* FROM global_h_ancestry t "
                     "JOIN active_objects d ON d.kind='commit' AND d.oid=t.descendant "
                     "JOIN active_objects a ON a.kind='commit' AND a.oid=t.ancestor")

    def activate(self, case):
        # Check the full supplied decoded object sets, not merely membership IDs.
        for row in object_signatures(case.facts):
            if self.signatures.get((row['kind'], row['oid'])) != row['fingerprint']:
                raise ValueError('case descriptions disagree with admitted immutable pool')
        conn = self.conn
        replace_rows(conn, 'active_objects', SCHEMA['objects'], case.facts['objects'])
        replace_rows(conn, 'roots', SCHEMA['roots'], case.facts['roots'])
        for name, columns in SCOPE_SCHEMA.items():
            replace_rows(conn, name, columns, case.scopes[name])
        if self.materialize_scopes:
            for name in ('p_compositions','s_targets','s_headers','p_table_rows','p_reuse_choices'):
                conn.execute(self.scope_definitions[name])
                conn.execute(f'CREATE OR REPLACE TEMP TABLE active_{name} AS SELECT * FROM {name}')
                kind = getattr(self, 'case_view_kind', 'VIEW')
                conn.execute(f'CREATE OR REPLACE {kind} {name} AS SELECT * FROM active_{name}')

    def availability_faults(self):
        conn = self.conn
        missing = conn.execute("""
            SELECT e.src, e.dst_kind, e.dst FROM edges e LEFT JOIN active_objects target
            ON target.kind=e.dst_kind AND target.oid=e.dst WHERE target.oid IS NULL
            UNION ALL
            SELECT r.commit_id,'commit',r.commit_id FROM roots r LEFT JOIN active_objects o
            ON o.kind='commit' AND o.oid=r.commit_id WHERE o.oid IS NULL;
        """).fetchall()
        return missing

    def check(self, case):
        self.activate(case)
        result = scope_verdicts(self.conn, case)
        result['availability_faults'] = self.availability_faults()
        return result


def isolated_check(conn, case):
    for name, columns in FACTS.items():
        create_table(conn, name, columns)
        replace_rows(conn, name, columns, case.facts[name])
    empty_context_tables(conn)
    replace_rows(conn, 'roots', SCHEMA['roots'], case.facts['roots'])
    create_table(conn, 'capsules', CAPSULE_SCHEMA)
    replace_rows(conn, 'capsules', CAPSULE_SCHEMA, project_capsules(case.facts))
    for name, columns in SCOPE_SCHEMA.items():
        replace_rows(conn, name, columns, case.scopes[name])
    rule_definitions(conn)
    return scope_verdicts(conn, case)


def clean(result):
    return not any(result.get(name) for name in ('disagreements', 'transition_faults', 'reuse_faults', 'availability_faults'))


def replay(evidence, output, baseline=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    cases = cases_from(evidence)
    input_seconds = time.perf_counter() - started
    records = []
    if baseline is not None:
        saved = json.loads(Path(baseline).read_text())
        if [row['case'] for row in saved['records']] != [case.name for case in cases]:
            raise ValueError('retained baseline cases differ')
        current_rules = {name: hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in saved['rule_sha256']}
        if current_rules != saved['rule_sha256']:
            raise ValueError('retained baseline predicates differ')
        records = [{'case': row['case'], 'isolated_seconds': row['isolated_seconds'], 'isolated': row['isolated']}
                   for row in saved['records']]
        isolated_seconds = saved['isolated_replay_seconds']
    else:
        total = time.perf_counter()
        for case in cases:
            started = time.perf_counter()
            with connect(':memory:') as conn:
                result = isolated_check(conn, case)
            records.append({'case': case.name, 'isolated_seconds': time.perf_counter()-started,
                            'isolated': result})
            if not clean(result):
                raise AssertionError('isolated replay differs: ' + case.name)
        isolated_seconds = time.perf_counter() - total
    started = time.perf_counter()
    with connect(output / 'shared.duckdb') as conn:
        oracle = SharedOracle(conn, cases, materialize_scopes=baseline is not None)
        setup_seconds = time.perf_counter() - started
        for case, record in zip(cases, records):
            started = time.perf_counter()
            result = oracle.check(case)
            record.update(shared_seconds=time.perf_counter()-started, shared=result)
            if not clean(result) or result['actual'] != record['isolated']['actual']:
                raise AssertionError('shared oracle differs: ' + case.name)
        objects = len(oracle.facts['objects'])
    shared_seconds = setup_seconds + sum(row['shared_seconds'] for row in records)
    report = {'input_read_seconds': input_seconds, 'isolated_replay_seconds': isolated_seconds,
              'shared_setup_seconds': setup_seconds, 'shared_complete_seconds': shared_seconds,
              'cases': len(cases), 'global_objects': objects, 'records': records,
              'retained_isolated_baseline': str(baseline) if baseline else None,
              'scoped_materialization': baseline is not None,
              'dml_imported': 'daggerml' in sys.modules,
              'rule_sha256': {name: hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in
                              ('reuse_checks.sql','paired_checks.sql','selection_checks.sql')},
              'qualification': 'SAME frozen decoded facts; no native reads/computation; single replay timings'}
    (output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    result = replay(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv)>3 else None)
    print(json.dumps({key:value for key,value in result.items() if key!='records'}, indent=2))
