# Stage 0 answer sheet
Curator-authored interpretations, not proof. Each fact has a structured locator in the [machine-readable sheet](ground-truth.json). Originals remain read-only; selected values are frozen under `fixtures/`.

## A. Original pathname flaw, sealed correction, new input-capture flaw

### A-original — actual-recorded-effects

The independent initial review reports retained_other_destroyed=true although the authorized ticket excluded it. The historical replay identifies retained UUID e52e649c-735a-61ca-2489-f1ea64dc7652 and an after-effect missing/nonpublic-receipt error. The archived apply code checked then reopened the mutable plan path.

- Unit: qualitative finding
- Harness: not separately rerun in Stage 0
- Tested system: unsafe deletion happened before rejection
- Limits: The initial review and later replay are separate reported runs; do not merge their UUIDs. Only the replay records the UUID. Raw plans/state were not imported.
- Evidence:
  - [`feasibility/hardening-review/evidence.json /review/cases/saved_plan_swapped_after_final_check`](fixtures/bridge-results.json) → `/values/0`, original SHA256 `ba129dc87755f2c0f58c84b7102abf31d9792f4f815cc092d892baadadba3536`, selected-value SHA256 `65459f6a41c9a87ddc920f8c3135eba126010b7fa4428b4f71276218b48226f6`.
  - [`feasibility/gate/followup-test-results.json /baseline_replay/initial_plan_swap_destroys_retained_other`](fixtures/followup-results.json) → `/values/0`, original SHA256 `70edb830ab82adba37620a405258a08d866f4c03cb374683d3121113e33b3f67`, selected-value SHA256 `d42e2e6feae126738d4b0811d22fec15da8e1850d69f0ba4e270ab8f3556041d`.
  - [`feasibility/gate/gate-initial.py lines:191-216`](fixtures/initial-code.json) → `/values/0`, original SHA256 `666d699e7ed4adac11585db98b2230eb564768dc21db72adc2394f6c1d3077ac`, selected-value SHA256 `6f138406f43a68cb7ec66478c4dbc2c55ff581eba870bbd4c387d1da4d269b8a`.
  - [`feasibility/gate/followup_tests.py lines:64-76`](fixtures/followup-code.json) → `/values/0`, original SHA256 `cc21c85408f9d61f72e785700b230d5e9acac04fff61aded127659c7fb7954ce`, selected-value SHA256 `fc2180d52d2b06ff66de54853a1c2eea198e98d7f456cb3b35897fb3d949bf55`.

### A-fix — actual-recorded-effects

The sealed follow-up reports seal mask 15, EPERM for write/grow/shrink/seal mutation, victim absent, and retained UUID 10f3287f-6d71-7d8c-071f-3271305af526 surviving. Independent final audit reports the same restricted outcome and actual apply through /proc/self/fd/3 with pass_fds=[3].

- Unit: qualitative finding
- Harness: not separately rerun in Stage 0
- Tested system: approved victim deleted; retained resource preserved in reported swap cases
- Limits: Final audit does not report numeric victim/survivor UUIDs; they cannot be borrowed from the follow-up run. Seals do not capture working directory or control provider effects.
- Evidence:
  - [`feasibility/gate/followup-test-results.json /adversarial/sealed_plan_survives_actual_final_barrier_swap`](fixtures/followup-results.json) → `/values/1`, original SHA256 `70edb830ab82adba37620a405258a08d866f4c03cb374683d3121113e33b3f67`, selected-value SHA256 `765e2c030f5cdeb241204174dd981bc62b723958f0db28cc6f8b5f8fdab5a474`.
  - [`feasibility/final-review/evidence.json /cases/sealed_saved_plan_swap`](fixtures/audit-results.json) → `/values/0`, original SHA256 `1ee5ff27592812145b1526b2d70cd36c9754cc74461ed83c4add6dfa2f3530e4`, selected-value SHA256 `cb4ab6bb8bca5832007236b9175f6affd81ab73df43cb9b14b315813c7958c2e`.
  - [`feasibility/gate/apply_input.py lines:1-69`](fixtures/sealing-code.json) → `/values/0`, original SHA256 `651bfe485502122c461e41588b479a96ead10d50ede7b09d03a536d4f7b3fa8f`, selected-value SHA256 `502b1a9090f06227f9229aca3789f12f9a5c2e75f1ad159e77bd4af45e965951`.
  - [`feasibility/gate/gate.py lines:255-281`](fixtures/current-gate.json) → `/values/1`, original SHA256 `37f33708aef5ef78a8fec32d466b04aa46602d7f8c5ff1f2cebc4d464cdb5afb`, selected-value SHA256 `0196a6f287ec2ad27f2382bdb8b9f427802564e1092f7ae09853ad7e232b6a47`.

