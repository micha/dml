# Python-to-Quint port: active work order and session handoff

**Priority: exclusive until complete.** Port the checks in the Python tests to Quint and clean up the superseded tests and machinery. No unrelated features, fixes, refactors, or tooling work. This work order owns migration scope and progress, not the product specification. The [validation policy](validation-policy.md) owns the gate; the [test guide](../tests/README.md) describes the existing interpreter and suites.

## Resume here

- Baseline: `f595d97` on `implementation-bound-invocation`. Baseline line numbers below remain usable after deletions: e.g. `git show f595d97:tests/test_recorded_calls.py`.
- **Packets 1–4 and packet 5's adoption and policy/intent slices are complete**; see the [evidence below](#packet-1-evidence), including [policy and intent replay](#packet-5-policy-and-intent-evidence). Resume at **packet 5, supersession and knowledge**: baseline `tests/test_recorded_calls.py:1591`, `:1646`, and `:1707`. Read only the relevant methods, histories, rules, and interpreter commands; leave typed pre-open cases (including `:1324`) for packet 10.
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
| 4. Reuse, result selection, attempt selection | 631–1139 except 763, plus CLI-representable cases of 1766 | Complete. The direct Python UUID type and raw short ID cases from 1766 stay with 763 in packet 10. |
| 5. Adoption, policy, intent, supersession | 1213–1707 except pre-open type cases | **Three slices:** adoption/deep chain; policy/intent decision; supersession/knowledge. Not one context window. |
| 6. Reuse tables | 2252–2547 | Separate implementation-scoped from intent-scoped tables. Capacity, identity, key, and historical validation differ. |
| 7. Argument-map, composition, closure records | Two remaining argument-map methods, composition graft, closure override and getter-graft | Use existing workflow histories. Isolate the 64-deep run if needed for Quint evaluation time; no new driver. |
| 8. Built-in stored records and values | Fixed operations, exact edges, bad profiles, canonical keys/NaN, limits and rollback | Keep persisted graphs and transactions separate from live handle identity. |
| 9. Live scopes and callbacks | `test_calls.py`, recorder ownership, ordinary callback cases, closure no-bind | Agree on handle/event evidence. Treat failures after a ref update separately from a stale ref rejected before the update. |
| 10. Public Python boundary | Binding, typed ordinary/closure arguments, recorded-call pre-open matrices | First typed values, encoding and diagnostics; separately ownership, destruction and thread affinity. |
| 11. Interpreter conformance and cleanup | Interpreter's nine methods, old registrations, fixtures, drivers, docs, final validation | Preserve an independent failure oracle. Do not delete a dependency used by a remaining Quint suite. |

These are working estimates, not promises that every packet fits one session. The four baseline files `test_recorded_calls.py`, `recorded_calls_histories.qnt`, `recorded_calls_rules.qnt`, and `run_recorded_calls.py` alone total 397,483 bytes. Use packet 1 to calibrate. Leave room for validation, review, and repair. Each subsequent slice should carry enough concrete evidence forward that the user need not re-explain the decision.

## Baseline obligation ledger

**Baseline: 122 Python methods in nine files; not 122 missing histories.** The line numbers identify methods, and the descriptions include their significant subcases. Read the baseline method and its helpers for exact fixture values and exception variants. Packets 1–4 and packet 5's first two slices closed 45 whole methods (7, 10, 11, 10, 3, and 4 respectively), plus the CLI-representable cases of `test_recorded_calls.py:1766`.

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
| 1766 | Attempt UUID case/variant, aliased/invalid output, stale input ID, arithmetic overflow: packet 4. Python `str` instead of UUID bytes and raw short commit bytes: packet 10. Both must reject atomically. |
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

## Packet 2 evidence

The [stored-result](../tests/recorded_calls_stored_histories.qnt) and
[transfer](../tests/recorded_calls_outbound_histories.qnt) histories share native
fixture steps for `2 + 3 → -17`. Execution produces `-102`, but inspection and
publication preserve the intentionally stored `-98`. CLI and native steps can
share explicit ID aliases without re-resolving a mutable pin. The workflow
runner observes file operations and byte equality; Quint checks the outcomes.

