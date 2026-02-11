# DaggerML Spec Overview

This directory is the source of truth for the DaggerML specification.
This overview is a navigation guide to authoritative spec documents.

Authority boundary:

- This overview is authoritative for spec navigation and source-of-truth mapping.
- Normative technical behavior is defined in the individual spec documents
  listed below.

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

## Concept ownership (source of truth)

- Record envelope, binary encoding, canonicalization, and object hashing:
  `docs/spec/object-model.md` (Sections 4-6)
- Datum/node/dag/tree/commit/ref/exec schemas and validation semantics:
  `docs/spec/object-model.md` (Sections 7 and 10)
- Repository keyspace, refs, GC, and excision behavior:
  `docs/spec/object-model.md` (Sections 8-9)
- Execution lifecycle, cache/retry behavior, in-flight policy, and remote
  execution snapshot flow: `docs/spec/execution-and-remotes.md` (Sections 1-5)
- Remote transfer protocol, adapter interfaces, and serverless/S3 model:
  `docs/spec/execution-and-remotes.md` (Sections 6-8)
- CLI command contract and repository-facing behavior:
  `docs/spec/cli.md` (Sections 2-3)
- CLI validation error surface and reason-string structure:
  `docs/spec/object-model.md` (Section 10, Section 10.2); CLI phrasing in
  `docs/spec/cli.md` (Section 4)
- Python API shape and language-level behavior:
  `docs/spec/python-bindings.md` (Sections 2-7)

## Status

Draft. This spec suite is the baseline for implementation.