### A-capture — actual-recorded-effects

The final audit records unchanged material digest and acceptance of changed main.tofu.json after planning; actual_state_input is SYNTHETIC-UNTRACKED-TOFU. Its safe runner excerpt shows same-census literals and subsequent SYNTHETIC-CHANGED-AFTER-PLAN. This is incomplete input capture, not a broken memfd seal.

- Unit: qualitative finding
- Harness: not separately rerun in Stage 0
- Tested system: capture contract falsified; no extra retained deletion demonstrated
- Limits: Retrospective reported evidence, not independently authenticated or complete environmental capture.
- Evidence:
  - [`feasibility/final-review/evidence.json /cases/uncaptured_tofu_json`](fixtures/audit-results.json) → `/values/1`, original SHA256 `1ee5ff27592812145b1526b2d70cd36c9754cc74461ed83c4add6dfa2f3530e4`, selected-value SHA256 `b74ba23314ff3ca86b4b91e2a7a9c30ff2b8a75cb9c40e031594e0a14f52e9a1`.
  - [`feasibility/final-review/audit.py lines:132-145`](fixtures/audit-code.json) → `/values/1`, original SHA256 `5fa39c336aeb2fdd9a01e17046722102e82ecf1a51ce5659ae5877d7dc4ddacd`, selected-value SHA256 `ccd5e71f85d26c33842d8d335c7ae63865269585dbcf81edef3d84f5ba341383`.
  - [`feasibility/gate/gate.py lines:62-76`](fixtures/current-gate.json) → `/values/0`, original SHA256 `37f33708aef5ef78a8fec32d466b04aa46602d7f8c5ff1f2cebc4d464cdb5afb`, selected-value SHA256 `d21b91963028373c7a5bd4cd11dbcee11eda1153aacbccdf643e358a4868b563`.

### A-counts — actual-recorded-effects

The follow-up reports 28 regression groups, 22 adversarial groups, 4 historical replay groups and 285 OpenTofu CLI invocations. Final audit reports 55 built-in plus 18 bridge CLI calls. These are not additive test counts.

- Unit: groups and CLI invocations (separate units)
- Harness: follow-up passed=true; final audit completed=true
- Tested system: includes probes that demonstrate unsafe behavior
- Limits: Retrospective reported evidence, not independently authenticated or complete environmental capture.
- Evidence:
  - [`feasibility/gate/followup-test-results.json /counts`](fixtures/followup-results.json) → `/values/2`, original SHA256 `70edb830ab82adba37620a405258a08d866f4c03cb374683d3121113e33b3f67`, selected-value SHA256 `5c100946ae44cbae95b63dd37c70ad7b03a48c8dee5501f840e293f978b50486`.
  - [`feasibility/final-review/evidence.json /cli_calls`](fixtures/audit-results.json) → `/values/6`, original SHA256 `1ee5ff27592812145b1526b2d70cd36c9754cc74461ed83c4add6dfa2f3530e4`, selected-value SHA256 `4c82a221b575ce7fe118b2e8cdf0764bf4ef570a3017e80b6d3438af9095f376`.
  - [`feasibility/final-review/evidence.json /bridge_cli_calls`](fixtures/audit-results.json) → `/values/7`, original SHA256 `1ee5ff27592812145b1526b2d70cd36c9754cc74461ed83c4add6dfa2f3530e4`, selected-value SHA256 `7ee29791fc17e986b97128845622b077fb45e349fdb80523fac9dba879b4ad60`.

## B. Adoption is not creation

### B-ordinary — actual-recorded-effects

local_file import reported Resource Import Not Implemented. The following create changed execution-created-content to configuration-content, overwriting the artifact.

