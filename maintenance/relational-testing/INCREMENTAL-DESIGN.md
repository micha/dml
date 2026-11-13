# Incremental testing — bounded controller candidate

**Subsequent GO:** user “reviewed. GO” approves this bounded plan for isolated implementation,
subject to concrete pre-edit/readiness gates. [Pre-edit plan](INCREMENTAL-PRE-EDIT.md) awaits gate
acceptance; [coordination](INCREMENTAL-COORDINATION.md) owns current state. No as-built claim or
commit/push/main integration follows; pending-GO status below is historical.

Status: PREPARED FOR REVIEW, not implemented or implementation GO. The user's
“agreed. proceed!” authorized preparation of this design, [example](INCREMENTAL-EXAMPLE.md)
and [conditional handoff](INCREMENTAL-HANDOFF.md), following the session
[handoff](HANDOFF.md). Exact engineering choices below are assistant recommendations.
No new experiment, dependency, main-source edit, commit or push is authorized.

## Goal and first family

Prove persistent, dependency-driven reuse across exercise → projection → check,
with new requests preserving OLD execution provenance and explicit fresh execution.
This is an isolated orchestration prototype, not a replacement suite or generic scheduler.
Random sampled refresh is explicitly DEFERRED.

Use the existing spike map/get family: `exerciser.py` at TWO checkpoints, both shipped
map/get versions, equal-valued distinct sources and three positions per recording.
`test_spike.py` already covers valid history, typed extraction uniqueness, real native
wrong-result mutation, missing roots and relational faults. Original tests remain unchanged.
This smaller family is recommended instead of first orchestrating all44 HOST-paired cases;
the latter remain retained evidence, not silently promoted replacement assurance.

A fresh normal exercise makes real native DML records/internal calls, not LOCAL jobs or
ordinary application Q/T. New controller request/attempt records concern the TEST STAGES;
they must not be counted as candidate application attempts. No child-custody/deadline/
transport/scientific-truth assurance is supplied by this family.

## Trust boundary and exact pinning

A trusted Python driver uses an independently pinned DML package/native extension solely
to record stage requests, attempts, outcomes and selections in its OWN controller store.
It runs candidate exercising in a separate process with an explicit candidate import path;
normalization likewise uses its declared decoder, checking imports no candidate DML.
Process separation avoids accidental module aliasing, not a security sandbox.

Recommended controller basis: worktree base `15555c01e4db19a20b4de7049f776c4d995bd5e0`,
its unchanged Python package and already prepared `build/spike-native/_core.abi3.so`.
The prototype driver itself is unbuilt. Git identity alone is NOT a sufficient pin.
After a future GO, prepare a frozen controller snapshot with exact file/artifact SHA256s,
resolved Python executable/version, native-extension provenance, resolved runtime libraries,
platform and dependency identities. Independently review the receipt and small bootstrap
storage/key/selection checks before first controller use. Do not claim an installed or
reproducible native build from a Git ancestor or hash alone. Missing provenance or public
seams must stop for review; no implicit rebuild/download/promotion.

Candidate identity conservatively covers ALL tracked candidate source/build declarations,
explicit additional source files, native artifact bytes and relevant runtime/dependency
configuration. A file-set manifest defines inclusion; unexpected executable inputs fail
admission rather than disappear from the hash. Candidate snapshots are owned copies of the
spike base, NOT the moving Iteration25 checkout. No code changes to the trusted recorder
package/native foundation are proposed. Controller changes select a NEW cache namespace;
no automatic trust promotion or reuse from an old controller namespace. The namespace pins
recording, dispatch, key/admission and publication code, NOT all replaceable E/P/C payloads.
Stage payloads have their own explicit manifests below; revising checker bytes alone must not
silently revise E's controller pin. The candidate snapshot manifest excludes orchestration/
checker files outside that snapshot, but includes every declared candidate build input.

This captures a declared local environment, not every ambient influence. Initial admission
is same pinned local platform/environment with fixed deterministic scenario inputs; reject
unsupported configuration. No arbitrary user code, wall-clock-dependent case, property-test
random corpus, network, remote execution or cross-platform reuse. Do not read secrets or
hash broad environment dumps. Actual generated property cases would need their own later plan.

## Stages and conservative identities

Use a versioned canonical JSON manifest with explicit type tags, sorted object keys,
SHA256 artifact identities, domain-separated stage keys and a format revision. Reject
ambiguous/duplicate fields and inconsistent same-ID descriptions. No native hash/layout change.

