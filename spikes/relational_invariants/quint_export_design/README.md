# Quint design pilot: native pinned-commit export traversal

Status: the design pilot has been checkpointed. An opt-in native walker matches the real Python
exporter on the pilot fixture. The public exporter still uses Python; there is no public API
change, generated checker, or maintained-gate integration.

## Authority boundary

This directory records the pilot design and evidence. [Pinned commit transfer](../../../docs/spec-next/transfer.md)
owns the existing export contract. [Repository](../../../docs/spec-next/repository.md),
[objects](../../../docs/spec-next/objects.md), and [records](../../../docs/spec-next/records.md)
own native storage, codecs and identity. The earlier [Quint feasibility spike](../quint_feasibility/README.md)
exercised selected native behaviors through Python; it did not model this walk.

## What the walker can rely on today

| Prerequisite | Existing behavior and evidence |
| --- | --- |
| Typed, validated reads | The public getters in [`repo.h`](../../../include/dml/repo.h) return owned copies; codec views borrow those bytes. [`repo.c`](../../../src/repo.c) checks the requested kind, content ID and direct typed references within the transaction. This is not transitive validation. [Native history-driver tests](../../../tests/python/test_history.py) exercise persisted objects and corrupt-store failures through C. |
| Ordered edges | The native codec tests [`test_object.c`](../../../tests/c/test_object.c) and [`test_record.c`](../../../tests/c/test_record.c) exercise stored parent order, canonical tree/binding names and composite order. The walker must also honor transfer-specific order: tree before parents, DAG root before bindings, MAP key before value. Do not sort parent IDs. |
| Snapshot at read begin | The isolated public-C [probe](snapshot_probe.c) begins a read, then waits for a separate process to publish a ref move and a new object before doing its first lookup. The original read sees only the old state; a fresh read sees the new state. The probe also gets `not_found` when it asks for the known commit ID in the tree namespace and checks that fetched bytes survive abort and close. A late-reader control distinguishes the two snapshots. |

Against `33a17bf` on Linux ARM64, both reviewers ran the read probe and the three native tests
(`test_record`, `test_repo`, `test_object`). The independent rerun also passed 14 selected history
cases for persisted ordering, corrupt reads and the limit of direct validation. Valgrind reported
zero errors or lost bytes; the writer child had 96 still-reachable bytes inherited from the
parent's two expected-record buffers. The parent freed its copies. Native logs are under the
ignored `build/export-prereqs.Ns89Ct/`. This checks prerequisites, not exporter behavior or
portability. Getters can detect a corrupt direct edge before the walk schedules that child;
the model does not establish error precedence on a multiply corrupt store.

## Traversal contract and counterexample

[`export_walk_model.qnt`](export_walk_model.qnt) models a worklist with separate active and
completed **typed** keys. [`export_walk_rules.qnt`](export_walk_rules.qnt) checks completeness
and uniqueness against an independent reachability fixed point. Exact output order is checked
against a fixture sequence written without running either traversal. The rules consume abstract
ordered edges; they do not encode, decode or hash native records.

Five Quint tests enumerate 12 fixture variants (three parent arrangements, two LIST orders,
and optional DAG binding), and exercise deliberate faults:

- In all eight merge variants, a first-parent-only walk still passes the weak ordering check
  **among rows it emitted**, but fails completeness. The parents diverge and share a base;
  neither branch subsumes the other. A real import that checks every dependency would reject
  such a thin bundle; the point is to reject it at export testing, not after transfer.
- Independently reversing the parents, MAP key/value, or two newly reached SET elements preserves
  membership and dependency order but changes the required byte-stable row order.
- Extra and duplicate rows pass the weak ordering check and fail complete, unique membership.
  A synthetic missing typed key and a cycle fail traversal. The same-token/different-kind case
  is an abstract control, not a claim of a native hash collision. The malformed cases exercise
  failed traversal, not resource cleanup or disposal of a partial output buffer.

The finite checks use Quint's TypeScript evaluator, not an unbounded proof or a model checker.
In disposable copies, substituting the first-parent walk and dropping the type from the active
membership check each made the positive test fail.

## Run the design checks

