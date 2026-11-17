"""Independent mixed-builtin predicates on case-local READ_ONLY/TEMP pooled facts."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from engine import quote
from schema import SCHEMA
from shared_index.project import Facts

SQL=Path(__file__).with_name('checks.sql')


def case_sql(case,output):
    values=','.join(f'({quote(kind)},{quote(oid)})' for kind,oid in case['membership'])
    result=['BEGIN TRANSACTION;',f'CREATE TEMP TABLE available(kind,oid) AS SELECT * FROM (VALUES {values});']
    for table in SCHEMA:
        if table=='roots':continue
        if table=='objects':condition='a.kind=p.kind AND a.oid=p.oid'
        elif table=='edges':condition='a.kind=p.src_kind AND a.oid=p.src'
        else:
            kind={'datums':'datum','map_entries':'datum','nodes':'node','dags':'dag','fields':'dag','tree_entries':'tree','commits':'commit'}[table]
            field='dag' if table=='fields' else 'oid'
            condition=f'a.kind={quote(kind)} AND a.oid=p.{field}'
        result.append(f'CREATE TEMP VIEW {table} AS SELECT p.* FROM pool_{table} p WHERE EXISTS(SELECT 1 FROM available a WHERE {condition});')
    result.append(f"CREATE TEMP TABLE subject(subject,method) AS SELECT {quote(case['subject'])},{quote(case['method'])};")
    result.append(SQL.read_text())
    result.append(f'COPY (SELECT * FROM faults ORDER BY invariant,subject,detail) TO {quote(Path(output).resolve())} (FORMAT JSON);')
    return '\n'.join(result)


def check_case(database,rows,case,directory,*,duckdb=None):
    if sorted([list(item) for item in Facts(rows).reached(case['target'])])!=case['membership']:
        raise ValueError('case availability differs')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    before=hashlib.sha256(Path(database).read_bytes()).hexdigest()
    sql=case_sql(case,directory/'rows.jsonl')
    (directory/'query.sql').write_text(sql)
    executable=duckdb or shutil.which('duckdb')
    if not executable:raise ValueError('DuckDB is missing; enter nix develop or supply duckdb explicitly')
    command=[executable,'-readonly','-batch','-bail','-json',str(database)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    stdout,stderr=process.communicate(sql)
    owner={'pid':process.pid,'wait_exit':process.returncode,'command':command}
    (directory/'stdout.log').write_text(stdout);(directory/'stderr.log').write_text(stderr)
    (directory/'owner.json').write_text(json.dumps(owner,sort_keys=True)+'\n')
    if process.returncode!=0:raise RuntimeError('SQL gate failed: '+stderr)
    faults=[json.loads(line) for line in (directory/'rows.jsonl').read_text().splitlines() if line.strip()]
    if hashlib.sha256(Path(database).read_bytes()).hexdigest()!=before:raise ValueError('pool mutated')
    return {'label':case['label'],'accepted':not faults,'faults':faults,'owner':owner}


def assert_agreement(case,result):
    if result['accepted']!=case['expected'] or result['accepted']!=case['observed']:
        raise AssertionError('independent original/assertion/relational disagreement: '+case['label'])
