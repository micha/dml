"""Call original16 assertion bodies unchanged; no-ref shared fixture/publication seam."""

import hashlib
from pathlib import Path
import sys

import pytest
import daggerml as d
from daggerml import builtin as b, local
from incremental.identity import canonical
from shared_index.exercise import role_dag, literal, id_list

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tests/python'))
import test_builtin as original
import test_builtin_profiles as profiles

FAULTS=['source-name','source-node','source-value','source-shape','source-root','operation-value',
        'operation-role','operation-args','operation-func','argument-value','argument-key',
        'entry-source','entries-shape','trace-shape','trace-primitive']
SPECS=[{'label':fault,'function':'strict-profile','fault':fault} for fault in FAULTS]+[
    {'label':'equal-nested-sources','function':'equal-sources','fault':None}]
INDEX='existing-exercise-index-v1'
RUN='existing-exercise-run-v1'
DESC='existing-exercise-description-v1'
CTX='existing-exercise-context-v1'
OBS='existing-exercise-observations-v1'
LIMITS={'cases':16,'roots':4,'builtin_reached':64,'positions':16,'arguments':16,'extract_objects':10000}


def source_capture():
    paths={'assertions':Path(profiles.__file__),'success_assertions':Path(original.__file__),
           'fixture_adapter':Path(__file__),'builtin':Path(b.__file__),'native_core':Path(d._core.__file__)}
    return {name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in paths.items()}


def fixture(tx,path):
    values=tx.put_datum(d.Datum.list([tx.put_datum(13),tx.put_datum(29)]))
    nodes={'list':tx.put_literal(values),'same-list':tx.put_literal(values),'key':literal(tx,'measurements')}
    source=tx.put_dag(root=nodes['list'],bindings=nodes)
    second=tx.put_dag(root=nodes['list'],bindings={**nodes,'method':literal(tx,'different source')})
    bindings={name:b.put_binding(tx,source_uri='dml://source/builtin/'+suffix) for name,suffix in
              [('empty','map/empty/v1'),('insert','map/insert/v1'),('get1','map/get/v1'),
               ('get2','map/get/v2'),('index','list/get/v1')]}
    external=local.put_local_binding(tx,source=b'raise SystemExit(0)',interpreter=sys.executable,timeout_ms=10000)
    base=tx.put_commit(tx.put_tree({**bindings,'source':source,'second':second,'external':external}))
    return path,base,source,second,bindings,external


def publish_without_ref(tx,base,dag,name='scope'):
    entries=dict(tx.get_tree(tx.get_commit(base).tree))
    entries[name]=dag
    return tx.put_commit(tx.put_tree(entries),parents=(base,))


def recorded(state):
    path,base,_,_,bindings,_=state
    with d.Repository(path) as repo,repo.write() as tx:
        with b.Recorder(tx,commit=base) as rec:
            sample=original.construction(rec,state)
            inputs=rec.arguments({'sample':sample})
            ops=rec.operations(map_binding=bindings['get1'],list_binding=bindings['index'])
            measured=ops.map_get(sample,'measurements')
            dag,ledger=rec.dag(measured),rec.trace()
            commit=publish_without_ref(tx,base,ledger)
            full=rec.dag(inputs)
    return path,commit,dag,full,ledger


