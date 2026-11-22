# DML

DML currently provides a C library for content-addressed data and history in a local
transactional repository. See the [as-built specification](docs/spec-next/README.md)
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

This builds two test-only executables in `build/core-check-quint/` and runs
`quint-create-ref`. Quint emits ref creation histories. The native runner
executes the C API, and a separate
read-only LMDB scan observes what each transaction published. Quint checks the
statuses and exact inventory changes against the [ref contract](docs/spec-next/repository.md#refs).
The check is local and opt-in; it does not measure coverage.

### Install and link the C library

For example, install the headers and static library under a local prefix:

```sh
meson setup build/release --buildtype=release --prefix="$PWD/build/install" --libdir=lib
meson compile -C build/release
meson install -C build/release
```

Include `<dml/dml.h>` in a C program. The archive includes the pinned vendor
libraries; on a Unix compiler driver that accepts `-pthread`, link like this:

```sh
cc -Ibuild/install/include example.c -Lbuild/install/lib -ldml -pthread -o example
```

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