The live replay passed 37 histories and its rule controls. Ten superseded
Python methods and two fixture helpers were removed; the focused suite
registration and helpers used elsewhere remain. The final
`scripts/check.sh --quint` gate passed all 28 suites in the Nix shell on
aarch64 Linux. macOS and Windows were not run locally. The table uses the
runner's one-based history and step numbers.

| Baseline `tests/test_recorded_calls.py` | Live history / steps | Rule and observed result |
|---|---|---|
| `:284` stored sum / fresh scale | `storedExecutionRequests` (28): scale 28, native graph 31–60, inspect 63 | `storedLinkedReport` matched the exact parent, sub-DAG and stored sum node, and checked a native and reported scale result of `-102`. |
| `:299` outbound lineage / collection | `outboundCollection` (34): export, stage, unlink, scale and release 41–48; decoy read 57, collect 60, readback 63–101 | `outboundVerdicts` matched exact transfer IDs and bundle removal. The unpinned decoy existed before collection and was swept; origin and staging refs were absent in the worker. `storedLinkedReport` matched the retained edges and `-102` with unchanged worker bytes on inspection; the origin's file also matched its checkpoint. |
| `:355` transfer and release guards | `outboundGuards` (35): export 3, 6; stage 8–9; scale 10; release 19, 20, 67, 73; moved pin read 76 | `outboundRejected` distinguished stale export, no-clobber, same/different bundle occupancy, stale scaling, missing result, wrong parent, wrong input DAG and moved incoming. `outboundForgery` read the persisted correct-parent/wrong-DAG case and the distinct equal-root producer; file/selection checks preserved the original state. |
| `:408` truncated import | `outboundTruncation` (36): truncate 29, reject 30 and 47, native absence 33–44 and 50–61, intact import/readback 64–73 | The one-byte shorter copy matched the exact source prefix. `outboundTruncated` saw `invalid_bounds` in both attempts, with initialized bytes unchanged in the second. Native reads found no pin or partial closure; the intact bundle published its intended pin and DAG. |
| `:430` stored return and factor guard | `storedReturnRequests` (33): worker/staged reports 56/60, unlink 61–62, absent producer 71, wrong factor 76/readback 79–80, publish 83, collect 89, lineage/readback 92–131 | `publishVerdict` distinguished the wrong factor without changing bytes, creating `main`, or losing the staged result. The right factor published the exact result. The decoy was present before collection and absent after; no source or staging pin remained. `storedLinkedReport` matched the retained commit and DAG links and `-98`; report hashes and the worker byte checkpoint matched. |
| `:490` late rollback | `outboundLateGuard` (37): ready report 10; create rejection 16 and readback 19–21; update 25 and alias 26, reads 29–30; missing staging 34 and reads 37–38 | `outboundRejected` verified the exact result and expected main operands, the late moved or missing staging diagnosis (distinct from alias rejection), and unchanged bytes. Native reads confirmed absent `main` after create and the exact prior tip after update. |
| `:2570` unsupported stored sum version | `unsupportedSumRequests` (29): native fixture 30–41, scale 44, refs 47–48 | `storedCliVerdict` checked the valid sum tree and persisted `example.sum@2`, then the version diagnosis, unchanged bytes, original producer pin and absent `main`. |
| `:2581` equal-root mismatched parent | `mismatchedParentRequests` (30): valid inspect 4, native fixture 7–45, reject 48–50, refs 53–54 | `mismatchProof` read distinct producer DAGs with one root and a forged commit sharing the genuine result's tree but naming the decoy parent. Inspect, export and publication each rejected the mismatch without changing bytes. Export produced no bundle. |
| `:2633` combined stored report | `combinedStoredRequests(true)` (31): native graph 48–73, inspect 76 | `storedLinkedReport` distinguished the selected source from the equal-root decoy and matched the physical sub-DAG and both stored results (`-17`, `-98`) with unchanged bytes. |
| `:2646` wrong node kind | `combinedStoredRequests(false)` (32): native input 48–59, inspect 62 | `storedCliVerdict` read the substituted `-17` literal in the input slot and required the wrong-node-kind rejection without writing. |