def exercise_case(state,spec):
    commits,observed,calls=[],[],[]
    inspector_commits={}
    depth=[0]
    old_put=d.Transaction.put_commit
    old_init=b.Inspector.__init__
    old_call=b.Recorder.call
    def put(tx,*args,**kwargs):
        commit=old_put(tx,*args,**kwargs)
        commits.append(str(commit))
        return commit
    def initialize(self,tx,*,commit):
        old_init(self,tx,commit=commit)
        inspector_commits[id(self)]=str(commit)
    def invoke(self,*args,**kwargs):
        returned=old_call(self,*args,**kwargs)
        calls.append({'func':args[0],'kind':returned.value.kind})
        return returned
    def wrapper(method,name):
        def call(self,subject,*args,**kwargs):
            top=depth[0]==0;depth[0]+=1
            try:
                result=method(self,subject,*args,**kwargs)
            except Exception as error:
                if top:observed.append({'method':name,'commit':inspector_commits[id(self)],
                    'subject':str(subject),'accepted':False,'error':type(error).__name__})
                raise
            else:
                if top:observed.append({'method':name,'commit':inspector_commits[id(self)],
                    'subject':str(subject),'accepted':True,'error':None})
                return result
            finally:depth[0]-=1
        return call
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(d.Transaction,'put_commit',put)
        patch.setattr(b.Inspector,'__init__',initialize)
        patch.setattr(b.Recorder,'call',invoke)
        for name in ('node','arguments','trace'):
            patch.setattr(b.Inspector,name,wrapper(getattr(b.Inspector,name),name))
        patch.setattr(original,'publish',publish_without_ref)
        if spec['function']=='strict-profile':
            setup=recorded(state)
            profiles.test_strict_native_source_argument_operation_and_trace_recomputation(setup,spec['fault'])
        else:
            original.test_equal_nested_collections_THIS_source_not_global_origin(state)
    if not commits or len(commits)+1>LIMITS['roots']:
        raise ValueError('original case commit census outside bounded profile')
    expected=spec['function']=='equal-sources'
    primary=[row for row in observed if row['commit']==commits[-1] and row['accepted']==expected]
    if not primary:raise ValueError('original primary inspection observation absent')
    return {'commits':commits,'primary':primary[-1],'observed':observed,'calls':calls,
            'original_assertion_completed':True,'expected':expected}


def index(tx,entries):
    return role_dag(tx,INDEX,{name:tx.put_subdag(desc) for name,desc in entries.items()})


def exercise(directory,*,namespace):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    path=directory/'repository'
    capture=source_capture();entries={};publications=[]
    with d.Repository(path,create=True) as repo,repo.write() as tx:
        state=fixture(tx,path)
        run=role_dag(tx,RUN,{'namespace':literal(tx,namespace),'specs':literal(tx,canonical(SPECS)),
                            'captures':literal(tx,canonical(capture)),'limits':literal(tx,canonical(LIMITS))})
        first=index(tx,{})
        previous=tx.put_commit(tx.put_tree({'exercise-index':first,'exercise-run':run}))
    publications.append(str(previous))
    (directory/'publication-000.json').write_bytes(canonical({'publication':str(previous)}))
    for number,spec in enumerate(SPECS,1):
        outcome=exercise_case(state,spec)
        occurrence=f'{namespace}/exercise-{number}'
        with d.Repository(path) as repo,repo.write() as tx:
            context=role_dag(tx,CTX,{'spec':literal(tx,canonical(spec)),
                'function':literal(tx,'test_builtin_profiles.test_strict_native_source_argument_operation_and_trace_recomputation'
                  if spec['function']=='strict-profile' else 'test_builtin.test_equal_nested_collections_THIS_source_not_global_origin'),
                'captures':literal(tx,canonical(capture)),'limits':literal(tx,canonical(LIMITS)),
                'method':literal(tx,outcome['primary']['method']),
                'subject':literal(tx,bytes.fromhex(outcome['primary']['subject'])),
                'expectations':literal(tx,canonical({'accepted':outcome['expected']}))})
            marker=role_dag(tx,'existing-exercise-occurrence-v1',{'occurrence':literal(tx,occurrence)})
            last=d.ObjectId.from_hex(outcome['commits'][-1])
            tree=dict(tx.get_tree(tx.get_commit(last).tree))
            tree.update({'exercise-context':context,'exercise-occurrence':marker})
            target=tx.put_commit(tx.put_tree(tree),parents=(last,))
            observations=role_dag(tx,OBS,{'assertion-completed':literal(tx,True),
                'validator-observations':literal(tx,canonical(outcome['observed'])),
                'calls':literal(tx,canonical(outcome['calls']))})
            roots=[state[1],*[d.ObjectId.from_hex(root) for root in outcome['commits']]]
            description=role_dag(tx,DESC,{'label':literal(tx,spec['label']),'occurrence':literal(tx,occurrence),
                'target':literal(tx,target.bytes),'roots':id_list(tx,roots),
                'context':tx.put_subdag(context),'observations':tx.put_subdag(observations)})
            entries[f'case-{number:03d}']=description
            latest=index(tx,entries)
            previous=tx.put_commit(tx.put_tree({'exercise-index':latest,'exercise-run':run}),parents=(previous,target))
        publications.append(str(previous))
        (directory/f'publication-{number:03d}.json').write_bytes(canonical({'publication':str(previous)}))
    handle={'repository':str(path.resolve()),'publication':str(previous),'publications':publications,'cases':len(entries)}
    (directory/'handle.json').write_bytes(canonical(handle))
    return handle
