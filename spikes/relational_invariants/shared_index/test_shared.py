from collections import Counter
import copy
import hashlib
import re
import subprocess
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run import bootstrap
bootstrap()
import daggerml as dml
from daggerml.transfer import export_commit, import_commit
from normalizer import extract
from schema import SCHEMA
from shared_index.exercise import exercise, publication, validate_cases
from shared_index.project import Facts, catalog, normalize
from shared_index.check import assert_expected, case_sql, check_case, pool


@pytest.fixture(scope='module')
def batch(tmp_path_factory):
    directory=tmp_path_factory.mktemp('shared-index')
    handle=exercise(directory/'batch',namespace='CONTROL/shared-index-focused-or-final')
    rows,projected,stats=normalize(handle['repository'],handle['publication'],directory/'normalized')
    return directory,handle,rows,projected,stats


@pytest.fixture(scope='module')
def database(batch):
    directory,_,rows,_,_=batch
    return pool(rows,directory/'pool')


def test_single_repo_empty_P0_and_publication_first_parent_chain(batch):
    _,handle,rows,projected,_=batch
    facts=Facts(rows)
    assert projected['completed_cases']==4 and projected['declared_cases']==4
    assert projected['first_parent_chain']==handle['publication_chain']
    assert facts.index(handle['publication_chain'][0])[1]=={}
    assert facts.parents(handle['publication_chain'][0])==[]
    for number,case in enumerate(projected['cases'],1):
        assert facts.parents(handle['publication_chain'][number])==[handle['publication_chain'][number-1],case['target']]
        assert facts.parents(case['target'])==case['roots'][1:]
        assert case['calls']==6
    assert sum(c['calls'] for c in projected['cases'])==24


def test_equal_values_shared_content_distinct_fresh_occurrences_and_targets(batch):
    _,_,rows,projected,_=batch
    left,right=projected['cases'][:2]
    assert left['parameters']==right['parameters'] and left['context']==right['context']
    assert left['occurrence']!=right['occurrence'] and left['target']!=right['target']
    assert left['roots'][0]==right['roots'][0]  # shared immutable fixture
    facts=Facts(rows)
    assert facts.tree(left['roots'][1])['trace']==facts.tree(right['roots'][1])['trace']
    assert sum(len(c['membership']) for c in projected['cases'])>len(rows['objects'])


@pytest.mark.parametrize('number',[0,1,2])
def test_old_pinned_publication_ignores_future_physically_present_cases(batch,number):
    _,handle,_,_,_=batch
    publication_id=handle['publication_chain'][number]
    rows,_=extract({'repository':handle['repository'],'roots':[publication_id]})
    prefix=catalog(rows,publication_id)
    assert prefix['completed_cases']==number
    assert prefix['first_parent_chain']==handle['publication_chain'][:number+1]


def test_extraction_reads_each_typed_object_once_and_is_read_only(batch,monkeypatch):
    _,handle,_,_,stats=batch
    counted=Counter()
    original=dml.Transaction.get_record
    def get_record(tx,kind,oid):
        counted[kind,str(oid)]+=1
        return original(tx,kind,oid)
    monkeypatch.setattr(dml.Transaction,'get_record',get_record)
    data=Path(handle['repository'])/'data.mdb'
    before=hashlib.sha256(data.read_bytes()).hexdigest()
    _,actual=extract({'repository':handle['repository'],'roots':[handle['publication']]})
    assert len(counted)==actual['unique_record_reads']==stats['unique_record_reads']
    assert set(counted.values())=={1}
    assert hashlib.sha256(data.read_bytes()).hexdigest()==before


