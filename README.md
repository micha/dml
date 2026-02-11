# DML

Local-first development with lightweight workflow guidance.

## Workflow

The canonical workflow is documented here:

- `AGENTS.md` (Agent guide)

## Build and Test

Use `scripts/check.sh` as the standard validation entrypoint.

- `scripts/check.sh` - build, run tests, and coverage reports
- `scripts/check.sh -v` - also run C tests under Valgrind
- `scripts/check.sh -f` - clean build artifacts before rebuilding
- `scripts/check.sh -m` - enable Mull mutation testing

The script enforces vendored dependency usage, runs coverage with gcov/lcov,
and writes HTML reports under:

- `build/coverage/html` (C coverage via gcov/lcov)
- `build/coverage/python-html` (Python coverage via coverage.py, when Python
  source files exist outside tests)

Python test dependencies are in `requirements-dev.txt` (pytest + Hypothesis).

Mutation testing uses `.mull.yml`; when `-m` is passed, `scripts/check.sh`
targets `build/check/test_version` by default when present.

## CLI Help

- Primary documentation surface: `dml --help` and `dml <command> --help`
- Optional `man dml` support may be added later from the same help metadata

## Docs

- `docs/documentation-guidelines.md` (How to write and maintain docs)
- `docs/architecture.md` (Architecture overview)
- `docs/spec/overview.md` (Specification)
- `docs/spec/object-model.md` (Packed records, hashing, keyspace)
- `docs/spec/execution-and-remotes.md` (Execution lifecycle and remotes)
- `docs/spec/cli.md` (CLI contract and error codes)
- `docs/spec/python-bindings.md` (Python API proposal)