- Unit: qualitative finding
- Harness: not separately rerun in Stage 0
- Tested system: unsupported adoption followed by destructive overwrite
- Limits: Retrospective reported evidence, not independently authenticated or complete environmental capture.
- Evidence:
  - [`feasibility/opentofu/evidence.json /probes/local_adoption`](fixtures/local-adoption.json) → `/values/0`, original SHA256 `3ad42d841e2261b72dae6d050d36af2eeed52d29d4c2f869450a1aea42f5858a`, selected-value SHA256 `eb6d3cbccbd8bd04559228db5d96636348ebd8a77034d65dc5d6ebaefa9acbe4`.

### B-surrogate — actual-recorded-effects

The built-in terraform_data adoption example is explicitly surrogate=true and reconciles with an update; it does not prove external-file byte preservation.

- Unit: qualitative finding
- Harness: not separately rerun in Stage 0
- Tested system: real CLI state-only surrogate, not actual artifact adoption
- Limits: Retrospective reported evidence, not independently authenticated or complete environmental capture.
- Evidence:
  - [`feasibility/opentofu/evidence.json /probes/surrogate_import/surrogate`](fixtures/local-adoption.json) → `/values/1`, original SHA256 `3ad42d841e2261b72dae6d050d36af2eeed52d29d4c2f869450a1aea42f5858a`, selected-value SHA256 `a17fcf0a2f50e2d495e4f90ce263410edc183add6c62699a2facbccf60410f74`.
  - [`feasibility/opentofu/evidence.json /probes/surrogate_import/cli_reconciliation_actions`](fixtures/local-adoption.json) → `/values/2`, original SHA256 `3ad42d841e2261b72dae6d050d36af2eeed52d29d4c2f869450a1aea42f5858a`, selected-value SHA256 `becc7569c8e7657f2bfed07d659791350489c7690c227169c4211da5298966f3`.

### B-provider — actual-recorded-effects

The custom provider results report actual CLI/declarative import, bytes/inode/mtime preservation during metadata update, lost-state re-import, and real SIGKILL recovery. The independent same-file bridge additionally records import_preserved_bytes_inode_mtime=true.

- Unit: 52 CLI invocations in artifact suite; qualitative preservation assertions
- Harness: not separately rerun in Stage 0
- Tested system: narrow actual provider adoption; forced replacement still deletes before Create fails
- Limits: No numeric before/after byte digest, inode or mtime is present in the allowlisted adoption result. Reported checks are inspectable assertions, not raw receipts. Stage 0 did not rerun provider or inspect state.
- Evidence:
  - [`feasibility/artifact/test-results.json `](fixtures/artifact-results.json) → `/values/0`, original SHA256 `3da0773c08cf21c4d42fccf922e09f904891b9fb82df0d8b4490045b426c660a`, selected-value SHA256 `58e015256d904d11603fe764058d88786159872fde6802ca6dba622fc1c3cf19`.
  - [`feasibility/final-review/evidence.json /cases/same_file_sealed_provider_journal_bridge`](fixtures/audit-results.json) → `/values/2`, original SHA256 `1ee5ff27592812145b1526b2d70cd36c9754cc74461ed83c4add6dfa2f3530e4`, selected-value SHA256 `51f1505829b7754235906c9885ee5150eb7dfc475d9dc44333c139875d97bd8a`.

## C. Unknown outcome and separate cleanup/computation

### C-unknown — actual-recorded-effects

The initial gate records process exit 73 after an effect with durable_status=unknown, empty manager manifest and no automatic acknowledgement. Another case exits before side effects; unknown is not a failed outcome.

- Unit: qualitative finding
- Harness: not separately rerun in Stage 0
- Tested system: effect-start uncertainty stays durable, not automatically failed
- Limits: This gate uses a fake policy journal; it does not supply research request/attempt IDs or a computation result.
- Evidence:
  - [`feasibility/gate/test-results-initial.json /cases/completed_effect_unknown_outcome`](fixtures/initial-results.json) → `/values/0`, original SHA256 `9ee92e3561d17692538252f5138b5843bab532c9369bd27fa480ee0c8b7cefaf`, selected-value SHA256 `c7c8fc6be324974bebcc7da155ad09eb5e1a9007ab5d341c9fa569e3ed8adb42`.
  - [`feasibility/gate/test-results-initial.json /cases/interrupted_apply`](fixtures/initial-results.json) → `/values/1`, original SHA256 `9ee92e3561d17692538252f5138b5843bab532c9369bd27fa480ee0c8b7cefaf`, selected-value SHA256 `db1f172ef11d1651104fa9c26518d708ea950e93b449cf2ffbeabe64abd9156f`.