Reuse the Quint 0.33.1 [tool setup](../quint_feasibility/README.md#run-locally), without the
native build from that recipe. From the repository root:

```sh
spike=spikes/relational_invariants/quint_export_design
quint="$PWD/build/quint-feasibility/tool/node_modules/.bin/quint"
"$quint" typecheck "$spike/export_walk_model.qnt"
"$quint" test "$spike/export_walk_model.qnt" --backend=typescript --max-samples=1
```

## Reproduce the C prerequisites

From the repository root in the Linux Nix development shell, with the vendored dependency
archives available, build under a fresh ignored directory rather than using the maintained gate's
build. The probe refuses an already existing store path before opening it.

```sh
(
  set -eu
  spike=spikes/relational_invariants/quint_export_design
  mkdir -p build
  out=$(mktemp -d "$PWD/build/export-prereqs.XXXXXX")
  export NIX_LDFLAGS="${NIX_LDFLAGS-}"
  export NIX_LDFLAGS="${NIX_LDFLAGS#-rpath $PWD/outputs/out/lib}"
  meson setup "$out/native" --wrap-mode=nodownload
  meson compile -C "$out/native" test_record test_repo test_object
  meson test -C "$out/native" --no-rebuild --print-errorlogs test_record test_repo test_object
  cc -std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -g -Iinclude \
    "$spike/snapshot_probe.c" "$out/native/libdml.a" -pthread -o "$out/snapshot_probe"
  timeout 10 "$out/snapshot_probe" "$out/store"

  # Expected exit 1 at the old-ref assertion, not a timeout or build failure.
  status=0
  timeout 10 "$out/snapshot_probe" "$out/late" --late-control > "$out/late.log" 2>&1 || status=$?
  test "$status" = 1
  grep -F 'same_id(&old, &actual)' "$out/late.log"
)
```

## Real Python export baseline

[`check_export_baseline.py`](check_export_baseline.py) builds a native repository with a shared base
and two divergent parent commits. It exports two pinned merges of those parents in opposite
stored orders. The left branch contributes a unique commit; the right also contributes a unique
tree and MAP/SET payload. The merge tree includes a repeated LIST element and a DAG reachable
through both a tree entry and a sub-DAG node. A stored unrelated datum is outside both closures.
The fixture has one DAG binding and one MAP pair: it checks root-before-binding and
key-before-value, not ordering among multiple bindings or MAP entries.

The checker supplies a hand-listed expected row sequence and fixture adjacency, neither
computed by the exporter or a reference DFS. It obtains IDs and expected packed bytes from
public native-backed insertion and reads. It checks canonical bundle bytes separately, then
passes the actual row order to direct Quint evaluation with the unchanged rules. The four
negative cases run the same Python exporter but temporarily replace its root edge list in memory;
no source file, fixture record, graph supplied to the oracle, or expected order changes.

| Export case | Rows, left-first / right-first | Ordered subset | Complete and unique | Exact order |
| --- | ---: | --- | --- | --- |
| Pristine | 22 / 22 | pass | pass | pass |
| Skip second parent | 13 / 21 | pass | fail | fail |
| Swap parents | 22 / 22 | pass | pass | fail |

On Linux ARM64, both pristine bundles matched the expected bytes and all 18 Quint verdicts
matched their case expectations. An independent review reran the checker in a separate process
with a fresh store and the same native binary, and verified the 24 declared graph vertices
against public typed reads. Raw bundles, the query module, and summary reproduced byte for byte;
ITF metadata can differ. Local artifacts are under
`build/export-baseline.CsO8IP/`, including the native build, the raw bundles, the Quint input
and output, a summary with bundle hashes and omitted IDs, and source/binary hashes. This checks
the current Python implementation and the oracle's sensitivity, not C export, performance, or
malformed-data handling by a new walker. The maintained full gate and CI were not rerun.

Run from the repository root in the Linux Nix development shell using the same Quint install
as the model. Build and stage an isolated copy of the Python runtime:

```sh
(
  set -eu
  spike=spikes/relational_invariants/quint_export_design
  quint="$PWD/build/quint-feasibility/tool/node_modules/.bin/quint"
  mkdir -p build
  out=$(mktemp -d "$PWD/build/export-baseline.XXXXXX")
  export NIX_LDFLAGS="${NIX_LDFLAGS-}"
  export NIX_LDFLAGS="${NIX_LDFLAGS#-rpath $PWD/outputs/out/lib}"
  meson setup "$out/native" --wrap-mode=nodownload
  meson compile -C "$out/native" _core.abi3.so
  mkdir -p "$out/python/daggerml"
  cp python/daggerml/daggerml/__init__.py python/daggerml/daggerml/transfer.py \
    "$out/native/_core.abi3.so" "$out/python/daggerml/"
  PYTHONPATH="$out/python" python -B "$spike/check_export_baseline.py" \
    --quint "$quint" --out "$out/evidence"
)
```

## Opt-in native comparison

[`src/export_walk.c`](../../../src/export_walk.c) acquires the ordered `(kind, ID, packed bytes)`
rows for an explicit commit using one live read transaction supplied by its caller. It keeps typed
active/completed state, visits one child at a time, and returns owned rows only on success. It
checks the row, per-record and aggregate packed-byte limits. The private `_core._export_rows`
hook is only compiled with `-Dexperimental_export_walk=true` (default: off). The experiment
changes neither the installed C API nor `export_commit()`, import, or on-disk storage. Python
still owns JSON/base64, encoded bundle-size checking, and exception mapping.

Reproduce on Linux in the repository's Valgrind shell. Use the same Quint install and vendored
wrap archives as above. The runner snapshots inputs, compiles both variants in new private source
copies, and prints the receipt directory. It never edits the checkout or `build/check`.

```sh
nix develop .#valgrind -c bash \
  spikes/relational_invariants/quint_export_design/run_native_export_control.sh \
  "$PWD/build/quint-feasibility/tool/node_modules/.bin/quint"
```

| Native build | Rows, left-first / right-first | Ordered subset | Complete and unique | Exact order |
| --- | ---: | --- | --- | --- |
| Pristine | 22 / 22 | pass | pass | pass |
| First-parent-only control | 13 / 21 | pass | fail | fail |

Both pristine exports matched the fixture's ordered rows and the **unchanged Python export bytes**.
The runner changes one C edge-count rule for the control, omitting the second parent in both
roots. The retained Quint rules distinguish incomplete exports from ordered subsets. Neither the
adapter nor the fixture changes between builds. The independent review reran both variants and
cross-checked the mutation diff and raw output.

The [boundary check](check_native_export_boundaries.py) compares exact, one-below and zero limits,
and checks missing root, missing reached child, and malformed reached child errors against the
Python exporter. The [allocation sweep](export_fault_sweep.py) injects each of 79 native and 23
binding allocation failures in the fixture and verifies recovery on the same read handle. Its
Valgrind run reported zero errors and zero lost bytes. It precompiles the staged Python because a
local CPython parser block also reproduced without executing DML; the broader comparison runs
normally to keep unrelated OpenSSL import diagnostics out of the allocation check. No new
suppressions were added. The independent native probes also checked finished rows after snapshot
close, 150 allocation failures on a 34-commit path, and a fake-getter cycle with a shared token
across two kinds. The synthetic cycle is not a claim about native hash collisions. Both native
probes reported zero Valgrind errors and zero bytes in use at exit.

The Linux ARM64 comparison receipts are under `build/export-native-control.zYZIls/`. The
independent review's receipts and disposable native probes are under `build/export-review.Tjv7NB/`.
The opt-in path is not part of the maintained coverage denominator. The full default
`scripts/check.sh -v` gate passed on Linux ARM64 with the hook off: 7 C tests, 3,423 Python tests,
100% maintained coverage, and both memory workloads. Its log is under
`build/export-validation.5EFbml/`. Remote CI and other platforms were not run.

## End-to-end export benchmark

[`native_export.py`](native_export.py) is a spike-only candidate: acquire owned packed rows in
one read transaction, close it, then use the public exporter's Python framing options and limits.
It neither replaces `export_commit()` nor changes any import or on-disk behavior. The benchmark
and boundary check do not need Quint.

On Linux, use the Nix development shell and vendored dependency archives as above. Use an idle
host with a CPU available to your process; substitute its number for `2` below. Both exporters
run through the same staged release build and interpreter.

```sh
(
  set -eu
  spike=spikes/relational_invariants/quint_export_design
  mkdir -p build
  out=$(mktemp -d "$PWD/build/export-benchmark.XXXXXX")
  export NIX_LDFLAGS="${NIX_LDFLAGS-}"
  export NIX_LDFLAGS="${NIX_LDFLAGS#-rpath $PWD/outputs/out/lib}"
  meson setup "$out/native" --wrap-mode=nodownload -Dbuildtype=release -Dexperimental_export_walk=true
  meson compile -C "$out/native" _core.abi3.so
  mkdir -p "$out/python/daggerml"
  cp python/daggerml/daggerml/__init__.py python/daggerml/daggerml/transfer.py \
    "$out/native/_core.abi3.so" "$out/python/daggerml/"
  export PYTHONPATH="$out/python"
  taskset -c 2 python -B "$spike/benchmark_export.py" --out "$out/evidence" --repeats 6
  python -B "$spike/check_encoded_export_boundaries.py" --out "$out/encoded"
)
```

[`benchmark_export.py`](benchmark_export.py) creates immutable fixtures at several sizes: shared
merge history (diamonds), deep linear history (commits), wide trees and DAGs (named entries or
bindings sharing one target), and distinct 1 MiB byte payloads in a list. Both wide fixtures have
just five output rows: they isolate edge fanout rather than unique row count. The
driver checks exact bundle bytes and expected row count before measuring; that also warms the file
cache. It alternates exporter order across serial pairs. Each worker opens the repository and
returns bundle bytes once in a fresh process. It times that call and reads Linux process peak RSS
(`VmHWM`) before hashing the result. RSS includes interpreter imports and resident mapped pages;
it is not a measurement of Python heap alone. `results.json` retains samples, hashes, CPU affinity
and per-case timing breakdowns from one separate instrumented run per exporter. The native
acquisition phase includes repository open/close and binding copies; Python interleaves walking
and base64, so its pre-JSON phase cannot separate them.

[`check_encoded_export_boundaries.py`](check_encoded_export_boundaries.py) uses independently
expected bundles for the two pinned merges. Both exporters accept an exact 3,201-byte cap, reject
when the cap is one byte smaller or zero with the same error, then export successfully again. The
check also verifies precedence between count, per-record and aggregate packed limits, and that
traversal errors still precede the encoded cap. It lowers the cap because with the default packed
and object count caps, base64, row punctuation, and the header together are bounded below 32 MiB.
In disposable copies, changing `>` to `>=` failed the exact-cap check, and dropping the check
failed the one-below case.

### Linux ARM64 results

Both paths produced identical bundle bytes in all 17 cases. Selected largest sizes below are
medians of six uninstrumented exports per path (Python 3.12.15, GCC 15.3 release build).

| Fixture | Python ms | C rows + Python ms | Speedup | Python RSS MiB | C rows + Python RSS MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| 8,192 shared diamonds | 191.92 | 53.72 | 3.57× | 50.86 | 46.52 |
| 8,192 linear commits | 53.37 | 15.95 | 3.35× | 31.81 | 30.63 |
| 16,384 tree entries | 514.95 | 334.64 | 1.54× | 30.22 | 26.07 |
| 16,384 DAG bindings | 513.18 | 331.65 | 1.55× | 30.39 | 26.07 |
| 12 MiB of byte payloads | 45.82 | 43.41 | 1.06× | 74.89 | 86.26 |

An independent release build reproduced the same bundle hashes and similar time and RSS ratios
for four of these cases. Primary receipts are under `build/export-benchmark.aIoVrD/` (use
`final/results.json`); independent receipts and disposable boundary controls are under
`build/export-benchmark-review.WENWKY/`. These synthetic, warm-cache runs do not establish
production workload ratios or performance on other hosts. The separate maintained `-v` gate
passed with the hook off and eight workers (7 C tests, 3,423 Python tests, 100% maintained
coverage, and both memory workloads); its log is under `build/export-benchmark-gate.n8e5ux/`.

At this checkpoint, quadrupling the entry count from 4,096 to 16,384 took roughly 15 times as
long on the candidate. In one phase sample the candidate spent 335 ms acquiring and binding the
widest tree and less than 2 ms framing it. Repository validation, Python's native decoder, and the
C walk all used indexed accessors that rescanned variable-length entries from the start. On the
12 MiB fixture, JSON/UTF-8 and return took about 26 ms on either path in the phase runs. The candidate also holds a complete
packed-row tuple before base64, and the measured peak RSS rose by about 11 MiB.

Keep `export_commit()` on Python. The native walk is promising for history-heavy closures, but
wide-record scaling and the packed-row handoff must be evaluated separately before proposing a
switch.

## Linear named-entry iteration

The follow-up replaces repeated indexed reads with a private forward cursor over validated
packed bytes. Repository get/put reference validation, DAG name lookup, Python object decoding,
and the opt-in C walker now consume tree entries and DAG bindings in packed order, without
rescanning the prefix. Public indexed accessors retain the same behavior; native CLI iteration
is outside this comparison. `export_commit()` still uses Python traversal. No packed records,
transfer format, or public interfaces changed.

[`benchmark_wide_export.py`](benchmark_wide_export.py) compares release builds before and after
the cursor change against the same five-row fixtures. It times packed get and insert (including
native reference validation), native decoding, lookup of the last DAG name, and both end-to-end
exporters. The isolated operation timers exclude repository and transaction setup. Inserts run
in a dependency-only store and abort after timing. Each timed call runs in a fresh process; its
result is checked against the fixture before the sample is accepted. The runtime order alternates
across pairs after warm-up. Fixture identities, bundle hashes, samples, and runtime
hashes are recorded in `results.json`.

Run in the Linux Nix shell with the vendored wrap archives and an idle CPU as above. Build the
baseline from checkpoint `6a3c4b8`; use the same staged release build recipe for the current
checkout. For example:

```sh
(
  set -eu
  spike=spikes/relational_invariants/quint_export_design
  mkdir -p build
  out=$(mktemp -d "$PWD/build/export-wide.XXXXXX")
  mkdir -p "$out/before-src/subprojects"
  git archive 6a3c4b8 | tar -x -C "$out/before-src"
  cp -a subprojects/packagecache "$out/before-src/subprojects/"
  export NIX_LDFLAGS="${NIX_LDFLAGS-}"
  export NIX_LDFLAGS="${NIX_LDFLAGS#-rpath $PWD/outputs/out/lib}"
  stage() {
    local label=$1 source=$2
    meson setup "$out/$label-build" "$source" --wrap-mode=nodownload \
      -Dbuildtype=release -Dexperimental_export_walk=true
    meson compile -C "$out/$label-build" _core.abi3.so
    mkdir -p "$out/$label-python/daggerml"
    cp "$source/python/daggerml/daggerml/"{__init__,transfer}.py \
      "$out/$label-build/_core.abi3.so" "$out/$label-python/daggerml/"
  }
  stage before "$out/before-src"
  stage after "$PWD"
  taskset -c 2 python -B "$spike/benchmark_wide_export.py" \
    --baseline-python "$out/before-python" --candidate-python "$out/after-python" \
    --out "$out/evidence" --repeats 6
)
```

### Linux ARM64 scaling results

At widths 4,096 → 8,192 → 16,384, doubling width took 3.55–4.00× as long before the
change and 1.79–2.25× as long after it, across the measured operations. At width 16,384,
the medians of six warm-cache samples were:

| Operation | Tree before → after (ms) | DAG before → after (ms) |
| --- | ---: | ---: |
| Packed get | 166.3 → 1.72 | 164.0 → 1.73 |
| Packed put | 169.6 → 1.65 | 168.1 → 1.67 |
| Native decode | 165.3 → 2.13 | 163.6 → 1.88 |
| Last-name lookup | — | 329.8 → 1.82 |
| Public Python export | 517.6 → 21.7 | 514.8 → 22.9 |
| Opt-in C walk + Python framing | 328.6 → 3.53 | 329.6 → 3.58 |

An independent pair of builds matched all eight fixture identities and bundle hashes and
reproduced the scaling (3.54–4.04× before versus 1.88–2.20× after per doubling). These are
synthetic fixtures with shared targets; packed put excludes sorting and commit, and last-name
lookup includes full read/reference validation. The benchmark does not measure RSS. Primary
and independent receipts are in `build/wide-iteration.PvlX8E/paired-evidence/results.json` and
`build/export-cursor-review.CjHqjl/evidence/results.json` respectively.

### Correctness checks

- Maintained regressions check variable-length names with distinct targets, canonical order,
  first-error precedence on read and write, and transaction poisoning. Independent review ran
  the new tests against both builds.
- The opt-in checks reproduced both pinned merge bundles, their Quint verdicts, all packed and
  encoded limit boundaries, storage errors, and recovery. Both exporters also matched the 17
  checkpoint fixtures' bundle hashes, row counts, and packed and encoded sizes.
- A 46-row fixture descends past the initial C stack capacity while both named cursors are
  suspended. It checks exact rows and resumes through aliases to distinct siblings. In a
  disposable build, resetting the tree cursor for every edge failed this oracle. Valgrind
  reported zero errors in the existing allocation sweep; the independent run on the deep fixture
  exercised 152 native and 47 binding allocation positions with recovery and zero errors.
- The maintained `scripts/check.sh -v` gate ran with the hook off and seven workers: 7 C tests,
  3,427 Python tests, 100% maintained coverage, and both Valgrind workloads. No new coverage
  exclusions, remote CI, or other platforms. Receipts: `build/export-cursor-gate.vwE78Q/`,
  `build/export-cursor-native.sNHJ9U/`, and `build/export-cursor-control.E4JfAO/`.

The public exporter already benefits from the cursor. The C walker stays opt-in.

## Packed-row handoff

The binding now frees each native packed buffer after copying the row into the Python tuple.
The tuple is returned only after all rows convert. On failure, the partial tuple is discarded
and the caller's existing bulk cleanup frees the remaining native buffers. Transaction ownership,
packed and encoded limits, and Python framing are unchanged.

To reproduce, use the [release-build benchmark recipe above](#end-to-end-export-benchmark) at
`70d254b` and with the handoff change. Pass `--case payload:1 --case payload:4 --case payload:12`
and use `--repeats 8`. Primary medians on Linux ARM64:

| Payload | Native before ms | Native after ms | Public RSS MiB | Native before RSS MiB | Native after RSS MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 MiB | 3.76 | 3.71 | 29.79 | 29.15 | 29.15 |
| 4 MiB | 14.73 | 15.02 | 42.58 | 45.81 | 45.19 |
| 12 MiB | 40.97 | 41.57 | 74.52 | 85.84 | 85.21 |

An independent run built both versions and alternated six before/after samples against the same
repositories. It reproduced the 0.625 MiB peak reduction at 4 and 12 MiB. It did not reproduce
the direction of the 12 MiB timing change. The native path still used about 11 MiB more peak RSS
than the public path at 12 MiB.

In a separate 12 MiB diagnostic, three fresh processes per exporter/build sampled `/proc/self/status`
at the end of binding, after closing the read transaction, before JSON, and after bundle return.
Writing `5` to `/proc/self/clear_refs` after each marker reset `VmHWM` for the next interval. Native
peak RSS through binding fell from 56.35 to 46.35 MiB, but by the start of JSON live RSS was
51.05 versus 50.43 MiB. The highest interval was JSON/UTF-8 through return: 83.05 versus 82.43 MiB
(public: 71.75 MiB). These measurements include mapped pages and allocator state, not just live
objects. The earlier release lowers the binding peak but does not remove the full Python tuple's
packed-byte lifetime during base64 framing.

The exporters produced identical bytes for all 17 fixtures and matched the checkpoint hashes.
The packed and encoded boundary checks, storage-error precedence, and Quint merge checks passed.
Under Valgrind, the pinned merge and 12 MiB fixture recovered on the same read handle at all
injected failure positions (79 native and 23 binding; 58 native and 18 binding, respectively),
with zero unsuppressed errors and no new suppressions. Independent review repeated the packed
and encoded boundary checks and pinned merge fault sweep. The [archived receipts](evidence/handoff/)
include primary and independent timing samples, the RSS probe and its samples, and hashes for the
17 parity fixtures. Paths in the primary timing receipts are relative to the original checkout.
The hook-off `-v` gate passed with eight workers: 7 C tests, 3,427 Python tests, 100% maintained
coverage, and both Valgrind workloads (local log: `build/export-handoff.OhkA9s/gate.log`).
No remote CI or other platforms ran.

At the close of the study, `export_commit()` still uses Python. Releasing packed Python rows as
base64 framing consumes them was considered but not tested.
