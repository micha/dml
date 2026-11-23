# Architecture

## Authority boundary

This document owns the implemented module boundaries. The
[as-built specification](spec-next/README.md) owns the technical contracts.

The C core implements datums, literal and sub-DAG-reference nodes, named rooted
DAGs, trees, and commits with full-record content IDs. LMDB-backed transactions
persist immutable objects and atomically create, update, or release refs to commits.

- [error.h](../include/dml/error.h): status and error representation.
- [record.h](../include/dml/record.h): datum codecs, buffers, and ID text conversion.
- [object.h](../include/dml/object.h): object codecs, borrowed views, and name validation.
- [repo.h](../include/dml/repo.h): repository and transaction handles, typed object
  storage, scoped node lookup, refs, and a read-only snapshot integrity checker.
  The checker follows typed edges from ref roots and classifies detached objects.
- [transfer.h](../include/dml/transfer.h): buffered commit export/import with an
  exact dependency closure and atomic import.

xxHash, LMDB, utf8proc, and uriparser are private dependencies of the [C library](../README.md#install-and-link-the-c-library).
The [LMDB entity diagram](lmdb-entity-diagram.html) shows the implemented storage model.

There is no maintained binding, CLI, execution layer, or remote adapter on this
branch. The [feasibility checkpoint](https://github.com/micha/dml/tree/feasibility-complete)
preserves the earlier implementations and evidence without defining current behavior.