Isolated negative controls also failed as intended. Recomputing the sum when
executing scale failed 28:63 (`wrong_stored_graph`). Committing `main` before
checking the staging guard kept the expected CLI error but failed 37:16
(`storage_changed`), with the native absence check also failing at 37:19.
Changing a retained prefix byte while still truncating by one byte failed 36:29
(`wrong_file_observation`) even though the import diagnostics were unchanged.

## Packet 3 evidence

The [plan histories](../tests/recorded_calls_plan_histories.qnt) and [receipt
histories](../tests/recorded_calls_receipt_histories.qnt) run against the public
binding through the workflow CLI, with independent native reads. Quint specifies
the persisted fixtures as individual native operations. For a future request
that the CLI planner cannot produce, the runner exposes one native bundle export
and a separate file write; the actual CLI stages and attempts to work the bundle.

Eleven corresponding Python methods were removed. The typed pre-open checks
remain for packet 10; `prepare_receipted_scale` still serves two packet 4 checks.
The gate runs the 11 new histories as `recorded-calls-durable`, separately
from the 37 original histories to bound replay time. Both suites passed with
coverage and controls; `scripts/check.sh --quint` passed all 29 suites in the
Nix shell on aarch64 Linux. macOS and Windows were not run locally. The table
gives one-based history and step numbers in the durable suite.

| Baseline `tests/test_recorded_calls.py` | Live history / steps | Rule and observed result |
|---|---|---|
| `:526` prior `main`, portable request, guarded return | `durableTipCase` (1): inspect 5; collect and native 17–29; export/import 30–39; reject 46 and native 49–51; publish/collect 55–56; native and inspect 59–83 | `planReadWithTip` matched the captured tip, factor, implementation, and request. The private plan and prior tip were absent from the worker but had survived collection at the origin. `planRejection` diagnosed stale `main` without writing. `durableLineage` matched exact ordered parents and the physical producer edge; refs were consumed, private commits swept, and the final report matched the worker's. |
| `:589` exact request with inconsistent result | `candidateCase` (2): native fixtures and readback 6–160; rejects 161–164; valid publication 165/168/171 | `candidateLayout` verified sole request parents, exact factors and links, and distinct equal-root producer DAGs. The factor, physical input, alias, and direct-operation failures had distinct diagnoses and unchanged bytes. `storedCandidateReport` matched the native, deliberately non-arithmetic `-98`. |
| `:1792` request and worker guards | `guardCase` (3): rejected requests 2–3, 5, 9; export mismatch 7; worker overflow 11; readback 14–15 and 20–23 | `planRejection` distinguished reserved ref, range, occupancy, mismatched plan pin, request already at `main`, and worker overflow. Bytes stayed unchanged, no wrong bundle or partial pin appeared, and the exact incoming request survived. |
| `:1827` unsupported future request | `futureRequestCase` (4): export/file/import 20–23, native 26–46, work 49, refs 52–53 | Native export and CLI import succeeded. `futureLayout` checked the persisted request tag, producer, implementation root `example.scale@3`, and factor. Only execution failed; worker bytes and incoming pin were preserved with no result. |
| `:1870` abandon with moved main, alias, and staged result | `abandonStagedCase` (5): abandon/repeat 16–17; refs 20–24; restored-tip rejection 28, refs 31–32; collect 37 and reads 40–46 | `planVerdicts` saw only the selected pin disappear; publication still rejected the missing pin and left no receipt. Native reads confirmed that collection swept the private plan and prior tip, not the staged result. Worker bytes matched the checkpoint. |
| `:1919` explicit collection | `abandonExplicitCase` (6): abandon 16, refs/objects 19–23, collect 26 and reads 29–31 | `planVerdicts` saw the 128-byte pin disappear with no `main`. Plan and request existed before collection and were absent after it, with the producer pinned throughout. |
| `:1939` invalid abandon selections | `abandonGuardsCase` (7): persisted graph 9–41, rejects 44–47, refs 50–53 | `malformedLayout` verified the correct plan tag and parent count but the wrong request DAG. Replaced pin, reserved `main`, wrong commit role, and wrong DAG were diagnosed without changing bytes; native refs remained exact. |
| `:1990` receipt graph and retry | `retryIdentity` (8): publish 9, native 12–46, retries/inspects 49–50, 65–66, 86–87; collect 74 and reads 77–83 | `exactReceiptGraph` matched the parentless one-entry commit, four literal strings, and result-ID root. `retryVerdict` and `exactReceiptReport` matched the result and receipt without writing, including with restored guards and after ref reuse and actual reclamation. |
| `:2047` four independent key fields and a fresh key | `keyFields` (9): ready refs 26–30; mismatches 33–34, 61, 78; alternate result 35–67; recaptured plan 76–77; fresh publish/retry 79/85, reports/alias readback 86–94 | `changedKeyFields` required exactly one changed field in each read-only rejection. `alteredResultMatches` checked the same request and different stored output; publication without a receipt succeeded. A 128-byte fresh key published and retried without consuming either alias. |
| `:2107` aliased and occupied keys | `keyGuards` (10): alias rejects 9–11, valid counterpart 12–49, persisted forgery 71–82, occupied-key/inspect rejects 85–87 | `forgedReceiptGraph` observed the same four native nodes as the genuine receipt with the plan-ID node as the wrong root. Publish and inspect diagnosed the malformed receipt; the nonreceipt and all aliases also rejected without writing. |
| `:2144` receipt rollback | `guardRollback` (11): rejects 14/29 and native 17–20/32–35; restore/publish 43 and native/report 46–52 | The moved staging pin and `main` already at the result each produced its own diagnosis with original bytes and no `ack`. Restoring the guards published the exact result and a readable receipt and consumed both pins. |

