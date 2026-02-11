# DaggerML Spec Overview

This directory is the source of truth for the new DaggerML specification.
It replaces the legacy `dml-json` + `lite3` storage specs.

## Reading order

1. `docs/spec/object-model.md` - canonical object model, encoding, hashing,
   keyspace, validation, and repository semantics.
2. `docs/spec/execution-and-remotes.md` - async execution lifecycle, caching,
   remote transfer, and adapter contracts.
3. `docs/spec/cli.md` - repository-facing CLI contract and admin operations.
4. `docs/spec/python-bindings.md` - proposed high-level Python API over core
   records.

## Scope

- Immutable content-addressed records in LMDB.
- Mutable refs for heads and index state.
- Full DAG provenance as a hard invariant.
- Deterministic binary encoding and hash stability across platforms.

## Status

Draft. This spec suite is intended to be the baseline for the clean-slate
implementation.
