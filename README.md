# DML

Local-first development with lightweight workflow guidance.

## Workflow

The canonical workflow is documented here:

- `AGENTS.md` (Agent guide)

## Build and Test

- Prereqs: Meson, clang-format, python3.
- Configure: `meson setup build`
- Build: `meson compile -C build`
- Test: `python3 -m pytest tests/python`
- Format: `meson compile -C build format`

For the full rebuild/test/format-check/coverage workflow, use
`scripts/check.sh`.
Use `scripts/check.sh -f` to wipe existing build artifacts before running.

See `AGENTS.md` for the full command reference.

## CLI Help

- Primary documentation surface: `dml --help` and `dml <command> --help`
- Optional `man dml` support may be added later from the same help metadata

## Docs

- `docs/architecture.md` (Architecture overview)
- `docs/spec/overview.md` (Specification)
- `docs/spec/object-model.md` (Packed records, hashing, keyspace)
- `docs/spec/execution-and-remotes.md` (Execution lifecycle and remotes)
- `docs/spec/cli.md` (CLI contract and error codes)
- `docs/spec/python-bindings.md` (Python API proposal)
