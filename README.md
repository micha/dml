# DML

DML currently provides a C library for content-addressed data and history in a local
transactional repository, with [binary commit transfer](docs/spec-next/transfer.md).
See the [as-built specification](docs/spec-next/README.md)
for the implemented contracts and [architecture](docs/architecture.md) for the module
boundaries.

The Python layers, CLI, previous test suites, and spike evidence are preserved at
[`feasibility-complete`](https://github.com/micha/dml/tree/feasibility-complete).
They are not maintained or run on the C consolidation branch.

## Build and validation

Use a C11 compiler, Meson 1.4 or newer, and Ninja. Meson uses the pinned dependency
wraps from `subprojects/`. Run the [build check](docs/validation-policy.md) with:

```sh
scripts/check.sh
```

This configures and compiles a debug build in `build/core-check/`. The CI matrix
runs this build-only check; it does not run behavioral tests or measure coverage.

### Quint behavior checks

Use Python 3.10+ and [Quint](https://quint.sh/) 0.33.1 (TypeScript backend). With Node.js
and npm, you can install Quint locally without changing the project dependencies:

```sh
npm install --prefix build/quint-tool --no-save --ignore-scripts @informalsystems/quint@0.33.1
PATH="$PWD/build/quint-tool/node_modules/.bin:$PATH" scripts/check.sh --quint
```

This builds the test executables in `build/core-check-quint/` and runs
`quint-refs`, `quint-transfer`, and focused interpreter and native fault tests.
The [shared trace interpreter](tests/README.md) replays requests from Quint against
native C executables. Quint checks observations against the
[ref contract](docs/spec-next/repository.md#refs) and [transfer contract](docs/spec-next/transfer.md).
Fresh native reads and separate read-only LMDB scans check snapshot publication,
rollback, datum readback from imported history, and recording, transferring back,
conditionally publishing a caller's result, and guarded staging-ref release.
The native fault test checks transfer allocation failures without adding hooks to the library.
These checks are local and opt-in; they do not measure coverage.

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
and its history. It [stages the import](docs/spec-next/transfer.md#informative-example)
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

The original repository imports and inspects the result without recomputing it,
then conditionally moves its `main` to the inspected commit. After reopening,
its `main` yields `44`. The worker releases `incoming` only if it still points
at the inspected input, then reopens and reads the same result and input through
`result-pin`.

### Optional Nix development shell

On x86_64 and aarch64 Linux/macOS, `nix develop` supplies the compiler, Meson, and
Ninja. On Linux it also supplies Valgrind for manual memory checks. The shell does
not run builds or checks automatically.

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
