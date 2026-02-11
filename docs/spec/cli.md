# CLI Specification

Status: Draft.

The CLI is repository-facing porcelain/plumbing over packed records and refs.
DAG construction and execution orchestration are primarily handled by language
bindings.

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

CLI SHOULD preserve stable high-level error classes from core validation:

- `invalid_header`
- `invalid_bounds`
- `invalid_kind`
- `invalid_payload`
- `invalid_utf8`

Detailed reason strings SHOULD include `record_type` and a short `detail` key.

## 5. Help and Documentation Surface

- `dml --help` and `dml <command> --help` are the primary user-facing
  documentation surface.
- Help output MUST be complete enough for command discovery and practical use,
  including argument semantics and examples where helpful.
- CLI help text is the source of truth for command documentation.
- A `man dml` page MAY be shipped for ecosystem compatibility, but it SHOULD be
  generated from the same command metadata/help source to avoid drift.