### C-physical-recovery — actual-recorded-effects

The joined provider bridge records SIGKILL exitcode=-9 after unlink: file_absent=true, journal_status=intent and manager_still_records_resource=true. Later recovery records actual absence and ticket_status=acknowledged with historical association retained.

- Unit: one reported SIGKILL/recovery sequence
- Harness: not separately rerun in Stage 0
- Tested system: disposal completed before durable receipt; later acknowledged
- Limits: Physical cleanup sequence is not the model computation trial. No timestamped full progress stream is imported; final audit did not repeat this SIGKILL.
- Evidence:
  - [`feasibility/hardening-review/evidence.json /review/cases/integrated_SIGKILL_after_provider_effect`](fixtures/bridge-results.json) → `/values/1`, original SHA256 `ba129dc87755f2c0f58c84b7102abf31d9792f4f815cc092d892baadadba3536`, selected-value SHA256 `75aa1291870e6c718e42d294bfd86bd3b4af6989fdc366e013e90e569a3070ca`.
  - [`feasibility/hardening-review/evidence.json /review/cases/integrated_recovery_and_historical_association`](fixtures/bridge-results.json) → `/values/2`, original SHA256 `ba129dc87755f2c0f58c84b7102abf31d9792f4f815cc092d892baadadba3536`, selected-value SHA256 `cfdc2e405b3cc8cbd752a9bb991648ae08a07abe0ea9788c660fa602b80f0c2d`.
  - [`feasibility/hardening-review/evidence.json /review/cases/immutable_history_versions_management_states`](fixtures/bridge-results.json) → `/values/3`, original SHA256 `ba129dc87755f2c0f58c84b7102abf31d9792f4f815cc092d892baadadba3536`, selected-value SHA256 `81cc562326c2b8496c2bee5e7267d423dfcf871a69b08e8593173ae35c4d9a01`.

### C-creation-history — actual-recorded-effects

Archived journal-v1 reports one unregistered orphan and no recovery after creation-before-registration. v2 reports zero unregistered orphans and recovery after creation-before-receipt, but same-byte pre-receipt replacement remains ambiguous.

- Unit: qualitative finding
- Harness: not separately rerun in Stage 0
- Tested system: durable intent narrows orphan gap; hostile replacement still not proven safe
- Limits: Retrospective reported evidence, not independently authenticated or complete environmental capture.
- Evidence:
  - [`feasibility/journal/evidence-v1.json /latest/crashes`](fixtures/journal-v1.json) → `/values/2`, original SHA256 `723cd026cd80be8ce7c67c729a2d3c3e745c6015e07beaa127dcbc66184d28dd`, selected-value SHA256 `be45536a18eb1c115a3780a5b490b394f946ab2c0dc228c0890637802aced9f1`.
  - [`feasibility/journal/evidence.json /latest/baseline_crashes`](fixtures/journal-v2.json) → `/values/1`, original SHA256 `8917e01bfd4229361f22de07c3d8b4788d1dc8fb3a83e3cc4f12147ce11a1fe2`, selected-value SHA256 `46c2fbef1d57c2c6f067a0412824396c6696f0ad7256c2d36313eaf0f35dc523`.
  - [`feasibility/journal/evidence.json /latest/followup_observations`](fixtures/journal-v2.json) → `/values/2`, original SHA256 `8917e01bfd4229361f22de07c3d8b4788d1dc8fb3a83e3cc4f12147ce11a1fe2`, selected-value SHA256 `d29a95edb22d17414da11b02eb6dbbb4815e0d4b08d99f1fba9396a5b41e48e2`.

### C-computation — simulation

Only the history simulation supplies request/attempt progress with unknown after crash, working/working/done, computation success and cleanup failed. Later simulated remediation keeps the same attempt and original failed cleanup. Do not splice this computation into the physical bridge.

