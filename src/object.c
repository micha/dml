#include <stdlib.h>
#include <string.h>

#include "dml/object.h"
#include "encoding.h"
#include "error_internal.h"
#include "record_internal.h"

static int alphanumeric(uint8_t byte) {
  return (byte >= 'a' && byte <= 'z') || (byte >= 'A' && byte <= 'Z') ||
         (byte >= '0' && byte <= '9');
}

dml_status dml_name_validate(dml_bytes name, dml_error *error) {
  if (name.data == NULL || name.len == 0 || name.len > DML_NAME_MAX_SIZE) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "name must contain 1..128 ASCII bytes");
  }
  for (size_t i = 0; i < name.len; i++) {
    uint8_t byte = name.data[i];
    if (!alphanumeric(byte) && (i == 0 || (byte != '.' && byte != '_' && byte != '-'))) {
      return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "name is outside the ASCII name profile");
    }
  }
  return DML_OK;
}

static int compare_names(dml_bytes left, dml_bytes right) {
  size_t common = left.len < right.len ? left.len : right.len;
  int order = memcmp(left.data, right.data, common);
  if (order != 0) return order;
  return (left.len > right.len) - (left.len < right.len);
}

static int compare_entries(const void *left, const void *right) {
  return compare_names(((const dml_tree_entry *)left)->name,
                       ((const dml_tree_entry *)right)->name);
}

static dml_status invalid(dml_error *error, dml_status status, const char *detail) {
  return dml_set_error(error, status, 0, detail);
}

/* Only called after envelope validation. Bounds are checked before each load. */
dml_status dml_validate_object(const uint8_t *data, size_t len, uint16_t type,
                                 dml_error *error) {
  if (type == DML_REC_NODE) {
    if (len != 40) return invalid(error, DML_INVALID_BOUNDS, "record_type=node;detail=size");
    if (dml_read_u32_le(data + 20) != DML_NODE_LITERAL) {
      return invalid(error, DML_INVALID_KIND, "record_type=node;detail=unsupported_kind");
    }
    return DML_OK;
  }
  if (type == DML_REC_DAG) {
    return len == 36 ? DML_OK : invalid(error, DML_INVALID_BOUNDS, "record_type=dag;detail=size");
  }
  if (type == DML_REC_COMMIT) {
    if (len < 40) return invalid(error, DML_INVALID_BOUNDS, "record_type=commit;detail=size");
    size_t count = dml_read_u32_le(data + 36);
    if (count != (len - 40) / 16 || (len - 40) % 16 != 0) {
      return invalid(error, DML_INVALID_BOUNDS, "record_type=commit;detail=parent_count");
    }
    for (size_t i = 0; i < count; i++) {
      for (size_t j = 0; j < i; j++) {
        if (memcmp(data + 40 + i * 16, data + 40 + j * 16, 16) == 0) {
          return invalid(error, DML_INVALID_PAYLOAD, "record_type=commit;detail=duplicate_parent");
        }
      }
    }
    return DML_OK;
  }
  if (len < 24) return invalid(error, DML_INVALID_BOUNDS, "record_type=tree;detail=size");
  size_t count = dml_read_u32_le(data + 20);
  size_t offset = 24;
  dml_bytes previous = {0};
  /* Minimum entry size is 4 + 1 + 16, so oversized counts fail immediately. */
  if (count > (len - offset) / 21) {
    return invalid(error, DML_INVALID_BOUNDS, "record_type=tree;detail=entry_count");
  }
  for (size_t i = 0; i < count; i++) {
    if (len - offset < 4) {
      return invalid(error, DML_INVALID_BOUNDS, "record_type=tree;detail=name_length");
    }
    size_t name_len = dml_read_u32_le(data + offset);
    offset += 4;
    if (len - offset < 16 || name_len > len - offset - 16) {
      return invalid(error, DML_INVALID_BOUNDS, "record_type=tree;detail=entry_bounds");
    }
    dml_bytes name = {data + offset, name_len};
    if (dml_name_validate(name, NULL) != DML_OK) {
      return invalid(error, DML_INVALID_PAYLOAD, "record_type=tree;detail=name_profile");
    }
    if (i != 0 && compare_names(previous, name) >= 0) {
      return invalid(error, DML_INVALID_PAYLOAD, "record_type=tree;detail=names_not_strictly_sorted");
    }
    previous = name;
    offset += name_len + 16;
  }
  return offset == len ? DML_OK : invalid(error, DML_INVALID_BOUNDS, "record_type=tree;detail=trailing_bytes");
}

dml_status dml_object_decode(const uint8_t *data, size_t len, dml_object_view *out,
                              dml_error *error) {
  if (out == NULL) return invalid(error, DML_INVALID_ARGUMENT, "object view is null");
  memset(out, 0, sizeof(*out));
  dml_status status = dml_record_validate(data, len, error);
  if (status != DML_OK) return status;
  uint16_t type = dml_read_u16_le(data + 6);
  if (type < DML_REC_NODE || type > DML_REC_COMMIT) {
    return invalid(error, DML_INVALID_KIND, "record is not a node/DAG/tree/commit");
  }
  out->record = data;
  out->record_len = len;
  out->type = (dml_record_type)type;
  if (type != DML_REC_TREE) memcpy(out->reference.bytes, data + (type == DML_REC_NODE ? 24 : 20), 16);
  if (type == DML_REC_TREE) out->count = dml_read_u32_le(data + 20);
  if (type == DML_REC_COMMIT) out->count = dml_read_u32_le(data + 36);
  return DML_OK;
}

