#!/usr/bin/env python3
"""One-time Stage 0 authorship/acquisition. Does not import or run study code.
After initial freeze use corpus.py --sources for reproducibility; never refresh
historical hashes implicitly. Definitions here are a curated allowlist, not graph roles.
"""
import argparse
from pathlib import Path
import corpus as C

# Safe reported JSON and selected safe source text only. No runtime reads.
SOURCES = [
 ('initial-manifest','gate/initial-checksums.json','json',[''], 'authored-claim'),
 ('initial-results','gate/test-results-initial.json','json',['/cases/completed_effect_unknown_outcome','/cases/interrupted_apply','/passed','/tool','/sandbox'], 'actual-recorded-effects'),
 ('initial-code','gate/gate-initial.py','text',[[191,216]], 'source-inspection'),
 ('followup-results','gate/followup-test-results.json','json',['/baseline_replay/initial_plan_swap_destroys_retained_other','/adversarial/sealed_plan_survives_actual_final_barrier_swap','/counts','/passed','/code_checksums','/sandbox','/python','/kernel','/sqlite','/tool'], 'actual-recorded-effects'),
 ('followup-code','gate/followup_tests.py','text',[[64,76],[100,136]], 'source-inspection'),
 ('current-gate','gate/gate.py','text',[[62,76],[255,281]], 'source-inspection'),
 ('sealing-code','gate/apply_input.py','text',[[1,69]], 'source-inspection'),
 ('audit-results','final-review/evidence.json','json',['/cases/sealed_saved_plan_swap','/cases/uncaptured_tofu_json','/cases/same_file_sealed_provider_journal_bridge','/sources','/versions','/tools','/cli_calls','/bridge_cli_calls','/completed','/audit_sha256','/sandbox'], 'actual-recorded-effects'),
 ('audit-code','final-review/audit.py','text',[[70,81],[132,145]], 'source-inspection'),
 ('local-adoption','opentofu/evidence.json','json',['/probes/local_adoption','/probes/surrogate_import/surrogate','/probes/surrogate_import/cli_reconciliation_actions','/version','/provider','/command_count','/runtime','/status'], 'actual-recorded-effects'),
 ('artifact-results','artifact/test-results.json','json',[''], 'actual-recorded-effects'),
 ('artifact-summary','artifact/summary.json','json',['/versions','/provider_sha256','/evidence','/limitations'], 'authored-claim'),
 ('journal-v1','journal/evidence-v1.json','json',['/contract_version','/sources','/latest/crashes','/latest/tests','/latest/run','/latest/success'], 'actual-recorded-effects'),
 ('journal-v1-code','journal/journal-v1.py','text',[[1,20]], 'source-inspection'),
 ('journal-v2','journal/evidence.json','json',['/contract_version','/latest/baseline_crashes','/latest/followup_observations','/latest/tests','/latest/baseline_tests','/latest/focused_tests','/latest/run','/latest/python','/latest/sqlite','/latest/platform','/sources','/historical_source_hashes_verified'], 'actual-recorded-effects'),
 ('bridge-results','hardening-review/evidence.json','json',['/review/cases/saved_plan_swapped_after_final_check','/review/cases/integrated_SIGKILL_after_provider_effect','/review/cases/integrated_recovery_and_historical_association','/review/cases/immutable_history_versions_management_states','/sources','/authoritative_run','/source_manifest'], 'actual-recorded-effects'),
 ('history-results','history/scenario-results.json','json',['/evidence','/model_version','/scenarios/1','/scenarios/2','/scenarios/3','/scenarios/5','/scenarios/6','/scenarios/7','/scenarios/9','/scenarios/10'], 'simulation'),
 ('history-summary','history/summary.json','json',['/tests','/limitations','/fixture'], 'authored-claim'),
 ('history-tests','history/test_model.py','text',[[62,72],[90,109]], 'source-inspection'),
 ('history-scenarios','history/run_scenarios.py','text',[[28,73]], 'source-inspection'),
 ('s3-manifest','adversarial/sources.json','json',['/aws_release','/aws_commit','/sources/aws_s3_object.go','/sources/aws_s3_delete.go','/sources/aws_s3_object.md'], 'authored-claim'),
 ('s3-summary','adversarial/summary.json','json',['/evidence','/strongest_findings','/limitations'], 'authored-claim'),
 ('s3-notes','adversarial/source-notes.md','text',[[52,94]], 'source-inspection'),
]


