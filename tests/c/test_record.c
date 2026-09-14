#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "dml/dml.h"

#define CHECK(condition)                                                        \
  do {                                                                          \
    if (!(condition)) {                                                         \
      fprintf(stderr, "check failed at %s:%d: %s\n", __FILE__, __LINE__,      \
              #condition);                                                      \
      return 1;                                                                 \
    }                                                                           \
  } while (0)

static int test_scalars(void) {
  dml_error error;
  dml_buffer record = {0};
  dml_datum_view view;
  dml_datum_input input = {.kind = DML_DATUM_NULL};

  CHECK(dml_datum_encode(&input, &record, &error) == DML_OK);
  CHECK(record.len == 40);
  CHECK(memcmp(record.data, "DML1", 4) == 0);
  CHECK(record.data[4] == 1 && record.data[6] == DML_REC_DATUM);
  CHECK(record.data[8] == 40 && record.data[20] == DML_DATUM_NULL);
  CHECK(record.data[32] == 40);
  CHECK(dml_datum_decode(record.data, record.len, &view, &error) == DML_OK);
  CHECK(view.kind == DML_DATUM_NULL && view.payload_len == 0);
  dml_buffer_free(&record);

  input.kind = DML_DATUM_BOOL;
  input.value.boolean = true;
  CHECK(dml_datum_encode(&input, &record, &error) == DML_OK);
  CHECK(record.len == 41 && record.data[40] == 1);
  record.data[40] = 2;
  CHECK(dml_record_validate(record.data, record.len, &error) == DML_INVALID_PAYLOAD);
  dml_buffer_free(&record);

  input.kind = DML_DATUM_I64;
  input.value.i64 = INT64_MIN;
  CHECK(dml_datum_encode(&input, &record, &error) == DML_OK);
  CHECK(record.data[47] == 0x80);
  dml_buffer_free(&record);

  input.kind = DML_DATUM_F64;
  input.value.f64 = -0.0;
  CHECK(dml_datum_encode(&input, &record, &error) == DML_OK);
  CHECK(memcmp(record.data + 40, "\0\0\0\0\0\0\0\0", 8) == 0);
  dml_buffer_free(&record);
  input.value.f64 = NAN;
  CHECK(dml_datum_encode(&input, &record, &error) == DML_OK);
  CHECK(record.data[46] == 0xf8 && record.data[47] == 0x7f);
  dml_buffer_free(&record);
  return 0;
}

static int test_text_and_uri(void) {
  static const uint8_t decomposed[] = {'e', 0xcc, 0x81};
  static const uint8_t composed[] = {0xc3, 0xa9};
  static const uint8_t invalid[] = {0xc0, 0x80};
  static const uint8_t uri[] = "HTTP://Example.COM/a/../b/%7e?q=%2f";
  static const uint8_t canonical_uri[] = "http://example.com/b/~?q=%2F";
  dml_datum_input input = {.kind = DML_DATUM_STRING};
  dml_buffer record = {0};
  dml_buffer normalized = {0};
  dml_error error;

  input.value.bytes.data = decomposed;
  input.value.bytes.len = sizeof(decomposed);
  CHECK(dml_datum_encode(&input, &record, &error) == DML_OK);
  CHECK(record.len == 42 && memcmp(record.data + 40, composed, 2) == 0);
  dml_buffer_free(&record);
  input.value.bytes.data = invalid;
  input.value.bytes.len = sizeof(invalid);
  CHECK(dml_datum_encode(&input, &record, &error) == DML_INVALID_UTF8);

  CHECK(dml_uri_canonicalize(uri, sizeof(uri) - 1, &normalized, &error) == DML_OK);
  CHECK(normalized.len == sizeof(canonical_uri) - 1);
  CHECK(memcmp(normalized.data, canonical_uri, normalized.len) == 0);
  input.kind = DML_DATUM_URI;
  input.value.bytes.data = normalized.data;
  input.value.bytes.len = normalized.len;
  CHECK(dml_datum_encode(&input, &record, &error) == DML_OK);
  CHECK(dml_record_validate(record.data, record.len, &error) == DML_OK);
  dml_buffer_free(&record);
  dml_buffer_free(&normalized);
  CHECK(dml_uri_canonicalize((const uint8_t *)"DML:x", 5, &normalized, &error) ==
        DML_INVALID_PAYLOAD);
  CHECK(dml_uri_canonicalize((const uint8_t *)"urn:a/%7e/../b", 14, &normalized,
                             &error) == DML_OK);
  CHECK(normalized.len == 12 && memcmp(normalized.data, "urn:a/~/../b", 12) == 0);
  dml_buffer_free(&normalized);
  return 0;
}

static int test_uri_syntax_before_normalization(void) {
  static const char *const invalid[] = {
      "%68ttp://example.com/",
      "http://example.com:%38%30/",
      "http://[::%31]/",
  };
  static const char *const valid[][2] = {
      {"http://example.com/a/%2e%2E/b", "http://example.com/b"},
      {"urn:a/%2e%2e/b", "urn:a/../b"},
      {"http://%65XAMPLE.com:80/%7e?q=%2f#", "http://example.com:80/~?q=%2F#"},
  };
  dml_buffer normalized = {0};
  dml_error error;

  for (size_t i = 0; i < sizeof(invalid) / sizeof(invalid[0]); i++) {
    CHECK(dml_uri_canonicalize((const uint8_t *)invalid[i], strlen(invalid[i]),
                               &normalized, &error) == DML_INVALID_PAYLOAD);
    CHECK(strcmp(error.detail, "record_type=datum;detail=uri_syntax") == 0);
    CHECK(normalized.data == NULL && normalized.len == 0);
  }
  for (size_t i = 0; i < sizeof(valid) / sizeof(valid[0]); i++) {
    CHECK(dml_uri_canonicalize((const uint8_t *)valid[i][0], strlen(valid[i][0]),
                               &normalized, &error) == DML_OK);
    CHECK(normalized.len == strlen(valid[i][1]));
    CHECK(memcmp(normalized.data, valid[i][1], normalized.len) == 0);
    dml_buffer_free(&normalized);
  }
  return 0;
}

static int test_collections_and_ids(void) {
  dml_object_id ids[3] = {{{2}}, {{1}}, {{1}}};
  dml_datum_map_entry entries[2] = {{{{2}}, {{4}}}, {{{1}}, {{3}}}};
  dml_datum_input input = {.kind = DML_DATUM_LIST};
  dml_buffer record = {0};
  dml_datum_view view;
  dml_object_id id;
  dml_object_id parsed;
  dml_datum_map_entry entry;
  char hex[33];
  dml_error error;

  input.value.ids.items = ids;
  input.value.ids.count = 3;
  CHECK(dml_datum_encode(&input, &record, &error) == DML_OK);
  CHECK(dml_datum_decode(record.data + 0, record.len, &view, &error) == DML_OK);
  CHECK(view.count == 3);
  CHECK(dml_datum_view_id(&view, 1, &id, &error) == DML_OK && id.bytes[0] == 1);
  CHECK(dml_datum_id(record.data, record.len, &id, &error) == DML_OK);
  CHECK(dml_object_id_format(&id, hex, &error) == DML_OK);
  CHECK(strlen(hex) == 32);
  CHECK(dml_object_id_parse(hex, 32, &parsed, &error) == DML_OK);
  CHECK(memcmp(id.bytes, parsed.bytes, 16) == 0);
  CHECK(dml_object_id_parse("ABCDEFABCDEFABCDEFABCDEFABCDEFAB", 32, &parsed,
                            &error) == DML_INVALID_ARGUMENT);
  dml_buffer_free(&record);

  input.kind = DML_DATUM_SET;
  input.value.ids.count = 2;
  CHECK(dml_datum_encode(&input, &record, &error) == DML_OK);
  CHECK(record.data[44] == 1 && record.data[60] == 2);
  dml_buffer_free(&record);
  input.value.ids.count = 3;
  CHECK(dml_datum_encode(&input, &record, &error) == DML_INVALID_PAYLOAD);

  input.kind = DML_DATUM_MAP;
  input.value.map.items = entries;
  input.value.map.count = 2;
  CHECK(dml_datum_encode(&input, &record, &error) == DML_OK);
  CHECK(dml_datum_decode(record.data, record.len, &view, &error) == DML_OK);
  CHECK(dml_datum_view_map_entry(&view, 0, &entry, &error) == DML_OK);
  CHECK(entry.key.bytes[0] == 1 && entry.value.bytes[0] == 3);
  dml_buffer_free(&record);
  return 0;
}

static int test_invalid_envelopes(void) {
  dml_datum_input input = {.kind = DML_DATUM_NULL};
  dml_buffer record = {0};
  dml_error error;
  CHECK(strcmp(dml_status_name(DML_INVALID_HEADER), "invalid_header") == 0);
  CHECK(strcmp(dml_status_name((dml_status)999), "unknown") == 0);
  CHECK(dml_record_validate(NULL, 0, &error) == DML_INVALID_HEADER);
  CHECK(dml_datum_encode(&input, &record, &error) == DML_OK);
  record.data[0] = 0;
  CHECK(dml_record_validate(record.data, record.len, &error) == DML_INVALID_HEADER);
  record.data[0] = 'D';
  record.data[12] = 1;
  CHECK(dml_record_validate(record.data, record.len, &error) == DML_INVALID_HEADER);
  dml_buffer_free(&record);
  dml_buffer_free(NULL);
  dml_error_clear(NULL);
  return 0;
}

int main(void) {
  CHECK(test_scalars() == 0);
  CHECK(test_text_and_uri() == 0);
  CHECK(test_uri_syntax_before_normalization() == 0);
  CHECK(test_collections_and_ids() == 0);
  CHECK(test_invalid_envelopes() == 0);
  return 0;
}