- Unit: simulated request/attempt lifecycle, not OS process effects
- Harness: not separately rerun in Stage 0
- Tested system: successful computation and failed cleanup coexist in model
- Limits: Retrospective reported evidence, not independently authenticated or complete environmental capture.
- Evidence:
  - [`feasibility/history/scenario-results.json /scenarios/5`](fixtures/history-results.json) → `/values/5`, original SHA256 `ae2a4c1d9a3a44bc84497d27e87e5f8bb4e2830faf93a4b5a4c96ae4a1d79e97`, selected-value SHA256 `6429df8007c0e093d7efd3d2b59f3dec340983404c3b4a7857243ea07707a042`.
  - [`feasibility/history/scenario-results.json /scenarios/6`](fixtures/history-results.json) → `/values/6`, original SHA256 `ae2a4c1d9a3a44bc84497d27e87e5f8bb4e2830faf93a4b5a4c96ae4a1d79e97`, selected-value SHA256 `736b919281504ac9579b7d5dde66d156e8768f421bd93b5f99f6504c83e834bc`.
  - [`feasibility/history/scenario-results.json /scenarios/7`](fixtures/history-results.json) → `/values/7`, original SHA256 `ae2a4c1d9a3a44bc84497d27e87e5f8bb4e2830faf93a4b5a4c96ae4a1d79e97`, selected-value SHA256 `9df8391bc1681a5e7a107e90f55a9d7b367d97b1aa4e020359343d674665f80d`.
  - [`feasibility/history/summary.json /limitations`](fixtures/history-summary.json) → `/values/1`, original SHA256 `c56484e9215b2a55686546cdc0b4cf54a3233671a79dc84d83381f33a76ebf17`, selected-value SHA256 `d156a6e8d9ce0cfa93de79b3ebe75da534b33c60349c1c89a0dd6d5109aaa181`.

## D. Reuse and identical results do not define occurrence identity

### D-fresh — simulation

Recorded model scenarios have distinct requests and attempts but result_roots=1; the content-only counterexample has actual_trials=2 and naive_unique_records=1. Safe runner source confirms two fresh calls.

- Unit: 2 simulated requests; 2 simulated attempts/trials; 1 result root
- Harness: not separately rerun in Stage 0
- Tested system: content deduplication does not collapse legitimate attempt identity
- Limits: Retrospective reported evidence, not independently authenticated or complete environmental capture.
- Evidence:
  - [`feasibility/history/scenario-results.json /scenarios/1`](fixtures/history-results.json) → `/values/2`, original SHA256 `ae2a4c1d9a3a44bc84497d27e87e5f8bb4e2830faf93a4b5a4c96ae4a1d79e97`, selected-value SHA256 `9fdd1352560a7822958587f2f940e0bc7a7f48d82f6431f16a30d8de8431d4b6`.
  - [`feasibility/history/scenario-results.json /scenarios/2`](fixtures/history-results.json) → `/values/3`, original SHA256 `ae2a4c1d9a3a44bc84497d27e87e5f8bb4e2830faf93a4b5a4c96ae4a1d79e97`, selected-value SHA256 `d69c28c5647054dcbeddda9c2de388635418d1f51691c6b4c0210c851dd93c76`.
  - [`feasibility/history/run_scenarios.py lines:28-73`](fixtures/history-scenarios.json) → `/values/0`, original SHA256 `fedcd68a0a0845ad4a0cfa7db779828d687415a7e49fcdb62b76c9afc6679eaf`, selected-value SHA256 `7dbf746b486ff84c293c8d190df2a0577dc0f4732f23f80600bf7f991d64fdfc`.

### D-reuse — source-inspection

The reported reuse scenario selects the original attempt. Source inspection of the model test constructs two requests sharing one successful attempt, then a fresh attempt raises reachable attempt count to two. Exact two-request/one-attempt counts are source-derived, not a new physical or Stage 0 execution.

