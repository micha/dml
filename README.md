# DML

[![CI](https://github.com/micha/dml/actions/workflows/ci.yml/badge.svg)](https://github.com/micha/dml/actions/workflows/ci.yml)

Local-first development with lightweight workflow guidance.

## Workflow

The canonical workflow is documented here:

- `AGENTS.md` (Agent guide)

To enforce commit message body wrapping locally:

`cp scripts/commit-msg-hook.sh .git/hooks/commit-msg && chmod +x .git/hooks/commit-msg`

## Build and Test

Use `scripts/check.sh` as the standard validation entrypoint.

- `scripts/check.sh` - build, run tests, and enforce 100% coverage
- `scripts/check.sh -v` - also run C tests, binding ownership and native CLI fault workloads under Valgrind
- `scripts/check.sh -f` - clean build artifacts before rebuilding
- `scripts/check.sh -m` - enable Mull mutation testing
- `scripts/check.sh -c` - build, run tests, and report coverage without percentage gates (used by CI)

The script enforces vendored dependency usage, runs coverage with gcov/lcov,
and writes HTML reports under:

- `build/coverage/html` (C coverage via gcov/lcov)
- `build/coverage/python-html` (Python coverage via coverage.py, when Python
  source files exist outside tests)

Python test dependencies are in `requirements-dev.txt` (pytest, Hypothesis, and
coverage.py). Windows CI installs the corresponding UCRT64 packages through
[MSYS2](https://www.msys2.org/docs/python/) so native extensions match its Python
build.

CI uses `scripts/check.sh -c`: coverage reports are informational, while build,
test, and report-generation failures still fail the job.

Mutation testing uses `.mull.yml`; when `-m` is passed, `scripts/check.sh`
targets `build/check/test_version` by default when present.

## C Editor Setup

Run `scripts/setup-lsp.sh` in your build environment (Meson, Ninja, a C compiler,
Python, and Python development headers are required). It configures a separate
editor build for the shared core and Python extension, then writes an ignored
`compile_commands.json` at the repository root. No compilation is required.

The database includes compiler-discovered system-header paths for environments
such as Nix, where an unwrapped clangd cannot infer them. It does not change
Neovim's global configuration or the coverage/mutation builds.

Rerun the script after changing build definitions, compilers, or Python
installations. Restart the clangd client in Neovim after the initial setup.
See [clangd project setup](https://clangd.llvm.org/installation.html#project-setup)
and [system-header discovery](https://clangd.llvm.org/guides/system-headers).

## CLI Help

- `dml --help` documents the inspection-only native CLI's global grammar.
- [CLI contract](docs/spec-next/cli.md) owns selectors, previews, JSON and errors.
- [Python API](docs/spec-next/python-api.md) constructs existing repository state.
- [Packaging](docs/packaging-and-distribution.md) explains root builds and console forwarding.

## Docs

Start with the [as-built specification](docs/spec-next/README.md) for implemented
DML behavior: datums, snapshot/history objects, transactional repository refs,
the low-level Python API, inspection CLI and explicit
[local recorded Python execution](docs/spec-next/local-execution.md) layer.
The [runnable local story](examples/local_execution.py) executes a trusted child,
records distinct attempts and durable result DAGs; capture and interruption limits
are explicit in that layer's contract.
The [pinned transfer layer](docs/spec-next/transfer.md) and
[runnable transfer story](examples/pinned_transfer.py) copy full recorded parent
history between local repositories without executing imported source or copying refs.
The [repository execution layer](docs/spec-next/repository-execution.md) and
[A → B → A story](examples/repository_execution.py) connect pinned transfer and the
unchanged local runner, validating returned selected history before atomic import
under a caller-chosen ref while leaving A's existing heads alone.
Its [glossary](docs/spec-next/glossary.md) owns the shared vocabulary. The old draft
specification below remains design context, not an implementation claim.

- `docs/documentation-guidelines.md` (How to write and maintain docs)
- `docs/packaging-and-distribution.md` (Python package layout and release plan)
- `docs/architecture.md` (Architecture overview)
- `docs/core-storage.md` (Native datum codec and local repository API)
- [docs/spec-next/README.md](docs/spec-next/README.md) (As-built specification)
- [tests/coverage-exclusions.md](tests/coverage-exclusions.md) (Coverage scope and rationale)
- `docs/spec/overview.md` (Old draft specification)
- `docs/spec/object-model.md` (Packed records, hashing, keyspace)
- `docs/spec/execution.md` (Execution lifecycle, caching, adapters)
- `docs/spec/remotes.md` (Remote snapshot flow and transfer)
- `docs/spec/cli.md` (CLI contract and error codes)
- `docs/spec/python-bindings.md` (Python API proposal)
- `docs/spec/maintainability.md` (Maintainability assessment rubric)
