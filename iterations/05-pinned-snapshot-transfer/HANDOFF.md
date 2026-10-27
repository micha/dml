# Iteration 5 handoff: pinned snapshot transfer

Status: the user approved this bounded plan, checkpointed it locally, then declared
Iteration 5 GO: implementation by the existing window-2 agent in a new session,
coordinator monitoring/review and fixes, followed after acceptance by worker
commit/push and exact-SHA CI verification/fixes. This supersedes the preparation-only
permission statements below for this turn. No extra workers, release/package
publication, cloud experiments or later feature turn. See [COORDINATION.md](COORDINATION.md).

Delivery is now complete and stopped at published `0ec769b`, with all six final
exact-SHA CI jobs passing. [RESULTS.md](RESULTS.md) and [REVIEW.md](REVIEW.md) own
actual delivery/assurance; [the as-built contract](../../../dml/docs/spec-next/transfer.md)
owns implemented behavior. The handoff below preserves the authorized work plan,
not permission to restart or add another feature turn.

## 1. Authority, learning goal and stop line

[DESIGN.md](DESIGN.md) owns candidate architecture/format/ref/validation semantics;
[EXAMPLE.md](EXAMPLE.md) owns the acceptance story. This handoff owns work order,
assurance and delivery. These are plans, not as-built contracts. The
[discussion](../../discussion.md) separates user agreements and candidate choices.

Goal: export one pinned DML commit with its complete all-parent typed object closure,
import into another initialized local repository atomically, and inspect unchanged
IDs/bytes/occurrences using ordinary Python/CLI. Learn whether existing native record
operations are sufficient for a small exchange layer toward later remote execution.

Stop after this slice and meaningful failure tests. No network/cloud, remote registry,
automatic sync, incremental/thin/resumable transfer, merge/shallow-history policy,
remote execution/recovery, reuse/facets, resources/GC/excision, observer/UI, CLI mutation
or general workflow framework. A missing native primitive requires a reproducer and
separate scope decision. Do not add stronger security/concurrency machinery merely
because a future transport may need it.

## 2. Required reading and preflight

After **separate implementation authorization**, follow the machine-wide index,
confirm `/work` is mounted, and read completely:

1. Design [AGENTS.md](../../AGENTS.md), [README.md](../../README.md) and current
   [discussion](../../discussion.md), especially the resume point/authorization.
2. This handoff, [DESIGN.md](DESIGN.md), [EXAMPLE.md](EXAMPLE.md).
3. Implementation [AGENTS.md](../../../dml/AGENTS.md),
   [documentation guidelines](../../../dml/docs/documentation-guidelines.md),
   [as-built instructions](../../../dml/docs/spec-next/AGENTS.md),
   [orientation](../../../dml/docs/spec-next/README.md) and
   [glossary](../../../dml/docs/spec-next/glossary.md).
4. Current [records](../../../dml/docs/spec-next/records.md),
   [objects](../../../dml/docs/spec-next/objects.md),
   [repository](../../../dml/docs/spec-next/repository.md),
   [Python API](../../../dml/docs/spec-next/python-api.md),
   [CLI](../../../dml/docs/spec-next/cli.md) and
   [local execution](../../../dml/docs/spec-next/local-execution.md) contracts.
5. Iteration 4 [RESULTS](../04-local-recorded-execution/RESULTS.md) and
   [REVIEW](../04-local-recorded-execution/REVIEW.md),
   [coverage catalog](../../../dml/tests/coverage-exclusions.md) and
   [packaging contract](../../../dml/docs/packaging-and-distribution.md).

Preparation inspected clean implementation `d498a6c` and design checkpoint `ee708c4`;
no tests/builds/prototypes ran and no implementation files changed. Reinspect live
state; do not reset work or treat prior CI as current-source validation.

Once authorized, identify implementer/reviewer and agree shared `build/check`
ownership before running standard checks (they wipe/reconfigure it). Record baseline,
selected candidates and exact commands/status in this directory's `RESULTS.md`.
Use fresh test-owned repositories and bounded local build/install/process scratch.
No extra agents, global tooling bootstrap, publication or inherited delegation.

Consult current standard-library JSON/base64, file/lifetime and process documentation
through the available documentation skill before selecting engineering calls. Preserve
declared Python/platform support; qualify tested versus declared boundaries. Do not
expose credentials or raw sensitive research bundles in reports.

## 3. Source seams and candidate changes

Paths below are relative to `/work/repos/micha/dml`:

| Seam | Inspect / candidate bounded work |
| --- | --- |
| Public record insertion | `python/daggerml/daggerml/__init__.py`: small mutation-guarded `Transaction.put_record(kind, record)` over existing `_core.put_record` |
| Existing native boundary | `python/daggerml/src/_core_module.c`, `_core.pyi`, `src/repo.c`, `include/dml/repo.h`: inspect validation/no-overwrite behavior; no native change intended |
| Transfer layer | New candidate `python/daggerml/daggerml/transfer.py`, explicitly imported, public operations only |
| Packaging | `meson.build` installs the new module via existing `python-runtime` tag |
| Examples | Add one runnable transfer story; reuse trusted local addition source rather than another maintained execution adapter |
| Tests | `tests/conftest.py`, public API/transfer round trips, properties, faults and private interruption fixture |
| Memory | Existing `tests/python/binding_memory.py` and native CLI workload; extend the binding workload narrowly for the new public insertion path if useful |
| Documentation | Owning transfer contract under `docs/spec-next/`, Python insertion contract and navigation/package orientation |

Do not edit old `docs/spec/`, `python/adapters/`, CLI grammar/JSON, core encodings,
release workflows or version/runtime declarations. Retain Iteration 4's short
parametrization IDs, finite CI job bound and Windows diagnostics; no rerun of the
large-ID mistake. Do not use private native APIs outside the low-level wrapper.

## 4. Recommended implementation sequence

### A. Resolve packed insertion first

Before a broad transfer module, add/test the candidate public insertion wrapper.
Take exact source records obtained through public reads, insert in dependency order
in a separate initialized repository, and verify returned IDs and exact bytes.
Exercise all ten datum kinds plus literal/sub-DAG nodes, named/root-only DAGs, trees
and ordered-parent commits. Include NaN/infinities, I64 extrema, NFC STRING/URI,
LIST duplicates, SET/MAP order and anonymous/shared graph structure.

No Python packed codec/hash is needed: existing native insertion validates records
and derives IDs. The public wrapper requires explicit kind/exact bytes and preserves
conversion/native failure poisoning, read-write rejection and lifetime rules. It is
not arbitrary key insertion, dependency bypass, immutable overwrite or raw LMDB IO.

If the seam cannot be implemented without changing native behavior, stop with the
smallest reproducer and request a scope decision. Do not silently expand the core.

### B. One typed edge enumerator and deterministic export

Implement a small typed dependency enumerator using owned public descriptions.
Keep kinds in graph keys. Follow root/anonymous nodes, composite datum keys/values,
all DAG bindings/tree entries and **all commit parents**. The complete source is
not a CLI prefix or current-tree-only scan.

Use iterative active/completed traversal, deterministic child order and postorder
emission. Test sharing versus cycles, deep histories beyond Python recursion depth,
exact object population and exclusion of truly unrelated source history. Preserve
original bytes with `get_record` in one pinned read transaction; no source writes.

Implement bounded format framing and base64 transport, not packed-record parsing.
Export returns owned bytes after handles close. Repeat export after source-head
movement and compare identical bytes. Reject missing/corrupt reached records and
profile overflow rather than returning partial output. Source native-read allocation
and long LMDB reader lifetime remain documented limitations.

### C. Atomic import with complete-bundle checks

Parse bounded input before destination writes where possible. Validate strict JSON
keys/types/format, IDs, base64, record/count totals and duplicate typed rows. Avoid
unbounded exception messages containing payloads; malformed/deep JSON must fail
cleanly without a destination batch. Record chosen profile limits in one owning
place, not drifting copies across readers/writers/tests.

One destination write transaction performs all native insertions, ID/byte checks,
typed dependency-before-dependent checks and full-root reachability/no-extra checks.
Dependencies must be earlier **bundle rows**, even if destination objects exist.
Do not treat native direct checks as proof of the entire bundle contract. Do not
skip existing keys or suppress stored corruption.

Optional destination ref is explicit create-or-same-target only, checked under the
same write lock. Different/malformed target fails without overwrite, repair, merge
or auto-name selection. Final commit/return only after the whole batch succeeds.
Import owns its transaction so an exception always aborts prior new objects/ref.
Do not expose a partial staging store, resume protocol or callback system.

### D. Failure, corruption and deterministic interruption

Use existing test-only raw corruption helpers for genuinely missing/corrupt source
or destination keys. They are fixture infrastructure, not shipped APIs. Distinguish
real malformed packed native records from substituted traversal graphs used to
exercise defensive cycle paths. No cryptographic-collision claim from synthetic IDs.

Late-row/ref/closure failure tests must introduce at least one new earlier object
and confirm its absence in a fresh reader after abort. Preserve unrelated destination
sentinels and refs. Test a real small-map import failure, not only a substituted
exception; use the existing map-size API and explicit whole-batch retry with a larger
map only as a caller-managed test, not automatic growth.

Private deterministic barriers should surround the storage-commit boundary:
terminate after a known number of puts but before commit, and after real commit but
before the helper returns. A fresh process proves old-state versus complete-state
publication. Do not infer failed import from a missing acknowledgement. Every process
has finite deadlines and finally-owned reap/scratch cleanup; classify portable and
signal/platform evidence separately. No installed fault controls.

### E. Installed acceptance and independent review

