# Installed validation-read experiment — rejected prototypes

The user approved installed Python validation-internal optimization by stating “proceed”
after the explicit request to retain C/storage/public APIs. Read the
[plan](VALIDATION-READS-PLAN.md), [review](HOLISTIC-REVIEW.md), and
[checkpoint](../../checkpoints/holistic-test-performance.md).

Outcome: **NO prototype retained in implementation**. DML restored CLEAN to local
`15555c01e4db19a20b4de7049f776c4d995bd5e0`; nothing committed/pushed/run in GHA.
Five-minute goal remains unmet. The experiments established read-count reductions but
not representative elapsed-time improvement; this does not justify shipping extra complexity.

## Bounded scope and evidence

Only installed `transfer.py`/`builtin.py` and one new test module were drafted. Low-level
Repository/Transaction source, public signatures, C/storage/entities/diagram/workflows,
original tests/assertions/budgets/deadlines/exclusions/thresholds unchanged. No dependency
fetch/hash repair/Nix invocation/install/native19/accepted-story/extra-agent/full-suite run.

Evidence: `../dml/build/validation-reads/20261107T230945Z/`.
Used existing cached serial Python3.13.15 environment with pytest9.0.3/Hypothesis6.151.10.
For focused coverage only, added existing cached coverage7.14.1 site-packages on invocation
PYTHONPATH; no package installation or changed tools flake/lock. Native counters isolated.
Missing xdist/pytest-cov/psutil and earlier Nix preparation failure still block the usual
complete parallel gate; cached serial profile/focused coverage is NOT full-gate assurance.

### Draft 1: bounded per-transaction read facade

Raw/typed immutable reads shared within actual transfer/Inspector transaction. Warm native
validity probes preserved; proxies/HOST getter changes delegated; no mutable refs/failures
cached, Inspector public tx identity unchanged. `focused-v1`:164 existing checks PASS5.15s.
`profile-v1`:ONE same representative HOST-native-metadata test PASS8.10s pytest/6.62s body,
10,324,177 profiler calls;57,126 raw reads versus106,095 baseline, but148,250 ref reads versus
99,281. Wrapper/state-probe overhead increased elapsed time. Explicitly REJECTED/restored,
source/log/XML/profile retained. Not an accepted new cache/public contract.

### Draft 2: decode one already-fetched record via getter algorithms

Transient packed-record frame fed existing native getter/codec algorithm to shared edge rule.
No long-lived cache/proof flags. Builtin retained scan and transfer use same typed dependency
rule, preserving builtin parent/tree ordering. `focused-v2`:165PASS8.54s (including one
representative case). `profile-v2`:ONE representative PASS7.09s pytest/5.63s body. Getter/frame
dispatch still did not establish a speedup; refined explicitly, older bytes retained.

### Draft 3: direct native-codec dependency projection

Same ONE fetched native raw record decoded with existing native codec, projecting dependency
IDs without constructing unused public wrapper fields; no replacement byte/role codec.
Proxy/HOST typed/object/raw/native getter substitutions deliberately fell back to original
behavior. Export/import framing, graph cycle/count/byte limits, semantic/provenance checks,
ALL parents and builtin traversal order retained. No supplied retained-membership proof.

Eight new checks measured one native raw read per exact reached object independently for
export and retained scanning; repeat scans still revalidate. Rich all-five-kind fixture includes
list/set/map/scalars, literal/sub-DAG nodes, DAG bindings, trees/multiple parents and unrelated
branch. Exact edge parity/closure/export-import bytes, HOST substitutions/proxy fallback,
native codec failure and tightened limits checked. Existing test functions unchanged.

- `focused-v3`:172PASS5.61s, no coverage.py.
- `profile-v3`:ONE representative PASS7.08s pytest/5.58s body;8,500,106 profiler calls.
- `covered-focused`:238 affected original+new controls PASS43.82s; final frozen draft
  builtin447/447 + transfer199/199 lines measured100 (646total). Includes original transfer
  framing/process/example and builtin profile/edges/atomicity/workflow checks. No new exclusion.
  Focused coverage is NOT native/full coverage/Valgrind/platform assurance; existing subprocess
  test results are not a newly accepted installed computational story/custody claim.

Final direct projection still measured132 retained scans/63exports/24 projection generator
entries-resumptions,76,944 raw reads (about27.5% fewer)/99,281 ref reads. Earlier current baseline
ONE profiled representative body5.25s/pytest6.48s, raw106,095/ref99,281; separate owning
[review](HOLISTIC-REVIEW.md) preserves baseline source/environment. Profiled nested times overlap,
instrumentation/load variation matter: not a fixed-workload whole-suite speedup or statistical
regression diagnosis. However **no convincing improvement is established**; don't repeat until
preferred timings appear or relabel read-count improvement as elapsed-time success.

## Decision and restoration

Final draft source/test/diff/digests retained in `rejected-final/` (also `covered-focused/source/`).
Restored ONLY the two owned runtime drafts to HEAD; removed ONLY the new owned test file after
preserving its bytes. Verified empty implementation source/index at15555c0, no active pytest/
Nix/check owner found. No shared coverage database/gate result replaced by focused evidence.
Initial checkpoint source and earlier rejected variants remain distinguishable.

The installed-Python extension permission applies to bounded performance work, not automatic
endless experiments. Stop this read-reduction slice. Stronger next direction is reducing repeated
WHOLE-history validation/recomputation, not more low-level read wrappers or per-test fixture caches.
Need concrete exact scope/identity/proof/budget/error/state plan before integrating a shared context;
132 scans/63 exports cannot be assumed to be all equivalent/distinct-root duplicates without data.

Full validation environment decision remains required before final engineering gate. No automatic
Nix repair/download/install/hash bypass/full/profile/story/CI/push. Both builds/source/evidence
coordinator-owned, old coding workers stopped; GHA disabled/native19 PAUSED/private candidate
retained/VP001 OPEN UNKNOWN/owner/revisit conditions unchanged. New design notes uncommitted.
