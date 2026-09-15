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
- `scripts/check.sh -v` - also run C tests under Valgrind
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

## CLI Help

- Primary documentation surface: `dml --help` and `dml <command> --help`
- Optional `man dml` support may be added later from the same help metadata

## Docs

- `docs/documentation-guidelines.md` (How to write and maintain docs)
- `docs/packaging-and-distribution.md` (Python package layout and release plan)
- `docs/architecture.md` (Architecture overview)
- `docs/core-storage.md` (Native datum codec and local repository API)
- `docs/spec/overview.md` (Specification)
- `docs/spec/object-model.md` (Packed records, hashing, keyspace)
- `docs/spec/execution.md` (Execution lifecycle, caching, adapters)
- `docs/spec/remotes.md` (Remote snapshot flow and transfer)
- `docs/spec/cli.md` (CLI contract and error codes)
- `docs/spec/python-bindings.md` (Python API proposal)
- `docs/spec/maintainability.md` (Maintainability assessment rubric)
