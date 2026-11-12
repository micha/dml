import copy
import hashlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run import bootstrap
bootstrap()
import daggerml as d
from normalizer import extract
from shared_index.check import pool
from shared_index.project import Facts
from shared_existing.exercise import exercise,SPECS
from shared_existing.project import normalize,catalog
from shared_existing.check import check_case,assert_agreement,case_sql


@pytest.fixture(scope='module')
def batch(tmp_path_factory):
    directory=tmp_path_factory.mktemp('shared-existing')
    handle=exercise(directory/'exercise',namespace=directory.name+'/original16')
    rows,projected,stats=normalize(handle['repository'],handle['publication'],directory/'normalized')
    database=pool(rows,directory/'pool')
    return directory,handle,rows,projected,stats,database


@pytest.mark.parametrize('number',range(16),ids=[s['label'] for s in SPECS])
def test_original_assertion_and_independent_scoped_predicate_agree(batch,number):
    directory,_,rows,projected,_,database=batch
    case=projected['cases'][number]
    result=check_case(database,rows,case,directory/'checks'/f'case-{number+1:03d}')
    assert_agreement(case,result)
    assert result['accepted']==(number==15)
    if number!=15:assert result['faults']


def test_publication_first_parent_original_commits_and_native_context(batch):
    _,handle,rows,projected,stats,_=batch
    facts=Facts(rows)
    assert len(projected['cases'])==16
    assert projected['first_parent_chain']==handle['publications']
    assert sum(len(c['calls']) for c in projected['cases'])==49
    assert len({c['occurrence'] for c in projected['cases']})==16
    for number,case in enumerate(projected['cases'],1):
        assert facts.parents(handle['publications'][number])==[handle['publications'][number-1],case['target']]
        assert facts.tree(case['target'])['exercise-context']==case['context']
        assert ('dag',case['subject']) in {tuple(r) for r in case['membership']}
    assert stats['unique_record_reads']==len(rows['objects'])


@pytest.mark.parametrize('number',[0,5,15])
def test_old_index_snapshot_excludes_future_existing_tests(batch,number):
    _,handle,_,_,_,_=batch
    root=handle['publications'][number]
    rows,_=extract({'repository':handle['repository'],'roots':[root]})
    assert len(catalog(rows,root)['cases'])==number


def test_recorded_and_expected_verdicts_never_change_query(batch,tmp_path):
    _,_,_,projected,_,_=batch
    case=projected['cases'][0]
    changed=copy.deepcopy(case)
    changed['observed']=True;changed['expected']=True;changed['spec']['fault']='pretend-success'
    assert case_sql(case,tmp_path/'rows')==case_sql(changed,tmp_path/'rows')


def test_foreign_case_membership_is_not_adopted(batch,tmp_path):
    _,_,rows,projected,_,database=batch
    case=copy.deepcopy(projected['cases'][-1])
    case['membership']=sorted([list(r) for r in set(map(tuple,case['membership']))|set(map(tuple,projected['cases'][0]['membership']))])
    with pytest.raises(ValueError,match='availability'):
        check_case(database,rows,case,tmp_path/'never')


def test_original_source_bytes_and_fixture_assertion_completion(batch):
    _,_,_,projected,_,_=batch
    import test_builtin,test_builtin_profiles
    for case in projected['cases']:
        assert case['captures']['assertions']==hashlib.sha256(Path(test_builtin_profiles.__file__).read_bytes()).hexdigest()
        assert case['captures']['success_assertions']==hashlib.sha256(Path(test_builtin.__file__).read_bytes()).hexdigest()
        assert case['observed']==case['expected']
        assert case['function'].startswith('test_builtin')