- Unit: source-derived 2 simulated requests; 1 reused attempt; 1 modeled execution before fresh branch
- Harness: not separately rerun in Stage 0
- Tested system: reuse adds no independent trial
- Limits: Structured scenario output lacks emitted request IDs and exact reuse request count. Summary reports 24 passing model tests but does not independently authenticate this individual test trace; source is not a retained execution transcript.
- Evidence:
  - [`feasibility/history/scenario-results.json /scenarios/3`](fixtures/history-results.json) → `/values/4`, original SHA256 `ae2a4c1d9a3a44bc84497d27e87e5f8bb4e2830faf93a4b5a4c96ae4a1d79e97`, selected-value SHA256 `2b6571f43104a8929abcf6a6be26d8067c818c0ca1d7559a7b660499d255e37b`.
  - [`feasibility/history/test_model.py lines:90-109`](fixtures/history-tests.json) → `/values/1`, original SHA256 `258eaefb6d078e45fb0731b05d310f93b5cccf70431cafb1195b232756228457`, selected-value SHA256 `5dfcad6ebcf645c2ae27e844ae7fa1f1cf07eb16a526279576165fcb6820d265`.
  - [`feasibility/history/summary.json /tests`](fixtures/history-summary.json) → `/values/0`, original SHA256 `c56484e9215b2a55686546cdc0b4cf54a3233671a79dc84d83381f33a76ebf17`, selected-value SHA256 `18438637b03d5b41855000e24da871551880617dc0976390660b35b2ddf4db21`.

### D-hidden — simulation

The model explicitly records one modeled attempt hiding two simulated executions; the discrepancy is not detectable without executor reporting.

- Unit: 1 modeled attempt; 2 simulated executions
- Harness: not separately rerun in Stage 0
- Tested system: attempt count alone is not complete external execution accounting
- Limits: Retrospective reported evidence, not independently authenticated or complete environmental capture.
- Evidence:
  - [`feasibility/history/scenario-results.json /scenarios/10`](fixtures/history-results.json) → `/values/9`, original SHA256 `ae2a4c1d9a3a44bc84497d27e87e5f8bb4e2830faf93a4b5a4c96ae4a1d79e97`, selected-value SHA256 `dd6ade3bf3a8d0e53c1a0d0f9f85cf47fa7b082399e821f6c9ae0e415f5aff8e`.

## E. Evidence classification and unavailable material

### E-s3 — source-inspection

The S3 findings are pinned-source inspection claims: metadata/content-changing updates can select empty bytes without configured body; versioned deletion calls all-version cleanup for the matching key. The source manifest pins AWS v6.70.0 at 5e13eedee7c22ac362e6ffdfbdcfd23a5f9f797f. cloud_executed=false.

- Unit: qualitative finding
- Harness: not separately rerun in Stage 0
- Tested system: not a cloud-tested result
- Limits: Primary source bundles under ignored runtime are metadata-only, not loaded or rehashed. Frozen manifest authenticates neither download nor claim; safe source notes remain authored interpretation. No external URI fetched.
- Evidence:
  - [`feasibility/adversarial/summary.json /evidence`](fixtures/s3-summary.json) → `/values/0`, original SHA256 `f3e096709be77e3b39e20e4b42f493fb9cd9f7ee0a04a9a606e16180809f4a3c`, selected-value SHA256 `9844ed16b369214f77cae65528d69632dfd93c8a0fbe94d0c3087739ffc37d61`.
  - [`feasibility/adversarial/summary.json /strongest_findings`](fixtures/s3-summary.json) → `/values/1`, original SHA256 `f3e096709be77e3b39e20e4b42f493fb9cd9f7ee0a04a9a606e16180809f4a3c`, selected-value SHA256 `aa25a5a959c7d33245de4d911bdcfc6b7df7fe31a35a048075268fec6e5fd774`.
  - [`feasibility/adversarial/sources.json /aws_commit`](fixtures/s3-manifest.json) → `/values/1`, original SHA256 `a99832c393b2a295e587353361b4a4ac95bd5fee8b7eb9f32448e6e7a9d63058`, selected-value SHA256 `4a7b297802f89fc2bba18752514c48fa1c478efad71316ad39650edab04fe592`.
  - [`feasibility/adversarial/sources.json /sources/aws_s3_object.go`](fixtures/s3-manifest.json) → `/values/2`, original SHA256 `a99832c393b2a295e587353361b4a4ac95bd5fee8b7eb9f32448e6e7a9d63058`, selected-value SHA256 `5061a5084b77ed9837970dcb296c002f6da9a9413402ac3396df9d650dc05521`.
  - [`feasibility/adversarial/sources.json /sources/aws_s3_delete.go`](fixtures/s3-manifest.json) → `/values/3`, original SHA256 `a99832c393b2a295e587353361b4a4ac95bd5fee8b7eb9f32448e6e7a9d63058`, selected-value SHA256 `3c992dd0225f9ae4c312a025a96ebbf1f612f79e4d0ead8b6efe7386e696f282`.
  - [`feasibility/adversarial/source-notes.md lines:52-94`](fixtures/s3-notes.json) → `/values/0`, original SHA256 `4d5e0130f422ea84934da8bf5b03600e64035ec99a2e5e851103d18a83c627ab`, selected-value SHA256 `e89e6369b7aecd9f3ef37042973786138f5591a7d973f78bb014b01b3e4bc720`.