def test_ref_operations_are_not_needed_in_exercise_or_import(tmp_path,monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError('shared exerciser must never use mutable refs')
    for name in ('create_ref','update_ref','get_ref'):
        monkeypatch.setattr(dml.Transaction,name,forbidden)
    handle=exercise(tmp_path/'empty',namespace='CONTROL/empty',cases=[])
    assert catalog(extract({'repository':handle['repository'],'roots':[handle['publication']]})[0],handle['publication'])['completed_cases']==0


def test_native_parent_export_retains_indexed_contexts_and_every_fork(batch,tmp_path):
    _,handle,_,projected,_=batch
    root=dml.ObjectId.from_hex(handle['publication'])
    raw=export_commit(handle['repository'],commit=root)
    destination=tmp_path/'imported'
    with dml.Repository(destination,create=True):pass
    imported=import_commit(destination,raw)
    assert imported.commit==root and export_commit(destination,commit=root)==raw
    rows,_=extract({'repository':str(destination),'roots':[str(root)]})
    assert catalog(rows,str(root))==projected
    facts=Facts(rows)
    for case in projected['cases']:
        assert ('commit',case['target']) in facts.objects
        assert all(('commit',root) in facts.objects for root in case['roots'])
        assert ('dag',case['context']) in facts.objects


def replace_scalar(rows,facts,dag,name,value):
    node=facts.nodes[facts.fields[dag][name]]
    for row in rows['datums']:
        if row['oid']==node['target']:
            row['scalar']=value
            return
    raise AssertionError('fixture scalar missing')


@pytest.mark.parametrize('fault',['target','roots','context-role','context-value','limits','occurrence','calls','parent-order','lost-prefix'])
def test_catalog_malformed_or_cross_case_authority_fails_closed(batch,fault):
    _,handle,original,projected,_=batch
    rows=copy.deepcopy(original)
    facts=Facts(rows)
    case=projected['cases'][1]
    description=case['description']
    if fault=='target':
        replace_scalar(rows,facts,description,'target','f'*32)
    elif fault=='roots':
        node=facts.nodes[facts.fields[description]['roots']]
        first=next(r for r in rows['edges'] if r['src_kind']=='datum' and r['src']==node['target'] and r['label']=='item-0')
        for datum in rows['datums']:
            if datum['oid']==first['dst']:datum['scalar']='f'*32
    elif fault=='context-role':
        replace_scalar(rows,facts,case['context'],'role','wrong-role')
    elif fault=='context-value':
        replace_scalar(rows,facts,case['context'],'parameters',b'{"value":999}'.hex())
    elif fault=='limits':
        replace_scalar(rows,facts,case['context'],'limits',b'{}'.hex())
    elif fault=='occurrence':
        replace_scalar(rows,facts,description,'occurrence',projected['cases'][0]['occurrence'])
    elif fault=='calls':
        observations=facts.field(description,'observations','subdag')
        replace_scalar(rows,facts,observations,'calls','0')
    elif fault=='parent-order':
        edges=[r for r in rows['edges'] if r['src_kind']=='commit' and r['src']==handle['publication'] and r['label'].startswith('parent-')]
        edges[0]['dst'],edges[1]['dst']=edges[1]['dst'],edges[0]['dst']
    else:
        index_dag=facts.tree(handle['publication'])['exercise-index']
        rows['fields']=[r for r in rows['fields'] if not(r['dag']==index_dag and r['name']=='case-001')]
    with pytest.raises((ValueError,KeyError)):
        catalog(rows,handle['publication'])


def test_shared_bad_graph_does_not_poison_other_case_checks(batch,database):
    directory,_,rows,projected,_=batch
    results=[]
    for case in projected['cases']:
        result=check_case(database,rows,case)
        assert_expected(case,result)
        results.append(result)
    assert [r['accepted'] for r in results]==[True,True,False,True]
    bad=projected['cases'][2]['bad_operation']
    assert all(bad not in {r['subject'] for r in result['violations']} for result in (results[0],results[1],results[3]))
    assert {r['subject'] for r in results[2]['violations'] if r['invariant']=='map_get_value'}=={bad}


def test_supplied_case_availability_cannot_include_another_case(batch,database):
    _,_,rows,projected,_=batch
    case=copy.deepcopy(projected['cases'][0])
    case['membership']=sorted([list(item) for item in set(map(tuple,case['membership']))|set(map(tuple,projected['cases'][2]['membership']))])
    with pytest.raises(ValueError,match='availability differs'):
        check_case(database,rows,case)


def test_prior_or_expected_verdict_never_changes_invariant_sql(batch):
    _,_,_,projected,_=batch
    case=projected['cases'][0]
    altered=copy.deepcopy(case)
    altered['expectations']['outcome']='reject'
    altered['expectations']['invariant']='arbitrary'
    altered['old_verdict']=False
    assert case_sql(altered)==case_sql(case)


def test_warning_stdout_is_retained_but_never_parsed_as_result(tmp_path,monkeypatch):
    # UNIT transport control only: no native exercise, real SQL or assertion-verdict proof.
    rows={name:[] for name in SCHEMA}
    target='a'*32
    rows['objects']=[{'kind':'commit','oid':target}]
    rows['commits']=[{'oid':target,'tree_id':'b'*32}]
    case={'target':target,'membership':[['commit',target]],'roots':[target],
          'sources':['c'*32,'d'*32],'expectations':{'positions':[None]},
          'label':'CONTROL/transport','occurrence':'CONTROL/transport-1'}
    database=tmp_path/'CONTROL-not-a-real-database'
    database.write_bytes(b'CONTROL transport mock, not SQL evidence')
    class FakeProcess:
        pid=999991  # Explicit UNIT fake, never inventoried as an actual process.
        returncode=0
        def __init__(self,*args,**kwargs):pass
        def communicate(self,sql):
            path=re.search(r" TO '([^']+)' \(FORMAT JSON\)",sql).group(1)
            Path(path).write_text('')
            return '\x1b[90mWARNING: keep this diagnostic\x1b[00m\n[]\n',''
    monkeypatch.setattr(subprocess,'Popen',FakeProcess)
    result=check_case(database,rows,case,output_directory=tmp_path/'transport-output')
    assert result['accepted'] and result['violations']==[]
    assert 'WARNING: keep this diagnostic' in (tmp_path/'transport-output/stdout.log').read_text()
    assert (tmp_path/'transport-output/rows.jsonl').read_bytes()==b''


def test_before_commit_publication_failure_preserves_old_index(batch):
    _,handle,_,projected,_=batch
    previous=dml.ObjectId.from_hex(handle['publication'])
    with pytest.raises(ValueError):
        with dml.Repository(handle['repository']) as repo,repo.write() as tx:
            run=dict(tx.get_tree(tx.get_commit(previous).tree))['exercise-run']
            description=dml.ObjectId.from_hex(projected['cases'][0]['description'])
            publication(tx,previous,dml.ObjectId.from_hex(projected['cases'][0]['target']),run,{'case-001':description})
            raise ValueError('deliberate before-commit interruption')
    rows,_=extract({'repository':handle['repository'],'roots':[str(previous)]})
    assert catalog(rows,str(previous))['completed_cases']==4


def test_missing_root_retains_explicit_projection_error_not_empty_success(batch,tmp_path):
    _,handle,_,_,_=batch
    output=tmp_path/'missing'
    with pytest.raises(dml.NotFoundError):
        normalize(handle['repository'],'f'*32,output)
    assert (output/'projection-error.json').exists()
    assert not (output/'catalog.json').exists()


@pytest.mark.parametrize('case',[{'label':'a','value':True,'fault':False},{'label':'a','value':42,'fault':'yes'}])
def test_case_schema_rejects_ambiguous_types(case):
    with pytest.raises(ValueError):validate_cases([case])
