"""Shared/materialized oracle boundaries over frozen facts only."""

from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from embedded import connect
from oracle_replay import SharedOracle, cases_from, clean, scope_verdicts

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'build/relational-spike/authority-final'


@pytest.fixture(scope='module')
def cached():
    cases = cases_from(EVIDENCE)
    with connect(':memory:') as conn:
        oracle = SharedOracle(conn, cases, materialize_scopes=True)
        yield oracle, cases


def hit_case(cases):
    return next(case for case in cases if 'test_existing_value_hit[same-inputs]' in case.name)


def test_all44_materialized_cases_match_original_scoped_verdicts(cached):
    oracle, cases = cached
    for case in cases:
        assert clean(oracle.check(case)), case.name


def test_switching_cases_restores_membership_scopes_and_cached_contexts(cached):
    oracle, cases = cached
    chosen = [hit_case(cases), cases[-1], cases[0], hit_case(cases)]
    for case in chosen:
        assert clean(oracle.check(case))
        assert oracle.conn.execute('SELECT count(*) FROM active_objects').fetchone()[0] == len(case.facts['objects'])


def test_global_fact_presence_does_not_supply_missing_case_availability(cached):
    oracle, cases = cached
    case = hit_case(cases)
    oracle.activate(case)
    datum = next(row['oid'] for row in case.facts['objects'] if row['kind']=='datum')
    assert oracle.conn.execute('SELECT count(*) FROM global_objects WHERE kind=? AND oid=?', ['datum',datum]).fetchone()[0] == 1
    oracle.conn.execute('DELETE FROM active_objects WHERE kind=? AND oid=?', ['datum',datum])
    assert oracle.availability_faults()
    assert oracle.conn.execute('SELECT count(*) FROM datums WHERE oid=?',[datum]).fetchone()[0] == 0


def test_ancestry_requires_available_ancestor_not_just_global_commit(cached):
    oracle, cases = cached
    case = hit_case(cases)
    oracle.activate(case)
    ancestor = oracle.conn.execute("SELECT ancestor FROM h_ancestry WHERE descendant<>ancestor LIMIT 1").fetchone()[0]
    assert oracle.conn.execute('SELECT count(*) FROM global_h_ancestry WHERE ancestor=?',[ancestor]).fetchone()[0] > 0
    oracle.conn.execute("DELETE FROM active_objects WHERE kind='commit' AND oid=?",[ancestor])
    assert oracle.conn.execute('SELECT count(*) FROM h_ancestry WHERE ancestor=?',[ancestor]).fetchone()[0] == 0
    assert oracle.availability_faults()


def test_conflicting_case_object_description_is_not_served_from_cache(cached):
    oracle, cases = cached
    case = deepcopy(hit_case(cases))
    datum = next(row for row in case.facts['datums'] if row['kind']=='i64')
    datum['scalar'] = '999'
    with pytest.raises(ValueError, match='descriptions disagree'):
        oracle.activate(case)


def test_packet_root_is_rechecked_not_cached_as_prior_success(cached):
    oracle, cases = cached
    case = deepcopy(hit_case(cases))
    scope_id = next(int(key) for key,value in case.expected.items() if value['kind']=='candidate' and value['verdict'] is True)
    row = next(row for row in case.scopes['candidate_scopes'] if row['scope_id']==scope_id)
    row['bundle_root'] = 'f'*32
    result = oracle.check(case)
    assert str(scope_id) in result['disagreements']
    assert result['actual'][str(scope_id)] is False


def test_header_claim_is_rechecked_in_fresh_scope(cached):
    oracle, cases = cached
    case = deepcopy(hit_case(cases))
    scope_id = next(int(key) for key,value in case.expected.items() if value['kind']=='candidate' and value['verdict'] is True)
    row = next(row for row in case.scopes['candidate_scopes'] if row['scope_id']==scope_id)
    import json
    receipt = json.loads(row['receipt_document'])
    receipt['token'] = '0'*32
    row['receipt_document'] = json.dumps(receipt,sort_keys=True,separators=(',',':'))
    result = oracle.check(case)
    assert str(scope_id) in result['disagreements']


def test_declared_intent_is_not_lost_in_shared_projections(cached):
    oracle, cases = cached
    case = deepcopy(hit_case(cases))
    row = next(row for row in case.scopes['resolution_scopes']
               if case.expected[str(row['scope_id'])]['verdict']=='reuse-selected')
    row['intent'] = 'urn:unsupported:purpose'
    result = oracle.check(case)
    assert str(row['scope_id']) in result['disagreements']