def freeze():
    if (C.HERE/'manifest.json').exists() or (C.HERE/'allowlist.json').exists():
        raise ValueError('already frozen: use corpus.py --sources, do not refresh historical identity')
    entries = []
    for sid, rel, kind, selectors, cls in SOURCES:
        path = 'feasibility/' + rel
        raw = C.read_bytes(C.ROOT, path)
        entries.append({'id':sid, 'path':path, 'kind':kind, 'selectors':selectors,
                        'sha256':C.digest(raw), 'original_bytes':len(raw),
                        'evidence_class':cls, 'sensitivity_review':'explicit curator allowlist; synthetic reported facts/source, not raw state',
                        'historical_environment':'only values supplied in cited source; otherwise unknown'})
    recipe = {'schema':'stage0-allowlist-v1', 'sources':entries, 'historical_bindings':[], 'supporting_paths':[]}
    fixtures = {e['id']:C.project(C.read_bytes(C.ROOT,e['path']), e) for e in entries}
    def cite(sid, locator):
        snap = fixtures[sid]
        index = next(i for i,r in enumerate(snap['values']) if r['locator']==locator)
        row = snap['values'][index]
        return {'source_id':sid, 'source_path':snap['source_path'], 'original_sha256':snap['original_sha256'],
                'original_locator':locator, 'fixture_pointer':f'/values/{index}', 'value_sha256':row['value_sha256']}
    def bind(target, manifest, selection, ptr):
        index = next(i for i,r in enumerate(fixtures[manifest]['values']) if r['locator']==selection)
        recipe['historical_bindings'].append({'target_id':target,'manifest_id':manifest,'selection_index':index,'digest_pointer':ptr,
             'meaning':'selected current/archive full bytes equal reported historical digest; not authenticated execution provenance'})
    bind('initial-code','initial-manifest','','/gate.py/sha256')
    bind('initial-results','initial-manifest','','/test-results.json/sha256')
    bind('journal-v1-code','journal-v1','/sources','/journal.py')
    bind('followup-code','followup-results','/code_checksums','/followup_tests.py')
    bind('current-gate','followup-results','/code_checksums','/gate.py')
    bind('sealing-code','followup-results','/code_checksums','/apply_input.py')
    bind('audit-code','audit-results','/audit_sha256','')
    # The archived vulnerable gate also matches the independent review's original source manifest.
    bind('initial-code','bridge-results','/sources','/3/sha256')
    bind('current-gate','audit-results','/sources','/0/sha256')
    bind('sealing-code','audit-results','/sources','/1/sha256')
    for sid, loc, path in [
        ('audit-results','/sandbox','feasibility/final-review/runtime/run-80e3f208/snapshot/gate/gate.py'),
        ('bridge-results','/source_manifest','feasibility/hardening-review/runtime/3/source-manifest.json'),
        ('artifact-results','','feasibility/artifact/runtime/r3'),
        ('journal-v1','/latest/run','feasibility/journal/runtime/run-cebhzcvj'),
        ('s3-manifest','/sources/aws_s3_object.go','feasibility/adversarial/runtime/sources/aws_s3_object.go'),
        ('s3-manifest','/sources/aws_s3_delete.go','feasibility/adversarial/runtime/sources/aws_s3_delete.go'),
    ]:
        recipe['supporting_paths'].append({'path':path,'citation':cite(sid,loc),
            'observation':C.metadata(C.ROOT,path),'observation_kind':'Stage 0 lstat, not historical availability or checksum verification',
            'contents_read':False,'derivation':'explicit reported sandbox/snapshot or source-notes location; no directory sweep'})
    truth = {'schema':'stage0-answer-v1','ingestion':'retrospective', 'historical_execution_ids_created':0,
             'identity_boundary':'source/fixture SHA256 identifies content; source IDs label curated copies, never historical requests/attempts/executions',
             'scenarios':[]}
    def scenario(letter, title):
        row={'id':letter,'title':title,'facts':[]};truth['scenarios'].append(row);return row
    def fact(row, name, answer, cls, citations, unit='qualitative finding', harness='not separately rerun in Stage 0', outcome='see cited recorded finding', limits='Retrospective reported evidence, not independently authenticated or complete environmental capture.'):
        row['facts'].append({'id':row['id']+'-'+name,'answer':answer,'evidence_class':cls,
            'origin':'curator-authored-interpretation-of-cited-evidence','unit':unit,'harness_result':harness,
            'system_outcome':outcome,'limitations':limits,'citations':[cite(*c) for c in citations]})
    a=scenario('A','Original pathname flaw, sealed correction, new input-capture flaw')
    fact(a,'original','The independent initial review reports retained_other_destroyed=true although the authorized ticket excluded it. The historical replay identifies retained UUID e52e649c-735a-61ca-2489-f1ea64dc7652 and an after-effect missing/nonpublic-receipt error. The archived apply code checked then reopened the mutable plan path.', 'actual-recorded-effects', [('bridge-results','/review/cases/saved_plan_swapped_after_final_check'),('followup-results','/baseline_replay/initial_plan_swap_destroys_retained_other'),('initial-code','lines:191-216'),('followup-code','lines:64-76')],outcome='unsafe deletion happened before rejection', limits='The initial review and later replay are separate reported runs; do not merge their UUIDs. Only the replay records the UUID. Raw plans/state were not imported.')
    fact(a,'fix','The sealed follow-up reports seal mask 15, EPERM for write/grow/shrink/seal mutation, victim absent, and retained UUID 10f3287f-6d71-7d8c-071f-3271305af526 surviving. Independent final audit reports the same restricted outcome and actual apply through /proc/self/fd/3 with pass_fds=[3].', 'actual-recorded-effects', [('followup-results','/adversarial/sealed_plan_survives_actual_final_barrier_swap'),('audit-results','/cases/sealed_saved_plan_swap'),('sealing-code','lines:1-69'),('current-gate','lines:255-281')],outcome='approved victim deleted; retained resource preserved in reported swap cases', limits='Final audit does not report numeric victim/survivor UUIDs; they cannot be borrowed from the follow-up run. Seals do not capture working directory or control provider effects.')
    fact(a,'capture','The final audit records unchanged material digest and acceptance of changed main.tofu.json after planning; actual_state_input is SYNTHETIC-UNTRACKED-TOFU. Its safe runner excerpt shows same-census literals and subsequent SYNTHETIC-CHANGED-AFTER-PLAN. This is incomplete input capture, not a broken memfd seal.', 'actual-recorded-effects', [('audit-results','/cases/uncaptured_tofu_json'),('audit-code','lines:132-145'),('current-gate','lines:62-76')],outcome='capture contract falsified; no extra retained deletion demonstrated')
    fact(a,'counts','The follow-up reports 28 regression groups, 22 adversarial groups, 4 historical replay groups and 285 OpenTofu CLI invocations. Final audit reports 55 built-in plus 18 bridge CLI calls. These are not additive test counts.', 'actual-recorded-effects', [('followup-results','/counts'),('audit-results','/cli_calls'),('audit-results','/bridge_cli_calls')],unit='groups and CLI invocations (separate units)',harness='follow-up passed=true; final audit completed=true',outcome='includes probes that demonstrate unsafe behavior')
    b=scenario('B','Adoption is not creation')
    fact(b,'ordinary','local_file import reported Resource Import Not Implemented. The following create changed execution-created-content to configuration-content, overwriting the artifact.', 'actual-recorded-effects', [('local-adoption','/probes/local_adoption')],outcome='unsupported adoption followed by destructive overwrite')
    fact(b,'surrogate','The built-in terraform_data adoption example is explicitly surrogate=true and reconciles with an update; it does not prove external-file byte preservation.', 'actual-recorded-effects', [('local-adoption','/probes/surrogate_import/surrogate'),('local-adoption','/probes/surrogate_import/cli_reconciliation_actions')],outcome='real CLI state-only surrogate, not actual artifact adoption')
    fact(b,'provider','The custom provider results report actual CLI/declarative import, bytes/inode/mtime preservation during metadata update, lost-state re-import, and real SIGKILL recovery. The independent same-file bridge additionally records import_preserved_bytes_inode_mtime=true.', 'actual-recorded-effects', [('artifact-results',''),('audit-results','/cases/same_file_sealed_provider_journal_bridge')],unit='52 CLI invocations in artifact suite; qualitative preservation assertions',outcome='narrow actual provider adoption; forced replacement still deletes before Create fails', limits='No numeric before/after byte digest, inode or mtime is present in the allowlisted adoption result. Reported checks are inspectable assertions, not raw receipts. Stage 0 did not rerun provider or inspect state.')
    c=scenario('C','Unknown outcome and separate cleanup/computation')
    fact(c,'unknown','The initial gate records process exit 73 after an effect with durable_status=unknown, empty manager manifest and no automatic acknowledgement. Another case exits before side effects; unknown is not a failed outcome.', 'actual-recorded-effects', [('initial-results','/cases/completed_effect_unknown_outcome'),('initial-results','/cases/interrupted_apply')],outcome='effect-start uncertainty stays durable, not automatically failed', limits='This gate uses a fake policy journal; it does not supply research request/attempt IDs or a computation result.')
    fact(c,'physical-recovery','The joined provider bridge records SIGKILL exitcode=-9 after unlink: file_absent=true, journal_status=intent and manager_still_records_resource=true. Later recovery records actual absence and ticket_status=acknowledged with historical association retained.', 'actual-recorded-effects', [('bridge-results','/review/cases/integrated_SIGKILL_after_provider_effect'),('bridge-results','/review/cases/integrated_recovery_and_historical_association'),('bridge-results','/review/cases/immutable_history_versions_management_states')],unit='one reported SIGKILL/recovery sequence',outcome='disposal completed before durable receipt; later acknowledged', limits='Physical cleanup sequence is not the model computation trial. No timestamped full progress stream is imported; final audit did not repeat this SIGKILL.')
    fact(c,'creation-history','Archived journal-v1 reports one unregistered orphan and no recovery after creation-before-registration. v2 reports zero unregistered orphans and recovery after creation-before-receipt, but same-byte pre-receipt replacement remains ambiguous.', 'actual-recorded-effects', [('journal-v1','/latest/crashes'),('journal-v2','/latest/baseline_crashes'),('journal-v2','/latest/followup_observations')],outcome='durable intent narrows orphan gap; hostile replacement still not proven safe')
    fact(c,'computation','Only the history simulation supplies request/attempt progress with unknown after crash, working/working/done, computation success and cleanup failed. Later simulated remediation keeps the same attempt and original failed cleanup. Do not splice this computation into the physical bridge.', 'simulation', [('history-results','/scenarios/5'),('history-results','/scenarios/6'),('history-results','/scenarios/7'),('history-summary','/limitations')],unit='simulated request/attempt lifecycle, not OS process effects',outcome='successful computation and failed cleanup coexist in model')
    d=scenario('D','Reuse and identical results do not define occurrence identity')
    fact(d,'fresh','Recorded model scenarios have distinct requests and attempts but result_roots=1; the content-only counterexample has actual_trials=2 and naive_unique_records=1. Safe runner source confirms two fresh calls.', 'simulation', [('history-results','/scenarios/1'),('history-results','/scenarios/2'),('history-scenarios','lines:28-73')],unit='2 simulated requests; 2 simulated attempts/trials; 1 result root',outcome='content deduplication does not collapse legitimate attempt identity')
    fact(d,'reuse','The reported reuse scenario selects the original attempt. Source inspection of the model test constructs two requests sharing one successful attempt, then a fresh attempt raises reachable attempt count to two. Exact two-request/one-attempt counts are source-derived, not a new physical or Stage 0 execution.', 'source-inspection', [('history-results','/scenarios/3'),('history-tests','lines:90-109'),('history-summary','/tests')],unit='source-derived 2 simulated requests; 1 reused attempt; 1 modeled execution before fresh branch',outcome='reuse adds no independent trial',limits='Structured scenario output lacks emitted request IDs and exact reuse request count. Summary reports 24 passing model tests but does not independently authenticate this individual test trace; source is not a retained execution transcript.')
    fact(d,'hidden','The model explicitly records one modeled attempt hiding two simulated executions; the discrepancy is not detectable without executor reporting.', 'simulation', [('history-results','/scenarios/10')],unit='1 modeled attempt; 2 simulated executions',outcome='attempt count alone is not complete external execution accounting')
    e=scenario('E','Evidence classification and unavailable material')
    fact(e,'s3','The S3 findings are pinned-source inspection claims: metadata/content-changing updates can select empty bytes without configured body; versioned deletion calls all-version cleanup for the matching key. The source manifest pins AWS v6.70.0 at 5e13eedee7c22ac362e6ffdfbdcfd23a5f9f797f. cloud_executed=false.', 'source-inspection', [('s3-summary','/evidence'),('s3-summary','/strongest_findings'),('s3-manifest','/aws_commit'),('s3-manifest','/sources/aws_s3_object.go'),('s3-manifest','/sources/aws_s3_delete.go'),('s3-notes','lines:52-94')],outcome='not a cloud-tested result',limits='Primary source bundles under ignored runtime are metadata-only, not loaded or rehashed. Frozen manifest authenticates neither download nor claim; safe source notes remain authored interpretation. No external URI fetched.')
    fact(e,'retirement','The model retirement example says physical_deletion_evidence=simulated assertion only and sensitive_content_erased=false. It supplies no evidence of actual legal excision or global copy erasure.', 'simulation', [('history-results','/scenarios/9'),('history-summary','/limitations')],outcome='simulation of retirement, not actual excision/erasure',limits='No genuine excised sensitive data was sought or ingested. Excised/unavailable external datasets are not demonstrated by this corpus.')
    fact(e,'availability','Original sandboxes and primary-source copies are separate locators; this package retains only selected safe reported evidence. Current availability is a separate Stage 0 lstat observation stored in manifest.json, not a historical availability event. External URLs remain unqueried.', 'authored-claim', [('audit-results','/sandbox'),('audit-results','/sources'),('bridge-results','/source_manifest'),('s3-manifest','/sources/aws_s3_object.go')],outcome='original evidence may be missing, restricted or disappear without destroying frozen fixtures',limits='lstat presence establishes no content hash, readability, completeness or authenticity. Missing at Stage 0 is not proof of historically missing, excised or failed.')
    gaps={'schema':'stage0-gaps-v1','items':[]}
    def gap(sid, text, impact, cs):
        gaps['items'].append({'id':sid,'description':text,'impact':impact,'citations':[cite(*x) for x in cs]})
    gap('raw-evidence','Raw plans, state, receipts, logs and historical source bundle contents excluded by sensitivity boundary.','Cannot independently inspect raw operations, numeric victim/survivor identities in final audit or adoption digest/inode/mtime pairs.', [('audit-results','/sources'),('artifact-results','')])
    gap('s3-primary','Pinned AWS primary-source copies receive lstat only; external URLs are not fetched.','Source claims remain inspectable authored trace, not independently reverified primary-source or cloud outcome.', [('s3-manifest','/sources/aws_s3_object.go'),('s3-notes','lines:52-94')])
    gap('occurrence-trace','Model summary emits booleans/counts, not retained request/attempt objects or all IDs.','Source-derived reuse counts must stay distinct from recorded model assertions; ingestion source labels are not historical IDs.', [('history-results','/scenarios/1'),('history-results','/scenarios/3'),('history-tests','lines:90-109')])
    gap('split-lifecycle','Real disposal recovery and simulated computation/cleanup are different evidence streams.','No complete real request/binding/attempt/computation/cleanup timeline can be reconstructed without invention.', [('bridge-results','/review/cases/integrated_SIGKILL_after_provider_effect'),('history-results','/scenarios/6')])
    gap('environment','Tool versions and hashes only where reported; no complete environment, dependencies or execution closure.','Current file hashes do not establish complete historical input capture or timing.', [('audit-results','/versions'),('audit-results','/tools'),('audit-results','/cases/uncaptured_tofu_json')])
    gap('authorization','Sealed bytes do not authorize provider Delete; forced replacement remains unsafe.','Harness success must not be presented as system safety.', [('artifact-results',''),('current-gate','lines:255-281')])
    gap('erasure','No actual excision, backup erasure or inaccessible external dataset was ingested.','Do not invent withdrawn/excised resources, synthetic historical events or global erasure.', [('history-results','/scenarios/9'),('s3-summary','/limitations')])
    gap('historical-attestation','Checksum manifests are retained reported data, not authenticated attestations.','Equal archive/full-file digest verifies bytes against reported digest only, not historical execution, independence, timestamp or provenance completeness.', [('initial-manifest',''),('journal-v1','/sources'),('audit-results','/sources')])
    gap('units','Historical metrics mix model tests, group counts, invocations and simulated attempts.','Never sum these into a generic tests-passed count or count retrospective ingestion as fresh research.', [('followup-results','/counts'),('history-summary','/tests'),('artifact-results','')])
    outputs=C.reconstruct(recipe)
    outputs['ground-truth.json']=C.canonical(truth)
    outputs['gaps.json']=C.canonical(gaps)
    lines=['# Stage 0 answer sheet\n','Curator-authored interpretations, not proof. Each fact has a structured locator in the [machine-readable sheet](ground-truth.json). Originals remain read-only; selected values are frozen under `fixtures/`.\n']
    for s in truth['scenarios']:
        lines.append(f"\n## {s['id']}. {s['title']}\n")
        for f in s['facts']:
            lines.append(f"\n### {f['id']} — {f['evidence_class']}\n\n{f['answer']}\n\n- Unit: {f['unit']}\n- Harness: {f['harness_result']}\n- Tested system: {f['system_outcome']}\n- Limits: {f['limitations']}\n- Evidence:\n")
            for c in f['citations']:
                lines.append(f"  - [`{c['source_path']} {c['original_locator']}`](fixtures/{c['source_id']}.json) → `{c['fixture_pointer']}`, original SHA256 `{c['original_sha256']}`, selected-value SHA256 `{c['value_sha256']}`.\n")
    lines.append('\n## Evidence gaps\n\nSee [gaps.json](gaps.json) for exact citations and [manifest.json](manifest.json) for bounded supporting-path availability.\n')
    outputs['ANSWER-SHEET.md']=''.join(lines).encode()
    outputs['allowlist.json']=C.canonical(recipe)
    outputs['manifest.json']=C.canonical({'schema':'stage0-corpus-v1','ingestion':'retrospective',
        'occurrence_identity':'no historical IDs created; source IDs label curated copies only',
        'allowlist_sha256':C.digest(outputs['allowlist.json']),
        'files':{k:C.digest(v) for k,v in outputs.items() if k!='allowlist.json'},
        'supporting_availability':recipe['supporting_paths'],
        'checksum_scope':'original full bytes pinned at curation; selections and package hashes verified; historical manifests are untrusted reported assertions, not signatures',
        'sanitization':'deterministic explicit pointer/line projection. No automatic secret-filter claim. Raw provider state, sessions, logs and external data excluded.'})
    (C.HERE/'fixtures').mkdir()
    for rel,data in outputs.items():
        path=C.HERE/rel
        with path.open('xb') as stream:
            stream.write(data)
    print(C.canonical(C.check(sources=True)).decode(),end='')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initial',action='store_true',required=True)
    parser.parse_args()
    freeze()
