"""Connection-local case checking against one immutable read-only oracle pool."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import sys
import time

import duckdb

from capsules import SCHEMA as CAPSULE_SCHEMA
from embedded import OWNERS, connect
from oracle_replay import FACTS, HERE, PROJECTIONS, SharedOracle, cases_from, clean, create_table, replace_rows
from schema import CONTEXT_COLUMNS, SCHEMA
from scope_schema import SCOPE_SCHEMA


def temporary_table(conn, name, columns):
    definition = ', '.join(f'"{key}" {kind}' for key, kind in columns.items())
    conn.execute(f'CREATE TEMP TABLE {name} ({definition})')


def pool_manifest(cases):
    value = [{'name':case.name,'facts':case.facts,'scopes':case.scopes,'expected':case.expected} for case in cases]
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def seed_pool(database, cases):
    if Path(database).exists():
        raise FileExistsError('use a NEW owned oracle pool')
    started = time.perf_counter()
    with connect(database) as conn:
        pool = SharedOracle(conn, cases)
        create_table(conn, 'global_object_signatures', {'kind':'VARCHAR','oid':'VARCHAR','fingerprint':'VARCHAR'})
        rows = [{'kind':kind,'oid':oid,'fingerprint':value} for (kind,oid),value in pool.signatures.items()]
        replace_rows(conn,'global_object_signatures',{'kind':'VARCHAR','oid':'VARCHAR','fingerprint':'VARCHAR'},rows)
        conn.execute('CREATE TABLE immutable_pool_metadata (fingerprint VARCHAR, cases INTEGER)')
        conn.execute('INSERT INTO immutable_pool_metadata VALUES (?,?)',[pool_manifest(cases),len(cases)])
    return time.perf_counter()-started


class ConnectionOracle(SharedOracle):
    """Each worker owns its connection and all mutable TEMP state.

    Subclass only reuses activation/admission/SELECT algorithms; no native constructors
    or repository handles are involved. Persistent pool is opened read-only.
    """
    def __init__(self, conn):
        self.conn = conn
        self.materialize_scopes = True
        self.case_view_kind = 'TEMP VIEW'
        self.signatures = {(kind,oid):value for kind,oid,value in
                           conn.execute('SELECT * FROM main.global_object_signatures').fetchall()}
        self.scope_definitions = {}
        for name in ('active_objects','roots','request_contexts'):
            columns = SCHEMA['objects'] if name=='active_objects' else SCHEMA['roots'] if name=='roots' else CONTEXT_COLUMNS
            temporary_table(conn,name,columns)
        for name, columns in SCOPE_SCHEMA.items():
            temporary_table(conn,name,columns)
        for name in FACTS:
            if name == 'objects':
                condition = 'o.kind=t.kind AND o.oid=t.oid'
            elif name == 'edges':
                condition = 'o.kind=t.src_kind AND o.oid=t.src'
            else:
                kind,column = OWNERS[name]
                condition = f"o.kind='{kind}' AND o.oid=t.{column}"
            conn.execute(f'CREATE TEMP VIEW {name} AS SELECT t.* FROM main.global_{name} t JOIN active_objects o ON {condition}')
        conn.execute("CREATE TEMP VIEW capsules AS SELECT t.* FROM main.global_capsules t JOIN active_objects o ON o.kind='dag' AND o.oid=t.dag")
        # All dependent views are TEMP too, never bound to another connection's state.
        for name in ('reuse_checks.sql','paired_checks.sql','selection_checks.sql'):
            sql = (HERE/name).read_text().replace('CREATE OR REPLACE VIEW','CREATE OR REPLACE TEMP VIEW')
            conn.execute(sql)
            for statement, view in re.findall(r'(CREATE OR REPLACE TEMP VIEW (\w+)\s+AS\s+.*?;)', sql, flags=re.S):
                self.scope_definitions[view] = statement
        for name,column in PROJECTIONS.items():
            conn.execute(f"CREATE OR REPLACE TEMP VIEW {name} AS SELECT t.* FROM main.global_{name} t "
                         f"JOIN active_objects o ON o.kind='dag' AND o.oid=t.{column}")
        conn.execute("CREATE OR REPLACE TEMP VIEW h_ancestry AS SELECT t.* FROM main.global_h_ancestry t "
                     "JOIN active_objects d ON d.kind='commit' AND d.oid=t.descendant "
                     "JOIN active_objects a ON a.kind='commit' AND a.oid=t.ancestor")

    def activate(self, case):
        # Atomic TEMP-state activation; failed admission/load cannot leak a half case.
        self.conn.execute('BEGIN')
        try:
            super().activate(case)
            self.conn.execute('COMMIT')
        except BaseException:
            self.conn.execute('ROLLBACK')
            raise


def reader_connection(database):
    return duckdb.connect(str(database), read_only=True, config={'threads':2})


def run_worker(database, cases, worker):
    started = time.perf_counter()
    results = []
    with reader_connection(database) as conn:
        oracle = ConnectionOracle(conn)
        initialization = time.perf_counter()-started
        for case in cases:
            begin = time.perf_counter()
            result = oracle.check(case)
            results.append({'case':case.name,'seconds':time.perf_counter()-begin,**result})
            if not clean(result):
                raise AssertionError('connection-local oracle disagrees: '+case.name)
    return {'worker':worker,'initialization_seconds':initialization,'seconds':time.perf_counter()-started,'results':results}


def run_workload(database, cases, workers):
    started = time.perf_counter()
    # Static round-robin makes the executed case set explicit and exactly-once.
    chunks = [cases[index::workers] for index in range(workers)]
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='oracle-reader') as executor:
        futures = [executor.submit(run_worker,database,chunk,index) for index,chunk in enumerate(chunks)]
        results = [future.result() for future in futures]
    elapsed = time.perf_counter()-started
    actual = [row['case'] for worker in results for row in worker['results']]
    if sorted(actual) != sorted(case.name for case in cases) or len(set(actual)) != len(cases):
        raise AssertionError('case scheduling incomplete or duplicate')
    return {'workers':workers,'elapsed_seconds':elapsed,'case_count':len(actual),'worker_results':results}


def capacity():
    import os
    cpus = sorted(os.sched_getaffinity(0))
    cores = set()
    for cpu in cpus:
        root = Path(f'/sys/devices/system/cpu/cpu{cpu}/topology')
        cores.add(((root/'physical_package_id').read_text().strip(),(root/'core_id').read_text().strip()))
    memory = {line.split(':')[0]:line.split(':')[1].strip() for line in Path('/proc/meminfo').read_text().splitlines()}
    available = int(memory['MemAvailable'].split()[0])*1024
    group = Path('/sys/fs/cgroup') / Path('/proc/self/cgroup').read_text().strip().split('::',1)[1].lstrip('/')
    quotas, limits = [], []
    while True:
        if (group/'cpu.max').exists():
            quota,period = (group/'cpu.max').read_text().split()
            if quota!='max': quotas.append(max(1,int(quota)//int(period)))
        if (group/'memory.max').exists():
            limit = (group/'memory.max').read_text().strip()
            if limit!='max':
                current = int((group/'memory.current').read_text())
                limits.append(max(0,int(limit)-current))
        if group==Path('/sys/fs/cgroup'): break
        group = group.parent
    allocatable = min([available,*limits])
    memory_workers = max(0,(allocatable-1024**3)//1024**3)
    cap = min([4,len(cores),*quotas,memory_workers])
    return {'affinity_logical':cpus,'physical_cores':len(cores),'quota_workers':quotas,
            'available_memory_bytes':available,'allocatable_memory_bytes':allocatable,
            'worker_cap':cap,'note':'bounded Linux-host probe; 1GiB reserve+1GiB per reader, not a measured maximum guarantee'}


def trial(evidence, output):
    output = Path(output)
    output.mkdir(parents=True,exist_ok=False)
    cases = cases_from(evidence)
    admission = capacity()
    (output/'capacity.json').write_text(json.dumps(admission,indent=2)+'\n')
    if admission['worker_cap']<1:
        raise RuntimeError('insufficient admitted resources')
    database = output/'pool.duckdb'
    setup = seed_pool(database,cases)
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    rounds = []
    for workers in (1,2,4):
        if workers>admission['worker_cap']: continue
        result = run_workload(database,cases,workers)
        result['including_pool_setup_seconds'] = setup+result['elapsed_seconds']
        (output/f'workers-{workers}.json').write_text(json.dumps(result,indent=2)+'\n')
        rounds.append({key:value for key,value in result.items() if key!='worker_results'})
    after = hashlib.sha256(database.read_bytes()).hexdigest()
    assert before==after, 'readers changed persistent oracle pool'
    assert 'daggerml' not in sys.modules
    report = {'setup_seconds':setup,'capacity':admission,'rounds':rounds,'pool_unchanged':True,
              'pool_sha256':before,'input_fingerprint':pool_manifest(cases),'dml_imported':False,
              'qualification':'single 1/2/4 retained-fact oracle trials; no suite/portability guarantee'}
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    print(json.dumps(trial(sys.argv[1],sys.argv[2]),indent=2))
