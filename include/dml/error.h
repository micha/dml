#ifndef DML_ERROR_H
#define DML_ERROR_H

typedef enum {
  DML_OK = 0,
  DML_INVALID_HEADER,
  DML_INVALID_BOUNDS,
  DML_INVALID_KIND,
  DML_INVALID_PAYLOAD,
  DML_INVALID_UTF8,
  DML_INVALID_ARGUMENT,
  DML_INVALID_STATE,
  DML_NOT_FOUND,
  DML_UNSUPPORTED_SCHEMA,
  DML_OUT_OF_MEMORY,
  DML_MAP_FULL,
  DML_STORAGE_ERROR,
  DML_INTEGRITY_ERROR
} dml_status;

typedef struct {
  dml_status code;
  int native_code;
  char detail[128];
} dml_error;

const char *dml_status_name(dml_status status);
void dml_error_clear(dml_error *error);

#endif