Isolated live mutations failed as intended. Skipping the requested result's
producer-DAG check failed 2:162 (`wrong_rejection`). Retaining the abandoned
plan under a hidden ref with other data available for GC still failed 5:42
(`wrong_native_status`). Changing both the receipt writer and reader to agree
on the wrong root failed 8:50 (`wrong_receipt_graph`). Ignoring the plan name
in the key failed 9:33, and treating `main` already at the result as success
failed 11:29 (both `wrong_rejection`).

## Packet 4 evidence

[Staged and direct reuse](../tests/recorded_calls_reuse_histories.qnt) and
[result and attempt selection](../tests/recorded_calls_selection_histories.qnt)
run in separate Meson entries with the shared recorded-calls runner. The runner
passes immutable native IDs into existing CLI commands and does not evaluate
fixture validity or decide the outcome. The histories make and read persisted
fixtures with individual native calls, then run the real public workflow.

Both entries passed (six reuse histories and five selection histories, with
coverage and controls). The final local `scripts/check.sh --quint` gate passed
all 31 suites in the Nix shell on aarch64 Linux with Quint 0.33.1. Ten Python
methods and three unused helpers were removed. `:763` and the two direct
Python argument cases of `:1766` remain for packet 10. The step numbers below
are one-based within each entry.

