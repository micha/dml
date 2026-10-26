#!/usr/bin/env python3
"""Targeted independent review. Does not change initial checks or worker sources."""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def rejected(fn,exception):
    try:fn()
    except exception as e:return str(e)
    raise AssertionError('expected pre-effect rejection')

def modules(base):
    sys.path.insert(0,str(base/'gate'))
    import gate as G
    import apply_input as A
    initial=load('initial_review',HERE/'checks.py')
    # Original source remains intact, but the subclass below adds only sealed apply.
    class SealedFileGate(initial.FileGate):
        def cli(self,*args,expected=0,extra=None,pass_fds=()):
            p=subprocess.run([self.ready['tofu'],*args],cwd=self.work,env=dict(self.env,**(extra or {})),
                             text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45,
                             pass_fds=pass_fds,umask=0o077)
            fd=os.open(self.work/'sealed-commands.jsonl',os.O_APPEND|os.O_CREAT|os.O_WRONLY|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'a') as log:
                os.fchmod(log.fileno(),0o600)
                log.write(json.dumps({'argv':args,'returncode':p.returncode,'pass_fds':pass_fds,
                                     'output_length':len(p.stdout),'output_logging':'omitted'})+'\n')
            assert p.returncode==expected, f'CLI failed: {args}, code {p.returncode}'
            return p.stdout
        def check_sealed(self,bundle,ticket,snapshot):
            assert bundle['plan_digest']==snapshot.sha256==ticket['plan_digest']
            assert self.material()==bundle['material'] and self.observe()==bundle['receipt']
            authoritative=self.j._verify(ticket) if self.j.db.in_transaction else self.j.verify(ticket)
            assert authoritative['victims']==[self.identity]
            doc=json.loads(self.cli('show','-json',snapshot.path,pass_fds=snapshot.pass_fds))
            c=doc['resource_changes']
            assert len(c)==1 and c[0]['address']=='immutable_artifact.result' and c[0]['change']['actions']==['delete']
            before=c[0]['change']['before'];row=self.j.resource(self.identity)
            assert before['resource_id']==self.identity and before['physical']==f"{row['dev']}:{row['ino']}" and before['sha256']==row['digest']
            self.j.check_file(self.identity)
        def apply_sealed(self,bundle,ticket,before_effect=None,pause=False):
            with A.sealed_plan(self.plan,bundle['plan_digest']) as snapshot:
                self.check_sealed(bundle,ticket,snapshot)
                self.j.begin_effect(ticket)
                with self.j.tx():
                    self.check_sealed(bundle,ticket,snapshot)
                    if before_effect:before_effect(snapshot)
                    assert self.material()==bundle['material']
                    self.cli('apply','-input=false','-no-color',snapshot.path,pass_fds=snapshot.pass_fds,
                             extra={'DML_ARTIFACT_TEST_PAUSE_AFTER_UNLINK':'1'} if pause else None)
                    after=self.observe();assert not after['present']
                self.j.ack(ticket)
                save(self.work/'sealed-after.json',after)
                return after
    initial.FileGate=SealedFileGate
    return G,A,initial,SealedFileGate

def child(base,work):
    G,A,initial,F=modules(base)
    J=load('candidate_journal',base/'journal/journal.py')
    ready=json.loads((base/'artifact/ready.json').read_text())
    r=json.loads((work/'receipt.json').read_text())
    j=J.Journal(work.parent/'journal.sqlite',work.parent/'files')
    f=F(base,work,j,r['resource_id'],ready)
    f.apply_sealed(json.loads((work/'bundle.json').read_text()),json.loads((work/'ticket.json').read_text()),pause=True)