| Stage | Exact computational dependencies in first key |
| --- | --- |
| Exercise E | Controller namespace; complete candidate build/runtime manifest; exerciser/harness bytes; scenario/seed policy; declared environment; limits and evidence-contract revision |
| Projection P | Namespace; selected E evidence digest and E key; extractor/decoder/package/native bytes; schema/capsule/materialization code and dependencies; root/context boundary; limits |
| Check C | Namespace; selected P artifact digest and P key; checker/query/transitive view bytes; DuckDB/runtime identity; assertion manifest and applicable scope/expectations/limits |

P includes the full E key even if changed candidate bytes happen to emit identical native
objects. C includes P's key as well as its data digest. This deliberately conservative chain
prevents byte-identical output from hiding a changed upstream computation. Precise dependency
slicing, selective build invalidation and value-only cross-run deduplication are deferred.

Explicit roots, checkpoint expectations, errors and supplied contexts are evidence inputs,
not inferred from whichever objects survived. Original expected verdicts are comparison
outputs kept separately, NEVER SQL predicate inputs. Expected rejection is a checked property,
not a swallowed failure; unexpected violation/exception/missing evidence remains non-success.

Artifact directories are immutable after publication and selected by exact manifests. Retain
portable native evidence through the existing pinned export/import boundary where needed;
do NOT copy live LMDB databases or lock files. Before promotion, verify native artifacts are
readable from their recorded roots and all selected files match digests. Exact portable capture
and root inventory must be reviewed before coding, not assumed feasible from this paragraph.

## Recording and reuse, without a generic framework

Recommended NEW spike-only ordinary DAG conventions, written through pinned public low-level
DML APIs (no new native entity or old application-role reinterpretation):

- request: distinct occurrence, stage/key/control, declared input manifest and selected basis;
- attempt: distinct fresh occurrence linked to its request, running/terminal observation;
- outcome: artifact-manifest digest/reference, computational result and errors;
- satisfaction: THIS request links to the OLD selected attempt/outcome on reuse;
- selection: one explicit known slot per stage/key, linked to a successful attempt/outcome.

Small hard-coded E/P/C sequencing only. No discovery by history scan, backend registry,
parallel scheduler or general callable evaluator. Controller can load ONLY declared known
slots, then revalidate key, terminal success, artifact completeness/digests and authority.
A found but malformed selection fails closed; absence produces fresh work. Unknown/failed
attempts cannot be selected as cached success. Corruption is not an automatic fresh fallback.

Adoption is a separate explicit controller operation after successful completion/verification;
no selection move just because fresh work finished. Publish a selection ref with the same
transactional compare-with-basis protection as its records. Changed concurrent basis rejects;
one serialized owner is the initial profile. Completed outcome + crash before adoption stays
unselected. Atomic DML publication does not make external files atomic: finalize owned artifact
manifest FIRST, then link/adopt; incomplete/unreferenced files are not reusable.

Retain old snapshots and demonstrate two branches keeping different selected successful
attempts for the same E key. No mutation/deletion of OLD attempts or unrelated stage selections.

## Occurrences and coverage

Scenario-position labels such as `checkpoint-0/call-1` are stable comparison labels.
Actual stage occurrences use controller-owned run namespace plus monotonic sequence, reserved
transactionally before activation. Distinct fresh runs have distinct namespaces/attempts even
when all candidate native content IDs match. Do not change existing candidate occurrence APIs.
Reusing a stage creates a new controller request/satisfaction, NOT a fresh attempt.

Keep requested and producing manifests, selection snapshot, stage dependencies, actual exit,
logs, observed errors, artifact fingerprints and NEW-versus-OLD annotations. Fresh instrumentation
belongs to the actual attempt that generated it. Reused evidence supplies historical assurance,
not fresh coverage counters, platform truth, independent empirical trials or a current full gate.
No cached coverage used to satisfy maintained100% thresholds; no coverage policy change here.

## Assurance and limits

Hybrid assurance remains necessary. SQL covers the selected map/get structure/value/source/
position obligations; direct tests cover pinned storage/ref behavior, extraction errors,
key dependencies, publication atomicity and artifact admission. Native codec/hash/budget,
process/custody and broader application contracts retain their existing direct foundation.
Positive agreement alone is not complete equivalence or a globally minimum proof.

Future validation must demonstrate real stage invocation COUNTS, not timing alone or monkeypatches
that bypass stage activation: unchanged reuse, checker-only invalidation, normalizer-only
invalidation, candidate-byte invalidation, explicit fresh, separate adoption/branch preservation,
wrong result, missing evidence, tampering, unsupported context and interrupted publication.
Exact finite activation allowance and pre-run plan are in the [handoff](INCREMENTAL-HANDOFF.md).
No five-minute/full-suite speedup promise. No runtime/performance engineering, C/storage/public
API change, maintained runner integration or paused native19/VP-001 investigation follows.