| Baseline `tests/test_recorded_calls.py` | Live history / steps | Rule and observed result |
|---|---|---|
| `:631` right request parent, wrong body implementation | `implementationCase` (reuse 1): native 84–143, inspect 146, rejects 147–151, refs 154–159 | `planLayout` and `resultLayout` matched the shared exact v2 request under the valid v2 and invalid v1 bodies. All five operations diagnosed the implementation mismatch with unchanged bytes and no bundle, receipt, destination, or proof. |
| `:663` invalid reuse inputs | `malformedCandidates` (reuse 2): native 123–237, valid inspect 240, stage 241–245, direct 246–250, requested publish 251 | `malformedCandidateLayouts` established the bad plan DAG, missing parent, wrong factor, different equal-root producer DAG, and wrong request parent. Both reuse paths rejected each for its own cause; requested publish also rejected the wrong parent. Bytes were unchanged with no destination or `main`. |
| `:717` staging stored evidence | `stageCase` (reuse 3): inspect/stage 115–116, refs 119–123, report 126, sweep/readback 132–137, publish 140, refs/report 143–150 | `resultLayout` and `resultReport` observed the stored `-98` even though execution would overflow. Staging at the 128-byte name retained the exact plan, prior `main`, receipt, and history. After dropping history and collecting, publish consumed only plan and destination, kept the receipt, and reported the same result. |
| `:799` direct reuse and proof-only retention | `directCase` (reuse 4): stale result/main 148/154, restored prior 169, publish 174, refs and graph 177–202, collect and readback 217–234 | `proofGraph` checked ordered plan/result parents, root and two historical strings (including the 128-byte plan name). Native reads proved `main` moved from a distinct tip to the exact stored result. Rebinding historical names and collecting preserved the original closure through the proof alone and swept the alternate. |
| `:873` unrelated and identical proof occupancy | `occupancyCase` (reuse 5): rejects 60/119, rollback 63–66/122–125, success/report 74/104, restored guards 113–116 | `existingRejectionVerdict` required the collision diagnosis and unchanged bytes. The successful proof reported absent prior `main`; after restoring all original guards the same operation rejected the identical proof rather than treating it as a receipt. |
| `:914` malformed stored proof | `malformedProofCase` (reuse 6): valid reads 89/117/327, native forgery 193–315, rejected reads 318–326 | `malformedProofGraph` and exact diagnoses distinguished reversed/missing parents, wrong nested result, wrong root/extra binding, invalid and aliased ref names, and wrong datum type. All reads left bytes unchanged. |
| `:951` portable selection and proof-only retention | `transfer` (selection 1): choose 20, native 23–41, collect 53, transfer 61–64, target reads 67–75, publish 82, graph 85–111, retry/rollback 118–123, collect 133 and readback 136–147 | `singleBinding` checked the request/result parents and historical ref despite stale `main`. Native reads found the original plan and prior tip swept and absent from the target; `selectionReadVerdict` matched the imported report. A distinct new plan published without the original result pin. `proofGraph` and `proofReport` matched plan and selection after a diagnosed, unchanged collision and collection with only the proof pinned. |
| `:1024` malformed result selection | `resultValidation` (selection 2): persisted results/choices 72–361, rejects 364–378, valid counterpart 387–389 | `candidate` and `forgedChoice` verified exact parent/body versions, ordered parents, historical name/type, and DAG root. `exactDiagnostic` distinguished the writer, reader, and publisher rejections with unchanged bytes. The matching selection inspected and published. |
| `:1072` occurrence identity and retention | `attempts` (selection 3): collision 11, work 12–15, native 18–52, choice 55–75, collect/readbacks 87–93, publish 96, proof 102–125, proof-only read 143 | Native checks found distinct IDs for distinct UUIDs, identical IDs on repeat, and one result shared by both attempts. `singleBinding` and `proofGraph` matched ordered attempts, choice, proof, and exact literals. Collection swept the unselected attempt but not the selected history; only the proof remained pinned at the last read. |
| `:1139` malformed nested attempt and selection | `attemptValidation` (selection 4): persisted results/attempts/choices 72–503, rejects 506–524, valid counterpart 533–535 | Native reads distinguished the wrong nested version, result parent, attempt request, arity, uppercase UUID with a hex letter, historical name, and a result in place of an attempt. `exactDiagnostic` required read-only rejection for every applicable select/inspect/publish operation. |
| `:1766` CLI worker guards | `guard` (selection 5): rejects 16–22, native refs 25–29 | Exact diagnoses distinguished uppercase UUID, bad variant, aliases, invalid ASCII name, stale request ID, and overflow; bytes and original refs stayed unchanged with no attempt or `main`. Python `str` and raw short bytes still use the narrowed boundary test. |

