#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include <utf8proc.h>

#include "dml/record.h"
#include "error_internal.h"

dml_status dml_text_normalize(const uint8_t *data, size_t len, dml_buffer *out,
                              dml_error *error) {
  static const uint8_t empty[] = "";
  utf8proc_uint8_t *normalized = NULL;
  utf8proc_ssize_t normalized_len;

  if (len > (size_t)PTRDIFF_MAX) {
    return dml_set_error(error, DML_INVALID_BOUNDS, 0,
                         "record_type=datum;detail=string_too_long");
  }
  normalized_len = utf8proc_map(data == NULL ? empty : data,
                                (utf8proc_ssize_t)len, &normalized,
                                UTF8PROC_STABLE | UTF8PROC_COMPOSE);
  if (normalized_len == UTF8PROC_ERROR_INVALIDUTF8) {
    return dml_set_error(error, DML_INVALID_UTF8, 0,
                         "record_type=datum;detail=string_invalid_utf8");
  }
  if (normalized_len < 0) {
    return dml_set_error(error, DML_OUT_OF_MEMORY, (int)normalized_len,
                         "utf8proc normalization failed");
  }
  out->data = normalized;
  out->len = (size_t)normalized_len;
  return DML_OK;
}
