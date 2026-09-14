# Architecture

Authority boundary:

- This document is authoritative for the implemented module boundaries and
  navigation to the current sources of truth.
- For normative technical behavior, see the spec suite listed below.

The repository implements a native C datum codec and LMDB-backed transactional
storage layer. Installed headers separate error/status types, packed datum APIs,
and opaque repository/transaction handles. xxHash, LMDB, utf8proc, and
uriparser remain private static dependencies.

Execution, DAG/commit codecs, remotes, and public Python bindings remain future
layers described only by their authoritative specifications.

For current design and behavior, use the spec suite:

- `docs/spec/overview.md`
- `docs/spec/object-model.md`
- `docs/spec/execution.md`
- `docs/spec/remotes.md`
- `docs/spec/cli.md`
- `docs/spec/python-bindings.md`

For the implemented lifecycle and ownership contract, see
`docs/core-storage.md`.
