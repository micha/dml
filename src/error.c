#include "dml/error.h"

#include <stdio.h>

#include "error_internal.h"

const char *dml_status_name(dml_status status) {
  static const char *const names[] = {
      "ok",                 "invalid_header", "invalid_bounds",
      "invalid_kind",       "invalid_payload", "invalid_utf8",
      "invalid_argument",   "invalid_state",  "not_found",
      "unsupported_schema", "out_of_memory",  "map_full",
      "storage_error",      "integrity_error",
  };

  if ((unsigned int)status >= sizeof(names) / sizeof(names[0])) {
    return "unknown";
  }
  return names[status];
}

void dml_error_clear(dml_error *error) {
  if (error == NULL) {
    return;
  }
  error->code = DML_OK;
  error->native_code = 0;
  error->detail[0] = '\0';
}

dml_status dml_set_error(dml_error *error, dml_status status, int native_code,
                         const char *detail) {
  if (error != NULL) {
    error->code = status;
    error->native_code = native_code;
    (void)snprintf(error->detail, sizeof(error->detail), "%s",
                   detail == NULL ? "" : detail);
  }
  return status;
}
