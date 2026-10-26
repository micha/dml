#!/usr/bin/env python3
"""Regression plus bounded, fresh, adversarial immutable-input experiments."""
import ast
import copy
import errno
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import platform
import sqlite3
import sys
from unittest.mock import patch
import uuid

import apply_input
import gate as G
import run_tests as T

HERE = Path(__file__).resolve().parent

def save(path, value):
    path.write_text(json.dumps(value,indent=2)+'\n')

def logs(root):
    return [json.loads(s) for s in (root/'cli.log').read_text().splitlines()] if (root/'cli.log').exists() else []

def add_other(root, hidden=False):
    cfg=json.loads((root/'main.tf.json').read_text())
    cfg['resource']['terraform_data']['other']={'input':'synthetic-other'}
    if not hidden:
        cfg['output']['dml_manifest']['value']['terraform_data.other']='${terraform_data.other.id}'
    save(root/'main.tf.json',cfg)
    return cfg

def main():
    # Private new paths only. Baseline raw logging is replayed under umask 077.
    os.umask(0o077)
    runtime=HERE/'runtime/followup'
    runtime.mkdir(parents=True,exist_ok=True,mode=0o700)
    assert len(list(runtime.glob('run-*')))<8, 'bounded eight follow-up runs; never prune'
    base=runtime/('run-'+uuid.uuid4().hex[:8]);base.mkdir(mode=0o700)
    checksums=json.loads((HERE/'initial-checksums.json').read_text())
    for item in checksums.values():
        assert G.digest((HERE/item['snapshot']).read_bytes())==item['sha256']
    spec=importlib.util.spec_from_file_location('initial_gate',HERE/'gate-initial.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    def reject_old(fn,reason):
        try:fn()
        except old.Rejected as e:
            assert reason in str(e)
            return str(e)
        raise AssertionError('expected historical rejection')
    regression=T.main(base/'regression')
    results={'sandbox':str(base),'python':sys.version,'kernel':platform.release(),'sqlite':sqlite3.sqlite_version,
             'tool':regression['tool'],'regression':regression,'adversarial':{},'baseline_replay':{}}
    def record(name,value,baseline=False):
        results['baseline_replay' if baseline else 'adversarial'][name]=value
        save(base/'results.json',results)
        print(name,json.dumps(value),flush=True)
    attacks=base/'attacks';attacks.mkdir(mode=0o700)

    # Byte-identical historical gate reproduces all four review attack classes.
    root=T.create(attacks,'initial-swap');add_other(root)
    old.cli(root,'apply','-auto-approve','-input=false','-no-color')
    j=old.FakeJournal(base/'initial-swap.db');g=old.Gate(root,j)
    other=old.observe(root)['manifest']['terraform_data.other'];j.publish(ident=other,member='A')
    t=g.plan('cleanup.tfplan','-destroy','-target=terraform_data.victim')
    old.cli(root,'plan','-destroy','-input=false','-no-color','-out=alternate.tfplan')
    token=j.reserve(t)
    outcome=reject_old(lambda:g.apply(t,token,root/'cleanup.tfplan',
        before_effect=lambda:(root/'cleanup.tfplan').write_bytes((root/'alternate.tfplan').read_bytes())),
        'missing/nonpublic receipt')
    assert not json.loads(old.cli(root,'state','pull')).get('resources')
    record('initial_plan_swap_destroys_retained_other',{'retained_uuid':other,'after_effect_error':outcome},True)

    root=T.create(attacks,'initial-hidden');add_other(root,hidden=True)
    j=old.FakeJournal(base/'initial-hidden.db');g=old.Gate(root,j);t=g.plan();token=j.reserve(t)
    outcome=reject_old(lambda:g.apply(t,token,root/'cleanup.tfplan'),'malformed identity mapping')
    assert len(json.loads(old.cli(root,'state','pull'))['resources'])==2
    record('initial_unexported_create_before_rejection',outcome,True)

    root=T.create(attacks,'initial-file')
    cfg=json.loads((root/'main.tf.json').read_text());cfg['resource']['terraform_data']['victim']['input']='${file("input.txt")}'
    save(root/'main.tf.json',cfg);(root/'input.txt').write_text('one')
    j=old.FakeJournal(base/'initial-file.db');g=old.Gate(root,j);t=g.plan()
    (root/'input.txt').write_text('two');g.check(t,root/'cleanup.tfplan')
    record('initial_file_dependency_change_accepted',True,True)

    root=T.create(attacks,'initial-sensitive')
    marker='SYNTHETIC-GATE-LOG-SENSITIVITY'
    cfg=json.loads((root/'main.tf.json').read_text());cfg['resource']['terraform_data']['victim']['input']='${sensitive("'+marker+'")}'
    save(root/'main.tf.json',cfg);old.material(root)
    old.cli(root,'apply','-auto-approve','-input=false','-no-color');old.observe(root)
    assert marker in (root/'cli.log').read_text()
    assert (root/'cli.log').stat().st_mode & 0o777 == 0o600
    record('initial_sensitive_expression_raw_log',{'synthetic_marker_present':True,'mode':'0600'},True)

    # Actual final-check barrier swaps approved path, tries modifying kernel object.
    root=T.create(attacks,'sealed-swap');add_other(root)
    G.cli(root,'apply','-auto-approve','-input=false','-no-color')
    before=G.observe(root);other=before['manifest']['terraform_data.other']
    G.cli(root,'plan','-destroy','-input=false','-no-color','-out=alternate.tfplan')
    cfg=json.loads((root/'main.tf.json').read_text())
    del cfg['resource']['terraform_data']['victim'];del cfg['output']['dml_manifest']['value']['terraform_data.victim']
    save(root/'main.tf.json',cfg)
    j=G.FakeJournal(base/'sealed-swap.db');j.publish(ident=other,member='A');g=G.Gate(root,j)
    t=g.plan();assert set(t['victims'])=={'terraform_data.victim'}
    token=j.reserve(t);barrier={}
    def swap():
        entries=logs(root);entry=next(e for e in reversed(entries) if e['argv'][:2]==['show','-json'])
        fd=entry['pass_fds'][0]
        assert entry['argv'][-1]=='/proc/self/fd/'+str(fd)
        approved=os.pread(fd,os.fstat(fd).st_size,0)
        assert G.digest(approved)==t['plan_digest']
        mask=fcntl.fcntl(fd,fcntl.F_GET_SEALS)
        denied={}
        for name,operation in [('write',lambda:os.pwrite(fd,b'x',0)),
             ('shrink',lambda:os.ftruncate(fd,0)),('grow',lambda:os.ftruncate(fd,len(approved)+1)),
             ('change_seals',lambda:fcntl.fcntl(fd,fcntl.F_ADD_SEALS,fcntl.F_SEAL_WRITE))]:
            try:operation()
            except OSError as e:
                assert e.errno==errno.EPERM;denied[name]='EPERM'
            else:raise AssertionError('seal bypass: '+name)
        (root/'cleanup.tfplan').write_bytes((root/'alternate.tfplan').read_bytes())
        assert G.digest((root/'cleanup.tfplan').read_bytes())!=t['plan_digest']
        assert os.pread(fd,len(approved),0)==approved
        barrier.update(seal_mask=mask,denied=denied,approved_digest=t['plan_digest'],mutable_path_changed=True)
    after=g.apply(t,token,root/'cleanup.tfplan',before_effect=swap)
    assert after['manifest']=={'terraform_data.other':other}
    entry=next(e for e in reversed(logs(root)) if e['argv'][0]=='apply')
    assert entry['argv'][-1].startswith('/proc/self/fd/') and entry['pass_fds']
    record('sealed_plan_survives_actual_final_barrier_swap',{'barrier':barrier,
        'retained_uuid_survives':other,'victim_absent':True,'apply_uses_passed_fd':True})

    root=T.create(attacks,'targeted-incomplete-output');add_other(root)
    G.cli(root,'apply','-auto-approve','-input=false','-no-color');before=G.observe(root)
    j=G.FakeJournal(base/'targeted-incomplete-output.db');g=G.Gate(root,j)
    error=T.reject(lambda:g.plan('cleanup.tfplan','-destroy','-target=terraform_data.victim'),'incomplete planned resource census')
    assert G.observe(root)==before
    record('original_targeted_delete_incomplete_receipt_rejected',{'error':error,'both_resources_preserved':True})

    root=T.create(attacks,'preflight-swap');j=G.FakeJournal(base/'preflight-swap.db');g=G.Gate(root,j)
    t=g.plan();token=j.reserve(t)
    G.cli(root,'plan','-destroy','-input=false','-no-color','-out=alternate.tfplan')
    (root/'cleanup.tfplan').write_bytes((root/'alternate.tfplan').read_bytes());count=len(logs(root))
    error=T.reject(lambda:g.apply(t,token,root/'cleanup.tfplan'),'changed plan bytes')
    assert len(logs(root))==count and G.observe(root)['manifest']
    record('swap_before_snapshot_rejected_before_cli',error)

    root=T.create(attacks,'config-at-barrier');j=G.FakeJournal(base/'config-at-barrier.db');g=G.Gate(root,j)
    T.config(root,empty=True);t=g.plan();token=j.reserve(t)
    error=T.reject(lambda:g.apply(t,token,root/'cleanup.tfplan',before_effect=lambda:T.config(root,prevent=True)),
                   'stale configuration/input at effect boundary')
    assert G.observe(root)['manifest']
    record('config_change_at_barrier_rejected_before_apply',error)

    # Every rejected expression/census fixture is rejected before ANY planning CLI.
    variants=[('unexported_resource',lambda c:c['resource']['terraform_data'].update(other={'input':'hidden'}),'incomplete resource census'),
      ('empty_manifest',lambda c:c['output']['dml_manifest'].update(value={}),'incomplete resource census'),
      ('missing_manifest',lambda c:c.pop('output'),'missing/unsupported manifest'),
      ('wrong_identity_expression',lambda c:c['output']['dml_manifest'].update(value={'terraform_data.victim':'${var.payload}'}),'malformed resource census identity'),
      ('file_expression',lambda c:c['resource']['terraform_data']['victim'].update(input='${file("input.txt")}'),'unsupported evaluation'),
      ('sensitive_expression',lambda c:c['resource']['terraform_data']['victim'].update(input='${sensitive("SYNTHETIC-ONLY")}'),'unsupported evaluation'),
      ('unknown_variable',lambda c:c['resource']['terraform_data']['victim'].update(input='${var.uncaptured}'),'unknown variable reference'),
      ('template_directive',lambda c:c['resource']['terraform_data']['victim'].update(input='%{if true}x%{endif}'),'unsupported evaluation'),
      ('sensitive_variable',lambda c:c['variable']['payload'].update(sensitive=True),'unsupported variable'),
      ('expression_default',lambda c:c['variable']['payload'].update(default='${file("input.txt")}'),'unsupported evaluation')]
    for name,mutate,reason in variants:
        root=T.create(attacks,name);before=G.observe(root)
        cfg=json.loads((root/'main.tf.json').read_text());mutate(cfg);save(root/'main.tf.json',cfg)
        (root/'input.txt').write_text('synthetic-uncaptured')
        j=G.FakeJournal(base/(name+'.db'));g=G.Gate(root,j);count=len(logs(root))
        error=T.reject(lambda:g.plan(),reason)
        assert len(logs(root))==count and not (root/'cleanup.tfplan').exists()
        # Observe reads current config; removed outputs do not change stored state.
        assert G.observe(root)==before
        record(name+'_rejected_before_planning',{'error':error,'planning_cli_calls':0,'state_unchanged':True})

    root=T.create(attacks,'unknown-tfvars');before=G.observe(root)
    save(root/'inputs.auto.tfvars.json',{'unknown':'synthetic'})
    j=G.FakeJournal(base/'unknown-tfvars.db');g=G.Gate(root,j);count=len(logs(root))
    error=T.reject(lambda:g.plan(),'unknown variable input');assert len(logs(root))==count
    record('unknown_tfvars_rejected_before_planning',error)

    root=T.create(attacks,'duplicate-json');j=G.FakeJournal(base/'duplicate-json.db');g=G.Gate(root,j)
    (root/'inputs.auto.tfvars.json').write_text('{"payload":"one","payload":"two"}')
    count=len(logs(root));error=T.reject(lambda:g.plan(),'duplicate JSON key');assert len(logs(root))==count
    record('duplicate_json_keys_rejected_before_planning',error)

    root=T.create(attacks,'complete-create');before=G.observe(root);add_other(root)
    j=G.FakeJournal(base/'complete-create.db');j.publish(ident=before['manifest']['terraform_data.victim'],member='A');g=G.Gate(root,j)
    t=g.plan();assert not t['victims'];token=j.reserve(t)
    after=g.apply(t,token,root/'cleanup.tfplan')
    assert set(after['manifest'])=={'terraform_data.victim','terraform_data.other'}
    assert after['manifest']['terraform_data.victim']==before['manifest']['terraform_data.victim']
    record('complete_census_creation_and_unknown_id_admitted',{'census':t['census'],'after':after['manifest']})

    # Malformed saved-plan census is independently checked, even if source is valid.
    with G.approved_plan(root/'cleanup.tfplan',t['plan_digest']) as snapshot:
        doc=json.loads(G.cli(root,'show','-json',snapshot.path,pass_fds=snapshot.pass_fds))
    malformed=copy.deepcopy(doc)
    malformed['output_changes']['dml_manifest']['after_unknown']={}
    record('missing_planned_unknown_id_rejected',T.reject(lambda:G.plan_census(malformed,t['receipt']),'incomplete planned manifest census'))
    malformed=copy.deepcopy(doc)
    malformed['configuration']['root_module']['outputs']['dml_manifest']['expression']['constant_value'].pop('terraform_data.other')
    record('missing_saved_configuration_census_rejected',T.reject(lambda:G.plan_census(malformed,t['receipt']),'incomplete resource census'))

    root=T.create(attacks,'sealing-unavailable');j=G.FakeJournal(base/'sealing-unavailable.db');g=G.Gate(root,j)
    T.config(root,empty=True);t=g.plan();token=j.reserve(t);count=len(logs(root))
    with patch.object(apply_input.os,'memfd_create',side_effect=OSError(errno.ENOSYS,'test unavailable')):
        error=T.reject(lambda:g.apply(t,token,root/'cleanup.tfplan'),'Linux plan sealing unavailable')
    assert len(logs(root))==count and G.observe(root)['manifest']
    record('memfd_unavailable_fails_closed',error)
    count=len(logs(root))
    with patch.object(apply_input.fcntl,'fcntl',side_effect=OSError(errno.EPERM,'test sealing denied')):
        error=T.reject(lambda:g.apply(t,token,root/'cleanup.tfplan'),'Linux plan sealing unavailable')
    assert len(logs(root))==count
    record('sealing_denied_fails_closed',error)

    # Not a marker-based filter: arbitrary literal body is returned but NEVER logged.
    root=T.create(attacks,'restricted-logs');cfg=json.loads((root/'main.tf.json').read_text())
    cfg['resource']['terraform_data']['victim']['input']=marker;save(root/'main.tf.json',cfg)
    G.cli(root,'apply','-auto-approve','-input=false','-no-color')
    raw=G.cli(root,'state','pull');assert marker in raw
    G.observe(root);assert marker not in (root/'cli.log').read_text()
    assert all('stdout' not in e and 'stderr' not in e and e['output_logging']=='omitted' for e in logs(root))
    assert (root/'cli.log').stat().st_mode&0o777==0o600
    assert (root/'terraform.tfstate').stat().st_mode&0o077==0
    record('state_bodies_not_logged_no_secret_filter',{'metadata_log_mode':'0600','state_owner_only':True,
         'raw_value_returned_in_memory':True,'raw_value_persisted_in_manager_state':True,'raw_value_not_logged':True})

    sources=['gate.py','apply_input.py','fixture_language.py','run_tests.py','followup_tests.py','journal_adapter.py']
    results['code_checksums']={n:G.digest((HERE/n).read_bytes()) for n in sources}
    for name in sources:ast.parse((HERE/name).read_text(),filename=name)
    results['documentation_checksums']={p.name:G.digest(p.read_bytes()) for p in (runtime/'docs').glob('*.html')}
    results['counts']={'regression_groups':len(regression['cases']), 'adversarial_groups':len(results['adversarial']),
                      'baseline_replay_groups':len(results['baseline_replay']),
                      'opentofu_cli_invocations':sum(len(p.read_text().splitlines()) for p in base.rglob('cli.log')),
                      'wrapper_cli_subprocesses':3,'abrupt_os_exits':2}
    results['passed']=True
    save(base/'results.json',results);save(HERE/'followup-test-results.json',results)
    print('FOLLOWUP PASS',json.dumps(results['counts']),base)

if __name__=='__main__':main()