def main(base):
    assert base.is_relative_to(HERE/'runtime/followup') and base.is_dir()
    G,A,initial,F=modules(base)
    GT=load('current_gate_tests',base/'gate/run_tests.py')
    J=load('candidate_journal',base/'journal/journal.py')
    number=next(i for i in range(1,9) if not (base/f'checks-{i}').exists())
    run=base/f'checks-{number}';run.mkdir()
    result={'base':str(base),'run':str(run),'cases':{}}
    def record(name,value):
        result['cases'][name]=value;save(run/'results.json',result);print(name,json.dumps(value),flush=True)
    def create(name):return GT.create(run,name)
    def current_state(root):return json.loads(G.cli(root,'state','pull'))
    # Exact original threat, adapted to a full-census non-targeted deletion plan.
    root=create('sealed-swap')
    cfg=json.loads((root/'main.tf.json').read_text())
    cfg['resource']['terraform_data']['other']={'input':'synthetic-other'}
    cfg['output']['dml_manifest']['value']['terraform_data.other']='${terraform_data.other.id}'
    save(root/'main.tf.json',cfg);G.cli(root,'apply','-auto-approve','-input=false','-no-color')
    observed=G.observe(root)
    other=observed['manifest']['terraform_data.other'];victim=observed['manifest']['terraform_data.victim']
    del cfg['resource']['terraform_data']['victim'];del cfg['output']['dml_manifest']['value']['terraform_data.victim']
    save(root/'main.tf.json',cfg)
    j=G.FakeJournal(run/'swap.db');j.publish(ident=other,member='A');g=G.Gate(root,j)
    ticket=g.plan();assert ticket['victims']=={'terraform_data.victim':victim}
    G.cli(root,'plan','-destroy','-input=false','-no-color','-out=alternate.tfplan')
    token=j.reserve(ticket)
    seal_evidence={}
    def swap():
        matches=[]
        for p in Path('/proc/self/fd').iterdir():
            try:
                if 'dml-candidate-approved-plan' in os.readlink(p):matches.append(int(p.name))
            except FileNotFoundError:pass
        assert len(matches)==1
        fd=matches[0];mask=fcntl.F_SEAL_WRITE|fcntl.F_SEAL_GROW|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_SEAL
        assert fcntl.fcntl(fd,fcntl.F_GET_SEALS)&mask==mask
        captured=os.pread(fd,A.MAX_PLAN_BYTES+1,0)
        assert hashlib.sha256(captured).hexdigest()==ticket['plan_digest']
        try:os.pwrite(fd,b'x',0)
        except OSError as e:seal_evidence['write_errno']=e.errno
        else:raise AssertionError('sealed memfd unexpectedly writable')
        assert seal_evidence['write_errno']==1
        seal_evidence.update(fd=fd,seals=fcntl.fcntl(fd,fcntl.F_GET_SEALS),digest_matches=True)
        (root/'cleanup.tfplan').write_bytes((root/'alternate.tfplan').read_bytes())
        assert sha(root/'cleanup.tfplan')!=ticket['plan_digest']
    after=g.apply(ticket,token,root/'cleanup.tfplan',before_effect=swap)
    assert after['manifest']=={'terraform_data.other':other}
    commands=[json.loads(x) for x in (root/'cli.log').read_text().splitlines()]
    effect=next(c for c in reversed(commands) if c['argv'][0]=='apply')
    assert effect['argv'][-1]==f"/proc/self/fd/{seal_evidence['fd']}" and effect['pass_fds']==[seal_evidence['fd']]
    record('actual_plan_swap_uses_approved_sealed_bytes',{'retained_other_survives':True,'authorized_victim_deleted':True,
           'substituted_plan_differs':True,'apply_argv':effect['argv'],'seals':seal_evidence})
    # Old expression/census counterexamples now reject before planning/apply.
    for name,value in [('file-expression','${file("input.txt")}'),('sensitive-expression','${sensitive("SYNTHETIC-ONLY")}')]:
        root=create(name);before=G.observe(root)
        cfg=json.loads((root/'main.tf.json').read_text());cfg['resource']['terraform_data']['victim']['input']=value
        save(root/'main.tf.json',cfg);(root/'input.txt').write_text('SYNTHETIC-ONLY')
        g=G.Gate(root,G.FakeJournal(run/(name+'.db')))
        cli_before=len((root/'cli.log').read_text().splitlines())
        error=rejected(lambda:g.plan(),G.Rejected)
        assert len((root/'cli.log').read_text().splitlines())==cli_before
        assert G.observe(root)==before and not (root/'cleanup.tfplan').exists()
        record(name,{'rejected':error,'state_unchanged':True,'no_plan_created':True,'planning_cli_invocations':0})
    root=create('unexported-create');before=G.observe(root)
    cfg=json.loads((root/'main.tf.json').read_text());cfg['resource']['terraform_data']['hidden']={'input':'synthetic-hidden'}
    save(root/'main.tf.json',cfg);g=G.Gate(root,G.FakeJournal(run/'hidden.db'))
    cli_before=len((root/'cli.log').read_text().splitlines())
    error=rejected(lambda:g.plan(),G.Rejected)
    assert len((root/'cli.log').read_text().splitlines())==cli_before
    assert G.observe(root)==before and len(current_state(root)['resources'])==1
    record('extra_managed_resource_pre_effect_rejection',{'rejected':error,'hidden_not_created':True,'planning_cli_invocations':0})
    root=create('config-effect');j=G.FakeJournal(run/'config.db');g=G.Gate(root,j)
    t=g.plan('cleanup.tfplan','-destroy');token=j.reserve(t)
    error=rejected(lambda:g.apply(t,token,root/'cleanup.tfplan',before_effect=lambda:GT.config(root,prevent=True)),G.Rejected)
    assert G.observe(root)['manifest']
    record('configuration_barrier_change_rejected',{'rejected':error,'resource_survives':True})
    # New source-capture bypass: only permitted built-in/literal fixture semantics,
    # but OpenTofu's higher-precedence JSON filename is absent from material().
    root=create('tofu-precedence');j=G.FakeJournal(run/'tofu.db');g=G.Gate(root,j)
    before_material=G.material(root)
    alternate=json.loads((root/'main.tf.json').read_text())
    alternate['resource']['terraform_data']['victim']['input']='SYNTHETIC-UNTRACKED-TOFU-LITERAL'
    save(root/'main.tofu.json',alternate)
    assert G.material(root)==before_material
    t=g.plan()
    alternate['resource']['terraform_data']['victim']['input']='SYNTHETIC-UNTRACKED-TOFU-CHANGED-AFTER-PLAN'
    save(root/'main.tofu.json',alternate)
    assert G.material(root)==before_material
    g.check(t,root/'cleanup.tfplan')
    token=j.reserve(t);g.apply(t,token,root/'cleanup.tfplan')
    state=current_state(root)
    assert state['resources'][0]['instances'][0]['attributes']['input']=='SYNTHETIC-UNTRACKED-TOFU-LITERAL'
    record('new_tofu_json_capture_bypass',{'material_digest_unchanged':True,'untracked_config_used':True,
           'changed_uncaptured_config_accepted_after_plan':True,
           'actual_input':'SYNTHETIC-UNTRACKED-TOFU-LITERAL','plan_sealing_not_broken':True})
    # New confidentiality probe remains inside literal/string variable language.
    root=create('literal-argv');g=G.Gate(root,G.FakeJournal(run/'argv.db'))
    canary='SYNTHETIC-LITERAL-ARGV-CANARY'
    t=g.plan('cleanup.tfplan','-var=payload='+canary)
    assert canary not in json.dumps(t) and canary in (root/'cli.log').read_text()
    assert (root/'cli.log').stat().st_mode&0o777==0o600
    assert all(c.get('output_logging')=='omitted' and 'stdout' not in c and 'stderr' not in c
               for c in [json.loads(x) for x in (root/'cli.log').read_text().splitlines()])
    record('new_literal_plan_argument_log_exposure',{'receipt_omits_value':True,'cli_argv_log_contains_value':True,
           'raw_stdout_stderr_omitted':True,'log_mode':'0600'})
    ready=json.loads((base/'artifact/ready.json').read_text())
    for tool in ('provider','tofu'):assert sha(Path(ready[tool]))==ready['checksums'][tool]
    # Positive real file bridge using the SAME worker sealing helper.
    f,j,rid,path=initial.fixture(base,f'sealed-followup-{number}',J.Journal,ready)
    j.commit('A','a1',operational=[rid]);j.commit('A','a2',parents=['a1']);j.head('A','main',None,'a2')
    b=f.prepare()
    record('sealed_bridge_full_history_protection',rejected(lambda:j.reserve([rid],b['roots']['revision'],b['plan_digest']),J.Rejected))
    j.excise(rid);b=f.prepare();ticket=j.reserve([rid],b['roots']['revision'],b['plan_digest']);save(f.work/'ticket.json',ticket)
    changed={}
    def bridge_swap(snapshot):
        f.plan.write_bytes(b'INVALID-SYNTHETIC-SUBSTITUTE-NOT-A-PLAN')
        changed.update(path_swapped=True,sealed_digest=snapshot.sha256,apply_path=snapshot.path)
    f.apply_sealed(b,ticket,before_effect=bridge_swap)
    assert not path.exists() and j.resource(rid)['disposed'] and rid in j.export()['associations']
    record('actual_artifact_bridge_sealed_swap_success',{'artifact_absent':True,'ticket':j._ticket(ticket['id'])['status'],
           'history_association_retained':True,**changed});j.close()
    # Actual provider effect before receipt, using sealed input in child and retry.
    f,j,rid,path=initial.fixture(base,f'sealed-crash-{number}',J.Journal,ready)
    b=f.prepare();ticket=j.reserve([rid],b['roots']['revision'],b['plan_digest']);save(f.work/'ticket.json',ticket)
    with (f.work/'sealed-crash.log').open('w') as log:
        p=subprocess.Popen([sys.executable,'-B',str(HERE/'followup_checks.py'),'--child',str(base),str(f.work)],
                           stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        deadline=time.monotonic()+15
        while path.exists() and p.poll() is None and time.monotonic()<deadline:time.sleep(.02)
        try:assert not path.exists(),'expected unlink before actual SIGKILL'
        finally:
            if p.poll() is None:os.killpg(p.pid,signal.SIGKILL)
            p.wait(timeout=5)
    j.close();j=J.Journal(f.work.parent/'journal.sqlite',path.parent);f.j=j
    assert j.verify(ticket)['status']=='intent' and not j.resource(rid)['disposed'] and f.observe()['present']
    f.apply_sealed(b,ticket)
    assert j.resource(rid)['disposed'] and not path.exists()
    record('actual_sealed_bridge_SIGKILL_retry',{'exitcode':p.returncode,'intent_survived':True,'manager_state_was_stale':True,
           'acknowledged_after_absence':True,'history_validated':j.validate_history()});j.close()
    # Focused surviving counterexample; do not inflate counts with unchanged suite.
    f,j,rid,path=initial.fixture(base,f'forced-replace-{number}',J.Journal,ready)
    f.cli('apply','-auto-approve','-input=false','-no-color','-replace=immutable_artifact.result',expected=1)
    assert not path.exists() and not j.resource(rid)['disposed']
    record('provider_forced_replacement_still_deletes',{'apply_exit':1,'file_deleted':True,'journal_did_not_authorize':True})
    j.close()
    result['passed']=True
    result['cli_invocations']=sum(1 for p in run.rglob('cli.log') for _ in p.read_text().splitlines())
    result['bridge_cli_invocations']=sum(1 for p in (base/'journal/runtime').glob(f'integrated-*-{number}/manager/sealed-commands.jsonl') for _ in p.read_text().splitlines())
    save(run/'results.json',result);save(base/'followup-review-results.json',result)
    print('PASS',run)

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--child':child(Path(sys.argv[2]),Path(sys.argv[3]))
    else:
        base=Path(sys.argv[1]) if len(sys.argv)>1 else Path(json.loads((HERE/'runtime/followup/latest.json').read_text())['base'])
        main(base.resolve())
