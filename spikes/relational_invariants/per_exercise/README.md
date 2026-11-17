# Per-exercise E/P/C reuse — isolated three-case prototype

**COMPLETE/ACCEPTED/STOPPED**, isolated/uncommitted. [Results and qualifications](../../../../dml-design/maintenance/relational-testing/PER-EXERCISE-RESULTS.md).
Actual63Q33T8E11P14C30reuse/newprocess/7groups/scopedpool/main-sibling15; SAME4272audit0;
causal final286PASS117.25s/XML0. Runtime10/source exact accepted story; finaltest-only canonical
byte-equivalent fixture bridge qualified. Originalfocus48/full284 RAWfailures preserved, PE-001–004
owning causal fixes/typed/outcome controls/reviewer owner-glob correction retained. Prior59 unchanged.
53story+8newCONTROLCLI wait0absent; own originals identity-retired/evidence retained. No further
reader/test/stage/preparation/build/CI/main/push/promotion; delegated gates bounded turn now stopped.
Post-gate README/design notes only; actual executed runtime and final test bytes unchanged.
[Design](../../../../dml-design/maintenance/relational-testing/PER-EXERCISE-DESIGN.md),
[coordination](../../../../dml-design/maintenance/relational-testing/PER-EXERCISE-COORDINATION.md).
Older modules/tests/roles/evidence remain unchanged; no main/API/native/build/install/CI/push.

Cases positive-a42/negative-b42/positive-c43, then negative-b44. ONE shared native evidence store,
case-isolated fixtures/six builtin positions/actual OLD producer descriptors. ONE shared decoder,
per-case immutable canonical P capsules; fixed conflict-checked pooled materialization/roots LOCAL.
C reads scoped pooled facts with source authority; negative requires ONLY exact owning counterexample,
not merely that the intended violation is present. Stage selectors reuse existing core unchanged.

Current grouping index records NEW requested spec/Q versus OLD-or-NEW producer T/O/key/artifact/
native descriptor/CN. Controller IDs in evidence are BYTES foreign refs, verified against actual
controller roles/satisfactions; controller grouping links native Q/T/O in its own store. No global
origin inference/rewritten producer occurrence/fake fresh attempt. Separate emptyP0/orderedPN parent
chains per batch generation, all current roots/history preserved. Whole candidate invalidation
conservative; no masks/evaluator/registry/scheduler/property randomness/discovery/eviction assumed.

P/C keys retain OWN upstream key/artifact/roots, not unrelated generation/pool identity. Fixed
materializer admission/confined ALL-view SQL is prerequisite. Reused checks are historical proof,
not new coverage/platform execution; ordinary grouping/pool admission still performs metadata IO.
Fresh results unselected until explicit adoption.15selector story bound; no increased caps/deadlines.

## Linux/Nix portability continuation

This section owns the current preparation workflow. The acceptance above is historical;
new manifests and runs do not inherit it. Linux x86-64 and ARM64 can generate their own
source/native/runtime identities. Other operating systems and the older indexed controller
(with its separate historical tool/fault-artifact pins) are outside this continuation.

Enter `nix develop` for the compiler, Python, pytest and DuckDB CLI. In that shell, build an
owned native extension without the shell's mutable output-directory RUNPATH:

```sh
export NIX_LDFLAGS="${NIX_LDFLAGS#-rpath $PWD/outputs/out/lib}"
meson setup build/spike-native --wrap-mode=nodownload
ninja -C build/spike-native _core.abi3.so
mkdir -p build/portable-spike
python -I -B spikes/relational_invariants/incremental/runtime.py "$PWD" \
  build/portable-spike/review.json --core build/spike-native/_core.abi3.so
```

Inspect the review manifest before preparation. It records tracked source bytes (plus the new
runtime support module before its first commit), an explicitly chosen native artifact, resolved
Nix executables and hashes, machine architecture, native library paths and runtime closure.
It is a review input, not a signature or a reproducible-build certificate. Keep its printed
SHA256 with review notes. Untracked application files are not implicitly admitted. Source or
artifact changes require a new manifest, not a relaxed comparison. Use fresh output directories.
Run focused tests with `-B`: importing frozen modules must not add bytecode files to the exact
asset inventory. An ordinary pytest invocation can contaminate its own snapshot; verification
then correctly rejects that snapshot rather than ignoring the extra files.

```sh
python -I -B spikes/relational_invariants/per_exercise/driver.py prepare "$PWD" \
  build/portable-spike/pins --review build/portable-spike/review.json
PORTABLE_REVIEW="$PWD/build/portable-spike/review.json" \
PER_EXERCISE_PINS="$PWD/build/portable-spike/pins/pins.json" \
  python -B -m pytest -q spikes/relational_invariants/test_portable_pins.py \
  spikes/relational_invariants/per_exercise/test_per_exercise.py
# After focused checks and review, one bounded seven-round acceptance story:
python -I -B spikes/relational_invariants/per_exercise/driver.py story \
  build/portable-spike/pins/pins.json build/portable-spike/story
```

Preparation checks review inputs before copying; verification checks frozen assets, source/native
claims and current runtime executable hashes. Runtime identity participates in namespaces and
stage keys. Checkers receive the pinned DuckDB executable explicitly; standalone shared-index
checks resolve DuckDB from PATH. Linux `/proc` receipts still reject loaded shared libraries
outside the declared immutable closure. This is not a security sandbox, hermetic build or
cross-machine cache portability claim. Receipts retain absolute locations and cannot be relocated.
No historical evidence stores, tests or services are automatically restarted by these commands.

Seven-round intended63Q33T8E11P14C30reuse/5poolload14queryCLI/1newcontinuation. Grouping7 events
additional to63requests+33attempt reservations. Actual scopes/caps/PIDs/true exits and artifact hashes
recorded, no security sandbox/reproducible build/fullcapture/current coverage claim. Current focused
CONTROL fixture is distinct from acceptance; direct helper execution/native reads/SQL counted
separately, not reported as selected acceptance attempts. Runtime errors retain partial evidence/STOP.
