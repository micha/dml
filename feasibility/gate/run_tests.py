#!/usr/bin/env python3
"""Fresh built-in-only CLI probes. No existing sandbox is removed/reused."""
import copy
import json
import multiprocessing as mp
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import uuid

from gate import FakeJournal, Gate, Rejected, cli, observe, receipt_from_state, verified_tool

HERE = Path(__file__).resolve().parent

def config(root, n='one', prevent=False, empty=False, replacement=False):
    resource = {} if empty else {'terraform_data':{'victim':{
        'input':'${var.payload}', 'triggers_replace': n,
        **({'lifecycle':{'prevent_destroy':True}} if prevent else {})}}}
    value = {} if empty else {'terraform_data.victim':'${terraform_data.victim.id}'}
    (root/'main.tf.json').write_text(json.dumps({'variable':{'payload':{'type':'string','default':'hello'}},
        **({'resource':resource} if resource else {}), 'output':{'dml_manifest':{'value':value}}}, indent=2))

def create(base, name):
    root = base/name
    root.mkdir(mode=0o700)
    config(root)
    cli(root,'init','-input=false','-no-color')
    cli(root,'apply','-auto-approve','-input=false','-no-color')
    return root

def reject(fn, reason):
    try:
        fn()
    except Rejected as e:
        assert reason in str(e), (reason,str(e))
        return str(e)
    raise AssertionError('expected rejection: '+reason)

def killed_apply(root, journal_path, ticket, token, ready, after=False):
    g = Gate(root, FakeJournal(journal_path))
    def checkpoint():
        ready.send('effect-completed-before-outcome' if after else 'validated-before-side-effect')
        os._exit(73)
    g.apply(ticket, token, Path(root)/'cleanup.tfplan',
            **({'after_effect':checkpoint} if after else {'before_effect':checkpoint}))

def blocked_apply(root, journal_path, ticket, token, ready, proceed):
    g = Gate(root, FakeJournal(journal_path))
    def checkpoint():
        ready.send('validated-before-side-effect')
        assert proceed.recv() == 'continue'
    g.apply(ticket, token, Path(root)/'cleanup.tfplan', checkpoint)

def publisher(journal_path, ready, result):
    # Deterministic lock observation while the apply process waits at its barrier.
    c=sqlite3.connect(journal_path,timeout=0)
    try:
        c.execute('BEGIN IMMEDIATE')
    except sqlite3.OperationalError as e:
        assert 'locked' in str(e)
        ready.send('observed-sqlite-writer-lock')
    else:
        c.rollback()
        raise AssertionError('gate writer lock was not held')
    finally:
        c.close()
    try:
        FakeJournal(journal_path).publish(member='new-repository')
        result.send('published')
    except Exception as e:
        result.send('rejected: '+str(e))

