#ifndef DML_RECORD_H
#define DML_RECORD_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "dml/error.h"

#define DML_RECORD_VERSION 1
#define DML_SCHEMA_VERSION 1
#define DML_OBJECT_ID_SIZE 16
#define DML_OBJECT_ID_HEX_SIZE 32

typedef enum {
  DML_REC_META = 1,
  DML_REC_DATUM = 2,
  DML_REC_NODE = 3,
  DML_REC_DAG = 4,
  DML_REC_TREE = 5,
  DML_REC_COMMIT = 6,
  DML_REC_REF = 7,
  DML_REC_TOMBSTONE = 8,
  DML_REC_EXEC = 9,
  DML_REC_EXEC_REQUEST = 10
} dml_record_type;

typedef enum {
  DML_DATUM_NULL = 1,
  DML_DATUM_BOOL = 2,
  DML_DATUM_I64 = 3,
  DML_DATUM_F64 = 4,
  DML_DATUM_BYTES = 5,
  DML_DATUM_STRING = 6,
  DML_DATUM_URI = 7,
  DML_DATUM_LIST = 8,
  DML_DATUM_SET = 9,
  DML_DATUM_MAP = 10
} dml_datum_kind;

typedef struct {
  uint8_t bytes[DML_OBJECT_ID_SIZE];
} dml_object_id;

typedef struct {
  uint8_t *data;
  size_t len;
} dml_buffer;

typedef struct {
  const uint8_t *data;
  size_t len;
} dml_bytes;

typedef struct {
  dml_object_id key;
  dml_object_id value;
} dml_datum_map_entry;

typedef struct {
  const dml_object_id *items;
  size_t count;
} dml_id_array;

typedef struct {
  const dml_datum_map_entry *items;
  size_t count;
} dml_map_array;

typedef struct {
  dml_datum_kind kind;
  union {
    bool boolean;
    int64_t i64;
    double f64;
    dml_bytes bytes;
    dml_id_array ids;
    dml_map_array map;
  } value;
} dml_datum_input;

typedef struct {
  const uint8_t *record;
  size_t record_len;
  const uint8_t *payload;
  size_t payload_len;
  dml_datum_kind kind;
  size_t count;
} dml_datum_view;

/* Output buffers must be empty. Failures leave them empty. */
dml_status dml_datum_encode(const dml_datum_input *input, dml_buffer *out,
                            dml_error *error);
dml_status dml_record_validate(const uint8_t *data, size_t len, dml_error *error);
/* A decoded view borrows the packed input bytes. */
dml_status dml_datum_decode(const uint8_t *data, size_t len, dml_datum_view *out,
                            dml_error *error);
dml_status dml_datum_view_id(const dml_datum_view *view, size_t index,
                             dml_object_id *out, dml_error *error);
dml_status dml_datum_view_map_entry(const dml_datum_view *view, size_t index,
                                    dml_datum_map_entry *out, dml_error *error);
dml_status dml_datum_id(const uint8_t *data, size_t len, dml_object_id *out,
                        dml_error *error);
dml_status dml_object_id_format(const dml_object_id *id,
                                char out[DML_OBJECT_ID_HEX_SIZE + 1],
                                dml_error *error);
dml_status dml_object_id_parse(const char *text, size_t len, dml_object_id *out,
                               dml_error *error);
dml_status dml_uri_canonicalize(const uint8_t *data, size_t len, dml_buffer *out,
                                dml_error *error);
void dml_buffer_free(dml_buffer *buffer);

#endif
