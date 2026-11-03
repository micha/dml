# Iteration24 first activation failure — finite READ-ONLY triage / correction proposal

Status: **historical failure/triage/plan preserved; controller-only correction approved and checked**.
See [corrected readiness](CORRECTED-READINESS.md) for current source/29checks/new metadata receipts.
Fresh story/readers/full/publication remain HOLD pending separate activation decision.
SAME worker/session/model, BOTH/source/builds/prefix/evidence worker-owned.

## Actual activation and SAME retained native state

Exact once-authorized command/start/end/trueexit/stdout/stderr:
`../dml/build/iteration24/acceptance/activation/`. Start2026-11-03T02:50:08.915436465Z,
end02:50:09.136936190Z, trueexit1. Primary traceback identifies controller195
`events.append(dict(kind=kind, **row))`: phase receipt already has `kind=get-a`, so duplicate
keyword raises TypeError after the native phase storage commit. No Native19/LMDB/VP001 diagnosis.

ONE finite installed READ-ONLY probe `acceptance/triage/probe.py` command/start/end/stdout report/
stderr/exit retained. Exit0, blocker-FIRST spawn/http/urllib/connect plus target-write/recording/
dispatch/Recorder/logical blockers; no source/arithmetic execution/newQ/T/target write. Public typed
reads/nonexecuting validators establish:

- Owned main/input/swapped/outer-1-decision/outer-1/request-reservation/outer-head refs checked.
  Dcommit47425885d485f9dfe6311a1ccefbf456; Qcommit8bb224da19d5c529757337de91ba2eb3;
  Q4673e790f73e04c4db528b868adff7ac, occurrencecq-cc8627d6042442d39810db8e782ebe5f.
- InitialT525f1c134e5fb471105b02b2e3e718c8, occurrenceca-27edda97742143449e51422fa8eca3ca,
  immutable role/request/plan only, no done/status. Actual owned headb24faa6f26b71bec3e0be512ea15475c
  has exact single initial-commit parent43227a33401dc6b91dbb9a606f8171d1.
- Native phase00 get-a dbed109676c145c829357370cb272e3f, exact Q/initialT/index0/previous/role,
  exactly phase+node payload additions, all old tree entries preserved. Getter043f0f08eeeafb2897b1a219d781ff66
  stores I64 13 (typed literal read, not arithmetic). `inspect_request` and `inspect_spine` agree:
  execute-fresh, same plan, one getter, zero ordinary calls, no return/failure/terminal.
- ALL-parent seven commits:1outerQ/1initialouterT/1getter,0leafQ/0LOCAL T/0publication/0outerterminal.
  Story/outer2/3/4 refs absent. Full ALL-parent census is distinct from incomplete TWO event rows.
- Final-disposition children[], noautomaticretry=true, outercomputationfinished=false. Execution1
  directory is EMPTY; no leaf directories/worker repositories. Current exact target argv owners
  ZERO in finite `/proc` sample; no historical PID signalling/reaping. Original wrapper PID was
  not recorded; true owning command exit/end and empty tracked-child disposition are retained.
- Failed caller data SHA256 before=after92d7d1abdd85b5385fd604f1a4fa87b1e645bd018733b324881f88878c67c508.
  Actual installed/interpreter/ten operational+captured helper/controller source hashes match original
  prelaunch metadata. `triage/custody-sample.json` retains primary identities/process sample.

Actual outcome: **partial outer UNKNOWN**. get-a is durably recorded; its event callback failed.
The event log is INCOMPLETE, not a full native history. No leaf launch/wait/custody occurred; zero-child
proof is Native zero-leaf census + empty owned paths + final tracked disposition + process sample,
not merely absence of events. Keep every original failed byte/context/path/hash/log; do not reuse
this failed Q/T/getter as a successful restart context or erase/overwrite it.

## Proposed controller-only correction (NOT edited/approved yet)

Use a distinct flat event-envelope key `event` for category; retain payload `kind` for phase kind.
For example, REAL phase row becomes `{event: "phase", kind: "get-a", commit: ..., previous: ...,
links: {node: ...}, index: 0}`. No dict-overwrite or dropped kind. Reject reserved payload key `event`
explicitly BEFORE appending/writing the event. Keep `Session._phase` and all native profiles/helper/
adapter/logical/source/bounds/deadline/custody behavior UNCHANGED; this is controller serialization.

Extract a small controller-specific event-append function used by the actual callback, enabling direct
regression of identical code. Dispatch/leaf-run control branches continue to use the callback CATEGORY,
not phase payload kind; exactly one permission and per-child native barrier remain unchanged.

Review/update together ONLY the owning consumers:

1. `installed_story.py`: event append and `verify_custody`'s four dispatch/spawn/wait/verified category
   filters use `event`; all payload request/PID/native command/source/wait comparisons retained.
2. `test_captured_call_tooling.py`: event fixture categories use `event`, existing negative controls
   remain exact. Add category/phase-kind persistence and reserved-key refusal tests.
3. Informative controller guide/source identities mention the envelope distinction. `offline_read.py`
   delegates to owning controller, has no direct category filters; no algorithm change assumed.
4. The failed two-row old-format log remains HISTORICAL exact bytes, not rewritten or silently parsed
   as new successful evidence. No generic event framework/schema/runtime API/automatic compatibility.

## Finite validation proposal BEFORE any future activation

Only after separate correction GO: ONE blocked metadata-only fixture calls actual current public
request authoring, `Session`, and REAL `Session.map_get(input,"a")`/`_phase` callback through the new
controller append function, with leaf-Q/dispatch/spawn/transport blocked. It captures the REAL emitted
row and independently checks native phase/payload/head/parent/getter value exactly. Assert both
`event=phase` and `kind=get-a` in actual JSONL, not a synthetic row-only proof; there is ONE new metadata
Q/T/getter and ZERO ordinary/LOCAL/OS computation. This proposed metadata population is NOT currently
run/authorized by read-only triage, and does not retry the failed installed context.

Predicted old-source negative: the SAME real `_phase` row passed to old append raises duplicate-kind
TypeError. New append preserves category+payload and completes the native-positive receipt regression.
Reserved `event` payload rejects without mutating event list/log. Existing custody primary ordering/
request/PID/source/command/wait negative controls run against the new envelope; no skip/threshold change.
Targeted source/static/link/current-TEN metadata readiness refresh only after accepted correction.
Any fresh once-installed launch/full remains a NEW explicit coordinator gate; no automatic retry.

GHAoff/native19PAUSED/VP001OPENUNKNOWN, no older diagnosis/waiver/budget/runtime/extra-worker change.
