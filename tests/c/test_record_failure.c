#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "dml/dml.h"

#define CHECK(condition)                                                        \
  do {                                                                          \
    if (!(condition)) {                                                         \
      fprintf(stderr, "check failed at %s:%d: %s\n", __FILE__, __LINE__,            \
              #condition);                                                      \
      return 1;                                                                 \
    }                                                                           \
  } while (0)

static size_t normalization_calls;
static size_t fail_normalization_call;

/* This test double replaces the text module when linking the static core.
 * ASCII input needs no transformation; fail only during post-encode validation. */
dml_status dml_text_normalize(const uint8_t *data, size_t len, dml_buffer *out,
                              dml_error *error) {
  normalization_calls++;
  if (normalization_calls == fail_normalization_call) {
    if (error != NULL) {
      dml_error_clear(error);
      error->code = DML_OUT_OF_MEMORY;
    }
    return DML_OUT_OF_MEMORY;
  }
  out->data = malloc(len + 1);
  if (out->data == NULL) return DML_OUT_OF_MEMORY;
  memcpy(out->data, data, len);
  out->len = len;
  return DML_OK;
}

static int test_validation_allocation_failure(bool with_error) {
  static const uint8_t text[] = "hello";
  dml_datum_input input = {
      .kind = DML_DATUM_STRING,
      .value.bytes = {text, sizeof(text) - 1},
  };
  dml_buffer record = {0};
  dml_error error;

  normalization_calls = 0;
  fail_normalization_call = 2;
  CHECK(dml_datum_encode(&input, &record, with_error ? &error : NULL) == DML_OUT_OF_MEMORY);
  CHECK(normalization_calls == 2);
  CHECK(record.data == NULL && record.len == 0);
  if (with_error) CHECK(error.code == DML_OUT_OF_MEMORY);

  fail_normalization_call = 0;
  CHECK(dml_datum_encode(&input, &record, with_error ? &error : NULL) == DML_OK);
  CHECK(dml_record_validate(record.data, record.len, NULL) == DML_OK);
  dml_buffer_free(&record);
  return 0;
}

int main(void) {
  CHECK(test_validation_allocation_failure(true) == 0);
  CHECK(test_validation_allocation_failure(false) == 0);
  return 0;
}
