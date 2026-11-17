"""Immutable pooled facts; READ_ONLY/TEMP per-case availability and independent SQL."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from engine import execute, quote
from schema import SCHEMA
from .project import Facts

CHECKS = Path(__file__).resolve().parents[1] / 'checks.sql'


def pool(rows, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    database = directory / 'pool.duckdb'
    sql = ['BEGIN TRANSACTION;']
    for table, columns in SCHEMA.items():
        fields = ', '.join(f'"{name}" {kind}' for name,kind in columns.items())
        sql.append(f'CREATE TABLE pool_{table} ({fields});')
        path = directory / (table+'.jsonl')
        path.write_text(''.join(json.dumps(row,sort_keys=True)+'\n' for row in rows[table]))
        if rows[table]:
            types = ', '.join(f'{quote(name)}: {quote(kind)}' for name,kind in columns.items())
            sql.append(f'INSERT INTO pool_{table} SELECT * FROM read_json({quote(path.resolve())}, '
                       f"format='newline_delimited', columns={{{types}}});")
    sql.append('CREATE UNIQUE INDEX object_identity ON pool_objects(kind,oid);')
    sql.append('COMMIT;')
    script = '\n'.join(sql)
    (directory/'load.sql').write_text(script+'\n')
    execute(database,script)
    return database


def case_sql(case, result_path=None):
    available = case['membership']
    if not available:
        raise ValueError('empty case availability')
    values = ','.join(f'({quote(kind)},{quote(oid)})' for kind,oid in available)
    sql = ['BEGIN TRANSACTION;', f'CREATE TEMP TABLE available(kind,oid) AS SELECT * FROM (VALUES {values});']
    for table in SCHEMA:
        if table == 'roots':
            roots = ','.join(f'({i},{quote(root)},{"NULL" if positions is None else positions})'
                             for i,(root,positions) in enumerate(zip(case['roots'],case['expectations']['positions'])))
            sql.append(f'CREATE TEMP TABLE roots(checkpoint,commit_id,expected_positions) AS SELECT * FROM (VALUES {roots});')
            continue
        if table == 'objects':
            condition = 'a.kind=p.kind AND a.oid=p.oid'
        elif table == 'edges':
            condition = 'a.kind=p.src_kind AND a.oid=p.src'
        else:
            kind = {'datums':'datum','map_entries':'datum','nodes':'node','dags':'dag','fields':'dag',
                    'tree_entries':'tree','commits':'commit'}[table]
            field = 'dag' if table=='fields' else 'oid'
            condition = f'a.kind={quote(kind)} AND a.oid=p.{field}'
        sql.append(f'CREATE TEMP VIEW {table} AS SELECT p.* FROM pool_{table} p '
                   f'WHERE EXISTS(SELECT 1 FROM available a WHERE {condition});')
    original = CHECKS.read_text()
    sql.append(original.replace('CREATE OR REPLACE VIEW ', 'CREATE OR REPLACE TEMP VIEW '))
    sources = ','.join(quote(source) for source in case['sources'])
    # Context controls authority, NOT a recorded check verdict or expected accept/reject answer.
    sql.append('CREATE TEMP VIEW contextual_faults AS '
               "SELECT 'context_source_scope' AS invariant,p.dag AS subject,'source outside declared fixture' AS detail "
               "FROM profiles p LEFT JOIN field_data s ON s.dag=p.dag AND s.name='source' "
               f"WHERE p.role='builtin-literal-source-v1' AND (s.target IS NULL OR s.target NOT IN ({sources})) "
               'UNION ALL '
               "SELECT 'context_binding_scope',o.dag,'unsupported captured binding' FROM operations o "
               "LEFT JOIN field_data s ON s.dag=o.binding AND s.name='source' "
               "WHERE s.scalar IS NULL OR s.scalar NOT IN ('dml://source/builtin/map/get/v1','dml://source/builtin/map/get/v2');")
    query = 'SELECT * FROM violations UNION ALL SELECT * FROM contextual_faults ORDER BY invariant,subject,detail'
    sql.append((query+';') if result_path is None else
               f'COPY ({query}) TO {quote(Path(result_path).resolve())} (FORMAT JSON);')
    # TEMP state rolls back at connection close; no persistent view/write/ref mutation.
    return '\n'.join(sql)


def check_case(database, rows, case, *, output_directory=None, duckdb=None):
    actual = sorted([list(item) for item in Facts(rows).reached(case['target'])])
    if actual != case['membership']:
        raise ValueError('supplied case availability differs from actual target closure')
    before = hashlib.sha256(Path(database).read_bytes()).hexdigest()
    directory = (Path(output_directory) if output_directory is not None else
                 Path(database).parent / ('check-'+hashlib.sha256(case['target'].encode()).hexdigest()[:16]))
    directory.mkdir(parents=True,exist_ok=False)
    result_path = directory/'rows.jsonl'
    sql = case_sql(case,result_path)
    (directory/'query.sql').write_text(sql)
    executable = duckdb or shutil.which('duckdb')
    if not executable:
        raise ValueError('DuckDB is missing; enter nix develop or supply duckdb explicitly')
    command = [executable,'-readonly','-batch','-bail','-json',str(database)]
    process = subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    stdout, stderr = process.communicate(sql)
    owner = {'pid':process.pid,'wait_exit':process.returncode,'command':command}
    (directory/'stdout.log').write_text(stdout)
    (directory/'stderr.log').write_text(stderr)
    (directory/'owner.json').write_text(json.dumps(owner,sort_keys=True)+'\n')
    if process.returncode != 0:
        raise RuntimeError(f'case SQL failed exit{process.returncode}: {stderr}')
    violations = [json.loads(line) for line in result_path.read_text().splitlines() if line.strip()]
    for row in violations:
        if type(row) is not dict or set(row) != {'invariant','subject','detail'} or any(type(v) is not str for v in row.values()):
            raise ValueError('invalid structured invariant result')
    if hashlib.sha256(Path(database).read_bytes()).hexdigest() != before:
        raise ValueError('checker changed immutable pool')
    return {'label':case['label'],'occurrence':case['occurrence'],'target':case['target'],
            'accepted':not violations,'violations':violations,
            'owner':owner,'result_directory':str(directory)}


def assert_expected(case, result):
    """Outside SQL: expectation is a test assertion, never an answer supplied to predicates."""
    if case['expectations']['outcome']=='accept':
        if not result['accepted']:
            raise AssertionError('positive context rejected: '+case['label'])
    else:
        actual = {row['subject'] for row in result['violations'] if row['invariant']=='map_get_value'}
        if result['accepted'] or actual != {case['bad_operation']}:
            raise AssertionError('specific negative context counterexample missing: '+case['label'])
