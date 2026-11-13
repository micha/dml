# v49 evidence descriptor/bootstrap audit — source-only, no edit/run

Actual owning sources reviewed: p.Request frozen dataclass564 fields base/decision_commit/commit/
request/request_id/closure/inputs/plan/action/selected/reused. inspect_reuse688 validates exact W and
returns SAME Request from inspect_request(cq,request); Request.commit IS actual owning Cq, not controller
JSON submission. inspect_completion returns dict; Selection in reuse_selection dataclass actual fields
commit/dag/validation/slot/completion/request/attempt/result/intent_uri/binding/inputs/attempt_id.

## Exact proposed evidence-only corrections

1. source_metadata: `hitReq=p.inspect_reuse(SOURCE,commit=hit)` ONCE; `selected=hitReq.selected`;
   `completed=selected["completion"]`; independently
   `nativeQ=p.inspect_request(SOURCE,commit=hitReq.commit,request=hitReq.request)`.
   Assert nativeQ actual Request and (commit,request,closure,inputs.dag,plan,action) equal hitReq's
   fields and action reuse-selected; old got.completion own success/A closure must differ nativeQ B.
   No repeated reused lookups/nonexistent submission/guessing JSON spelling.
2. Audit caught ONE additional existing probe mistake BEFORE launch: `actual.action=="fresh"` is
   wrong; control string fresh resolves native action **execute-fresh** (inspect_completion833 and
   resolve/record_request actual). Change ONLY exact positive to `actual.action=="execute-fresh"`,
   preserving reusedNone and native fresh-B Q/dimensions positive. Not weak guessedalias/pass flag.

All other accessed descriptors matched sources: backend.current/closure/inputs; Request.commit/
request/reused; Bound(kind,intent,target); Description.dag; selected dict completion/request/closure;
Selection.dag/result/request/inputs/binding. p.inspect_completion dict calls/request/closure/outcome,
PUBLICreturned Inspector.value; actual double contract tuple keys count1; native get_ref/get_dag
bindings/put_subdag/public rewrite methods current. V2 only scalar upstream-slot change, no futureDag.

Bootstrap actual tests/conftest.__file__ /ROOT currentcheckout, PACKAGE current source/__init__.py,
BUILD DML_BIN existingbuild/check/dml and _core build/check; full source/native hashes retained v49.
No conftest/runtime/helpers/package/init/bootstrap copy/install/build/shared source change needed.
Original v48collection/v49readfailedprobe/source/seedhash stable retained. No newQ/seed mutation yet.

Status STOP pending explicit correction+ONE same TWO-case evidence-only completion review. No source
patch/run authorized by this audit; no othercases/HOST/OS/seed/standardfull/story/install/CI/push.