### E-retirement — simulation

The model retirement example says physical_deletion_evidence=simulated assertion only and sensitive_content_erased=false. It supplies no evidence of actual legal excision or global copy erasure.

- Unit: qualitative finding
- Harness: not separately rerun in Stage 0
- Tested system: simulation of retirement, not actual excision/erasure
- Limits: No genuine excised sensitive data was sought or ingested. Excised/unavailable external datasets are not demonstrated by this corpus.
- Evidence:
  - [`feasibility/history/scenario-results.json /scenarios/9`](fixtures/history-results.json) → `/values/8`, original SHA256 `ae2a4c1d9a3a44bc84497d27e87e5f8bb4e2830faf93a4b5a4c96ae4a1d79e97`, selected-value SHA256 `9e98a64c2ef37ce05a8a0540b62bfc4c81f94639a711370695fff291713e5356`.
  - [`feasibility/history/summary.json /limitations`](fixtures/history-summary.json) → `/values/1`, original SHA256 `c56484e9215b2a55686546cdc0b4cf54a3233671a79dc84d83381f33a76ebf17`, selected-value SHA256 `d156a6e8d9ce0cfa93de79b3ebe75da534b33c60349c1c89a0dd6d5109aaa181`.

### E-availability — authored-claim

Original sandboxes and primary-source copies are separate locators; this package retains only selected safe reported evidence. Current availability is a separate Stage 0 lstat observation stored in manifest.json, not a historical availability event. External URLs remain unqueried.

- Unit: qualitative finding
- Harness: not separately rerun in Stage 0
- Tested system: original evidence may be missing, restricted or disappear without destroying frozen fixtures
- Limits: lstat presence establishes no content hash, readability, completeness or authenticity. Missing at Stage 0 is not proof of historically missing, excised or failed.
- Evidence:
  - [`feasibility/final-review/evidence.json /sandbox`](fixtures/audit-results.json) → `/values/10`, original SHA256 `1ee5ff27592812145b1526b2d70cd36c9754cc74461ed83c4add6dfa2f3530e4`, selected-value SHA256 `98ce99660682e163e490e6659d8e911f396d863ad500e1308690680e448cb17e`.
  - [`feasibility/final-review/evidence.json /sources`](fixtures/audit-results.json) → `/values/3`, original SHA256 `1ee5ff27592812145b1526b2d70cd36c9754cc74461ed83c4add6dfa2f3530e4`, selected-value SHA256 `8c157ee5efc92b54d602271f383eeca8acc29ad75b1520708ba516226be39b01`.
  - [`feasibility/hardening-review/evidence.json /source_manifest`](fixtures/bridge-results.json) → `/values/6`, original SHA256 `ba129dc87755f2c0f58c84b7102abf31d9792f4f815cc092d892baadadba3536`, selected-value SHA256 `995c82871e1299345b21dd714d3aec74786677f649dedcf331c674f155aed628`.
  - [`feasibility/adversarial/sources.json /sources/aws_s3_object.go`](fixtures/s3-manifest.json) → `/values/2`, original SHA256 `a99832c393b2a295e587353361b4a4ac95bd5fee8b7eb9f32448e6e7a9d63058`, selected-value SHA256 `5061a5084b77ed9837970dcb296c002f6da9a9413402ac3396df9d650dc05521`.

## Evidence gaps

See [gaps.json](gaps.json) for exact citations and [manifest.json](manifest.json) for bounded supporting-path availability.
