#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "dml/dml.h"
#include "../../src/encoding.h"
#include "../../src/error_internal.h"
#include "../../src/record_internal.h"

dml_status dml_text_normalize(const uint8_t *data, size_t len, dml_buffer *out,
                              dml_error *error);

#define CHECK(expression) do { \
  if (!(expression)) { fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #expression); return 1; } \
} while (0)

static void datum(uint8_t *out, uint32_t kind, size_t len) {
  memset(out, 0, 128);
  dml_encode_header(out, DML_REC_DATUM, (uint32_t)len);
  dml_write_u32_le(out + 20, kind);
  dml_write_u64_le(out + 24, len - 40);
  dml_write_u64_le(out + 32, 40);
}

static int test_helpers_and_arguments(void) {
  size_t size;
  dml_error error;
  CHECK(!dml_size_add(SIZE_MAX, 1, &size));
  CHECK(dml_size_add(1, SIZE_MAX - 1, &size) && size == SIZE_MAX);
  CHECK(!dml_size_mul(SIZE_MAX, 2, &size));
  CHECK(dml_size_mul(0, SIZE_MAX, &size) && size == 0);
  CHECK(dml_set_error(&error, DML_INVALID_STATE, 7, NULL) == DML_INVALID_STATE);
  CHECK(error.native_code == 7 && error.detail[0] == '\0');
  dml_object_id id = {{0}};
  char hex[33];
  CHECK(dml_object_id_format(NULL, hex, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_object_id_format(&id, NULL, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_object_id_parse(NULL, 32, &id, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_object_id_parse("", 0, &id, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_object_id_parse("0123456789abcdef0123456789abcdef", 32, NULL, &error) == DML_INVALID_ARGUMENT);
  const char *invalid[] = {"z123456789abcdef0123456789abcdef", "0z23456789abcdef0123456789abcdef",
    "/123456789abcdef0123456789abcdef", "0/23456789abcdef0123456789abcdef",
    ":123456789abcdef0123456789abcdef", "0:23456789abcdef0123456789abcdef"};
  for (size_t i = 0; i < sizeof(invalid) / sizeof(invalid[0]); i++) {
    CHECK(dml_object_id_parse(invalid[i], 32, &id, &error) == DML_INVALID_ARGUMENT);
  }
  dml_buffer out = {0};
  dml_datum_input input = {.kind = DML_DATUM_NULL};
  CHECK(dml_datum_encode(NULL, &out, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_datum_encode(&input, NULL, &error) == DML_INVALID_ARGUMENT);
  out.len = 1;
  CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_ARGUMENT);
  out.len = 0; out.data = (uint8_t *)&input;
  CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_ARGUMENT);
  out.data = NULL;
  input.kind = (dml_datum_kind)0;
  CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_KIND);
  input.kind = (dml_datum_kind)11;
  CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_KIND);
  input.kind = DML_DATUM_BYTES; input.value.bytes = (dml_bytes){NULL, 1};
  CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_ARGUMENT);
  input.kind = DML_DATUM_STRING;
  CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_ARGUMENT);
  input.kind = DML_DATUM_BYTES; input.value.bytes = (dml_bytes){(const uint8_t *)"x", SIZE_MAX};
  CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_BOUNDS);
  input.value.bytes.len = UINT32_MAX;
  CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_BOUNDS);
  input.kind = DML_DATUM_LIST; input.value.ids = (dml_id_array){NULL, 1};
  CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_ARGUMENT);
  input.value.ids = (dml_id_array){&id, SIZE_MAX};
  CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_BOUNDS);
  input.value.ids.count = UINT32_MAX;
  CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_BOUNDS);
  input.value.ids.count = (size_t)UINT32_MAX + 1;
  CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_BOUNDS);
  input.kind = DML_DATUM_MAP; input.value.map = (dml_map_array){NULL, 1};
  CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_ARGUMENT);
  dml_datum_map_entry entry = {id, id};
  input.value.map = (dml_map_array){&entry, SIZE_MAX};
  CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_BOUNDS);
  input.value.map.count = UINT32_MAX;
  CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_BOUNDS);
  input.value.map.count = (size_t)UINT32_MAX + 1;
  CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_BOUNDS);
  const dml_datum_kind empty_kinds[] = {DML_DATUM_BYTES, DML_DATUM_STRING, DML_DATUM_LIST,
                                       DML_DATUM_SET, DML_DATUM_MAP};
  for (size_t i = 0; i < sizeof(empty_kinds) / sizeof(empty_kinds[0]); i++) {
    memset(&input, 0, sizeof(input)); input.kind = empty_kinds[i];
    CHECK(dml_datum_encode(&input, &out, &error) == DML_OK);
    dml_buffer_free(&out);
  }
  input.kind = DML_DATUM_URI; input.value.bytes = (dml_bytes){(const uint8_t *)"relative", 8};
  CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_PAYLOAD);
  const char *noncanonical[] = {"HTTP://example.com/x", "http://example.com/%7e"};
  for (size_t i = 0; i < sizeof(noncanonical) / sizeof(noncanonical[0]); i++) {
    input.value.bytes = (dml_bytes){(const uint8_t *)noncanonical[i], strlen(noncanonical[i])};
    CHECK(dml_datum_encode(&input, &out, &error) == DML_INVALID_PAYLOAD);
  }
  CHECK(dml_datum_decode(NULL, 0, NULL, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_record_validate(NULL, 1, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_record_validate((const uint8_t *)"x", SIZE_MAX, &error) == DML_INVALID_HEADER);
  CHECK(dml_text_normalize((const uint8_t *)"x", (size_t)PTRDIFF_MAX + 1, &out, &error) == DML_INVALID_BOUNDS);
  CHECK(dml_text_normalize(NULL, 0, &out, &error) == DML_OK);
  dml_buffer_free(&out);
  return 0;
}

static int test_malformed_datums(void) {
  uint8_t raw[128];
  dml_error error;
  dml_datum_view view;
  datum(raw, DML_DATUM_NULL, 40);
  dml_write_u64_le(raw + 32, 41);
  CHECK(dml_record_validate(raw, 40, &error) == DML_INVALID_BOUNDS);
  datum(raw, DML_DATUM_NULL, 40); raw[24] = 1;
  CHECK(dml_record_validate(raw, 40, &error) == DML_INVALID_BOUNDS);
  datum(raw, 0, 40);
  CHECK(dml_record_validate(raw, 40, &error) == DML_INVALID_KIND);
  datum(raw, 11, 40);
  CHECK(dml_record_validate(raw, 40, &error) == DML_INVALID_KIND);
  datum(raw, DML_DATUM_NULL, 41);
  CHECK(dml_record_validate(raw, 41, &error) == DML_INVALID_PAYLOAD);
  datum(raw, DML_DATUM_BOOL, 40);
  CHECK(dml_record_validate(raw, 40, &error) == DML_INVALID_PAYLOAD);
  datum(raw, DML_DATUM_I64, 41);
  CHECK(dml_record_validate(raw, 41, &error) == DML_INVALID_PAYLOAD);
  datum(raw, DML_DATUM_F64, 41);
  CHECK(dml_record_validate(raw, 41, &error) == DML_INVALID_PAYLOAD);
  datum(raw, DML_DATUM_F64, 48);
  dml_write_u64_le(raw + 40, UINT64_C(0x8000000000000000));
  CHECK(dml_record_validate(raw, 48, &error) == DML_INVALID_PAYLOAD);
  dml_write_u64_le(raw + 40, UINT64_C(0x7ff0000000000001));
  CHECK(dml_record_validate(raw, 48, &error) == DML_INVALID_PAYLOAD);
  dml_write_u64_le(raw + 40, UINT64_C(0x7ff0000000000000));
  CHECK(dml_record_validate(raw, 48, &error) == DML_OK);
  dml_write_u64_le(raw + 40, UINT64_C(0x7ff8000000000000));
  CHECK(dml_record_validate(raw, 48, &error) == DML_OK);
  datum(raw, DML_DATUM_STRING, 43);
  memcpy(raw + 40, "e\xcc\x81", 3);
  CHECK(dml_record_validate(raw, 43, &error) == DML_INVALID_PAYLOAD);
  datum(raw, DML_DATUM_STRING, 44);
  memcpy(raw + 40, "\xcc\x95\xcc\x80", 4); /* NFC reorders, without changing byte count. */
  CHECK(dml_record_validate(raw, 44, &error) == DML_INVALID_PAYLOAD);
  datum(raw, DML_DATUM_STRING, 41); raw[40] = 0xff;
  CHECK(dml_record_validate(raw, 41, &error) == DML_INVALID_UTF8);
  const char *uri = "HTTP://example.com/x";
  datum(raw, DML_DATUM_URI, 40 + strlen(uri));
  memcpy(raw + 40, uri, strlen(uri));
  CHECK(dml_record_validate(raw, 40 + strlen(uri), &error) == DML_INVALID_PAYLOAD);
  uri = "http://example.com/%7e";
  datum(raw, DML_DATUM_URI, 40 + strlen(uri)); memcpy(raw + 40, uri, strlen(uri));
  CHECK(dml_record_validate(raw, 40 + strlen(uri), &error) == DML_INVALID_PAYLOAD);
  datum(raw, DML_DATUM_URI, 41); raw[40] = '%';
  CHECK(dml_record_validate(raw, 41, &error) == DML_INVALID_PAYLOAD);
  for (int kind = DML_DATUM_LIST; kind <= DML_DATUM_MAP; kind++) {
    datum(raw, (uint32_t)kind, 43);
    CHECK(dml_record_validate(raw, 43, &error) == DML_INVALID_BOUNDS);
    datum(raw, (uint32_t)kind, 44); raw[40] = 1;
    CHECK(dml_record_validate(raw, 44, &error) == DML_INVALID_BOUNDS);
    datum(raw, (uint32_t)kind, 45);
    CHECK(dml_record_validate(raw, 45, &error) == DML_INVALID_BOUNDS);
    datum(raw, (uint32_t)kind, 44);
    CHECK(dml_datum_decode(raw, 44, &view, &error) == DML_OK && view.count == 0);
  }
  datum(raw, DML_DATUM_MAP, 108); raw[40] = 2;
  CHECK(dml_record_validate(raw, 108, &error) == DML_INVALID_PAYLOAD);
  dml_encode_header(raw, DML_REC_DATUM, 20);
  CHECK(dml_record_validate(raw, 20, &error) == DML_INVALID_BOUNDS);
  dml_encode_header(raw, DML_REC_META, 20);
  CHECK(dml_record_validate(raw, 20, &error) == DML_INVALID_BOUNDS);
  dml_encode_meta(raw); raw[20] = 2;
  CHECK(dml_record_validate(raw, DML_META_SIZE, &error) == DML_UNSUPPORTED_SCHEMA);
  dml_encode_meta(raw);
  CHECK(dml_datum_decode(raw, DML_META_SIZE, &view, &error) == DML_INVALID_KIND);
  CHECK(dml_datum_decode(NULL, 0, &view, &error) == DML_INVALID_HEADER);
  dml_encode_header(raw, 0, 20);
  CHECK(dml_record_validate(raw, 20, &error) == DML_INVALID_KIND);
  dml_encode_header(raw, 65535, 20);
  CHECK(dml_record_validate(raw, 20, &error) == DML_INVALID_KIND);
  return 0;
}

static int test_accessor_and_uri_arguments(void) {
  dml_datum_view view = {.kind = DML_DATUM_NULL};
  dml_object_id id;
  dml_datum_map_entry entry;
  dml_error error;
  CHECK(dml_datum_view_id(NULL, 0, &id, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_datum_view_id(&view, 0, NULL, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_datum_view_id(&view, 0, &id, &error) == DML_INVALID_ARGUMENT);
  view.kind = DML_DATUM_LIST;
  CHECK(dml_datum_view_id(&view, 0, &id, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_datum_view_map_entry(NULL, 0, &entry, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_datum_view_map_entry(&view, 0, NULL, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_datum_view_map_entry(&view, 0, &entry, &error) == DML_INVALID_ARGUMENT);
  view.kind = DML_DATUM_MAP;
  CHECK(dml_datum_view_map_entry(&view, 0, &entry, &error) == DML_INVALID_ARGUMENT);
  dml_buffer out = {0};
  const uint8_t *uri = (const uint8_t *)"urn:x";
  CHECK(dml_uri_canonicalize(uri, 5, NULL, &error) == DML_INVALID_ARGUMENT);
  out.data = (uint8_t *)uri;
  CHECK(dml_uri_canonicalize(uri, 5, &out, &error) == DML_INVALID_ARGUMENT);
  out.data = NULL; out.len = 1;
  CHECK(dml_uri_canonicalize(uri, 5, &out, &error) == DML_INVALID_ARGUMENT);
  out.len = 0;
  CHECK(dml_uri_canonicalize(NULL, 1, &out, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_uri_canonicalize(NULL, 0, &out, &error) == DML_INVALID_PAYLOAD);
  CHECK(dml_uri_canonicalize(uri, (size_t)PTRDIFF_MAX + 1, &out, &error) == DML_INVALID_PAYLOAD);
  CHECK(dml_uri_canonicalize((const uint8_t *)"http:\0x", 7, &out, &error) == DML_INVALID_PAYLOAD);
  CHECK(dml_uri_canonicalize((const uint8_t *)"http:\xff", 6, &out, &error) == DML_INVALID_PAYLOAD);
  CHECK(dml_uri_canonicalize((const uint8_t *)"relative", 8, &out, &error) == DML_INVALID_PAYLOAD);
  const char *valid[] = {"http://example.com/%AA/%ab/%2F/%2f/%41/%61/%30/%2D/%2E/%5F/%7E",
                         "abc:x", "Dmx:x", "d-l:x", "a:/x"};
  for (size_t i = 0; i < sizeof(valid) / sizeof(valid[0]); i++) {
    CHECK(dml_uri_canonicalize((const uint8_t *)valid[i], strlen(valid[i]), &out, &error) == DML_OK);
    dml_buffer_free(&out);
  }
  return 0;
}

static int test_object_boundaries(void) {
  dml_buffer packed = {0};
  dml_error error;
  dml_object_id id = {{1}};
  dml_object_input input = {.type = DML_REC_COMMIT};
  input.value.commit.parents = (dml_id_array){&id, SIZE_MAX / 16};
  CHECK(dml_object_encode(&input, &packed, &error) == DML_INVALID_BOUNDS);
  input.value.commit.parents.count = UINT32_MAX;
  CHECK(dml_object_encode(&input, &packed, &error) == DML_INVALID_BOUNDS);
  uint8_t raw[128] = {0};
  dml_encode_header(raw, DML_REC_TREE, 66);
  dml_write_u32_le(raw + 20, 2); dml_write_u32_le(raw + 24, 18);
  memset(raw + 28, 'a', 18);
  CHECK(dml_record_validate(raw, 66, &error) == DML_INVALID_BOUNDS);
  dml_encode_header(raw, DML_REC_TREE, 67);
  dml_write_u32_le(raw + 24, 23); memset(raw + 28, 'a', 23);
  CHECK(dml_record_validate(raw, 67, &error) == DML_INVALID_BOUNDS);
  dml_object_view view = {.type = DML_REC_TREE};
  CHECK(dml_object_view_parent(&view, 0, &id, &error) == DML_INVALID_ARGUMENT);
  view.type = DML_REC_COMMIT;
  dml_tree_entry entry;
  CHECK(dml_object_view_entry(&view, 0, &entry, &error) == DML_INVALID_ARGUMENT);
  datum(raw, DML_DATUM_SET, 60); raw[40] = 1; raw[44] = 2;
  dml_datum_view values;
  CHECK(dml_datum_decode(raw, 60, &values, &error) == DML_OK);
  CHECK(dml_datum_view_id(&values, 0, &id, &error) == DML_OK && id.bytes[0] == 2);
  return 0;
}

int main(void) {
  CHECK(test_helpers_and_arguments() == 0);
  CHECK(test_malformed_datums() == 0);
  CHECK(test_accessor_and_uri_arguments() == 0);
  CHECK(test_object_boundaries() == 0);
  return 0;
}
