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

## Before switching the public exporter

Measure end-to-end export time and peak memory on shared, deep and wide graphs. In particular, the
indexed tree-entry and binding accessors scan from the start of the record, and the new binding
materializes the complete packed row set before encoding. This experiment neither establishes a
speedup nor tests the encoded-size limit via an alternate public exporter. Keep codec-iteration
redesign separate and leave the default Python path in place pending the measurements.
