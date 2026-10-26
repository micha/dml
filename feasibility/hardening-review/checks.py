#!/usr/bin/env python3
"""Independent attacks and explicit narrow actual-file/provider/journal adapter.
Only generated review-owned fixtures; no generic HCL/provider safety claim.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')

def reject(fn, exc):
    try:
        fn()
    except exc as e:
        return str(e)
    raise AssertionError('expected rejection')

class FileGate:
    """Adapter for this generated single-resource JSON fixture, not worker Gate.
    Owns provider-aware parsing/physical receipt correlation, reuses gate hashes.
    All callers and namespace writers must cooperate with journal reservation.
    """
    def __init__(self, base, work, journal, identity, ready):
        self.base, self.work, self.j, self.identity, self.ready = base, work, journal, identity, ready
        self.plan = work/'cleanup.tfplan'
        self.env = {'PATH':os.environ['PATH'], 'HOME':str(work/'home'),
                    'TF_CLI_CONFIG_FILE':ready['cli_config'], 'TF_IN_AUTOMATION':'1',
                    'CHECKPOINT_DISABLE':'1', 'TMPDIR':str(HERE/'runtime/t')}
        (HERE/'runtime/t').mkdir(exist_ok=True)
    def cli(self, *args, expected=0, extra=None):
        p = subprocess.run([self.ready['tofu'], *args], cwd=self.work,
                           env=dict(self.env, **(extra or {})), text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)
        with (self.work/'commands.jsonl').open('a') as f:
            f.write(json.dumps({'argv':args, 'returncode':p.returncode, 'output':p.stdout})+'\n')
        assert p.returncode == expected, p.stdout
        return p.stdout
    def material(self):
        files = sorted(p for p in self.work.iterdir() if p.name.endswith(('.tf','.tf.json','.tfvars','.tfvars.json')) or p.name == '.terraform.lock.hcl')
        assert {p.name for p in files} == {'main.tf.json','.terraform.lock.hcl'}
        assert not any(p.is_symlink() for p in files)
        # Generated fixture is frozen byte-for-byte. No expressions beyond manifest fields.
        return {p.name:sha(p) for p in files}
    def observe(self):
        state = json.loads(self.cli('state','pull'))
        assert state['version'] == 4 and isinstance(state['lineage'], str) and type(state['serial']) is int
        resources = state.get('resources', [])
        assert len(resources) <= 1
        for r in resources:
            assert r['mode']=='managed' and r['type']=='immutable_artifact' and r['name']=='result' and not r.get('module')
            assert r['provider']=='provider["dml.invalid/feasibility/immutable"]'
            assert len(r['instances'])==1 and 'deposed' not in r['instances'][0] and 'index_key' not in r['instances'][0]
            a = r['instances'][0]['attributes']
            row = self.j.resource(self.identity)
            assert a['id']==a['resource_id']==self.identity
            assert a['physical']==f"{row['dev']}:{row['ino']}" and a['sha256']==row['digest']
            assert a['path']==Path(row['path']).name and a['owner']=='managed'
        output = state.get('outputs',{}).get('manifest', {})
        assert not output.get('sensitive',False)
        return {'lineage':state['lineage'], 'serial':state['serial'], 'snapshot_digest':sha_bytes(state),
                'manifest':output.get('value'), 'present':bool(resources)}
    def prepare(self):
        material, receipt, roots = self.material(), self.observe(), self.j.snapshot()
        self.cli('plan','-destroy','-input=false','-no-color','-out=cleanup.tfplan')
        assert material == self.material() and receipt == self.observe() and roots == self.j.snapshot()
        doc = json.loads(self.cli('show','-json','cleanup.tfplan'))
        assert doc['format_version']=='1.2' and not doc.get('errored',False)
        changes = doc['resource_changes']
        assert len(changes)==1
        c = changes[0]
        assert c['address']=='immutable_artifact.result' and c['type']=='immutable_artifact' and c['mode']=='managed'
        assert not c.get('module_address') and 'index' not in c
        assert c['change']['actions']==['delete'] and not c['change'].get('importing')
        a = c['change']['before']
        row = self.j.resource(self.identity)
        assert a['resource_id']==self.identity and a['physical']==f"{row['dev']}:{row['ino']}" and a['sha256']==row['digest']
        bundle = {'material':material, 'receipt':receipt, 'roots':roots, 'plan_digest':sha(self.plan)}
        save(self.work/'bundle.json', bundle)
        save(self.work/'plan-summary.json', {'actions':c['change']['actions'],'identity':self.identity,'physical':a['physical']})
        return bundle
    def check(self, bundle, ticket):
        assert bundle['plan_digest']==sha(self.plan)==ticket['plan_digest']
        assert self.material()==bundle['material'] and self.observe()==bundle['receipt']
        authoritative = self.j._verify(ticket) if self.j.db.in_transaction else self.j.verify(ticket)
        assert authoritative['victims']==[self.identity]
        _, present = self.j.check_file(self.identity)
        # If absent after a crash, provider retry can converge manager state.
        return present
    def apply(self, bundle, ticket, pause=False):
        self.check(bundle,ticket)
        self.j.begin_effect(ticket)
        with self.j.tx():
            self.check(bundle,ticket)
            self.cli('apply','-input=false','-no-color','cleanup.tfplan',
                     extra={'DML_ARTIFACT_TEST_PAUSE_AFTER_UNLINK':'1'} if pause else None)
            after = self.observe()
            assert not after['present']
        self.j.ack(ticket)  # Observes actual absence, never just apply return code.
        save(self.work/'after.json',after)
        return after

def sha_bytes(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def fixture(base, name, Journal, ready):
    root = base/'journal/runtime'/('integrated-'+name)
    root.mkdir()
    files = root/'files'
    files.mkdir()
    j = Journal(root/'journal.sqlite', files)
    j.member('A'); j.member('B')
    rid = j.create_file('artifact', b'SYNTHETIC-INTEGRATED-ONLY\n')
    row = j.resource(rid)
    st = files.stat()
    receipt = {'path':Path(row['path']).name, 'sha256':row['digest'], 'owner':'managed',
               'resource_id':rid, 'physical':f"{row['dev']}:{row['ino']}", 'root_identity':f'{st.st_dev}:{st.st_ino}'}
    work = root/'manager'
    work.mkdir()
    config = {'terraform':{'required_providers':{'immutable':{'source':ready['source'],'version':ready['version']}}},
              'provider':{'immutable':{'root':str(files)}},
              'resource':{'immutable_artifact':{'result':{k:receipt[k] for k in ('path','sha256','owner','resource_id')}}},
              'output':{'manifest':{'value':{k:'${immutable_artifact.result.'+k+'}' for k in receipt}}}}
    save(work/'main.tf.json',config)
    save(work/'receipt.json',receipt)
    f = FileGate(base,work,j,rid,ready)
    path = Path(row['path'])
    before = (sha(path),path.stat().st_ino,path.stat().st_mtime_ns)
    f.cli('init','-input=false','-no-color')
    f.cli('import','-input=false','-no-color','immutable_artifact.result',json.dumps(receipt,separators=(',',':')))
    f.cli('apply','-auto-approve','-input=false','-no-color')
    f.cli('plan','-detailed-exitcode','-input=false','-no-color')
    assert before == (sha(path),path.stat().st_ino,path.stat().st_mtime_ns)
    j.adopted(rid)
    return f, j, rid, path

def child(base, work):
    J = load('candidate_journal',base/'journal/journal.py').Journal
    ready = json.loads((base/'artifact/ready.json').read_text())
    r = json.loads((work/'receipt.json').read_text())
    j = J(work.parent/'journal.sqlite',work.parent/'files')
    f = FileGate(base,work,j,r['resource_id'],ready)
    f.apply(json.loads((work/'bundle.json').read_text()),json.loads((work/'ticket.json').read_text()),pause=True)

def main(base):
    assert base.is_relative_to(HERE/'runtime') and base.is_dir()
    sys.path.insert(0,str(base/'gate'))
    G = load('candidate_gate',base/'gate/gate.py')
    J = load('candidate_journal',base/'journal/journal.py')
    GT = load('candidate_gate_tests',base/'gate/run_tests.py')
    number = next(i for i in range(1, 9) if not (base/f'attacks-{i}').exists())
    result = {'cases':{}, 'base':str(base), 'review_run':number}
    def record(name,value):
        result['cases'][name]=value
        save(base/f'review-results-{number}.json',result)
        save(base/'review-results.json',result)
        print(name,json.dumps(value),flush=True)
    attacks = base/f'attacks-{number}'
    attacks.mkdir()
    # Independent final-check gap: a filesystem writer is not fenced by SQLite.
    root = GT.create(attacks,'check-gap')
    journal = G.FakeJournal(attacks/'check-gap.db')
    gate = G.Gate(root,journal)
    t = gate.plan('cleanup.tfplan','-destroy')
    token = journal.reserve(t)
    outcome = reject(lambda:gate.apply(t,token,root/'cleanup.tfplan',before_effect=lambda:GT.config(root,prevent=True)),G.Rejected)
    assert not json.loads(G.cli(root,'state','pull')).get('resources')
    record('configuration_changed_after_final_check',{'destroyed':True,'new_prevent_destroy_ignored':True,
           'after_effect_receipt_failure':outcome,
           'adapter':'existing before_effect test callback; no candidate source edits'})
    # Swap the saved plan after validation: the checked pathname is not immutable.
    root=GT.create(attacks,'plan-swap')
    config=json.loads((root/'main.tf.json').read_text())
    config['resource']['terraform_data']['other']={'input':'synthetic-other'}
    config['output']['dml_manifest']['value']['terraform_data.other']='${terraform_data.other.id}'
    save(root/'main.tf.json',config)
    G.cli(root,'apply','-auto-approve','-input=false','-no-color')
    journal=G.FakeJournal(attacks/'plan-swap.db');gate=G.Gate(root,journal)
    other=G.observe(root)['manifest']['terraform_data.other'];journal.publish(ident=other,member='A')
    t=gate.plan('cleanup.tfplan','-destroy','-target=terraform_data.victim')
    assert list(t['victims'])==['terraform_data.victim']
    G.cli(root,'plan','-destroy','-input=false','-no-color','-out=alternate.tfplan')
    token=journal.reserve(t)
    outcome=reject(lambda:gate.apply(t,token,root/'cleanup.tfplan',
                   before_effect=lambda:(root/'cleanup.tfplan').write_bytes((root/'alternate.tfplan').read_bytes())),G.Rejected)
    assert not json.loads(G.cli(root,'state','pull')).get('resources')
    record('saved_plan_swapped_after_final_check',{'retained_other_destroyed':True,
           'authorized_ticket_excluded_other':True,'after_effect_failure':outcome})
    # Allowed file() expression creates uncaptured material dependence.
    root = GT.create(attacks,'file-expression')
    config = json.loads((root/'main.tf.json').read_text())
    config['resource']['terraform_data']['victim']['input']='${file("input.txt")}'
    save(root/'main.tf.json',config)
    (root/'input.txt').write_text('one')
    journal = G.FakeJournal(attacks/'file-expression.db');gate=G.Gate(root,journal)
    t=gate.plan(); (root/'input.txt').write_text('two')
    gate.check(t,root/'cleanup.tfplan')
    record('uncaptured_file_expression',{'check_accepted_changed_dependency':True,
           'accepted_expression':'${file("input.txt")}', 'not_a_universal_HCL_capture':True})
    # Retention with no configured member passes the fake's census validation.
    root = GT.create(attacks,'empty-census')
    journal = G.FakeJournal(attacks/'empty.db');gate=G.Gate(root,journal)
    t=gate.plan('cleanup.tfplan','-destroy');token=journal.reserve(t)
    with journal.tx() as c:
        count=c.execute('SELECT count(*) FROM members').fetchone()[0]
    assert count==0
    record('fake_gate_empty_census',{'reservation_accepted':True,'member_count':count,
           'real_journal_requires_nonempty_census':True})
    # Manifest validation after effect is too late to enforce total resource census.
    root = GT.create(attacks,'unexported-create')
    config = json.loads((root/'main.tf.json').read_text())
    config['resource']['terraform_data']['hidden']={'input':'synthetic-hidden'}
    save(root/'main.tf.json',config)
    journal=G.FakeJournal(attacks/'hidden.db');gate=G.Gate(root,journal)
    t=gate.plan();token=journal.reserve(t)
    outcome=reject(lambda:gate.apply(t,token,root/'cleanup.tfplan'),G.Rejected)
    state=json.loads(G.cli(root,'state','pull'))
    assert len(state['resources'])==2
    record('unexported_creation_before_receipt_rejection',{'created_unmapped_resource':True,'after_effect_failure':outcome})
    # The variable-sensitive check is not a general sensitivity check.
    root = GT.create(attacks,'sensitive-expression')
    config=json.loads((root/'main.tf.json').read_text())
    marker='SYNTHETIC-REVIEW-SENSITIVE'
    config['resource']['terraform_data']['victim']['input']='${sensitive("'+marker+'")}'
    save(root/'main.tf.json',config)
    G.material(root)
    G.cli(root,'apply','-auto-approve','-input=false','-no-color')
    receipt=G.observe(root)
    assert marker not in json.dumps(receipt) and marker in (root/'cli.log').read_text()
    record('sensitive_expression_receipt_vs_raw_log',{'material_accepted':True,'receipt_omits_value':True,'raw_cli_log_contains_value':True})
    # Modules fail closed rather than gaining universal composition support.
    config['module']={'child':{'source':'./unused'}}
    save(root/'main.tf.json',config)
    record('module_composition_explicitly_unsupported',reject(lambda:G.material(root),G.Rejected))
    ready=json.loads((base/'artifact/ready.json').read_text())
    for tool in ('provider','tofu'):
        assert sha(Path(ready[tool]))==ready['checksums'][tool]
    f,j,rid,path=fixture(base,f'shared-{number}',J.Journal,ready)
    record('existing_gate_provider_incompatibility',reject(lambda:G.material(f.work),G.Rejected))
    j.commit('A','a1',operational=[rid]);j.commit('A','a2',parents=['a1']);j.head('A','main',None,'a2')
    j.commit('B','b1',provenance=[rid]);j.head('B','main',None,'b1')
    b=f.prepare()
    record('actual_full_history_protects_provider_file',reject(lambda:j.reserve([rid],b['roots']['revision'],b['plan_digest']),J.Rejected))
    j.head('A','main','a2',None)
    record('shared_consumer_still_protects',reject(lambda:j.reserve([rid],j.revision(),b['plan_digest']),J.Rejected))
    j.member('B',False)
    record('unavailable_registered_member',reject(lambda:j.reserve([rid],j.revision(),b['plan_digest']),J.Rejected))
    j.member('B',True)
    j.excise(rid) # Candidate has no authenticated excision authority protocol.
    b=f.prepare();ticket=j.reserve([rid],b['roots']['revision'],b['plan_digest'])
    save(f.work/'ticket.json',ticket)
    record('ack_before_effect_rejected',reject(lambda:j.ack(ticket),J.Rejected))
    j.begin_effect(ticket)
    record('ack_with_file_present_rejected',reject(lambda:j.ack(ticket),J.Rejected))
    # A real child runs real provider Delete; parent kills entire group after unlink.
    log=(f.work/'killed-child.log').open('w')
    p=subprocess.Popen([sys.executable,'-B',str(HERE/'checks.py'),'--child',str(base),str(f.work)],
                       stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    deadline=time.monotonic()+15
    while path.exists() and p.poll() is None and time.monotonic()<deadline:
        time.sleep(.02)
    try:
        assert not path.exists(), 'expected real provider unlink before kill'
    finally:
        if p.poll() is None: os.killpg(p.pid,signal.SIGKILL)
        p.wait(timeout=5);log.close()
    j.close();j=J.Journal(f.work.parent/'journal.sqlite',path.parent);f.j=j
    assert j.verify(ticket)['status']=='intent' and not j.resource(rid)['disposed']
    assert f.observe()['present']
    record('integrated_SIGKILL_after_provider_effect',{'exitcode':p.returncode,'file_absent':True,
           'journal_status':j.verify(ticket)['status'],'manager_still_records_resource':True,
           'fence_survives':reject(lambda:j.member('late'),J.Rejected)})
    # Same saved plan can finish against unchanged stale state, accepting absent file.
    f.apply(b,ticket)
    assert j.resource(rid)['disposed'] and rid in j.export()['associations']
    record('integrated_recovery_and_historical_association',{'ticket_status':j._ticket(ticket['id'])['status'],
           'actual_absence':not path.exists(), 'historical_B_head_retained':True,
           'old_operational_head_reacquisition':reject(lambda:j.head('A','main',None,'a1'),J.Rejected)})
    j.commit('A','tombstone',provenance=[rid]);j.head('A','history',None,'tombstone')
    record('new_provenance_allowed_new_operation_rejected',reject(lambda:j.commit('A','new-op',operational=[rid]),J.Rejected))
    # v1 retained only mutable observations; v2 now snapshots every projection change.
    tables=[r[0] for r in j.db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    evidence={'tables':tables,'obligation_now':j.obligations()[0],'ticket_now':j._ticket(ticket['id'])}
    if hasattr(j,'history'):
        history=j.history()
        kinds=[o['kind'] for e in history for o in e['projection']['obligations'] if o['target']==rid]
        states=[t['status'] for e in history for t in e['projection']['tickets'] if t['id']==ticket['id']]
        assert {'creation','adoption','managed','disposal'}<=set(kinds)
        assert {'reserved','intent','acknowledged'}<=set(states)
        old=history[0]
        assert j.history_at(old['hash'])==old
        evidence.update(immutable_history_validated=j.validate_history(),obligation_kinds=sorted(set(kinds)),
                        ticket_states=sorted(set(states)),prior_snapshot_unchanged=True,
                        exact_manager_receipt_remains_adapter_sidecar=True)
        record('immutable_history_versions_management_states',evidence)
    else:
        record('v1_mutable_projection_only',evidence)
    j.close()
    f,j,rid,path=fixture(base,f'identity-{number}',J.Journal,ready)
    b=f.prepare();ticket=j.reserve([rid],b['roots']['revision'],b['plan_digest'])
    old=path.with_name(path.name+'-old');path.rename(old);path.write_bytes(old.read_bytes())
    record('integrated_pre_effect_physical_mismatch',reject(lambda:f.apply(b,ticket),J.Rejected))
    assert path.exists() and old.exists() and j.verify(ticket)['status']=='reserved'
    j.close()
    result['passed']=True;save(base/f'review-results-{number}.json',result);save(base/'review-results.json',result)

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--child':
        child(Path(sys.argv[2]),Path(sys.argv[3]))
    else:
        base=Path(sys.argv[1]) if len(sys.argv)>1 else Path(json.loads((HERE/'runtime/latest.json').read_text())['base'])
        main(base.resolve())
