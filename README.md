# DML

DML currently provides a C library for content-addressed data and history in a local
transactional repository, with [binary commit transfer](docs/spec-next/transfer.md)
and an optional [Python core binding](docs/spec-next/python.md).
See the [as-built specification](docs/spec-next/README.md)
for the implemented contracts and [architecture](docs/architecture.md) for the module
boundaries.

The earlier Python package, CLI, test suites, and spike evidence are preserved at
[`feasibility-complete`](https://github.com/micha/dml/tree/feasibility-complete).
That package and its application layers are not maintained or run on this branch.

## Build and validation

Use a C11 compiler, Meson 1.4 or newer, and Ninja. Meson uses the pinned dependency
wraps from `subprojects/`. Run the [build check](docs/validation-policy.md) with:

```sh
scripts/check.sh
```

This configures and compiles a debug build in `build/core-check/` without running
tests. The CI matrix uses `--quint` to build and run the checks below.

### Quint behavior checks

The opt-in Nix shell supplies Python and pins [Quint](https://quint.sh/) 0.33.1
for the TypeScript backend:

```sh
nix develop .#quint -c ./scripts/check.sh --quint
```

Without Nix, use CPython 3.10+ with its development headers and install Quint
locally with Node.js and npm:

```sh
npm install --prefix build/quint-tool --no-save --ignore-scripts @informalsystems/quint@0.33.1
PATH="$PWD/build/quint-tool/node_modules/.bin:$PATH" scripts/check.sh --quint
```

On Windows, use the MSYS2 UCRT64 toolchain, including Python and Node. To bypass
npm launchers, point `DML_QUINT_SCRIPT` at the installed JavaScript entry point
(as CI does on every runner):

```sh
DML_QUINT_SCRIPT=build/quint-tool/node_modules/@informalsystems/quint/dist/src/cli.js \
  ./scripts/check.sh --quint
```

Pass `DML_QUINT_SCRIPT=` to switch an existing build back to `quint` on `PATH`.

This builds the test executables in `build/core-check-quint/` and runs
`quint-refs`, `quint-transfer`, `quint-gc`, `quint-staged-import`, the
[provenance handoff and recorded-calls integrations](tests/README.md#process-integration),
and focused interpreter, Python binding, integrity, boundary, and fault tests.
The [shared trace interpreter](tests/README.md) replays one core function per
Quint request. Ref replay uses public `daggerml.core`; the other core replay
suites still use a private test binding. Quint checks observations against the
[ref contract](docs/spec-next/repository.md#refs), [transfer contract](docs/spec-next/transfer.md),
and [garbage collection contract](docs/spec-next/repository.md#explicit-garbage-collection).
Reopened read transactions and independent LMDB scans check snapshot publication,
rollback, datum readback from imported history, and recording, transferring back,
conditionally publishing a caller's result, and guarded staging-ref release.
The transfer history also checks exact unreachable IDs before staging an import and
retention after releasing `incoming`. The staging suite checks that a staged
result survives collection even when publication is stale, and that a rejected
import leaves no new objects or refs. The collection suite checks ref ordering,
rollback, and exact persisted removals. Native checks exercise damaged repositories,
allocation failures, and deletion failures. These checks run in CI on Linux and
macOS (x86-64 and ARM64) and Windows (x86-64). CI does not measure coverage or
build a Python wheel.

### Install the Python binding

With GIL-enabled CPython 3.10 or newer, Python development headers, and the native
build tools above, build and install a local wheel from the checkout. For example,
with an active virtual environment:

```sh
python -m pip install .
python -c 'from daggerml import core; print(core.TXN_READ)'
```

The wheel targets the CPython ABI and platform used to build it. It contains no
CLI, C development files, or historical `daggerml` application modules. The
standalone C build does not require Python headers; pass `-Dpython_bindings=true`
to also build and install the binding with Meson. See the
[Python contract](docs/spec-next/python.md) for supported operations and an example.

### Record two composed calls in Python

With the [public binding installed](#install-the-python-binding), run the
[recorded-calls example](examples/recorded_calls.py) from the checkout. Use a new
repository path with an existing parent directory:

```sh
python examples/recorded_calls.py record ./calls-repo 7 5 3
python examples/recorded_calls.py inspect ./calls-repo
```

`record` computes `sum(7, 5)` and then `scale(sum_result, 3)`. It prints the ID of
an initial commit published to `main` in the same write transaction as both calls.
The inputs and results must fit signed 64-bit integers. Arithmetic overflow aborts
the write and leaves the initialized repository without a published snapshot.

This is an application convention using ordinary DML objects, not a new core
record type. The commit's sole tree entry, `recorded-calls-v1`, selects the scale
DAG. Each call DAG's root is its result literal and its `implementation` binding
names the versioned operation. Sum binds `a` and `b`. Scale binds `factor` and an
`input` sub-DAG node that points to the exact sum DAG. Scale reads its first
argument through this edge, not by looking up the scalar value.

`inspect` opens a read transaction and prints JSON with the commit ID and both
calls in dependency order. It follows the stored edge and reports argument and
result values and node IDs without executing or verifying either operation. The
versioned names identify implementations by example convention, not by code
fingerprint or attestation. IDs identify immutable records, not distinct execution
attempts; recording identical calls can produce the same IDs. Inspection leaves
committed data unchanged; the repository still uses LMDB's normal locking.

### Install and link the C library

For example, install the headers and static library under a local prefix:

```sh
meson setup build/release --buildtype=release --prefix="$PWD/build/install" --libdir=lib
meson compile -C build/release
meson install -C build/release
```

The archive includes the pinned vendor libraries. On a Unix compiler driver that
accepts `-pthread`, build and run the [standalone transfer example](examples/transfer_history.c)
against the installed headers and archive:

```sh
run_dir=$(mktemp -d "$PWD/build/transfer-example.XXXXXX")
cc -std=c11 -Ibuild/install/include examples/transfer_history.c \
  build/install/lib/libdml.a -pthread -o "$run_dir/transfer_history"
"$run_dir/transfer_history" "$run_dir/source" "$run_dir/destination"
```

The program creates two revisions in the source repository and transfers the tip
and its history. It [atomically stages the import](docs/spec-next/transfer.md#atomic-staging)
under `incoming` and reopens the destination to inspect it while `main` is still
absent. It then explicitly publishes the inspected commit to `main` and reopens
again. Through both refs it verifies that the tip reads `43` and its first parent
reads `42`. Use two distinct paths that do not yet exist, with existing parent
directories. The program leaves both repositories and the staging ref for inspection.

Alternatively, use two fresh paths to [record a result without publishing to `main`](docs/spec-next/transfer.md#record-a-result-without-publishing-to-main):

```sh
"$run_dir/transfer_history" --lineage "$run_dir/input" "$run_dir/worker"
```

The worker reopens and verifies that `result-pin` yields `44`, that its sole parent
is the exact staged input (`43`), and that the recorded implementation ID is
`example.add-one@1`. The worker's `main` remains absent.

To [return and publish that result](docs/spec-next/transfer.md#return-and-publish-the-recorded-result),
run the full workflow from two new paths:

```sh
"$run_dir/transfer_history" --round-trip "$run_dir/original" "$run_dir/compute"
```

The original repository stages the result under `returned` and inspects it without
recomputing it. It conditionally moves `main` to the inspected commit and releases
`returned` only after successful publication. After reopening, its `main` yields
`44`. The worker releases `incoming` only if it still points at the inspected
input, then reopens and reads the same result and input through `result-pin`.

To run [explicit garbage collection](docs/spec-next/repository.md#explicit-garbage-collection)
after each staged import and again after releasing the staging refs, use
`--round-trip --collect` with two fresh paths. The example expects zero removals
and verifies the pinned and published lineage again.

To diagnose a repository without modifying it, use the
[read-only integrity and reachability API](docs/spec-next/repository.md#snapshot-integrity-and-reachability).
It distinguishes damage from intact objects that no ref retains. It does not
perform garbage collection.

### Three-process provenance handoff

Using the installed library and `$run_dir/source` from the first example above,
run the [handoff](docs/spec-next/transfer.md#resume-a-handoff-across-processes) as
three separate processes:

```sh
cc -std=c11 -Ibuild/install/include examples/provenance_handoff.c \
  build/install/lib/libdml.a -pthread -o "$run_dir/provenance_handoff"
"$run_dir/provenance_handoff" request "$run_dir/source" "$run_dir/request.dml" \
  example.add-one@1 snapshot value
"$run_dir/provenance_handoff" work "$run_dir/handoff-worker" "$run_dir/result.dml" "$run_dir/request.dml"
"$run_dir/provenance_handoff" publish "$run_dir/source" "$run_dir/result.dml"
"$run_dir/provenance_handoff" release-input "$run_dir/handoff-worker"
```

The request arguments are the versioned operation (`example.add-one@1` or
`example.subtract-one@1`), tree entry and DAG binding. The request commit records
all three and points back to the source snapshot. Only the bundle files cross
between roles.

The fourth command is optional worker cleanup. Use a fresh worker path when
supplying a request bundle. This example uses fixed ref names for one handoff
at a time; don't reuse or retarget those refs while that handoff is active.
Keep `request-pin` until publication succeeds and leave `result-pin` in place
to retain the worker's result, request and input snapshot.

- Run `request SOURCE NEW_REQUEST` without the operation and selector to export
  the existing `request-pin`, even if `main` has moved.
- Run `work WORKER NEW_RESULT` without the request path to resume from `incoming`
  or re-export an already committed `result-pin`.
- Run `stage-result SOURCE RESULT` to stop after staging. Run `publish SOURCE`
  without the result path to resume from the committed `returned` ref.

At any committed checkpoint, inspect either repository without rerunning the
operation or changing refs:

```sh
"$run_dir/provenance_handoff" inspect source "$run_dir/source"
"$run_dir/provenance_handoff" inspect worker "$run_dir/handoff-worker"
```

The source view reports why a staged result is blocked or whether it passes
publication checks in the current snapshot. See the
[inspection semantics](docs/spec-next/transfer.md#inspect-a-committed-checkpoint).

These are committed repository checkpoints, not arbitrary crash recovery or
idempotent retries of the entire workflow. Bundle paths are regular binary files.
Export never overwrites an existing file, but an interrupted write can leave a
partial file. Discard incomplete exports and retry to a fresh output path.

### Optional Nix development shell

On x86_64 and aarch64 Linux/macOS, `nix develop` supplies the compiler, Meson, and
Ninja. On Linux it also supplies Valgrind for manual memory checks. Use the
separate `.#quint` shell for [Quint behavior checks](#quint-behavior-checks).
Neither shell runs builds or checks automatically.

```sh
nix develop -c scripts/check.sh
```

## C editor setup

Run `scripts/setup-lsp.sh` in the build environment to generate an ignored
`compile_commands.json` for clangd from a separate build in `build/editor/`.
This optional tool uses Python 3 to assemble the database, including system-header
paths for Nix compiler wrappers. It does not compile or install anything.

## Contributing

See [AGENTS.md](AGENTS.md) for code and documentation conventions and
[the validation policy](docs/validation-policy.md) for reporting what was checked.
