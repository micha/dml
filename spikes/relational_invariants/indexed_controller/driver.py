"""Thin fixed profile adapter; reuse original Store/keys/artifacts unchanged."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]));__package__='indexed_controller'
    legacy_path=Path(__file__).resolve().parents[2]/'base/controller/code'
    if legacy_path.is_dir():sys.path.insert(0,str(legacy_path))

from incremental.artifacts import describe,finalize
from incremental.identity import FORMAT,canonical,digest,key
from incremental.records import Store
from incremental.stages import load_dml
from incremental.driver import PYTHON,environment,LIMITS
from .pins import prepare,verify


def envelope(pins,stage,*,candidate='A',variant=None,upstream=None):
    if candidate not in ('A','B'):raise ValueError('unsupported candidate')
    dependencies={'wrapper':pins['wrapper'],'runtime':pins['runtime_digest']}
    context={'profile':'indexed-original16-v1','cases':16}
    if stage=='E':dependencies.update(candidate=pins['payloads'][candidate],exercise=pins['payloads']['A'])
    else:
        if upstream is None or len(upstream['roots'])!=1:raise ValueError('one pinned indexed publication required')
        dependencies.update(upstream_key=upstream['key'],upstream_artifact=upstream['digest'])
        context['roots']=upstream['roots']
        if stage=='P' and variant in ('P1','P2'):dependencies.update(normalizer=pins['payloads'][variant],decoder=pins['recorder'])
        elif stage=='C' and variant in ('C1','C2'):dependencies.update(checker=pins['payloads'][variant])
        else:raise ValueError('unsupported indexed stage variant')
    result={'format':FORMAT,'namespace':pins['namespace'],'stage':stage,'dependencies':dependencies,
            'context':context,'limits':dict(LIMITS)}
    key(result);return result


class Controller:
    def __init__(self,pins_path,directory,*,namespace,create=False):
        if not namespace.startswith('ACCEPTANCE/'):raise ValueError('explicit acceptance namespace required')
        self.pins_path=Path(pins_path).resolve();self.pins=verify(self.pins_path)
        self.directory=Path(directory).resolve()
        if create:self.directory.mkdir(parents=True,exist_ok=False);(self.directory/'artifacts').mkdir()
        dml=load_dml(Path(self.pins['root'])/'base/controller/daggerml',name='indexed_controller_dml')
        self.store=Store(dml,self.directory/'controller.dml',self.directory/'artifacts',namespace,create=create)

    def result(self,terminal,request,fresh):
        _,q,outcome,reference,artifact=self.store.terminal(terminal)
        path=self.directory/'artifacts'/reference['name']
        roots=[]
        if outcome['status']=='success' and artifact['stage'] in ('E','P'):
            roots=json.loads((path/('evidence.json' if artifact['stage']=='E' else 'roots.json')).read_bytes())['roots']
        return {'request':str(request),'terminal':str(terminal),'fresh':fresh,'key':q['key'],
                'name':reference['name'],'digest':reference['sha256'],'stage':artifact['stage'],'roots':roots,'status':outcome['status']}

    def stage(self,stage,*,candidate='A',variant=None,upstream=None,fresh=False):
        verify(self.pins_path)
        if upstream is not None:
            terminal=self.store.dml.ObjectId.from_hex(upstream['terminal'])
            _,q,_,reference,artifact=self.store.terminal(terminal)
            if (artifact['stage']!=('E' if stage=='P' else 'P') or q['key']!=upstream['key']
                    or reference!={'name':upstream['name'],'sha256':upstream['digest']}
                    or self.result(terminal,terminal,False)['roots']!=upstream['roots']):
                raise ValueError('upstream publication/producer authority differs')
        inputs=envelope(self.pins,stage,candidate=candidate,variant=variant,upstream=upstream)
        request,_=self.store.request(inputs,'fresh' if fresh else 'reuse')
        reuse=None if fresh else self.store.reuse(request)
        if reuse is not None:return self.result(reuse[0],request,False)
        initial,producer,_=self.store.begin(request)
        name='attempt-'+producer.rsplit('-',1)[-1]
        parent=self.directory/'artifacts';partial=parent/(name+'.partial');partial.mkdir()
        job={'pins':str(self.pins_path),'stage':stage,'candidate':candidate,'variant':variant,
             'producer':producer,'key':key(inputs),'output':str(partial),
             'upstream':None if upstream is None else str(parent/upstream['name'])}
        job_path=self.directory/(name+'.job.json');job_path.write_bytes(canonical(job))
        command=[PYTHON,'-I','-B',str(Path(self.pins['root'])/'code/indexed_controller/stages.py'),str(job_path)]
        with (partial/'stdout.log').open('wb') as stdout,(partial/'stderr.log').open('wb') as stderr:
            process=subprocess.Popen(command,cwd=self.directory,env=environment(self.pins,self.directory),
                                     stdout=stdout,stderr=stderr,start_new_session=True)
            owner={'pid':process.pid,'group':process.pid,'command':command,'producer':producer}
            (self.directory/(name+'.owner.json')).write_bytes(canonical(owner))
            code=process.wait()
        owner['wait_exit']=code;(self.directory/(name+'.owner.json')).write_bytes(canonical(owner))
        status='success' if code==0 else 'rejected' if stage=='C' and code==1 and (partial/'verdict.json').is_file() else 'error'
        if status!='error':
            receipt=json.loads((partial/'receipt.json').read_bytes())
            expected_payload=candidate if stage=='E' else variant
            expected_package=(Path(self.pins['root'])/candidate/'python/daggerml/daggerml' if stage=='E' else
                              Path(self.pins['root'])/'base/controller/daggerml')/'__init__.py'
            entry={'E':'exercise.py','P':'project.py','C':'check.py'}[stage]
            if (receipt['key']!=job['key'] or receipt['stage']!=stage or receipt['producer']!=producer
                or receipt['process']!={'pid':process.pid,'parent':os.getpid(),'group':process.pid}
                or receipt['payload']!=expected_payload or receipt['package']!=str(expected_package)
                or receipt['core_sha256']!=self.pins['core_sha256'] or receipt['runtime']!=self.pins['runtime_digest']
                or receipt['python']!=PYTHON or receipt['entry_sha256']!=digest((Path(self.pins['root'])/expected_payload/
                    'spikes/relational_invariants/shared_existing'/entry).read_bytes())
                or len(receipt['children'])!={'E':0,'P':1,'C':16}[stage]
                or any(c['wait_exit']!=0 or c['command'][0]!=self.pins['runtime']['duckdb'] for c in receipt['children'])):
                raise ValueError('actual indexed stage receipt/ownership/source differs')
        artifact=describe(partial,stage=stage,key=key(inputs),producer=producer,dependencies=inputs['dependencies'],status=status,exit_code=code)
        fingerprint=finalize(partial,parent/name,artifact)
        terminal,_=self.store.finish(initial,name,fingerprint)
        result=self.result(terminal,request,True)
        if status=='error':raise RuntimeError('indexed stage error; retain raw evidence and STOP: '+name)
        return result

    def chain(self,candidate,projection,checker,*,fresh=False):
        e=self.stage('E',candidate=candidate,fresh=fresh)
        p=self.stage('P',variant=projection,upstream=e,fresh=fresh)
        c=self.stage('C',variant=checker,upstream=p,fresh=fresh)
        if c['status']!='success':raise ValueError('indexed invariant agreement failed; STOP')
        return {'E':e,'P':p,'C':c}


def story(pins_path,directory):
    namespace='ACCEPTANCE/indexed-original16-v1'
    controller=Controller(pins_path,directory,namespace=namespace,create=True);rows=[]
    configs=[('A','P1','C1',False),('A','P1','C1',False),('A','P1','C2',False),
             ('A','P2','C2',False),('B','P2','C2',False),('B','P2','C2',True)]
    for number,(candidate,p,c,fresh) in enumerate(configs,1):
        if number==2:
            output=controller.directory/'continuation.json'
            command=[PYTHON,'-I','-B',str(Path(controller.pins['root'])/'code/indexed_controller/driver.py'),
                     'continue',str(controller.pins_path),str(controller.directory)]
            with (controller.directory/'continuation.stdout').open('wb') as stdout,(controller.directory/'continuation.stderr').open('wb') as stderr:
                env=environment(controller.pins,controller.directory)
                process=subprocess.Popen(command,env=env,stdout=stdout,stderr=stderr)
                owner={'pid':process.pid,'command':command};code=process.wait();owner['wait_exit']=code
                (controller.directory/'continuation.owner.json').write_bytes(canonical(owner))
            if code!=0:raise ValueError('fresh-process continuation failed; STOP')
            row=json.loads(output.read_bytes())
        else:row=controller.chain(candidate,p,c,fresh=fresh)
        rows.append(row);(controller.directory/'observed-rounds.json').write_bytes(canonical(rows))
        if number in (1,3,4,5):
            for result in row.values():
                if result['fresh']:controller.store.adopt(controller.store.dml.ObjectId.from_hex(result['terminal']))
    bits=[tuple(int(row[s]['fresh']) for s in ('E','P','C')) for row in rows]
    if bits!=[(1,1,1),(0,0,0),(0,0,1),(0,1,1),(1,1,1),(1,1,1)]:raise ValueError('fresh stage matrix differs')
    bkey=envelope(controller.pins,'E',candidate='B')
    if str(controller.store.selected(bkey))!=rows[4]['E']['terminal']:raise ValueError('fresh auto-adopted E')
    basis=controller.store.head();controller.store.fork('explicit-new-E',basis)
    controller.store.adopt(controller.store.dml.ObjectId.from_hex(rows[5]['E']['terminal']),branch='explicit-new-E',expected=basis)
    if str(controller.store.selected(bkey))!=rows[4]['E']['terminal']:raise ValueError('sibling changed old choice')
    result={'rounds':rows,'requests':18,'fresh':{'E':3,'P':4,'C':5},'reused':6,'continued_in_fresh_process':True}
    (controller.directory/'result.json').write_bytes(canonical(result));return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['prepare','story','continue']);parser.add_argument('source',type=Path);parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    if args.mode=='prepare':print(canonical({'namespace':prepare(args.source,args.destination)['namespace']}).decode())
    elif args.mode=='story':print(canonical(story(args.source,args.destination)).decode())
    else:
        controller=Controller(args.source,args.destination,namespace='ACCEPTANCE/indexed-original16-v1')
        row=controller.chain('A','P1','C1')
        if any(result['fresh'] for result in row.values()):raise ValueError('continuation unexpectedly executed a stage')
        (controller.directory/'continuation.json').write_bytes(canonical(row));print(canonical(row).decode())
