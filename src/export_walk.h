#ifndef DML_EXPORT_WALK_H
#define DML_EXPORT_WALK_H

#include "dml/repo.h"

typedef struct {
  size_t max_objects;
  size_t max_record_bytes;
  size_t max_packed_bytes;
} dml_export_limits;

typedef struct {
  dml_record_type type;
  dml_object_id id;
  dml_buffer record;
} dml_export_row;

typedef struct {
  dml_export_row *items;
  size_t count;
} dml_export_rows;

typedef enum {
  DML_EXPORT_NONE = 0,
  DML_EXPORT_CYCLE,
  DML_EXPORT_OBJECT_LIMIT,
  DML_EXPORT_RECORD_LIMIT,
  DML_EXPORT_PACKED_LIMIT
} dml_export_failure;

/* Private pinned export. Caller owns a live read transaction and supplies an
 * empty output slot and non-null failure slot. On failure the output remains
 * empty; the failure slot distinguishes traversal/profile errors from native
 * read and allocation failures. Successful rows own their bytes independently
 * of the transaction and are in dependency-first order. */
dml_status dml_export_walk(dml_txn *txn, const dml_object_id *root,
                           const dml_export_limits *limits, dml_export_rows *out,
                           dml_export_failure *failure, dml_error *error);
/* Null-safe; clears the slot. */
void dml_export_rows_free(dml_export_rows *rows);

#endif
