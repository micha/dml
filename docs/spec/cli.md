# CLI Specification

Status: Draft.

The CLI is repository-facing porcelain/plumbing over packed records and refs.
DAG construction and execution orchestration are primarily handled by language
bindings.

Authority boundary:

- This document is authoritative for CLI commands, arguments, and
  repository-facing CLI behavior.
- For packed-record schemas, canonical encoding/hashing, keyspace, and
  validation/error semantics, see `docs/spec/object-model.md`.
- For execution semantics, see `docs/spec/execution.md`.
- For remote transfer semantics, see `docs/spec/remotes.md`.
- For Python API surface and binding behavior, see
  `docs/spec/python-bindings.md`.

## 1. Scope

- Repository administration.
- Branch/head/index management.
- Commit history inspection.
- Remote fetch/pull/push behavior.

## 2. Commands

- `dml schema`
  - Read `meta/schema` and print schema version.

- `dml version`
  - Print tool version and supported schema window.

- `dml log <head>`
  - Walk commit parents from `refs/heads/<head>`.
  - Default traversal is linear parent walk.

- `dml branch <name> <commit>`
  - Create/update `refs/heads/<name>` to `<commit>`.

- `dml merge <target> <source>`
  - Fast-forward only.
  - Update `refs/heads/<target>` to `refs/heads/<source>` if target is ancestor.

- `dml heads`
  - List refs under `refs/heads/`.

- `dml ref <name>`
  - Print commit id for `refs/heads/<name>`.

- `dml index list`
  - List refs under `refs/index/`.

- `dml index prune <name>`
  - Delete `refs/index/<name>` only (no object GC).

## 3. Behavioral Rules

- Ref updates MUST be atomic.
- Push ref updates MUST reject non-fast-forward by default.
- Fetch/pull MUST update remote-tracking refs atomically after object transfer.
- Missing optional meta fields (for example `meta/created_by`) MUST be treated
  as unknown, not as hard errors.

## 4. Error Surface

CLI SHOULD preserve core validation error classes and reason-string structure as
defined in `docs/spec/object-model.md` (Section 10 and Section 10.2).

## 5. Help and Documentation Surface

- `dml --help` and `dml <command> --help` are the primary user-facing
  documentation surface.
- Help output MUST be complete enough for command discovery and practical use,
  including argument semantics and examples where helpful.
- CLI help text is the source of truth for command documentation.
- A `man dml` page MAY be shipped for ecosystem compatibility, but it SHOULD be
  generated from the same command metadata/help source to avoid drift.
