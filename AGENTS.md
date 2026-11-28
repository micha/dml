# Agent Guide

## Validation

Follow the [validation policy](docs/validation-policy.md). The final gate is
`scripts/check.sh --quint`; without `--quint`, the script only builds the C core.
See the [README](README.md#build-and-validation) for setup.

Keep core replay to one C API call per step and application behavior in separate
workflow specs. Replay runners report observations; Quint decides whether they
satisfy the contract. Keep fault-injection state out of the installed library.
The [Python-to-Quint port ledger](docs/python-to-quint-port.md) records where
former Python checks are covered.

## Documentation

Read the [documentation guidelines](docs/documentation-guidelines.md) before
editing docs. Update the owning [as-built contract](docs/spec-next/README.md#concept-ownership)
when implemented behavior changes, and the [LMDB diagram](docs/lmdb-entity-diagram.html)
when its depicted storage or boundaries change.

## Build outputs

Treat `build/` as disposable and keep temporary Git worktrees outside it. Preserve
experiment evidence separately; see `git show archive/experiments:experiments/README.md`.
