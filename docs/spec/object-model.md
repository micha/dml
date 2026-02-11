# Object Model Specification

Status: Draft.

This document defines the canonical on-disk model for DaggerML repositories.
It is normative unless a section is marked Informative.

## 1. Decision Summary

- Replace legacy `dml-json` + `lite3` persistence with packed binary records in
  LMDB.
- Preserve full DAG topology for provenance and reproducibility.
- Keep immutable content-addressed objects and mutable refs (git-like model).
- Require deterministic encoding, canonical ordering, and stable hashing.
- Keep compatibility windows tool-defined, not repository-defined.

## 2. Conformance

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted
as described in RFC 2119.

## 3. Core Model

### 3.1 Object classes

- Content-addressed records: datum, node, dag, tree, commit, exec.
- Mutable records: refs.
- Metadata records: meta.
- Excision markers: tombstones.

### 3.2 Provenance invariant

- Readers MUST be able to reconstruct the full DAG topology from stored object
  relationships.
- Nodes, DAGs, commits, and exec pinning MUST preserve causal lineage.

### 3.3 Ref model

- Heads and index refs are mutable pointers addressed by name.
- Refs are not content-addressed objects and are excluded from object hashing.

## 4. Record Envelope

All LMDB values for packed records use the fixed header below.

```c
#pragma pack(push, 1)
typedef struct {
  uint32_t magic;      // 'DML1'
  uint16_t version;    // record format version
  uint16_t type;       // record kind
  uint32_t total_len;  // bytes including header
  uint32_t flags;      // reserved
  uint32_t checksum;   // optional; 0 in canonical storage
} dml_rec_header;
#pragma pack(pop)
```

Envelope rules:

- `magic` MUST be `0x314C4D44` (`DML1`, little-endian).
- `total_len` MUST equal LMDB value length and be at least header size.
- Readers MUST reject trailing bytes.
- Canonical stored records MUST set `checksum = 0`.
- Checksums MAY be used in transfer streams (import/export/push/pull), but do
  not change object identity.

## 5. Encoding and Canonicalization

### 5.1 Primitive encoding

- Integers use fixed-width types (`u32`, `u64`, `i64`).
- Floats use IEEE-754 `f64` little-endian.
- Disk encoding is always little-endian.
- No pointers in persisted structs.
- Variable data is stored in trailing blob regions addressed by offsets.

### 5.2 Offset safety

- Offsets are measured from record start.
- Readers MUST validate every `ofs + len <= total_len`.
- Blob regions MUST be gap-free and encoded in declaration order.

### 5.3 Text and URI rules

- Strings and names MUST be valid UTF-8.
- Strings and names MUST be normalized to NFC.
- URI datums MUST be RFC 3986 canonical form.
- Names and URIs used in LMDB keys MUST be percent-encoded.
- Name length MUST be <= 255 bytes after UTF-8 encoding and before
  percent-encoding.

### 5.4 Canonical ordering

- Sets: sort by object id bytes; reject duplicates.
- Maps: sort by key id bytes; reject duplicate keys.
- Trees: sort by name bytes; reject duplicates.
- DAG name entries: sort by name bytes; reject duplicates.
- Commit exec entries: sort by node id bytes; reject duplicates.

### 5.5 Float canonicalization

- `-0.0` MUST be normalized to `+0.0`.
- NaN MUST be normalized to one fixed bit pattern.

## 6. Object IDs and Hashing

- Object id algorithm: `XXH3_128`.
- `dml_object_id` size: 16 bytes.
- Hash input is the packed record byte sequence with `magic`, `total_len`, and
  `checksum` treated as zero.
- `type` and `version` are included in the hash domain.
- Ref records are excluded from content-addressed hashing.

## 7. Record Types

Type ids:

```c
enum dml_rec_type {
  DML_REC_META = 1,
  DML_REC_DATUM = 2,
  DML_REC_NODE = 3,
  DML_REC_DAG = 4,
  DML_REC_TREE = 5,
  DML_REC_COMMIT = 6,
  DML_REC_REF = 7,
  DML_REC_TOMBSTONE = 8,
  DML_REC_EXEC = 9,
  DML_REC_EXEC_REQUEST = 10,
};
```

