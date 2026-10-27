#ifndef DML_OBJECT_H
#define DML_OBJECT_H

#include "dml/record.h"

#define DML_NODE_LITERAL 1
#define DML_NAME_MAX_SIZE 128

typedef struct {
  dml_bytes name;
  dml_object_id dag;
} dml_tree_entry;

typedef struct {
  dml_record_type type;
  union {
    struct { uint32_t kind; dml_object_id datum; } node;
    dml_object_id root;
    struct { const dml_tree_entry *items; size_t count; } tree;
    struct { dml_object_id tree; dml_id_array parents; } commit;
  } value;
} dml_object_input;

typedef struct {
  const uint8_t *record;
  size_t record_len;
  dml_record_type type;
  /* Datum for a node, root for a DAG, tree for a commit; zero for a tree. */
  dml_object_id reference;
  size_t count; /* Tree entries or commit parents. */
} dml_object_view;

/* Names: 1..128 ASCII bytes, alphanumeric first, then alphanumeric, '.', '_' or '-'. */
dml_status dml_name_validate(dml_bytes name, dml_error *error);
/* Encodes node/DAG/tree/commit. Output must be empty; failures leave it empty. */
dml_status dml_object_encode(const dml_object_input *input, dml_buffer *out,
                              dml_error *error);
/* Views and tree-entry names borrow the original packed bytes. */
dml_status dml_object_decode(const uint8_t *data, size_t len, dml_object_view *out,
                              dml_error *error);
dml_status dml_object_view_entry(const dml_object_view *view, size_t index,
                                  dml_tree_entry *out, dml_error *error);
dml_status dml_object_view_parent(const dml_object_view *view, size_t index,
                                   dml_object_id *out, dml_error *error);
/* Immutable datum/node/DAG/tree/commit only; excludes metadata and refs. */
dml_status dml_object_id_compute(const uint8_t *data, size_t len, dml_object_id *out,
                                  dml_error *error);

#endif
