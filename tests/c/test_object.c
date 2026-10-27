#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "dml/dml.h"
#include "../../src/encoding.h"

#define CHECK(condition) do { \
  if (!(condition)) { fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #condition); return 1; } \
} while (0)

static int test_roundtrips(void) {
  dml_object_input input = {.type = DML_REC_NODE, .value.node = {DML_NODE_LITERAL, {{1}}}};
  dml_buffer record = {0};
  dml_object_view view;
  dml_object_id id, again;
  dml_error error;
  for (int type = DML_REC_NODE; type <= DML_REC_COMMIT; type++) {
    input.type = (dml_record_type)type;
    memset(&input.value, 0, sizeof(input.value));
    if (type == DML_REC_NODE) input.value.node.kind = DML_NODE_LITERAL;
    CHECK(dml_object_encode(&input, &record, &error) == DML_OK);
    CHECK(dml_object_decode(record.data, record.len, &view, &error) == DML_OK);
    CHECK(view.type == (dml_record_type)type && view.count == 0);
    CHECK(dml_object_id_compute(record.data, record.len, &id, &error) == DML_OK);
    CHECK(dml_object_id_compute(record.data, record.len, &again, &error) == DML_OK);
    CHECK(memcmp(&id, &again, sizeof(id)) == 0);
    CHECK(dml_datum_id(record.data, record.len, &again, &error) == DML_INVALID_KIND);
    for (size_t len = 0; len < record.len; len++) {
      CHECK(dml_record_validate(record.data, len, &error) != DML_OK);
    }
    if (type != DML_REC_TREE) {
      record.data[type == DML_REC_NODE ? 24 : 20] = 1;
      CHECK(dml_object_id_compute(record.data, record.len, &again, &error) == DML_OK);
      CHECK(memcmp(&id, &again, sizeof(id)) != 0);
    }
    dml_buffer_free(&record);
  }
  dml_object_id parents[2] = {{{2}}, {{1}}};
  input.type = DML_REC_COMMIT;
  input.value.commit.tree = (dml_object_id){{3}};
  input.value.commit.parents = (dml_id_array){parents, 2};
  CHECK(dml_object_encode(&input, &record, &error) == DML_OK);
  CHECK(dml_object_decode(record.data, record.len, &view, &error) == DML_OK);
  CHECK(view.count == 2 && view.reference.bytes[0] == 3);
  CHECK(dml_object_view_parent(&view, 0, &again, &error) == DML_OK && again.bytes[0] == 2);
  CHECK(dml_object_view_parent(&view, 1, &again, &error) == DML_OK && again.bytes[0] == 1);
  CHECK(dml_object_view_parent(&view, 2, &again, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_object_view_parent(NULL, 0, &again, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_object_view_parent(&view, 0, NULL, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_object_view_entry(&view, 0, NULL, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_object_id_compute(record.data, record.len, &id, &error) == DML_OK);
  record.data[40] = 4;
  CHECK(dml_object_id_compute(record.data, record.len, &again, &error) == DML_OK);
  CHECK(memcmp(&id, &again, sizeof(id)) != 0);
  memcpy(record.data + 56, record.data + 40, 16);
  CHECK(dml_record_validate(record.data, record.len, &error) == DML_INVALID_PAYLOAD);
  dml_buffer_free(&record);
  parents[1] = parents[0];
  CHECK(dml_object_encode(&input, &record, &error) == DML_INVALID_PAYLOAD);
  CHECK(record.data == NULL && record.len == 0);
  input.value.commit.parents = (dml_id_array){NULL, 1};
  CHECK(dml_object_encode(&input, &record, &error) == DML_INVALID_ARGUMENT);
  input.value.commit.parents = (dml_id_array){parents, SIZE_MAX};
  CHECK(dml_object_encode(&input, &record, &error) == DML_INVALID_BOUNDS);
  return 0;
}

static int test_trees(void) {
  dml_tree_entry entries[] = {
    {{(const uint8_t *)"ab", 2}, {{2}}},
    {{(const uint8_t *)"a", 1}, {{1}}},
    {{(const uint8_t *)"z", 1}, {{3}}}
  };
  dml_object_input input = {.type = DML_REC_TREE, .value.tree = {entries, 3}};
  dml_buffer record = {0}, sorted = {0};
  dml_object_view view;
  dml_tree_entry entry;
  dml_error error;
  CHECK(dml_object_encode(&input, &record, &error) == DML_OK);
  CHECK(dml_object_decode(record.data, record.len, &view, &error) == DML_OK);
  CHECK(view.count == 3);
  CHECK(dml_object_view_entry(&view, 0, &entry, &error) == DML_OK);
  CHECK(entry.name.len == 1 && entry.name.data[0] == 'a' && entry.dag.bytes[0] == 1);
  CHECK(dml_object_view_entry(&view, 2, &entry, &error) == DML_OK);
  CHECK(entry.name.len == 1 && entry.name.data[0] == 'z' && entry.dag.bytes[0] == 3);
  CHECK(dml_object_view_entry(&view, 3, &entry, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_object_view_entry(NULL, 0, &entry, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_object_view_entry(&view, 0, NULL, &error) == DML_INVALID_ARGUMENT);
  dml_tree_entry temporary = entries[0]; entries[0] = entries[1]; entries[1] = temporary;
  CHECK(dml_object_encode(&input, &sorted, &error) == DML_OK);
  CHECK(record.len == sorted.len && memcmp(record.data, sorted.data, record.len) == 0);
  dml_buffer_free(&sorted);
  entries[1].name = entries[0].name;
  CHECK(dml_object_encode(&input, &sorted, &error) == DML_INVALID_PAYLOAD);
  record.data[28] = 'z';
  CHECK(dml_record_validate(record.data, record.len, &error) == DML_INVALID_PAYLOAD);
  record.data[28] = '/';
  CHECK(dml_record_validate(record.data, record.len, &error) == DML_INVALID_PAYLOAD);
  record.data[28] = 'a';
  dml_write_u32_le(record.data + 24, UINT32_MAX);
  CHECK(dml_record_validate(record.data, record.len, &error) == DML_INVALID_BOUNDS);
  dml_buffer_free(&record);
  input.value.tree.items = NULL;
  CHECK(dml_object_encode(&input, &record, &error) == DML_INVALID_ARGUMENT);
  input.value.tree.items = entries;
  input.value.tree.count = SIZE_MAX;
  CHECK(dml_object_encode(&input, &record, &error) == DML_INVALID_BOUNDS);
  input.value.tree.count = 1;
  entries[0].name.len = 0;
  CHECK(dml_object_encode(&input, &record, &error) == DML_INVALID_ARGUMENT);
  return 0;
}

static int test_invalid_arguments_and_shapes(void) {
  dml_object_input input = {.type = DML_REC_NODE, .value.node.kind = 2};
  dml_buffer record = {0};
  dml_object_view view;
  dml_object_id id;
  dml_error error;
  CHECK(dml_object_encode(&input, &record, &error) == DML_INVALID_KIND);
  CHECK(dml_object_encode(NULL, &record, NULL) == DML_INVALID_ARGUMENT);
  CHECK(dml_object_encode(&input, NULL, NULL) == DML_INVALID_ARGUMENT);
  record.len = 1;
  CHECK(dml_object_encode(&input, &record, NULL) == DML_INVALID_ARGUMENT);
  record.len = 0;
  record.data = (uint8_t *)&input;
  CHECK(dml_object_encode(&input, &record, NULL) == DML_INVALID_ARGUMENT);
  record.data = NULL;
  input.type = DML_REC_REF;
  CHECK(dml_object_encode(&input, &record, NULL) == DML_INVALID_KIND);
  CHECK(dml_object_decode(NULL, 0, NULL, NULL) == DML_INVALID_ARGUMENT);
  CHECK(dml_object_decode(NULL, 1, &view, NULL) == DML_INVALID_ARGUMENT);
  CHECK(dml_object_id_compute(NULL, 0, NULL, NULL) == DML_INVALID_ARGUMENT);
  const char *invalid_names[] = {"", ".", "_a", "-a", "a/b", "a b", "a\\b", "é"};
  for (size_t i = 0; i < sizeof(invalid_names) / sizeof(invalid_names[0]); i++) {
    CHECK(dml_name_validate((dml_bytes){(const uint8_t *)invalid_names[i], strlen(invalid_names[i])},
                            &error) == DML_INVALID_ARGUMENT);
  }
  CHECK(dml_name_validate((dml_bytes){NULL, 1}, NULL) == DML_INVALID_ARGUMENT);
  uint8_t name[129]; memset(name, 'A', sizeof(name));
  CHECK(dml_name_validate((dml_bytes){name, 129}, NULL) == DML_INVALID_ARGUMENT);
  CHECK(dml_name_validate((dml_bytes){name, 128}, NULL) == DML_OK);
  CHECK(dml_name_validate((dml_bytes){(const uint8_t *)"A0._-z", 6}, NULL) == DML_OK);
  CHECK(dml_name_validate((dml_bytes){(const uint8_t *)"a\0b", 3}, NULL) == DML_INVALID_ARGUMENT);

  uint8_t raw[80];
  for (int type = DML_REC_NODE; type <= DML_REC_COMMIT; type++) {
    for (size_t len = 20; len < 44; len++) {
      memset(raw, 0, sizeof(raw));
      dml_write_u32_le(raw, 0x314c4d44);
      dml_write_u16_le(raw + 4, 1);
      dml_write_u16_le(raw + 6, (uint16_t)type);
      dml_write_u32_le(raw + 8, (uint32_t)len);
      dml_status status = dml_record_validate(raw, len, &error);
      if ((type == DML_REC_DAG && len == 36) ||
          (type == DML_REC_TREE && len == 24) || (type == DML_REC_COMMIT && len == 40)) {
        CHECK(status == DML_OK);
      } else CHECK(status != DML_OK);
    }
  }
  dml_datum_input datum = {.kind = DML_DATUM_NULL};
  CHECK(dml_datum_encode(&datum, &record, NULL) == DML_OK);
  CHECK(dml_object_decode(record.data, record.len, &view, NULL) == DML_INVALID_KIND);
  dml_buffer_free(&record);
  memset(raw, 0, sizeof(raw));
  dml_write_u32_le(raw, 0x314c4d44);
  dml_write_u16_le(raw + 4, 1);
  dml_write_u16_le(raw + 6, DML_REC_META);
  dml_write_u32_le(raw + 8, 24);
  dml_write_u32_le(raw + 20, 1);
  CHECK(dml_object_id_compute(raw, 24, &id, NULL) == DML_INVALID_KIND);
  return 0;
}

int main(void) {
  CHECK(test_roundtrips() == 0);
  CHECK(test_trees() == 0);
  CHECK(test_invalid_arguments_and_shapes() == 0);
  return 0;
}