Implement [EXAMPLE.md](EXAMPLE.md) with real local attempts in A, full pinned export,
file-mediated fresh-process import into B and existing CLI inspection. Transferred
source must never run during export/import/inspection; assert no new occurrences,
no inferred refs and no historical-path/resource actions.

Build fresh current wheels through existing packaging tools. Run parent/exporter,
importer/reader and console outside the checkout with source PYTHONPATH unset;
assert installed module/extension/console/native paths. Close A before importer
launch and prove the importer needs only the bundle/B, not A. Compare every typed
record byte, parent order and deterministic re-export. Preserve existing local
runtime/tag/platform assurance qualifications; ask rather than bootstrap new tools.

Then pause runtime/test edits and release shared build ownership for independent
coordinator review/default checks. Surface findings/fixes with regressions. A passing
local suite is not permission to publish or proceed to another feature turn.

## 5. Acceptance and assurance matrix

| Area | Required evidence |
| --- | --- |
| Public packed insertion | Exact bytes/IDs; all existing kinds; explicit type; poison/abort on conversion/native failure; read/lifetime edges |
| Full typed closure | All parents, root/bindings, nested/shared DAGs, composite datum children; no unrelated branch-only data |
| Pin/determinism | Fixed commit ID, one source read snapshot; head movement has no effect; repeated export and B re-export bytes match |
| Native authority | Invalid header/type/version/NFC/float/order/length rejected; computed ID and exact bytes checked; no alternate Python codec |
| Self-contained bundle | Omitted child/parent rejected even when present in B; duplicate/extra/wrong-root/forward rows rejected |
| Import atomicity | Late failure removes earlier new objects/ref together; unrelated existing state unchanged |
| Idempotence/ref policy | Existing identical records/ref preserved; different/malformed ref and corrupt object rejected without repair |
| Persistence/process loss | Real map-full, injected write/commit faults, precommit death versus postcommit acknowledgement loss, fresh-reader oracle |
| Limits/framing | Invalid UTF-8/JSON/duplicate keys/base64, truncated/trailing input, encoded/decoded/count limits; short test IDs |
| No execution/ref inference | Attempt/result identity unchanged; no source code/URI/resource action; source reservation/publication refs absent |
| Installed/platform | Current source/wheel provenance, separated processes and old CLI outputs; declared versus actually tested runtimes/platforms qualified |

Prefer Hypothesis for bounded valid graph generation, order/identity/round-trip
properties and framing boundaries. Use a small deterministic set for real process
kills/map-full, not randomized hundreds of subprocess interruptions. Byte equality
is the oracle for canonical floats/NaN; Python NaN value equality is not.

Standard validation remains current `scripts/check.sh`, preserving C/Python gates.
Prior local pattern, to reinspect before use:

```sh
nix develop ../dml-build-tools --quiet --log-format raw --no-write-lock-file \
  -c bash scripts/check.sh -v
```

Keep new public wrapper/transfer/example code in measured Python source. Host-side
coverage is not installed/fresh-process coverage unless actually instrumented.
Retain meaningful private faults and precise exclusions/suppressions; no difficult
real failure may be hidden merely to reach a percentage. No new C is intended, so
Mull is not Python mutation assurance. Check available Python mutation tooling; if
absent, report the gap and use bounded negative-oracle probes for omitted-dependency,
ID-mismatch, ref-conflict and late-abort guards rather than pretending a broad score.

Retain binding/CLI memory workloads and, if extended, state exactly which new raw
insertion paths were exercised. Do not turn unchanged native source or old Valgrind
results into a new process-memory/security guarantee. Default `-v`, informational
CI `-c`, exclusions, skips and installed-only evidence stay distinguishable.

## 6. Documentation, delivery and review boundary

Only after implementation exists, add an owning as-built document such as
`docs/spec-next/transfer.md` for format/limits, transfer APIs, full-closure checks,
ref/atomicity behavior and trust/capture boundaries. Low-level `put_record` contract
belongs in `python-api.md`; native encoding/storage contracts remain in their owning
docs. Update navigation/Mermaid map, package orientation and examples in the same
scoped change. No glossary change is required merely for the explicitly document-local
object-closure label; do not redefine computational closure or remote as this bundle.

`RESULTS.md` here should record baseline/source state, selected choices/deviations,
changed files, exact commands/exits/counts, actual atomicity/process/installed evidence,
negative-oracle survivors/gaps, coverage populations/exclusions, memory suppressions,
platform/runtime limits and outstanding issues. Independent review especially checks
raw insertion poison/lifetime, typed completeness despite preexisting destination
records, all-parent history, late-error abort, optional ref behavior and no implicit
execution/reservation copying. Validate local Markdown targets/anchors and whitespace.

Stop for review when the bounded implementation is satisfactory. Future delegation,
commit/push and exact-SHA CI monitoring require separate user authorization for this
turn; do not inherit Iteration 4's completed request. No cloud/release/package
publication or later turn. This preparation does not assign a worker or start code.
