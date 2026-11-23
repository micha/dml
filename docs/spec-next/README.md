# DML: as-built specification

## Authority boundary

This document owns navigation and the implemented scope. The technical contracts
belong to the documents below. The [draft specification](../spec/overview.md)
describes proposals, not additional implemented behavior.

## Concept ownership

| Topic | Authority |
| --- | --- |
| Datum kinds, canonical records, content identity, buffers, and errors | [Records and datums](records.md) |
| Nodes, DAGs, trees, commits, names, and borrowed views | [Snapshot and history objects](objects.md) |
| Repository initialization, storage keys, transactions, refs, retention, and integrity checks | [Local repository and transactions](repository.md) |
| Binary commit bundle, export, and atomic import | [Commit transfer](transfer.md) |
| Working vocabulary | [Glossary](glossary.md) |
| Documentation conventions | [Writing guidelines](../documentation-guidelines.md) and [agent guide](AGENTS.md) |

## What exists today

The [C core](../../src/) implements ten datum kinds, deterministic record encoding
and content IDs, literal and sub-DAG-reference nodes, rooted DAGs with named
bindings, named trees, and ordered-parent commits. An LMDB-backed repository
stores these objects and mutable refs under local storage transactions. It can
[check integrity and reachability](repository.md#snapshot-integrity-and-reachability)
without collecting objects. It can also export and atomically import self-contained
binary commit bundles without changing refs. The [public headers](../../include/dml/) define the API, and the
[entity diagram](../lmdb-entity-diagram.html) shows the implemented storage layout.

The [feasibility checkpoint](https://github.com/micha/dml/tree/feasibility-complete)
contains the earlier application layers and validation evidence. It does not extend
this branch's implemented scope or establish current test coverage.

## Development policy

Until `v1.0.0`, repositories and development state are ephemeral. Format and schema
numbers describe the current implementation, not a promise to migrate older state.
This does not authorize deleting unrelated data or unmanaged resources.

Document behavior as implemented. Use MUST, SHOULD, and MAY for normative contracts
and identify examples as informative. For current validation, see the
[development validation policy](../validation-policy.md).
