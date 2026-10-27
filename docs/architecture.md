# Architecture

Authority boundary:

- This document is authoritative for the implemented module boundaries and
  navigation to the current sources of truth.
- For normative implemented behavior, see the
  [as-built specification](spec-next/README.md).

The native C core implements datums, literal nodes, rooted DAGs, trees and commits,
with full-record content IDs. LMDB-backed storage transactions persist immutable
objects and atomically create or update repository-scoped refs to commits.
Installed headers separate these module boundaries:

- [error.h](../include/dml/error.h): status and error representation.
- [record.h](../include/dml/record.h): datum codecs, buffers and ID text conversion.
- [object.h](../include/dml/object.h): snapshot/history codecs, borrowed views,
  the ASCII name profile and immutable-object identity.
- [repo.h](../include/dml/repo.h): opaque repository/storage-transaction handles,
  typed object storage and ref operations.

xxHash, LMDB, utf8proc and uriparser remain private static dependencies. The CLI and
Python package entry points remain scaffolds; they do not expose the repository
workflow exercised by the native test drivers.

## Technical navigation

Start with [spec-next/README.md](spec-next/README.md) for the implemented contract:

- [Records and datums](spec-next/records.md): common envelope, identity and ownership.
- [Snapshot and history objects](spec-next/objects.md): fields, names and ordering.
- [Local repository and transactions](spec-next/repository.md): storage, direct
  reference checks, refs and handle lifecycle.
- [Glossary](spec-next/glossary.md): shared vocabulary.

The [old draft specification](spec/overview.md) describes proposed broader layers;
it is not evidence that those layers are implemented. Design agreements and future
iteration planning live in the sibling
[dml-design checkout](../../dml-design/README.md).
