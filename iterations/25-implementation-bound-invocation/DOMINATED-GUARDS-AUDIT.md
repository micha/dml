# Five exact guard decisions — SOURCE-ONLY, no markers/runtime change

## Session263: conditional implication; copied Request state limitation explicit

Normal constructor54..56 independently re-inspects actual Q at Request.commit, compares entire
Request, requires execute-fresh. inspect_request validates plan basis +inner selectionIDs against
resolve's actual inspect_leaf_success(q.base,knownslot). _invoke_ordinary reads SAME immutable q.plan:
pf.basis is same q.base; pinned is exact S.dag for namedslot; later inspect_leaf_success SAMEbasis/slot
must return same S. No callback between reading pf fields and that successful read. Native records/
commit IDs immutable, cache tuple contains frozen Selection; scratch mayallocate outside source.

BUT Session.q attribute can be replaced by trusted receipt callback between phases. A deliberately
invalid copied Request.plan could reach263; an independently valid OTHER Request still carries a
correct own basis/selection and cannot. Therefore no unconditional impossible-state assertion/no
exclusion selected. Under user no-false-SDK-descriptor constraint test route genuinely blocked; one
needs explicit copied-invalid-Request expectation contract or conditional no-value review. No fake
plan/provider/selection authored to force count. Production source unchanged.

## Profile1112: same pinned S preserved, conditional exact native proof

Reusable prep action derives from actual plan/hit1025..1028. inner_selected[slot] is actual named S
read at q.base. Backward ledger enforces initialT/add-only phases/unchanged existingentries; public
Q and W each exact single-addition delta. W1053 pins inner_selected.dag/T/R. ReuseDONE1098 forces
same named default ADD_SLOT/DOUBLE_SLOT, not arbitrary witness slot. No such existingslot may be
replaced by any accepted delta. Thus current[slot]==base[slot]==inner_selected.dag, and successful
inspect_leaf_success(current,slot).dag is that SAME native S. No externalcallback in this reader;
no Source writes/aliasing live handles; source/limit/function keyed operation-local memo only.
If selected.request differs ownQ, 1112's S inequality cannot hold on accepted ledger. No marker;
independent source proof review/captured-byte consequences still required.

## Profile1114: meaningful COUNTEREXAMPLE, NOT dominated

Own request occurrence is namespace/create-ref fresh, NOT necessarily globally fresh immutable-ID.
Import real successful old history into a NEWcase repo (refs not imported); make current basis tree
omit old producer `request-qid` name while retaining actual S and its full original ancestry. Native
SDK metadata may record SAME old qid/B/input/intent at a NEW Cq in this namespace using explicit
request_id/qualified UUID collision. Q hash dedups to OLD producer requestID, despite NEW metadata
submission; no false descriptor. Current plan chooses reuse, W pins OLD S, DONEdefaultslot and
publicOLDproofs pass; selected.request==ownQ but prep=reuse-selected/joinedNone. 1114 properly refuses
fresh originalQ/joinedF relationship. Draft should test actual native collision, not mark line.
Needs first-stage validation of namespace absence/sourceQ fields/actual q-ID identity/publicW/S,
not a claim executed. No ordinary job necessary. Source protects separate Q occurrence semantics.

## Profile1123: conditional fresh/reuse intent+fullMAP implication

Fresh: pending CALL owner/target/input1037 plus successful public_prepare1078 fixes ownQLocal B/input/
intent; S for SAME ownQ is publicvalidated. inspect_leaf_success confirms returned.inputs==S.inputs,
exact target closure and original capture/input identity. Thus selected intent/fullMAP equals request.
Reuse: at preparation1016..1028 selected_old same pinnedS +actual fullMAP/key equality determine
reuse-selected. W1053/defaultslot1098/unchanged namespace delta1112 proof preserve SAMEselectedS;
no source input changes through accepted phases. Hence equality rechecked1123 is implied. Memo
retains completeIDs/depth/limits and native scopes owner-bound; no externalcallable/logical callback
between these native checks. SDK preparation return contract violation is separately tested535/1078;
if independently real OTHER spec can pass dimensionchecks while changing intent assumption, proof
must be rejected—not force private inspector. Conditional candidate only/no marker.

## Profile834: exact initial/Q/F plan/action implication

Completion reads F.request/F.initial/F.plan; prelude808 requires initial.request==F.request and
initial.plan==F.plan. inspect_spine930 on SAME initial/request/aid requires actualQ actionexecute-fresh
and actualQ.plan==initial.plan. Returned spine.submission is that exact immutable Cq. Repeat
inspect_request(path,Cq,F.request) at832 must return same action/plan. Entire inspect_completion is
ONE operation-local _inspection_proof scope, function/path/commit/request/depth/limits keyed; nested
successful reads retain unions/owner-state, no navigation through mutable ref values. No supplied
backend/receipt/logicalcallback in reader; temporary SDK validation allocation is scratch only, not
Source graph/nativeIDs. F, initial, Cq and request pinned IDs cannot mutate between930 and834.
Shared returned memo dictionaries require independent scrutiny, but frozen Request.plan/action not
an externally handed mutable expectation during this internal call. Candidate no-value raise only,
not guardcondition/test skip/threshold approval.

## Additional concrete coupling found: Profile539

The proposed changed-x literal route does NOT reach539: at527 selected.inputs must equal prefix
constructed double_inputs; inspect_spine982 has already proved that map's x source is exact first
call R. Firstcall1116 has certified R from selectedS. At531 same firstcall selection/slot must equal
D.upstream/slot; unchanged ledger/delta retains that SAME S in basis. Thus later upstream read returns
that S/R and firstcall capture contract requires ADD intent. This suggests repeated source/producer
checks539 dominated by exact prior-source proof, not an available literal-transplant test. Conditional
candidate proof only; no marker/claim100, no fake altered prefix result/selection descriptor.

## Consequences / no edit

No markers approved. Any inline profile pragma changes cb9196 source/captured outerB payload/hash/
TEN/finalsource/install; any Session pragma similarly changes captured adapter integration bytes.
Complete AST INCLUDINGlocations equality can preserve behavior but not source/capture identity.
Current v52 successful history/reader evidence remains exact executed OLDbytes; no forced rerecord/
reinstall/reader replay implied, no silent newhash100. Prefer tests for genuine cases, independent
proof/engineering disposition required for conditionally dominated candidates. SourceBOTH ours,
model/sessionOFF/agent unchanged, no native read/test/report/OS/full/story/build/CI/push.