dml_status dml_object_view_entry(const dml_object_view *view, size_t index,
                                  dml_tree_entry *out, dml_error *error) {
  if (view == NULL || out == NULL || view->type != DML_REC_TREE || index >= view->count) {
    return invalid(error, DML_INVALID_ARGUMENT, "invalid tree entry access");
  }
  size_t offset = 24;
  for (size_t i = 0; i < index; i++) offset += 20 + dml_read_u32_le(view->record + offset);
  out->name.len = dml_read_u32_le(view->record + offset);
  out->name.data = view->record + offset + 4;
  memcpy(out->dag.bytes, out->name.data + out->name.len, 16);
  return DML_OK;
}

dml_status dml_object_view_parent(const dml_object_view *view, size_t index,
                                   dml_object_id *out, dml_error *error) {
  if (view == NULL || out == NULL || view->type != DML_REC_COMMIT || index >= view->count) {
    return invalid(error, DML_INVALID_ARGUMENT, "invalid commit parent access");
  }
  memcpy(out->bytes, view->record + 40 + index * 16, 16);
  return DML_OK;
}

dml_status dml_object_encode(const dml_object_input *input, dml_buffer *out,
                              dml_error *error) {
  if (input == NULL || out == NULL || out->data != NULL || out->len != 0) {
    return invalid(error, DML_INVALID_ARGUMENT, "invalid object encode arguments");
  }
  dml_error_clear(error);
  size_t len;
  dml_tree_entry *sorted = NULL;
  switch (input->type) {
    case DML_REC_NODE:
      if (input->value.node.kind != DML_NODE_LITERAL) {
        return invalid(error, DML_INVALID_KIND, "record_type=node;detail=unsupported_kind");
      }
      len = 40;
      break;
    case DML_REC_DAG: len = 36; break;
    case DML_REC_COMMIT: {
      dml_id_array parents = input->value.commit.parents;
      if (parents.items == NULL && parents.count != 0) {
        return invalid(error, DML_INVALID_ARGUMENT, "invalid parent array");
      }
      if (!dml_size_mul(parents.count, 16, &len) || !dml_size_add(len, 40, &len) || len > UINT32_MAX) {
        return invalid(error, DML_INVALID_BOUNDS, "commit is too large");
      }
      break;
    }
    case DML_REC_TREE: {
      size_t count = input->value.tree.count;
      const dml_tree_entry *items = input->value.tree.items;
      if (items == NULL && count != 0) return invalid(error, DML_INVALID_ARGUMENT, "invalid tree array");
      if (count > (UINT32_MAX - 24) / 21) return invalid(error, DML_INVALID_BOUNDS, "tree is too large");
      len = 24;
      for (size_t i = 0; i < count; i++) {
        dml_status status = dml_name_validate(items[i].name, error);
        if (status != DML_OK) return status;
        if (!dml_size_add(len, 20 + items[i].name.len, &len) || len > UINT32_MAX) {
          return invalid(error, DML_INVALID_BOUNDS, "tree is too large");
        }
      }
      if (count != 0) {
        size_t allocation;
        if (!dml_size_mul(count, sizeof(*sorted), &allocation)) {
          return invalid(error, DML_INVALID_BOUNDS, "tree array is too large");
        }
        sorted = malloc(allocation);
        if (sorted == NULL) return invalid(error, DML_OUT_OF_MEMORY, "allocating tree entries");
        memcpy(sorted, items, allocation);
        qsort(sorted, count, sizeof(*sorted), compare_entries);
      }
      break;
    }
    default: return invalid(error, DML_INVALID_KIND, "unsupported object type");
  }
  uint8_t *data = malloc(len);
  if (data == NULL) {
    free(sorted);
    return invalid(error, DML_OUT_OF_MEMORY, "allocating object record");
  }
  dml_encode_header(data, input->type, (uint32_t)len);
  switch (input->type) {
    case DML_REC_NODE:
      dml_write_u32_le(data + 20, DML_NODE_LITERAL);
      memcpy(data + 24, input->value.node.datum.bytes, 16);
      break;
    case DML_REC_DAG: memcpy(data + 20, input->value.root.bytes, 16); break;
    case DML_REC_COMMIT:
      memcpy(data + 20, input->value.commit.tree.bytes, 16);
      dml_write_u32_le(data + 36, (uint32_t)input->value.commit.parents.count);
      if (input->value.commit.parents.count != 0) {
        memcpy(data + 40, input->value.commit.parents.items, input->value.commit.parents.count * 16);
      }
      break;
    case DML_REC_TREE: {
      size_t offset = 24;
      dml_write_u32_le(data + 20, (uint32_t)input->value.tree.count);
      for (size_t i = 0; i < input->value.tree.count; i++) {
        dml_write_u32_le(data + offset, (uint32_t)sorted[i].name.len);
        memcpy(data + offset + 4, sorted[i].name.data, sorted[i].name.len);
        memcpy(data + offset + 4 + sorted[i].name.len, sorted[i].dag.bytes, 16);
        offset += 20 + sorted[i].name.len;
      }
      break;
    }
    default: break; /* Type checked above. */
  }
  free(sorted);
  dml_status status = dml_validate_object(data, len, input->type, error);
  if (status != DML_OK) {
    free(data);
    return status;
  }
  out->data = data;
  out->len = len;
  return DML_OK;
}
