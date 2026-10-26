# Fresh cross-model final audit

Read ../WORKER.md, ../ITERATION.md and ../CANDIDATES.md. Own only
feasibility/final-review/. This is a bounded final audit of an extensive completed
study, not a mandate to build another framework. No new dependencies/cloud/system
operations, other worker edits, or commits. Finish a concise report and atomic done.

Context: first feasibility study and candidate journal/provider/handoff review are
complete. A targeted gate fix is complete. The resumed hardening reviewer suffered
two model-provider internal-server errors before publishing its followup marker;
partial scripts/results are under hardening-review/. Do not treat that failed
followup as a completed independent audit. You are a fresh different-model reviewer.

Read reports/summaries selectively, especially:
- journal/report.md + summary.json: v2, 35 tests, append-only hashed snapshots and
  pre-effect creation intent, real kills; v1 preserved and rejected for new databases.
- artifact/report.md + summary.json: actual Go provider, 52 CLI calls, bytes-
  preserving import; forced replacement still deletes before Create fails.
- gate/report.md + summary.json + followup-done.json: sealed memfd approved plan,
  fixture-only expression whitelist, pre-effect resource census, body-free logs;
  28 regression/22 focused/4 historical groups, 285 real CLI calls.
- hardening-review/report.md: actual same-file journal/provider handoff via FileGate,
  SIGKILL recovery, prior plan-swap counterexample and remaining limitations.

Inspect changed gate/apply_input/fixture_language code and independent followup
scripts. Preserve source hashes. Independently run a SMALL focused set (roughly
4–8 cases), not another 285-call full suite or unchanged artifact suite:
1. Actual saved-plan swap at final-check barrier against current gate; approved
   victim can disappear, extra retained object must survive. Inspect actual argv/
   inherited sealed descriptor and Linux write/grow/shrink restrictions.
2. Unexported resource and file()/sensitive() expressions reject before effects;
   confirm positive fixture still works. Limit generality claims.
3. Compare FileGate bridge: if it can use the sealed-byte helper, run one actual
   same-file provider/journal disposal in fresh sandbox; otherwise explicitly
   leave positive bridge under original cooperative assumptions.
4. At least one new small adversarial check within claimed scope, or a concrete
   source finding with limits. Keep provider-side Delete authority, direct CLI
   bypass, raw state confidentiality, complete membership/dependencies, and manager
   receipt sidecars visible. Full HCL and native DML remain untested/unsupported.

Existing followup_prepare/checks/run/collect code may help but must be inspected,
not blindly rerun. Frozen source snapshots and already-completed safe results can
be reused if hash-verified and clearly labelled inspected evidence. Allocate only
new owned ignored sandboxes; do not delete existing fixtures. Use short temp paths
for provider sockets. Do not recreate archived failures through unsafe paths.

Report what is independently verified vs inspected vs unresolved. A pass is a
qualified feasibility judgment, not production safety. If an interface prevents
integration, state that rather than fabricating identity mappings. End with the
approaches/decisions worth reviewing in the morning, not a new giant task list.
Keep the final report ~700–1300 words plus machine-readable summary. No unbounded
retries; if this model/tool run fails, deliver a blocked report if possible.
