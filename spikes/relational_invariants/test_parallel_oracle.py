"""Connection-local TEMP-state isolation on SAME frozen oracle facts."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
from pathlib import Path
import sys
from threading import Barrier

import duckdb
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from oracle_replay import cases_from, clean, scope_verdicts
from parallel_oracle import ConnectionOracle, reader_connection, run_workload, seed_pool

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def pool(tmp_path_factory):
    cases=cases_from(ROOT/'build/relational-spike/authority-final')
    database=tmp_path_factory.mktemp('immutable-oracle')/'pool.duckdb'
    seed_pool(database,cases)
    return database,cases


def test_all44_cases_two_connections_match_and_leave_pool_unchanged(pool):
    database,cases=pool
    before=hashlib.sha256(database.read_bytes()).hexdigest()
    result=run_workload(database,cases,2)
    assert result['case_count']==44
    assert all(clean(row) for worker in result['worker_results'] for row in worker['results'])
    assert hashlib.sha256(database.read_bytes()).hexdigest()==before


def test_concurrent_distinct_cases_cannot_overwrite_each_others_temp_state(pool):
    database,cases=pool
    good=next(case for case in cases if 'test_existing_value_hit[same-inputs]' in case.name)
    bad=next(case for case in cases if 'test_existing_selection_validation_shapes[S-role]' in case.name)
    gate=Barrier(2,timeout=20)
    def read(case):
        with reader_connection(database) as conn:
            oracle=ConnectionOracle(conn)
            oracle.activate(case)
            gate.wait()
            result=scope_verdicts(conn,case)
            count=conn.execute('SELECT count(*) FROM active_objects').fetchone()[0]
            gate.wait()
            assert clean(result)
            assert count==len(case.facts['objects'])
            assert clean(scope_verdicts(conn,case))
            return count
    with ThreadPoolExecutor(max_workers=2) as workers:
        futures=[workers.submit(read,case) for case in (good,bad)]
        counts=[future.result() for future in futures]
    assert counts[0]!=counts[1]


def test_temp_mutation_in_one_connection_is_invisible_in_another(pool):
    database,cases=pool
    case=cases[0]
    with reader_connection(database) as first, reader_connection(database) as second:
        a,b=ConnectionOracle(first),ConnectionOracle(second)
        a.activate(case);b.activate(case)
        first.execute('DELETE FROM active_objects')
        assert a.availability_faults()
        assert not b.availability_faults()
        assert clean(scope_verdicts(second,case))


def test_persistent_pool_write_is_denied_but_temp_case_writes_work(pool):
    database,cases=pool
    with reader_connection(database) as conn:
        oracle=ConnectionOracle(conn)
        assert clean(oracle.check(cases[0]))
        with pytest.raises(duckdb.Error,match='read-only|read only|READ_ONLY'):
            conn.execute('DELETE FROM main.global_objects')


def test_failed_temp_activation_rolls_back_entire_previous_case(pool):
    database,cases=pool
    good=next(case for case in cases if 'test_existing_value_hit[same-inputs]' in case.name)
    malformed=deepcopy(good)
    malformed.scopes['candidate_scopes'][0]['job_document']='deliberate invalid JSON'
    with reader_connection(database) as conn:
        oracle=ConnectionOracle(conn)
        oracle.activate(good)
        before=scope_verdicts(conn,good)
        with pytest.raises(duckdb.ConversionException):
            oracle.activate(malformed)
        assert scope_verdicts(conn,good)==before
        assert conn.execute('SELECT count(*) FROM active_objects').fetchone()[0]==len(good.facts['objects'])


def test_altered_packet_remains_rejected_with_independent_connection(pool):
    database,cases=pool
    case=deepcopy(next(case for case in cases if 'test_existing_value_hit[same-inputs]' in case.name))
    key=next(key for key,value in case.expected.items() if value['kind']=='candidate' and value['verdict'] is True)
    row=next(row for row in case.scopes['candidate_scopes'] if row['scope_id']==int(key))
    row['bundle_root']='f'*32
    with reader_connection(database) as conn:
        result=ConnectionOracle(conn).check(case)
        assert key in result['disagreements'] and result['actual'][key] is False