### 7.1 `DML_REC_META`

Repository metadata.

```c
typedef struct {
  dml_rec_header h;
  uint32_t schema_version;
} dml_rec_meta;
```

### 7.2 `DML_REC_DATUM`

Value primitives and collections.

```c
enum dml_datum_kind {
  DML_DATUM_NULL = 1,
  DML_DATUM_BOOL = 2,
  DML_DATUM_I64 = 3,
  DML_DATUM_F64 = 4,
  DML_DATUM_BYTES = 5,
  DML_DATUM_STRING = 6,
  DML_DATUM_URI = 7,
  DML_DATUM_SET = 8,
  DML_DATUM_MAP = 9,
};

typedef struct {
  dml_rec_header h;
  uint32_t kind;
  uint64_t payload_len;
  uint64_t payload_ofs;
} dml_rec_datum;
```

Rules:

- `STRING` payload is UTF-8 NFC bytes.
- `URI` payload is canonical UTF-8 URI bytes.
- `SET` stores sorted unique datum object ids.
- `MAP` stores sorted unique `{key_id, value_id}` pairs.
- Datum references in composite datums MUST reference datum ids only.
- User-provided `dml:` URIs are reserved and MUST be rejected by core
  validation.

### 7.3 `DML_REC_NODE`

Node kinds and payload references.

```c
enum dml_node_kind {
  DML_NODE_LITERAL = 1,
  DML_NODE_CALL = 2,
  DML_NODE_IMPORT = 3,
  DML_NODE_BUILTIN = 4,
};

typedef struct {
  dml_rec_header h;
  uint32_t kind;
  uint32_t input_count;
  dml_object_id target_dag;
  dml_object_id literal_value;
  dml_object_id function_ref;
  uint64_t inputs_ofs;
} dml_rec_node;
```

Rules:

- `LITERAL`: uses `literal_value`, `input_count = 0`.
- `IMPORT`: uses `target_dag`, `input_count = 0`.
- `CALL`: uses `function_ref` and node inputs.
- `BUILTIN`: uses `function_ref` and node inputs.
- `function_ref` MUST reference a `DML_DATUM_URI`.
- `inputs_ofs` points to `input_count` node ids.

Import namespace rules:

- Import node names expose imported DAG names as a namespaced handle.
- Imported root is accessible via reserved name `root`.
- Imported names are never merged into the local DAG namespace.

### 7.4 `DML_REC_EXEC`

Execution outcome for call or builtin nodes.

```c
enum dml_exec_status {
  DML_EXEC_OK = 1,
  DML_EXEC_ERROR = 2,
};

typedef struct {
  dml_rec_header h;
  dml_object_id node_id;
  uint32_t status;
  dml_object_id result_value;
  dml_object_id error_value;
} dml_rec_exec;
```

Rules:

- `status=OK` uses `result_value`; `error_value` is zeroed.
- `status=ERROR` uses `error_value`; `result_value` is zeroed.
- For `CALL`, `result_value` is a DAG id (call-result DAG).
- For `BUILTIN`, `result_value` is a datum id.

### 7.5 `DML_REC_EXEC_REQUEST`

Execution metadata attached to call attempts.

```c
typedef struct {
  dml_rec_header h;
  dml_object_id node_id;
  dml_object_id meta_map;
} dml_rec_exec_request;
```

Rules:

- `meta_map` MUST be a datum map with UTF-8 string keys.
- Exec request records do not affect node identity.

### 7.6 `DML_REC_DAG`

Root node id plus optional node-name map.

```c
typedef struct {
  dml_rec_header h;
  dml_object_id root_node;
  uint32_t name_count;
  uint64_t names_ofs;
} dml_rec_dag;
```

Name entry:

```c
typedef struct {
  uint64_t name_ofs;
  uint32_t name_len;
  dml_object_id node_id;
} dml_dag_node_name;
```

Rules:

- Graph edges are discovered from node inputs, not from names.
- Name map is optional and not part of node identity.

### 7.7 `DML_REC_TREE`

Named collection of DAG ids.

