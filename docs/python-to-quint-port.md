# Python-to-Quint port: active work order and session handoff

**Priority: exclusive until complete.** Port the checks in the Python tests to Quint and clean up the superseded tests and machinery. No unrelated features, fixes, refactors, or tooling work. This work order owns migration scope and progress, not the product specification. The [validation policy](validation-policy.md) owns the gate; the [test guide](../tests/README.md) describes the existing interpreter and suites.

## Resume here

- Baseline: `f595d97` on `implementation-bound-invocation`. Baseline line numbers below remain usable after deletions: e.g. `git show f595d97:tests/test_recorded_calls.py`.
- **Packet 1 is complete**; see its [live evidence](#packet-1-evidence). Resume at **packet 2**: start with the stored-result and outbound transfer cases, sharing the false-arithmetic fixture in Quint. Read only the relevant methods, histories, rules, and interpreter commands. Preserve the distinction between a stored result and a fresh computation.
- The user wants reviewable behavioral evidence, not a translation from one large imperative suite into another. Quint specifies the requests, expected outcomes, and required scenarios. Python may execute a requested operation and report observed facts. Do not add Python tests, a Python driver per scenario, or Python code that decides correctness and returns a verdict disguised as evidence.
- First try existing commands in the shared trace interpreter. Keep one core API call per core step. Use workflow commands for actual application operations. If an operation or observation is missing, identify the exact property, why the current evidence cannot distinguish right from wrong, and the smallest proposed interpreter change. Discuss it before building a workaround or weakening the check. Do not silently waive a guarantee.
- Size work by **working context**, not method count. Approval of a packet covers its ordinary steps; do not ask for permission after each case. A context handoff should record the last completed obligation, remaining obligations, decisions, and actual validation results. Escalate a design decision, not routine continuation.

## How to close an obligation

For each guarantee, record **baseline `file:line` and subcase → Quint history/step → rule distinguishing the wrong outcome → actual result**. A currently exercised history and sufficient rule require no new test. If a method has several guarantees, close them separately. A model check, synthetic rule control, or similar test name is not evidence that the implementation exhibits that behavior. Synthetic controls are useful *in addition* to replay.

Use focused validation while working and `scripts/check.sh --quint` for the final relevant sources. Preserve installed-consumer validation for the public binding. Do not count missing, skipped, or failing checks as passed. Remove a Python check and its obsolete registration only once all its obligations have a disposition. Review the diff for scenario logic or assertions newly hidden in Python.

## Decisions that affect the size of the port

1. **Application report versus stored graph.** CLI output and `data.mdb` byte comparisons do not independently establish exact commit parents, tree entries, DAG roots, node kinds, or object collection. Packet 1 added [individual native reads on the workflow repository](../tests/README.md#recorded-calls) through `tests/replay_core.py`. Quint can compare the native IDs with the CLI's reported IDs. Do not infer a physical edge from the application's own JSON.
2. **Execution versus inspection.** `checkCalls` in `tests/recorded_calls_rules.qnt` correctly expects arithmetic for execution. Inspection of a deliberately stored `2 + 3 → -17`, scale-by-6 `→ -98` must return `-17` and `-98`. Use a stored-evidence rule rather than weakening the execution rule. When executing scale against the stored `-17`, the newly computed result is `-102`.
3. **Rejection versus cause.** `rejectedWriteVerdict` checks a diagnosed failure and unchanged state, not necessarily the expected reason. Set up the *other* guards to succeed. Distinguish no directory, an initialized empty repository, an absent ref, and a swept object. Preserve meaningful CLI exit/stdout/stderr and independent pre/post observations. An aborted transaction used to derive a candidate datum ID is a probe, not a committed write.
4. **Persisted forgery versus fabricated observation.** A control that mutates a report tests a Quint rule. Where the Python test writes a well-formed but inconsistent record, exercise the actual reader/publisher against that record. Prove the fixture has the intended defect and include its valid counterpart. Prefer expressing construction in Quint using existing primitive writes.
5. **Python API versus strings.** CLI text cannot represent a bytes subclass, bool versus int, a dropped last reference, or a path that raises if touched. `CoreHistory.run` prevents some invalid transitions before the public binding and discards consumed aliases. A harness error is not an observed binding rejection. Do not substitute the private replay extension for the installed binding.
6. **Live identity versus equal values.** `tests/ordinary_rules.qnt` already compares identity tokens for handoffs. Reuse that idea where identity, callback entry, no binding, or a particular failure point is the guarantee. Do not instrument private functions to answer a question a public result or native record already answers. Do not introduce fault-injection state into the installed library.
7. **Interpreter conformance.** An interpreter cannot establish the correctness of its own verdict handling just by issuing a passing verdict. Drive known input and inspect output/exit status independently. Decide explicitly whether exact generated Quint source formatting is a contract in addition to round-trip semantics.

## Proposed packets (not one prompt per test)

| Packet | Scope | Context boundary |
|---|---|---|
| 1. Calibrate on recorded calls | `test_recorded_calls.py` lines 108, 171, 231, 245, 2654, 2659, 2682 | Establish independent native observations, path absence, and diagnostics. If evidence plumbing is costly, prove a single end-to-end slice first. |
| 2. Stored results, transfer, return | Lines 284–490 and 2570–2646 | Share false-arithmetic and equal-root fixtures. Split outbound handoff from return if needed. |
| 3. Durable plans, abandon, receipts | 526, 589, 1792, 1827, 1870–2144; typed pre-open cases go to packet 10 | Plan/worker/abandon first; receipt identity and retry second. |
| 4. Reuse, result selection, attempt selection | 631–1139 except 763, plus 1766 | Stage/direct reuse proof first; selection and attempt shape second. Route Python-only type variants to packet 10. |
| 5. Adoption, policy, intent, supersession | 1213–1707 except pre-open type cases | **Three slices:** adoption/deep chain; policy/intent decision; supersession/knowledge. Not one context window. |
| 6. Reuse tables | 2252–2547 | Separate implementation-scoped from intent-scoped tables. Capacity, identity, key, and historical validation differ. |
| 7. Argument-map, composition, closure records | Two remaining argument-map methods, composition graft, closure override and getter-graft | Use existing workflow histories. Isolate the 64-deep run if needed for Quint evaluation time; no new driver. |
| 8. Built-in stored records and values | Fixed operations, exact edges, bad profiles, canonical keys/NaN, limits and rollback | Keep persisted graphs and transactions separate from live handle identity. |
| 9. Live scopes and callbacks | `test_calls.py`, recorder ownership, ordinary callback cases, closure no-bind | Agree on handle/event evidence. Treat failures after a ref update separately from a stale ref rejected before the update. |
| 10. Public Python boundary | Binding, typed ordinary/closure arguments, recorded-call pre-open matrices | First typed values, encoding and diagnostics; separately ownership, destruction and thread affinity. |
| 11. Interpreter conformance and cleanup | Interpreter's nine methods, old registrations, fixtures, drivers, docs, final validation | Preserve an independent failure oracle. Do not delete a dependency used by a remaining Quint suite. |

These are working estimates, not promises that every packet fits one session. The four baseline files `test_recorded_calls.py`, `recorded_calls_histories.qnt`, `recorded_calls_rules.qnt`, and `run_recorded_calls.py` alone total 397,483 bytes. Use packet 1 to calibrate. Leave room for validation, review, and repair. Each subsequent slice should carry enough concrete evidence forward that the user need not re-explain the decision.

## Baseline obligation ledger

**Baseline: 122 Python methods in nine files; not 122 missing histories.** The line numbers identify methods, and the descriptions include their significant subcases. Read the baseline method and its helpers for exact fixture values and exception variants. Only the seven packet 1 methods have been closed.

### `tests/test_recorded_calls.py` (65)

Existing Quint anchors: `recorded_calls_histories.qnt` and `recorded_calls_rules.qnt`: together/split, handoff/return, durable/retry/abandon, reuse/version/selection/attempt/adoption, policy/implementation intent/supersession, multi-input and intent tables. Compare the *rule* as well as the history.

| Line | Guarantee to account for |
|---:|---|
| 108 | Fresh-process record/inspect report matches independently stored main, parentless one-entry tree, both three-binding DAGs, literal kinds/values and physical producer link. |
| 171 | Equal result node, distinct producers/scale commits, exact parents and input edges; moving the producer pin then deleting both input pins leaves both read-only reports intact. |
| 231 | Stale versus missing pin rejects although requested commit exists; preserve both input refs, no main. |
| 245 | Duplicate sum, producer-as-output, occupied main, scale overflow: preserve refs/file and leave candidate datum absent. |
| 284 | Scale consumes stored -17 and writes -102; no reexecution of sum. |
| 299 | Transfer, release and collect; decoy actually swept, origin refs not copied, exact parent and sub-DAG retained, stored value scaled, both repositories unchanged by inspection. Existing handoff collecting zero is not this case. |
| 355 | Wrong export pin/no file, no-clobber, same- and different-bundle staging occupancy, stale scale, release with missing result/wrong parent/right parent but wrong input DAG/moved incoming pin. |
| 408 | Truncated import into fresh and initialized worker: invalid bounds, no partial DAG/ref, existing bytes unchanged; intact bundle succeeds. |
| 430 | Publish returned stored -98 with source pins gone; wrong factor rejects; both lineage links survive collection, decoy swept, source reads exact worker report, worker unchanged. |
| 490 | Late staging delete guard rolls back both create and update of main; cover moved/missing staging pin and main alias, not an earlier main-guard rejection. |
| 526 | Capture nonempty prior main, keep plan and prior tip out of exported request, reject stale main then restore/publish; verify consumed refs, ordered links and actual reclamation. |
| 589 | Exact request parent but wrong factor or equal-root wrong physical producer; reject aliased refs and wrong direct publication operation; structurally valid non-arithmetic result accepted. |
| 631 | Exact v2 request parent with v1 result body fails inspect/export/requested publish/stage reuse/direct reuse; no bundle, receipt, output or proof. |
| 663 | Bad plan DAG, parentless result, wrong factor, same-root wrong producer, wrong request parent; both reuse operations reject; requested publish also rejects wrong parent. |
| 717 | Stage stored -98 whose execution would overflow, 128-character destination; plan/main/receipt/history preserved, history pin dropped and collected, later publish consumes plan/destination. |
| 763 | Both reuse APIs validate every ref slot/name/alias and both exact bytes IDs before path access (including subclasses, mutable bytes, lengths). |
| 799 | Stale result/main rejects; direct reuse moves main **from a distinct prior tip** without executing; verify ordered proof parents/root/fields, max-length name, proof-only retention and unrelated data swept. A main already at the result cannot prove the update. |
| 873 | Unrelated proof occupant and identical already-created proof both reject after restoring all other guards; proof ref is not an idempotency receipt. |
| 914 | Read-only rejection of reversed/missing proof parents, wrong nested result, wrong root/extra binding, bad/aliased ref names, wrong datum type. |
| 951 | Selection retains request/result but not private plan; transfer, publish with new plan and no original result pin; occupied proof rolls back; proof alone survives collection. |
| 1024 | Select/inspect/publish revalidate exact request and version, parent order/count, historical name/type and DAG root. |
| 1072 | Distinct IDs give distinct attempts for same result; repeated ID/request under a free ref gives identical attempt. Exact attempt/choice/proof parents and fields, unrelated collision, selected vs swept objects. |
| 1139 | Wrong nested version/result/request, parent count, uppercase UUID, invalid historical name, result substituted for attempt; exercise select/inspect/publish. Use a hex letter in the valid UUID: uppercasing a digits-only UUID changes nothing. |
| 1213 | Adoption without live plan, ordered previous-choice/attempt parents, occupied-output rollback, refs and retention after collection. |
| 1249 | Adopt/inspect/publish check entire chain: single/swapped parents, legacy root, repeated attempt, other request and buried bad name. |
| 1307 | Inspect 1,025 alternating adoption links; exact tip, previous selection and final attempt. |
| 1324 | Every adoption slot: invalid ID/name, main and pairwise aliases reject before creating repo. |
| 1345 | Legacy policy reuse rejects wrong selection/late collision, preserves prior refs; ordered plan/policy/selection and plan's captured main; equal intentions have distinct decision IDs but otherwise equal reports. |
| 1403 | Bad policy parent/default; wrong decision parents, selection, root, UUID, override/reason/fields/aliases; define/request revalidate bad policy; fresh ignores slot that reuse would reject. |
| 1470 | Bad intent ancestor, changed defaults/slots, aliased slots, unsupported version, wrong decision implementation/override/reason/slot/plan or foreign selection; inspect and revalidate on child define/request. |
| 1545 | Fresh ignores slot; explicit reuse overrides execute default; late occupied output rolls back; omitted selection fields versus actual selected attempt and result. |
| 1591 | Supersession exact/distinct pins and commits, nonempty evidence, legal refs/endpoints/reason; late occupied output and stacked declaration reject; ordered parents, main and slots unchanged. |
| 1646 | Bad declaration root/type/reason/endpoints/count/order/stacked ancestry, direct and as knowledge; unrelated, absent, malformed, or inapplicable knowledge rejected read-only. |
| 1707 | Transferred old/new decision pins and sibling knowledge, no origin refs; preserve historical absence and change only separately requested knowledge view. |
| 1766 | Attempt UUID case/variant/type, aliased/invalid output, short/stale input ID, arithmetic overflow; reject atomically. |
| 1792 | Bad request ref/factor, occupied plan, export mismatch/no file, main already names request, worker overflow: no partial state. |
| 1827 | Structurally valid future implementation request imports; work (not import) rejects without losing input or creating result. |
| 1870 | Abandon only selected pin despite moved main, alias, staged result; restoration cannot authorize publish. GC removes private plan/prior main but not staged result; worker unchanged. |
| 1919 | Abandon max-length pin, no main/result; plan and request remain until explicit GC, producer survives. |
| 1939 | Replaced pin, main alias, wrong role, plan DAG/request mismatch all reject abandon without writes. |
| 1971 | Exact plan-name/ID type, names, lengths, reserved main; no path access on invalid input. |
| 1990 | Exact four-field parentless receipt, root and refs; unchanged retry and inspection after input names reused and original objects swept. |
| 2047 | Change each of four receipt-key fields independently even when new publication is ready; max-length fresh key succeeds/retries without touching aliases. |
| 2107 | Receipt aliases main/plan/staging, occupied nonreceipt, matching fields with wrong root; publish/inspect reject without writes. |
| 2144 | Failed staging/main guards reserve no receipt; main already at result does not infer success; restore guards then succeed. |
| 2174 | Exact Python types and ASCII grammar/length for plan/staging/receipt slots before path access. |
| 2195 | Ref/ID bytes subclasses, bool/int subclass/string and out-of-range factor rejected before repository open. |
| 2252 | 16 request keys; reject seventeenth through writer and reader of forged delta; adoption at capacity changes only one mapping, old table intact. |
| 2285 | Reject result-only and cross-version selections on table insertion. |
| 2302 | Buried key/selection mismatch invalidates apparent hit for inspect/request; explicit fresh bypasses invalid table and omits table evidence. |
| 2329 | Table scoped to intent genesis and implementation; same fields/different lineage and same lineage/wrong version reject; explicit original version succeeds. |
| 2351 | Execute default bypasses bad table pin; explicit reuse requires exact hit; verify reason and field absence/presence. |
| 2377 | Swap hit decision's table parent to empty table; reject forged decision, genuine hit still reads. |
| 2418 | Later removal cannot hide bad inserted key; wrong parent count, factor type or table role rejected by inspect and request. |
| 2455 | At 16 intent keys remove one and refill; order, other rows, and previous table unchanged. |
| 2482 | Distinct selection commits naming same attempt cannot count as adoption; result-only selection cannot be inserted. |
| 2508 | Cross-version reuse keeps requested plan/implementation and original producing request/implementation distinct; verify physical parents and reject swapped plan or table. |
| 2547 | Occupied decision after main update, or occupied table-edit output, leaves no partial main/pending or other changes. |
| 2570 | Unsupported stored sum version cannot be scaled despite matching pin and expected tree entry. |
| 2581 | Equal sum roots do not excuse mismatched commit parent and input DAG; inspect/export/publish reject; no bundle. |
| 2633 | Combined fixture reports stored -17/-98 and exact selected producer, not recomputation or equal-root decoy; bytes unchanged. |
| 2646 | Equal literal value cannot replace required producer sub-DAG edge; wrong node kind rejected read-only. |
| 2654 | Out-of-range CLI input never creates the repository directory. |
| 2659 | Combined record: sum overflow and valid minimum sum then scale overflow; neither main nor candidate datum survives. |
| 2682 | Second combined record cannot replace published snapshot: old main exact, file unchanged. |

### Other application/library files (31)

| Baseline file and line | Guarantee to account for |
|---|---|
| `tests/test_argument_maps.py:61` | Transplant getter trace between different constructions with equal value; forged **attempt** inspection fails. Existing returned-source history changes the **request** source instead. |
| `:74` | Inspect a linear 64-deep returned-source walk successfully. Existing 64-attempt budget history branches; it does not establish depth. |
| `tests/test_composition.py:33` | Named getter key equal to required literal key produces 42 but is not that path; compose rejects with no native changes. |
| `tests/test_closures.py:38` | Exact signed I64 type/range for captured scale and invocation; no writes. |
| `:48` | Reject stored invocation arguments that try to override captured scale. |
| `:62` | Inspect returns 84 without binding the callable or writing. |
| `:70` | Equivalent wrong getter in producing trace invalid even on scale miss; not the same as a changed closure parent. |
| `tests/test_ordinary_calls.py:34` | Caught fabricated equal-node error poisons subsequent work; add prefix survives, main unchanged, escaped callback unusable. |
| `:61` | Healthy but ended session cannot use escaped callback; no writes. |
| `:80` | Failure **after** double-phase ref update and separately after final main update; only current batch rolls back; exact prior prefix survives. |
| `:112` | Bool/float and both out-of-I64 directions rejected before recording. |
| `tests/test_calls.py:20` | Nested invocation preserves object identity; copied value survives exit, subsequent invoke rejects. |
| `:31` | Fabricated input vs foreign result, each rejects and poisons scope. |
| `:44` | Catching expired-target error cannot make outer invocation return successfully. |
| `:60` | Foreign thread never enters adapter; owner can subsequently invoke it exactly once. |
| `:84` | Unsupported getter capture inspectable by exact named slot; bad count, wrong slot, metadata shadowing reject. |
| `:97` | Built-in result 42, exactly one call with exact prepared native argument DAG and getter binding. |
| `:111` | Equal copy cannot replace prepared argument; scope poisoned, recorder trace empty. |
| `tests/test_builtins.py:73` | Five actual handlers, equal values with distinct sources, version-specific entry, argument/source/return edges and order, opaque immutable handles, value after exit, offline read without dispatch/authoring. |
| `:131` | Unknown binding inspectable but not executable; wrong function/binding pair also rejects. |
| `:141` | Reject wrong binding root/role, adapter/interpreter/timeout/source types, extra field. |
| `:158` | Wrong argument names, missing map key in both versions, wrong map/key types; negative, out-of-bounds, bool and float list indices. |
| `:186` | NFC duplicate keys rejected at argument construction and map insert. |
| `:199` | Caught conversion poisons recorder; previously staged operation, arguments, commit and ref absent. |
| `:217` | Late outer failure removes new argument/operation/trace/return DAGs. |
| `:234` | Foreign and fabricated handles reject; reload by native ID gives distinct local object, same value and DAG. |
| `:248` | Inactive, reentered and ended recorder reject; staged work rolls back. |
| `:262` | Logical literal cannot inject native collection-member IDs; earlier staged record rolls back. |
| `:274` | Canonical packed NaN survives map/list operations with same datum ID and value bytes. |
| `:290` | 16/17 call positions, 16/17 arguments, 64/65 distinct records; repeated ID doesn't consume a distinct-record slot. |
| `:322` | Reject independent lies in source, arguments, operation semantics, and returned value. |

### `tests/test_python_binding.py` (17)

| Line | Guarantee to account for at the public binding |
|---:|---|
| 17 | Missing repo: status, integer native code, detail, no directory. |
| 26 | Bad create flag, NUL path, negative/noninteger/small map size: specific errors/no creation; valid size succeeds. |
| 38 | Live transaction conflicts, failing commit consumes handle, repeat commit differs, abort idempotent, subsequent writer succeeds, closed repo rejects further use. |
| 60 | Python type/handle/ID-length errors do not poison native write; earlier datum commits and reads back exactly. |
| 79 | Empty MAP bytes, canonical order independent of input order, duplicate-key status/detail. |
| 91 | Reject malformed MAP container, pair type/arity, key/value bytes type and ID length. |
| 107 | NULL takes None; URI takes bytes; canonical URI round-trips; relative, NUL, invalid UTF-8/escape and noncanonical forms reject. |
| 121 | LIST order/duplicates, empty members, sorted MAP pairs; truncated, mutable and noncollection inputs reject. |
| 137 | Reject LIST iterators, sets, bare bytes, mutable IDs and wrong-length IDs. |
| 144 | MAP cannot reference node instead of datum; native rejection poisons commit and rolls back earlier key. |
| 161 | NFC-equivalent keys share ID; duplicate rejects; nested MAP/LIST/NULL/URI transfer, staging ref, node, exact bytes/order read back. |
| 207 | Strict bundle arguments and owned bytes; active txn conflicts, malformed bundle, occupied staging; delete+collect two then abort restores identical export. |
| 249 | View keeps temporary input usable; negative index, bounds, wrong kind and non-view have distinct errors. |
| 263 | Bytes subclass with backreference is destroyed, not retained by view; view remains usable. |
| 278 | Transaction keeps repo alive after caller reference goes away; commit and reopen/read succeed. |
| 298 | Owner-thread drop of transaction rolls back. |
| 306 | Foreign close/abort/commit reject; last foreign reference drops; owner reaps and staged datum is absent. |

### `tests/test_trace_interpreter.py` (9)

| Line | Guarantee to account for independently of the interpreter under test |
|---:|---|
| 41 | Dispatch ordered writes/read, exact observations, close fixture. |
| 52 | Unknown op/wrong arity include history and step in diagnostic; cleanup still occurs. |
| 62 | Exactly requested native calls and scans; failed write leaves txn, explicit failed commit consumes it. |
| 89 | Unexpected binding exception is not misreported as native status despite similar arguments. |
| 96 | Independent bundle parser accepts valid frame; rejects short header/frame header/payload and trailing bytes. |
| 106 | 16/17 batch boundary preserves attempts, history order and scenario metadata. |
| 122 | Interned ref snapshots preserve names/targets/order/duplicates, no input mutation, reject unexpected fields. |
| 136 | Columnar defaults, nested values, false vs zero, order and history boundaries preserved; reject differing fields. |
| 158 | Missing per-step verdict fails even if coverage and controls say true. |

## Packet 1 evidence

The recorded-calls workflow now runs both CLI commands and single-call native
steps against the same paths. CLI commands use their existing receipt aliases;
native steps carry their own read IDs and close all handles before the next CLI
command. The runner emits facts; Quint checks the receipt, stored graph,
diagnostics, and pre/post state. The core-only suites still scan LMDB inventory.

Numbers below are the recorded-calls runner's one-based history and step numbers.
All listed steps passed in the live workflow (27 histories; coverage and controls
passed). The seven corresponding Python methods and the unused `number` helper
were removed; the focused Python suite registration is still needed. The final
`scripts/check.sh --quint` gate passed all 28 suites in the Nix shell on aarch64
Linux; macOS and Windows were not run locally.

Two isolated CLI mutations also failed as intended: substituting a literal ID
for the reported input node failed history 20 step 60 (`wrong_native_graph`);
committing staged data on overflow without changing the CLI diagnostic or `main`
failed histories 25 and 26 step 11 (`wrong_native_status`).

| Baseline `tests/test_recorded_calls.py` | Live history / steps | Rule and observed result |
|---|---|---|
| `:108` combined record and inspect | `combinedGraphRequests` (20): record 1, native 2–59, inspect 60 | `combinedGraphMatches` matched the receipt/native `main`, no parents, one named tree entry, both exact three-binding DAG paths, literal kinds and values, physical sub-DAG input, and the full report. |
| `:171` independently pinned equal sums and scales | `splitGraphRequests` (21): writes 1–4, sum inspect 5, native paths 6–52, scale reads 53–54 | `splitGraphMatches` checked distinct sum commits, sum DAGs and scale commits, a common native I64 root of 12, and each named snapshot's exact parent and typed input DAG edge. The scale and sum reports selected the right paths. |
| `:171` moved/released pins | 21: move/readback 55–64, reports 65–66, release/readback 67–78, reports 79–80 | `physicalVerdicts` observed the moved pin at the decoy and both released pins absent. `physicalInspect` matched both reports to the original pair at each phase; all inspection steps left `data.mdb` unchanged. |
| `:231` stale / missing | `pinRejectionRequests` (22): native 3–10 and 13–20, rejections 11–12 | `pinRejectionVerdicts` saw the two original pins, no missing pin or `main`, and distinguished the expected-commit mismatch from the native missing-ref diagnosis. Both failures had exit 1, empty stdout, and unchanged `data.mdb`. |
| `:245` duplicate sum / producer-as-output / occupied main / scale overflow | `writeRejectionRequests` (23): writes 9, 24, 39, 54; native readbacks 12–15, 27–30, 42–45, 57–60 | `writeRejectionVerdicts` distinguished the ref collisions from arithmetic failure. Each write left the file and original refs unchanged, with no `overflow` ref or candidate I64 datum. Candidate IDs came from aborted probes. |
| `:2654` out of range | `rangeRejectionRequests` (24): step 1 | `freshRejectionVerdict` saw the argument-range diagnosis and no path before or after. |
| `:2659` sum / scale overflow | `overflowRequests` (25, 26): step 1, aborted probe 2–7, readback 8–13 in each | `overflowRejectionVerdicts` saw distinct arithmetic diagnoses and initialized repositories with no `main` and no candidate datum (max / min I64). |
| `:2682` repeat combined record | `repeatRejectionRequests` (27): first write 1, repeat 7, native `main` reads 4 and 10 | `repeatRejectionVerdicts` saw a diagnosed rejection, the same `data.mdb` bytes, and the original receipt ID in native `main` both times. |

## Removal dependencies and finish line

Three existing replay files (`tests/run_argument_map_poison.py`, `tests/run_argument_map_request_integrity.py`, `tests/run_argument_map_returned_source.py`) import fixture functions from `tests/test_recorded_calls.py`. `tests/test_argument_maps.py` and `tests/test_calls.py` also import from it. Do not strand those imports. Review remaining drivers for duplicate orchestration and behavioral judgments; keep necessary evidence collection distinct from tests. Do not start an unrelated harness rewrite.

Complete means: all ledger obligations accounted for against live behavior or an explicit user decision; no residual Python tests or obsolete registrations; no stranded fixtures; validation and installed-consumer instructions reflect the resulting suites; final results and any exceptions reported under the validation policy. Until then, this remains the only workstream.
