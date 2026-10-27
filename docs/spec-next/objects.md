# Snapshot and history objects

Status: implemented literal nodes, rooted DAGs, trees and commits; record format 1.

## Authority boundary

This document owns the implemented node/DAG/tree/commit fields, canonical ordering,
name profile and codec views. For the common envelope, identity and buffer ownership,
see [records.md](records.md#packed-representation). For persisted keys and
transactional reference checks, see [repository.md](repository.md).
Terms follow the [glossary](glossary.md).

Normative sections describe the current implementation.

## Typed object structure

A literal node MUST reference a datum. A DAG MUST designate a node as its root.
A tree entry MUST associate a name with a DAG. A commit MUST reference a tree and
an ordered list of parent commits. References are 16-byte full-record content IDs.
The codecs validate structural encoding; storage checks direct referenced objects
as described in [repository reference validation](repository.md#writes-and-reference-validation).

A tree-entry name is not a named binding within a DAG. Parent lists record history;
constructing a commit with multiple parents is not a merge operation.

## Packed bodies

Each body follows the [20-byte envelope](records.md#packed-representation).
Integers MUST be little-endian. Records MUST occupy exactly their encoded length;
truncation, trailing bytes and unsupported node kinds MUST be rejected.

| Type / envelope tag | Body after byte 20 | Total size |
| --- | --- | --- |
| Node / 3 | u32 kind = 1 (`DML_NODE_LITERAL`), datum ID | 40 bytes |
| DAG / 4 | Root node ID | 36 bytes |
| Tree / 5 | u32 entry count; entries below | 24 bytes + entries |
| Commit / 6 | Tree ID, u32 parent count, parent IDs in order | 40 bytes + 16 × parent count |

Each tree entry is a u32 name byte length, name bytes without a terminator, then
its DAG ID. There are no offsets, gaps, native structure padding or persisted
pointers. An empty tree is valid. A DAG always has one root reference.

An initial commit has zero parents. Supplied parent order MUST be preserved;
duplicate parent IDs MUST be rejected. Changing parent order changes content
identity. Duplicate checking currently uses pairwise comparison.

## Names and tree ordering

`dml_name_validate()` implements this intentionally narrow name profile, shared
with [ref names](repository.md#refs):

- 1–128 ASCII bytes, case-sensitive.
- First byte: `A`–`Z`, `a`–`z` or `0`–`9`.
- Remaining bytes: those characters, `.`, `_` or `-`.

Names outside this profile MUST be rejected, not normalized or interpreted as
filesystem paths. This profile does not accept Unicode or slash-separated names.

The tree encoder sorts entries by lexicographic name bytes; a prefix sorts before
its extension. Duplicate names MUST be rejected even if their DAG targets match.
Packed validation requires strictly increasing names and never silently sorts a
stored record. Input entry order does not contribute to tree identity after
canonicalization; entry names and targets do.

## C codec and views

Public declarations are in [object.h](../../include/dml/object.h).

- `dml_object_input` discriminates node/DAG/tree/commit input using `type`.
  `dml_object_encode()` accepts only those four types and returns an owned buffer.
- `dml_object_decode()` validates packed bytes and returns a borrowed
  `dml_object_view`. Its `reference` is the node's datum, DAG's root or commit's
  tree; it is zero for a tree. `count` denotes tree entries or commit parents.
- `dml_object_view_entry()` returns a DAG ID and borrowed name bytes;
  `dml_object_view_parent()` copies a parent ID. Accessors require a valid,
  unchanged decoded view and reject wrong view types/out-of-range indices.
  Tree entry access scans preceding entries; it is linear in the requested index.
- Callers MUST retain the original bytes unchanged while using a view or borrowed
  name. Encoded and repository-read buffers follow
  [records buffer ownership](records.md#c-api-ownership).

`dml_record_validate()` supports these objects as well as metadata and datums.
`dml_object_id_compute()` provides their full-record identities using the common
[hash domain](records.md#record-identity). Codec validation does not resolve IDs
against a repository.

## Informative example

```text
I64 datum 42 <- literal node <- rooted DAG <- tree entry "example" <- commit C1
I64 datum 43 <- literal node <- rooted DAG <- tree entry "example" <- commit C2
C2 has parent C1; ref main points at C2.
```

These arrows are object references, not execution steps. Retrieve the commit's
tree, its entry's DAG, the DAG's root node and the node's datum to inspect a
snapshot. Retrieve parent commits to inspect history.

## Implementation evidence

- [object.c](../../src/object.c): name profile, codecs and borrowed views.
- [object_id.c](../../src/object_id.c): common immutable-object identity.
- [C object tests](../../tests/c/test_object.c): boundaries and round trips.
- [Object property tests](../../tests/python/test_objects_hypothesis.py): independent
  encoding oracles, canonical ordering and malformed records.
- [History tests](../../tests/python/test_history.py): fresh-process snapshots,
  branching and ordered multiple-parent persistence.

Actual validation runs and outstanding gates are recorded in the
[Iteration 1 delivery notes](../../../dml-design/iterations/01-minimum-viable-repository/RESULTS.md).
