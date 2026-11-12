"""Fixed original16 E/P/C stages, actual PID/CLI receipts and portable indexed authority."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys


def execute(job):
    pins=json.loads(Path(job['pins']).read_bytes());root=Path(pins['root']);out=Path(job['output'])
    sys.path.insert(0,str(root/'base/controller/code'))
    from incremental.identity import canonical,digest
    from incremental.stages import load_dml
    sys.path.insert(0,pins['runtime']['tools'])
    stage=job['stage'];payload=root/(job['candidate'] if stage=='E' else job['variant'])
    package=payload/'python/daggerml/daggerml' if stage=='E' else root/'base/controller/daggerml'
    dml=load_dml(package)
    parent=payload/'spikes/relational_invariants';sys.path.insert(0,str(parent))
    os.environ['DML_BIN']=str(payload/'build/spike-native/dml')  # import hint, NEVER CLI dispatch
    original=subprocess.Popen;children=[];cap={'E':0,'P':1,'C':16}[stage]
    def cli(command,*args,**kwargs):
        if type(command) is not list or command[0] not in ('duckdb',pins['runtime']['duckdb']) or len(children)>=cap:
            raise ValueError('stage child outside pinned finite SQL allowance')
        command=[pins['runtime']['duckdb'],*command[1:]]
        child=original(command,*args,**kwargs);children.append((child,command));return child
    def forbidden(*args,**kwargs):raise ValueError('indexed stage cannot activate network')
    subprocess.Popen=cli;socket.socket.connect=forbidden;socket.create_connection=forbidden
    result={'stage':stage,'producer':job['producer'],'key':job['key'],'payload':payload.name,
            'process':{'pid':os.getpid(),'parent':os.getppid(),'group':os.getpgrp()}}
    if stage=='E':
        from shared_existing.exercise import exercise
        from daggerml import transfer
        working=out.parent/(out.name+'.native-working')
        handle=exercise(working,namespace=job['producer'])
        bundle=transfer.export_commit(handle['repository'],commit=dml.ObjectId.from_hex(handle['publication']))
        (out/'publication.bundle').write_bytes(bundle)
        evidence={'publication':handle['publication'],'roots':[handle['publication']],
                  'bundle_sha256':digest(bundle),'cases':16,'source_occurrence':job['producer']}
        (out/'evidence.json').write_bytes(canonical(evidence))
        result.update(working=str(working),entry='shared_existing/exercise.py')
    elif stage=='P':
        from daggerml import transfer
        from shared_existing.project import normalize
        from shared_index.check import pool
        upstream=Path(job['upstream']);evidence=json.loads((upstream/'evidence.json').read_bytes())
        bundle=(upstream/'publication.bundle').read_bytes()
        if digest(bundle)!=evidence['bundle_sha256'] or evidence['cases']!=16:
            raise ValueError('indexed evidence boundary differs')
        working=out.parent/(out.name+'.native-working')
        with dml.Repository(working,create=True):pass
        imported=transfer.import_commit(working,bundle)
        if str(imported.commit)!=evidence['publication']:raise ValueError('imported publication differs')
        rows,catalog,stats=normalize(working,evidence['publication'],out/'normalized')
        if len(catalog['cases'])!=16:raise ValueError('incomplete indexed batch')
        pool(rows,out/'pool')
        (out/'roots.json').write_bytes(canonical({'roots':evidence['roots'],'cases':16}))
        result.update(working=str(working),typed_reads=stats['unique_record_reads'],entry='shared_existing/project.py')
    elif stage=='C':
        from schema import SCHEMA
        from shared_existing.check import check_case
        from shared_existing.project import catalog as reconstruct
        upstream=Path(job['upstream']);norm=upstream/'normalized'
        rows={name:[json.loads(line) for line in (norm/(name+'.jsonl')).read_text().splitlines()] for name in SCHEMA}
        catalog=json.loads((norm/'catalog.json').read_bytes())
        if reconstruct(rows,catalog['publication'])!=catalog:raise ValueError('projection artifact catalog differs')
        database=upstream/'pool/pool.duckdb';before=digest(database.read_bytes());verdicts=[]
        for number,case in enumerate(catalog['cases'],1):
            verdicts.append(check_case(database,rows,case,out/'checks'/f'case-{number:03d}'))
        if len(verdicts)!=16 or before!=digest(database.read_bytes()):raise ValueError('case count/pool changed')
        agreement=all(v['accepted']==c['expected']==c['observed'] for c,v in zip(catalog['cases'],verdicts))
        (out/'verdict.json').write_bytes(canonical({'cases':verdicts,'agreement':agreement}))
        result.update(agreement=agreement,entry='shared_existing/check.py')
    else:raise ValueError('unsupported stage')
    if len(children)!=cap or any(child.returncode!=0 for child,_ in children):raise ValueError('stage CLI census/exit differs')
    result['children']=[{'pid':child.pid,'wait_exit':child.returncode,'command':command} for child,command in children]
    result['entry_sha256']=digest((parent/result['entry']).read_bytes())
    result['package']=str(Path(dml.__file__).resolve());result['core_sha256']=digest(Path(dml._core.__file__).read_bytes())
    if result['core_sha256']!=pins['core_sha256']:raise ValueError('loaded recorder/candidate core differs')
    libraries={}
    for line in Path('/proc/self/maps').read_text().splitlines():
        fields=line.split()
        if len(fields)<6 or not fields[-1].startswith('/') or '.so' not in fields[-1]:continue
        path=Path(fields[-1]).resolve()
        if path==Path(dml._core.__file__).resolve():continue
        if path.name.startswith('_core_fault'):
            if digest(path.read_bytes())!='b3f8821144bf64cda49c9ecfaba282e6f88dcdf4517087fab046fa925520febd':raise ValueError('eager dependency differs')
        elif not any(str(path).startswith(prefix+'/') for prefix in pins['runtime']['closure']):
            raise ValueError('loaded library outside declared runtime')
        libraries[str(path)]=digest(path.read_bytes())
    result.update(libraries=libraries,runtime=pins['runtime_digest'],python=str(Path(sys.executable).resolve()))
    (out/'receipt.json').write_bytes(canonical(result))
    return 1 if stage=='C' and not result['agreement'] else 0


if __name__=='__main__':
    raise SystemExit(execute(json.loads(Path(sys.argv[1]).read_bytes())))