Isolated live controls failed as intended. Skipping the real `main` update
failed reuse 4:177 (`wrong_native_value`), omitting the nested result check
failed reuse 6:320 (`wrong_rejection`), and treating an identical proof as a
receipt failed reuse 5:119 (`wrong_rejection`). Accepting an uppercase stored
UUID failed selection 4:510 (`wrong_rejection`); changing both the selected
proof reader and writer to agree on the wrong root failed selection 1:89
(`wrong_native_graph`).

## Packet 5 adoption evidence

The [adoption suite](../tests/recorded_calls_adoption_histories.qnt) uses the
shared workflow runner. It passes native basis IDs into the real adoption
command so Quint can exercise persisted forgeries. Every link of the deep
chain is requested in Quint as an encode and a put; Python only dispatches
those calls and collects observations.

All three live histories passed with coverage and synthetic controls. The
final local `scripts/check.sh --quint` gate passed all 32 suites in the Nix
shell on aarch64 Linux with Quint 0.33.1. The three superseded Python methods
were removed; their shared fixture and the `:1324` typed pre-open test remain.
The step numbers below are one-based within `recorded-calls-adoption`.

| Baseline `tests/test_recorded_calls.py` | Live history / steps | Rule and observed result |
|---|---|---|
| `:1213` adoption without a plan and late output collisions | `retention` (1): abandon 14, missing plan 17, reject/adopt/reject 20–22, native 25–53 | `retentionVerdicts` required the occupied-ref diagnosis and unchanged bytes for both an unrelated occupant and the identical adopted version. The successful write left the other pins exact and `plan` and `main` absent. `adoptionGraph` matched the ordered selection/attempt parents and the sole `attempt_ref` literal as the DAG root. |
| `:1213` retention after collection | 1: release 58–61, collect 64, native 67–79, inspect 82 | Collection swept the abandoned plan, but the old choice, both attempts and their request remained after their pins were gone. `adoptionReport` matched the exact predecessor and adopted attempt without writing. |
| `:1249` malformed versions and ancestry | `malformedChain` (2): native 24–483, writer-only guards 484–485, adopt/inspect/publish triples 486–503, refs 506–523, valid counterparts 526–553 | Native graph checks established the ordered layouts, including the alternate request with the same computed scalar. Exact diagnostics distinguished legacy basis, foreign attempt, one or swapped parents, legacy root, repeated attempt, foreign request and buried bad name. Every rejection left bytes unchanged and ready pins intact. The valid chain inspected, accepted another adoption and published the exact result. |
| `:1307` iterative deep read | `deep` (3): build 33–2082, tip and predecessor 2088–2107, inspect 2110 | `deepVerdicts` checked success and 1,025 distinct link IDs, and read both ordered parents of each of the last two links natively. `adoptionReport` matched the exact tip, previous selection and final attempt without writing. |

Isolated live controls failed as intended. Reversing the adoption writer's
parents failed 1:53 (`wrong_adoption_graph`). Skipping the historical-name
check on non-head links failed the malformed history at step 501
(`wrong_rejection`). Imposing a 1,000-link limit failed the deep history at
step 2110 (`wrong_inspect`).

## Packet 5 policy and intent evidence

The [policy](../tests/recorded_calls_policy_histories.qnt) and
[intent](../tests/recorded_calls_intent_histories.qnt) suites use the shared
runner. Native IDs reach the real CLI as explicit expected commits; native
reads check persisted graphs independently of the reports. Each suite passed
two live histories with coverage and rule controls. Four superseded Python
methods and three unused helper methods were removed. The final local
`scripts/check.sh --quint` gate passed all 34 suites in the Nix shell on
aarch64 Linux with Quint 0.33.1. Step numbers are one-based within each suite.