```c
typedef struct {
  dml_rec_header h;
  uint32_t entry_count;
  uint64_t entries_ofs;
} dml_rec_tree;

typedef struct {
  uint64_t name_ofs;
  uint32_t name_len;
  dml_object_id dag_id;
} dml_tree_entry;
```

Rules:

- Entries sorted lexicographically by name bytes.
- Entry names unique.

### 7.8 `DML_REC_COMMIT`

Versioned snapshot of tree, parent links, and exec pinning.

```c
typedef struct {
  dml_rec_header h;
  dml_object_id tree_id;
  uint32_t parent_count;
  uint64_t parents_ofs;
  uint32_t exec_count;
  uint64_t execs_ofs;
} dml_rec_commit;

typedef struct {
  dml_object_id node_id;
  dml_object_id exec_id;
  dml_object_id request_map;
} dml_exec_entry;
```

Rules:

- Exec entries sorted by `node_id` and unique.
- Exec entries exist only for executable nodes (`CALL`, `BUILTIN`).
- Structural nodes (`LITERAL`, `IMPORT`) have no exec entries.
- `request_map` is optional and, if set, points to a datum map with UTF-8
  string keys.

### 7.9 `DML_REC_REF`

Mutable pointer to a target commit.

```c
enum dml_ref_kind {
  DML_REF_HEAD = 1,
  DML_REF_INDEX = 2,
};

typedef struct {
  dml_rec_header h;
  uint32_t kind;
  dml_object_id target_commit;
} dml_rec_ref;
```

Rules:

- Ref name is carried by LMDB key, not record payload.
- Index ref names SHOULD be UUIDs.

### 7.10 `DML_REC_TOMBSTONE`

Marker used for excision while preserving object ids.

```c
typedef struct {
  dml_rec_header h;
  uint32_t reason_code;
  uint64_t message_ofs;
  uint32_t message_len;
} dml_rec_tombstone;
```

## 8. Keyspace

### 8.1 Object keys

Content-addressed objects MUST use type-prefixed keys:

- `objects/commits/<id>`
- `objects/dags/<id>`
- `objects/nodes/<id>`
- `objects/trees/<id>`
- `objects/datums/<id>`
- `objects/execs/<id>`

`<id>` is lowercase hex (32 chars for 16-byte ids).

### 8.2 Ref keys

- `refs/heads/<name>`
- `refs/index/<name>`

Names MUST be UTF-8 NFC and percent-encoded in keys.

### 8.3 Meta keys

- `meta/schema` -> `DML_REC_META`
- `meta/created_by` -> UTF-8 tool version string (optional)
- `meta/last_migrated_by` -> UTF-8 tool version string (optional)

## 9. Repository Semantics

### 9.1 Workflow sketch (informative)

1. Open or initialize repository.
2. Resolve base head commit.
3. Create/update index ref with an in-progress DAG entry in tree.
4. Add nodes and commits on index ref.
5. Select DAG result node.
6. Squash index history, rebase on base head, and fast-forward merge.

Index refs are recovery-friendly staging pointers and MUST be updated atomically.

### 9.2 GC and excision

- Reachability roots: `refs/heads/*` and `refs/index/*`.
- GC is mark-and-sweep over reachable content-addressed objects.
- Excision replaces removed objects with tombstones at the same object id.
- Readers MUST reject tombstones as valid objects.

Tombstone read failures MUST map to:

- error code: `invalid_payload`
- reason: `record_type=tombstone;detail=excised`

## 10. Validation and Errors

Error codes:

- `invalid_header`
- `invalid_bounds`
- `invalid_kind`
- `invalid_payload`
- `invalid_utf8`

Reason strings SHOULD use this format:

`record_type=<type>;detail=<short_reason>`

Common invariants:

- Header fields valid for declared record type/version.
- All offsets in bounds.
- UTF-8 validity and NFC normalization.
- Canonical sorting and duplicate rejection where required.

## 11. Open Questions

1. Canonical storage for in-flight execution tracking.
2. Final keyspace location for `DML_REC_EXEC_REQUEST` objects.
3. Deterministic commit-tree placement for execution result DAGs.