def main(base=None):
    verified_tool()
    if base is None:
        runs = HERE/'runtime/followup/regression'
        runs.mkdir(parents=True,exist_ok=True,mode=0o700)
        existing = list(runs.glob('run-*'))
        assert len(existing) < 8, 'bounded eight follow-up runs; no automatic deletion'
        base = runs/('run-'+uuid.uuid4().hex[:8])
    base.mkdir(mode=0o700)
    results = {'sandbox':str(base), 'python':sys.version, 'tool':json.loads(cli(base,'version','-json')), 'cases':{}}
    def record(name, value):
        results['cases'][name] = value
        (base/'results.json').write_text(json.dumps(results,indent=2)+'\n')
        print(name, json.dumps(value), flush=True)

    root = create(base,'hazard')
    j = FakeJournal(base/'hazard.db'); g = Gate(root,j)
    t = g.plan('cleanup.tfplan','-destroy')
    ident = t['victims']['terraform_data.victim']
    token = j.reserve(t)
    # In real research a new reference arrives; fake journal forbids it with reservation.
    config(root,prevent=True)
    record('saved_plan_gate', reject(lambda:g.apply(t,token,root/'cleanup.tfplan'),'stale configuration'))
    # Direct CLI bypasses the candidate and does not consider the new prevent_destroy.
    cli(root,'apply','-input=false','-no-color',str(root/'cleanup.tfplan'))
    raw = json.loads(cli(root,'state','pull'))
    assert not raw.get('resources')
    record('saved_plan_raw_hazard', {'destroyed':ident,'despite_unapplied_prevent_destroy':True})

    root = create(base,'retained')
    j = FakeJournal(base/'retained.db'); g=Gate(root,j)
    ident = observe(root)['manifest']['terraform_data.victim'];j.publish(ident=ident,member='research-A')
    for kind in ('update','replace','destroy'):
        config(root,n='two' if kind=='replace' else 'one',empty=kind=='destroy')
        if kind=='update':
            (root/'inputs.auto.tfvars.json').write_text(json.dumps({'payload':'changed'}))
        elif (root/'inputs.auto.tfvars.json').exists():
            (root/'inputs.auto.tfvars.json').unlink()
        t=g.plan(kind+'.tfplan')
        assert t['victims']=={'terraform_data.victim':ident}
        record('retained_'+kind,reject(lambda:j.reserve(t),'retained actual identity'))
    j.publish(disposition=ident)
    t=g.plan('cleanup.tfplan');token=j.reserve(t)
    after=g.apply(t,token,root/'cleanup.tfplan')
    assert after['manifest']=={}
    record('explicit_disposition_cleanup',{'before':ident,'after':after})

    root=create(base,'stale');j=FakeJournal(base/'stale.db');g=Gate(root,j)
    t=g.plan()
    (root/'inputs.auto.tfvars.json').write_text(json.dumps({'payload':'other'}))
    record('input_changed',reject(lambda:g.check(t,root/'cleanup.tfplan'),'stale configuration'))
    (root/'inputs.auto.tfvars.json').unlink()
    original=(root/'cleanup.tfplan').read_bytes()
    (root/'cleanup.tfplan').write_bytes(original+b'x')
    record('plan_bytes_changed',reject(lambda:g.check(t,root/'cleanup.tfplan'),'changed plan bytes'))
    (root/'cleanup.tfplan').write_bytes(original)
    j.publish(member='new-member')
    record('membership_changed',reject(lambda:j.reserve(t),'stale root/membership'))
    t=g.plan();j.publish(ident=observe(root)['manifest']['terraform_data.victim'])
    record('roots_changed',reject(lambda:j.reserve(t),'stale root/membership'))

    # Correlation: separate output read then a replacement then a state read.
    root=create(base,'receipts')
    first=observe(root)
    old_output=json.loads(cli(root,'output','-json'))['dml_manifest']['value']
    config(root,n='two')
    cli(root,'apply','-auto-approve','-input=false','-no-color')
    raw=json.loads(cli(root,'state','pull'));second=receipt_from_state(raw)
    assert first['manifest'] != second['manifest'] and first['lineage']==second['lineage'] and second['serial']>first['serial']
    mixed=copy.deepcopy(raw);mixed['outputs']['dml_manifest']['value']=old_output
    record('mixed_receipt',reject(lambda:receipt_from_state(mixed),'malformed identity mapping'))
    record('address_not_identity',{'before':first,'after':second})
    for name,mutate,reason in [
        ('missing',lambda s:s['outputs'].pop('dml_manifest'),'missing/nonpublic'),
        ('sensitive',lambda s:s['outputs']['dml_manifest'].update(sensitive=True),'missing/nonpublic'),
        ('serial',lambda s:s.update(serial=None),'unknown state'),
        ('mapping',lambda s:s['outputs']['dml_manifest'].update(value={'wrong':'id'}),'malformed identity')]:
        s=copy.deepcopy(raw);mutate(s)
        record('receipt_'+name,reject(lambda:receipt_from_state(s),reason))
    j=FakeJournal(base/'receipts.db');g=Gate(root,j)
    t=g.plan();t['receipt']=first
    record('old_observation',reject(lambda:g.check(t,root/'cleanup.tfplan'),'stale manager receipt'))
    # An old retained UUID is not retention of its successor at the same address.
    j.publish(ident=first['manifest']['terraform_data.victim'])
    (root/'inputs.auto.tfvars.json').write_text(json.dumps({'payload':'new-object-update'}))
    t=g.plan();token=j.reserve(t)
    assert t['victims']['terraform_data.victim']==second['manifest']['terraform_data.victim']
    omitted=copy.deepcopy(t);omitted['victims']={}
    record('omitted_ticket_victims',reject(lambda:g.check(omitted,root/'cleanup.tfplan'),'ticket victim/plan mismatch'))
    g.apply(t,token,root/'cleanup.tfplan')
    record('old_identity_does_not_retain_successor',{'admitted_current_uuid':t['victims'],
        'retained_old_uuid':first['manifest']})

    root=create(base,'interrupted');j=FakeJournal(base/'interrupted.db');g=Gate(root,j)
    config(root,empty=True);t=g.plan();token=j.reserve(t)
    ctx=mp.get_context('spawn');recv,send=ctx.Pipe(False)
    p=ctx.Process(target=killed_apply,args=(root,j.path,t,token,send));p.start()
    assert recv.poll(60) and recv.recv()=='validated-before-side-effect'
    p.join(30);assert p.exitcode==73
    with j.tx() as c:
        status=c.execute('SELECT status FROM reservations WHERE token=?',(token,)).fetchone()[0]
    assert status=='unknown' and observe(root)['manifest']
    record('interrupted_apply',{'exitcode':p.exitcode,'durable_status':status,'side_effect_started':False,
        'new_publisher':reject(lambda:j.publish(member='late'),'live/unknown reservation'),
        'blind_retry':reject(lambda:g.apply(t,token,root/'cleanup.tfplan'),'missing/mismatched/live')})

    root=create(base,'outcome-gap');j=FakeJournal(base/'outcome-gap.db');g=Gate(root,j)
    config(root,empty=True);t=g.plan();token=j.reserve(t)
    recv,send=ctx.Pipe(False)
    p=ctx.Process(target=killed_apply,args=(root,j.path,t,token,send,True));p.start()
    assert recv.poll(60) and recv.recv()=='effect-completed-before-outcome'
    p.join(30);assert p.exitcode==73
    with j.tx() as c:
        status=c.execute('SELECT status FROM reservations WHERE token=?',(token,)).fetchone()[0]
    assert status=='unknown' and observe(root)['manifest']=={}
    record('completed_effect_unknown_outcome',{'exitcode':p.exitcode,'durable_status':status,
        'manager_manifest':{},'automatic_acknowledgement':False})

    root=create(base,'cooperative');j=FakeJournal(base/'cooperative.db');g=Gate(root,j)
    config(root,empty=True);t=g.plan();token=j.reserve(t)
    ready_r,ready_w=ctx.Pipe(False);cont_r,cont_w=ctx.Pipe(False)
    p=ctx.Process(target=blocked_apply,args=(root,j.path,t,token,ready_w,cont_r));p.start()
    assert ready_r.poll(60) and ready_r.recv()=='validated-before-side-effect'
    pub_r,pub_w=ctx.Pipe(False);result_r,result_w=ctx.Pipe(False)
    q=ctx.Process(target=publisher,args=(j.path,pub_w,result_w));q.start()
    assert pub_r.poll(60) and pub_r.recv()=='observed-sqlite-writer-lock'
    # No sleep-based ordering: the publisher observed SQLITE_BUSY before release.
    cont_w.send('continue')
    p.join(60);q.join(60);assert p.exitcode==q.exitcode==0
    assert result_r.poll(1);out=result_r.recv();assert out=='published'
    assert observe(root)['manifest']=={}
    record('publisher_between_check_and_effect',{'excluded_while_apply_transaction':True,'after_apply':out,
        'note':'manual fake member publication after completed cleanup; real root acquisition must also reject disposed identities'})
    # A still-reserved token blocks a new publisher even without active writer tx.
    root=create(base,'reservation');j=FakeJournal(base/'reservation.db');g=Gate(root,j)
    t=g.plan();token=j.reserve(t)
    record('durable_reservation_fence',reject(lambda:j.publish(member='late'),'live/unknown reservation'))
    record('missing_reservation',reject(lambda:g.apply(t,'absent',root/'cleanup.tfplan'),'missing/mismatched/live'))
    with j.tx() as c:
        c.execute("UPDATE reservations SET status='completed'")
        c.execute("INSERT INTO members VALUES ('offline',0)")
    record('unavailable_member',reject(lambda:j.reserve(t),'unavailable member'))
    root=create(base,'cli-driver')
    config(root,empty=True)
    journal_path=base/'cli-driver.db';ticket_path=root/'approval.json'
    def wrapper(action,*extra):
        command=[sys.executable,'-B',str(HERE/'gate.py'),action,'--root',str(root),
                 '--journal',str(journal_path),'--ticket',str(ticket_path),*extra]
        p=subprocess.run(command,capture_output=True,text=True,timeout=60)
        with (base/'wrapper.log').open('a') as f:
            f.write(json.dumps({'command':command,'code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})+'\n')
        assert p.returncode==0,p.stderr
        return p.stdout
    wrapper('plan');token=wrapper('reserve').strip();after=json.loads(wrapper('apply','--token',token))
    assert after['manifest']=={}
    record('deployment_neutral_cli_driver',{'actions':['plan','reserve','apply'],'after':after})
    (root/'unsupported.tf').write_text('# unparsed HCL is outside candidate scope\n')
    g=Gate(root,FakeJournal(journal_path))
    record('unsupported_material',reject(lambda:g.plan(),'unsupported material'))

    from journal_adapter import probe
    root=create(base,'real-adapter-manager')
    j=FakeJournal(base/'adapter-plan.db');g=Gate(root,j)
    config(root,empty=True);t=g.plan()
    record('real_journal_adapter_attempt',probe(base,root,t))
    results['passed']=True
    (base/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    (HERE/'test-results.json').write_text(json.dumps(results,indent=2)+'\n')
    print('PASS',base)
    return results

if __name__=='__main__':main()