| Baseline `tests/test_recorded_calls.py` | Live history / steps | Rule and observed result |
|---|---|---|
| `:1345` wrong request and late collision | `reuseSteps` (policy 1): refs 25–33 and 40–48, rejects 36–37 | `existingRejectionVerdict` distinguished incompatible selection from occupied output with unchanged bytes. Native refs confirmed the distinct prior `main`, original plan and other pins stayed exact; neither unused output appeared. |
| `:1345` captured main and distinct decisions | policy 1: valid reuse 51, native 54–104, inspect 107; repeats 108–109, native 112–204, inspect 207–208 | `reuseInspection` matched the ordered plan/policy/selection and request/prior-main parents, UUID-rooted decision DAG, and exact result-only report. Native `main` moved to the selected result. The two later decisions retained equal intent and reports except for distinct commit and UUID. |
| `:1403` stored policy and decision validation | `readerSteps` (policy 2): native 304–707, rejects 710–722, valid read and define 736–737 | `graph` matched the actual layouts of the genuine and forged records. Exact diagnostics distinguished wrong policy parent/default, decision parents/selection/root/UUID/override/reason/fields/aliases, and malformed-basis rejection on define and request with no writes. |
| `:1403` bypass malformed slot only on fresh | policy 2: default reject 723, refs 726–733, fresh 738, native 741–787, inspect 790 | Explicit fresh used the same malformed selection operand that default reuse rejected. `readerInspection` checked the plan and the fresh report with no selection or attempt fields. |
| `:1470` intent versions and stored decisions | `lineage` (intent 1): valid definitions and miss 19–21, native 22–67 and 393–933, rejects 934–946, valid reports 947–948, refs 949–964 | `missLayout` matched the exact v2 request and ordered plan/definition edges; `shapeMatches` checked ancestry and each persisted defect. Exact diagnoses distinguished changed defaults/slots, aliased slots, unsupported implementation, wrong ancestor, wrong decision implementation/override/reason/slot/plan name and foreign selection. Inspect, child define and request rejections left bytes unchanged. |
| `:1545` fresh routes, late rollback, explicit reuse | `routing` (intent 2): rejects 39–40 and refs 41–53; write/read pairs 54–57 and 64–65; native 58–63 and 66–87 | Reuse rejected a non-selection pinned in the v2 slot; the late occupied decision left no new plan or `main`. `decisionRead` required the two fresh reasons and absent selection keys. An explicit v1 reuse overrode execute-by-default, reported the exact request, attempt and result, and native `main` named that result without a pending plan. |

Isolated live controls failed as intended: a constant decision UUID failed
policy 1:208 (`wrong_decision_identity`); skipped reason validation failed
policy 2:718 (`wrong_rejection`); a partial commit with the same occupied-ref
diagnostic failed policy 1:37 (`storage_changed`). Accepting changed intent
fields failed intent 1:934 (`wrong_rejection`); adding an empty selection field
to a fresh report failed intent 2:55 (`wrong_selection_fields`); skipping the
reuse update of `main` failed intent 2:68 (`wrong_native_status`).

## Removal dependencies and finish line

Three existing replay files (`tests/run_argument_map_poison.py`, `tests/run_argument_map_request_integrity.py`, `tests/run_argument_map_returned_source.py`) import fixture functions from `tests/test_recorded_calls.py`. `tests/test_argument_maps.py` and `tests/test_calls.py` also import from it. Do not strand those imports. Review remaining drivers for duplicate orchestration and behavioral judgments; keep necessary evidence collection distinct from tests. Do not start an unrelated harness rewrite.

Complete means: all ledger obligations accounted for against live behavior or an explicit user decision; no residual Python tests or obsolete registrations; no stranded fixtures; validation and installed-consumer instructions reflect the resulting suites; final results and any exceptions reported under the validation policy. Until then, this remains the only workstream.
