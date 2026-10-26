#!/usr/bin/env python3
"""Seven bounded independent probes; writes only fresh final-review runtime.
Reuses inspected fixture builders/FileGate, never their suite entrypoints.
"""
import errno
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import sys
import uuid

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, v): p.write_text(json.dumps(v, indent=2)+'\n')
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

def main():
    os.umask(0o077)
    runtime = HERE/'runtime'; runtime.mkdir(exist_ok=True)
    assert len(list(runtime.glob('run-*'))) < 4, 'bounded runs; no automatic pruning'
    run = runtime/('run-'+uuid.uuid4().hex[:8]); run.mkdir()
    frozen = run/'snapshot'; frozen.mkdir()
    manifest = []
    sources = ['gate/gate.py','gate/apply_input.py','gate/fixture_language.py','gate/run_tests.py',
               'journal/journal.py','artifact/ready.json','artifact/main.go',
               'hardening-review/checks.py','hardening-review/followup_checks.py',
               'hardening-review/followup_prepare.py','hardening-review/followup_run.py',
               'hardening-review/followup_collect.py']
    for rel in sources:
        src = PARENT/rel; dst = frozen/rel; dst.parent.mkdir(parents=True, exist_ok=True)
        before = sha(src); shutil.copyfile(src,dst)
        assert sha(src)==sha(dst)==before
        manifest.append({'source':str(src),'copy':str(dst),'sha256':before})
    (frozen/'tools').symlink_to(PARENT/'tools', target_is_directory=True)
    (frozen/'journal/runtime').mkdir()
    sys.path.insert(0,str(frozen/'gate'))
    import gate as G
    import apply_input as A
    GT = load('fixture_builders', frozen/'gate/run_tests.py')
    I = load('inspected_bridge', frozen/'hardening-review/checks.py')
    J = load('journal_v2', frozen/'journal/journal.py')
    I.HERE = HERE  # inspected FileGate creates TMPDIR here, never in original worker
    ready = json.loads((frozen/'artifact/ready.json').read_text())
    for tool in ('provider','tofu'):
        assert sha(Path(ready[tool])) == ready['checksums'][tool]
    G.verified_tool()
    result = {'sandbox':str(run),'sources':manifest,'cases':{},
              'versions':{'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,
                          'linux':platform.release(),'opentofu':'1.13.2','provider':'immutable 0.1.0'},
              'tools':{k:ready['checksums'][k] for k in ('provider','tofu')}}
    save(run/'source-manifest.json',manifest)
    def record(name,value):
        result['cases'][name]=value; save(run/'results.json',result)
        print(name,json.dumps(value),flush=True)
    def create(name): return GT.create(run,name)
    def logs(root): return [json.loads(x) for x in (root/'cli.log').read_text().splitlines()]

    root=create('swap'); cfg=json.loads((root/'main.tf.json').read_text())
    cfg['resource']['terraform_data']['other']={'input':'synthetic-retained'}
    cfg['output']['dml_manifest']['value']['terraform_data.other']='${terraform_data.other.id}'
    save(root/'main.tf.json',cfg); G.cli(root,'apply','-auto-approve','-input=false','-no-color')
    before=G.observe(root); survivor=before['manifest']['terraform_data.other']
    del cfg['resource']['terraform_data']['victim']; del cfg['output']['dml_manifest']['value']['terraform_data.victim']
    save(root/'main.tf.json',cfg)
    j=G.FakeJournal(run/'swap.sqlite'); j.publish(ident=survivor,member='A'); g=G.Gate(root,j)
    ticket=g.plan(); assert ticket['victims']=={'terraform_data.victim':before['manifest']['terraform_data.victim']}
    G.cli(root,'plan','-destroy','-input=false','-no-color','-out=alternate.tfplan'); token=j.reserve(ticket)
    evidence={}
    def swap():
        matches=[]
        for p in Path('/proc/self/fd').iterdir():
            try:
                if 'dml-candidate-approved-plan' in os.readlink(p): matches.append(int(p.name))
            except FileNotFoundError: pass
        assert len(matches)==1; fd=matches[0]
        data=os.pread(fd,A.MAX_PLAN_BYTES+1,0)
        assert hashlib.sha256(data).hexdigest()==ticket['plan_digest']
        evidence.update(fd=fd,seals=fcntl.fcntl(fd,fcntl.F_GET_SEALS),approved_digest=True)
        assert evidence['seals']==15
        for name,fn in [('write',lambda:os.pwrite(fd,b'x',0)),
                        ('grow',lambda:os.ftruncate(fd,len(data)+1)),
                        ('shrink',lambda:os.ftruncate(fd,len(data)-1)),
                        ('seal_change',lambda:fcntl.fcntl(fd,fcntl.F_ADD_SEALS,fcntl.F_SEAL_FUTURE_WRITE))]:
            try: fn()
            except OSError as e: assert e.errno==errno.EPERM; evidence[name+'_errno']=e.errno
            else: raise AssertionError('seal restriction failed: '+name)
        (root/'cleanup.tfplan').write_bytes((root/'alternate.tfplan').read_bytes())
        assert sha(root/'cleanup.tfplan')!=ticket['plan_digest']
    after=g.apply(ticket,token,root/'cleanup.tfplan',before_effect=swap)
    assert after['manifest']=={'terraform_data.other':survivor}
    effect=next(c for c in reversed(logs(root)) if c['argv'][0]=='apply')
    assert effect['argv'][-1]==f"/proc/self/fd/{evidence['fd']}" and effect['pass_fds']==[evidence['fd']]
    record('sealed_saved_plan_swap',{'victim_deleted':True,'retained_identity_preserved':True,
                                   'kernel':evidence,'actual_apply':effect})

    for name,expression in [('file_expression','${file("input.txt")}'),
                            ('sensitive_expression','${sensitive("SYNTHETIC-ONLY")}'),
                            ('unexported_resource',None)]:
        root=create(name); before=G.observe(root); cfg=json.loads((root/'main.tf.json').read_text())
        if expression: cfg['resource']['terraform_data']['victim']['input']=expression
        else: cfg['resource']['terraform_data']['hidden']={'input':'synthetic-hidden'}
        save(root/'main.tf.json',cfg)
        count=len(logs(root)); g=G.Gate(root,G.FakeJournal(run/(name+'.sqlite')))
        try:g.plan()
        except G.Rejected as e: error=str(e)
        else:raise AssertionError('expected pre-effect rejection')
        assert len(logs(root))==count and not (root/'cleanup.tfplan').exists()
        assert G.observe(root)==before
        record(name,{'rejected':error,'planning_cli_calls':0,'state_unchanged':True})

    root=create('positive'); g=G.Gate(root,G.FakeJournal(run/'positive.sqlite'))
    save(root/'inputs.auto.tfvars.json',{'payload':'SYNTHETIC-POSITIVE'})
    t=g.plan(); tok=g.journal.reserve(t); after=g.apply(t,tok,root/'cleanup.tfplan')
    state=json.loads(G.cli(root,'state','pull'))
    assert state['resources'][0]['instances'][0]['attributes']['input']['value']=='SYNTHETIC-POSITIVE'
    assert all(c['output_logging']=='omitted' and 'stdout' not in c and 'stderr' not in c for c in logs(root))
    assert (root/'cli.log').stat().st_mode & 0o777 == 0o600
    record('positive_captured_string_fixture',{'update_applied':True,'body_free_logs':True,'log_mode':'0600'})

    # Adversarial check: literal-only same-census OpenTofu-preferred filename.
    root=create('tofu-precedence'); g=G.Gate(root,G.FakeJournal(run/'precedence.sqlite'))
    material=G.material(root); cfg=json.loads((root/'main.tf.json').read_text())
    cfg['resource']['terraform_data']['victim']['input']='SYNTHETIC-UNTRACKED-TOFU'
    save(root/'main.tofu.json',cfg); assert G.material(root)==material
    t=g.plan()
    cfg['resource']['terraform_data']['victim']['input']='SYNTHETIC-CHANGED-AFTER-PLAN'
    save(root/'main.tofu.json',cfg); assert G.material(root)==material
    g.check(t,root/'cleanup.tfplan'); tok=g.journal.reserve(t); g.apply(t,tok,root/'cleanup.tfplan')
    state=json.loads(G.cli(root,'state','pull'))
    value=state['resources'][0]['instances'][0]['attributes']['input']['value']
    assert value=='SYNTHETIC-UNTRACKED-TOFU'
    record('uncaptured_tofu_json',{'material_unchanged':True,'changed_file_accepted_after_plan':True,
                                 'actual_state_input':value,'sealed_plan_not_broken':True})

    class SealedFileGate(I.FileGate):
        """Own subclass of inspected FileGate, using current worker sealing helper.
        Same narrow physical mapping; not generic Gate integration.
        """
        def cli(self,*args,expected=0,extra=None,pass_fds=()):
            p=subprocess.run([self.ready['tofu'],*args],cwd=self.work,
                             env=dict(self.env,**(extra or {})),capture_output=True,text=True,
                             timeout=45,pass_fds=pass_fds,umask=0o077)
            with (self.work/'sealed-commands.jsonl').open('a') as log:
                log.write(json.dumps({'argv':args,'returncode':p.returncode,'pass_fds':pass_fds,
                                      'stdout_length':len(p.stdout),'stderr_length':len(p.stderr)})+'\n')
            assert p.returncode==expected, 'provider CLI failed; output kept in memory only'
            return p.stdout
        def check_snapshot(self,bundle,ticket,snapshot):
            assert snapshot.sha256==bundle['plan_digest']==ticket['plan_digest']
            assert self.material()==bundle['material'] and self.observe()==bundle['receipt']
            authority=self.j._verify(ticket) if self.j.db.in_transaction else self.j.verify(ticket)
            assert authority['victims']==[self.identity]
            doc=json.loads(self.cli('show','-json',snapshot.path,pass_fds=snapshot.pass_fds))
            c=doc['resource_changes']; assert len(c)==1
            assert c[0]['address']=='immutable_artifact.result' and c[0]['change']['actions']==['delete']
            before=c[0]['change']['before']; row=self.j.resource(self.identity)
            assert before['resource_id']==self.identity and before['physical']==f"{row['dev']}:{row['ino']}" and before['sha256']==row['digest']
            self.j.check_file(self.identity)
        def apply_sealed(self,bundle,ticket):
            with A.sealed_plan(self.plan,bundle['plan_digest']) as snapshot:
                self.check_snapshot(bundle,ticket,snapshot); self.j.begin_effect(ticket)
                with self.j.tx():
                    self.check_snapshot(bundle,ticket,snapshot)
                    self.plan.write_bytes(b'SYNTHETIC-INVALID-PATH-SUBSTITUTE')
                    assert self.material()==bundle['material']
                    self.cli('apply','-input=false','-no-color',snapshot.path,pass_fds=snapshot.pass_fds)
                    after=self.observe(); assert not after['present']
                self.j.ack(ticket)
                return snapshot.path
    I.FileGate=SealedFileGate
    f,j,rid,path=I.fixture(frozen,'final-audit',J.Journal,ready)
    j.commit('A','a1',operational=[rid]); j.commit('A','a2',parents=['a1']); j.head('A','main',None,'a2')
    b=f.prepare()
    try:j.reserve([rid],b['roots']['revision'],b['plan_digest'])
    except J.Rejected as e: protection=str(e)
    else:raise AssertionError('history should retain file')
    j.excise(rid); b=f.prepare(); ticket=j.reserve([rid],b['roots']['revision'],b['plan_digest'])
    apply_path=f.apply_sealed(b,ticket)
    assert not path.exists() and j.resource(rid)['disposed'] and rid in j.export()['associations']
    assert j._ticket(ticket['id'])['status']=='acknowledged' and j.validate_history()
    record('same_file_sealed_provider_journal_bridge',{'import_preserved_bytes_inode_mtime':True,
           'full_history_rejection':protection,'artifact_absent':True,'status':'acknowledged',
           'association_retained':True,'apply_descriptor':apply_path,'path_swap_ineffective':True,
           'adapter':'owned SealedFileGate subclass; original fixture builder and physical receipt'})
    j.close()
    for item in manifest: assert sha(Path(item['source']))==sha(Path(item['copy']))==item['sha256']
    result['cli_calls']=sum(len(p.read_text().splitlines()) for p in run.rglob('cli.log'))
    result['bridge_cli_calls']=sum(len(p.read_text().splitlines()) for p in run.rglob('sealed-commands.jsonl'))
    result['completed']=True; result['audit_sha256']=sha(Path(__file__))
    save(run/'results.json',result); save(HERE/'evidence.json',result)
    print('COMPLETE',run,flush=True)

if __name__=='__main__': main()
