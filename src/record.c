#include <float.h>
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "dml/record.h"
#include "encoding.h"
#include "error_internal.h"
#include "record_internal.h"

_Static_assert(sizeof(double) == 8, "DML requires IEEE-754 binary64 storage");
_Static_assert(FLT_RADIX == 2 && DBL_MANT_DIG == 53 && DBL_MAX_EXP == 1024,
               "DML requires IEEE-754 binary64");

dml_status dml_text_normalize(const uint8_t *data, size_t len, dml_buffer *out,
                              dml_error *error);

void dml_encode_header(uint8_t *data, uint16_t type, uint32_t len) {
  dml_write_u32_le(data, 0x314c4d44u);
  dml_write_u16_le(data + 4, DML_RECORD_VERSION);
  dml_write_u16_le(data + 6, type);
  dml_write_u32_le(data + 8, len);
  dml_write_u32_le(data + 12, 0);
  dml_write_u32_le(data + 16, 0);
}

dml_status dml_validate_envelope(const uint8_t *data, size_t len,
                                 uint16_t *type, dml_error *error) {
  if (data == NULL && len != 0) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "invalid record span");
  }
  if (len < DML_HEADER_SIZE || len > UINT32_MAX) {
    return dml_set_error(error, DML_INVALID_HEADER, 0,
                         "record_type=unknown;detail=header_size");
  }
  if (dml_read_u32_le(data) != 0x314c4d44u) {
    return dml_set_error(error, DML_INVALID_HEADER, 0,
                         "record_type=unknown;detail=magic");
  }
  if (dml_read_u16_le(data + 4) != DML_RECORD_VERSION) {
    return dml_set_error(error, DML_INVALID_HEADER, 0,
                         "record_type=unknown;detail=version");
  }
  if (dml_read_u32_le(data + 8) != len) {
    return dml_set_error(error, DML_INVALID_HEADER, 0,
                         "record_type=unknown;detail=total_len");
  }
  if (dml_read_u32_le(data + 12) != 0 || dml_read_u32_le(data + 16) != 0) {
    return dml_set_error(error, DML_INVALID_HEADER, 0,
                         "record_type=unknown;detail=reserved_header");
  }
  *type = dml_read_u16_le(data + 6);
  return DML_OK;
}

void dml_encode_meta(uint8_t out[DML_META_SIZE]) {
  dml_encode_header(out, DML_REC_META, DML_META_SIZE);
  dml_write_u32_le(out + DML_HEADER_SIZE, DML_SCHEMA_VERSION);
}

static dml_status validate_text(const uint8_t *data, size_t len,
                                dml_error *error) {
  dml_buffer normalized = {0};
  dml_status status = dml_text_normalize(data, len, &normalized, error);
  if (status != DML_OK) {
    return status;
  }
  if (normalized.len != len || (len != 0 && memcmp(normalized.data, data, len) != 0)) {
    dml_buffer_free(&normalized);
    return dml_set_error(error, DML_INVALID_PAYLOAD, 0,
                         "record_type=datum;detail=string_not_nfc");
  }
  dml_buffer_free(&normalized);
  return DML_OK;
}

static dml_status validate_composite(uint32_t kind, const uint8_t *payload,
                                     size_t payload_len, size_t *count,
                                     dml_error *error) {
  size_t width = kind == DML_DATUM_MAP ? 32 : 16;
  if (payload_len < 4) {
    return dml_set_error(error, DML_INVALID_BOUNDS, 0,
                         kind == DML_DATUM_LIST
                             ? "record_type=datum;detail=list_payload_too_short"
                             : kind == DML_DATUM_SET
                                   ? "record_type=datum;detail=set_payload_too_short"
                                   : "record_type=datum;detail=map_payload_too_short");
  }
  *count = dml_read_u32_le(payload);
  if (*count > (payload_len - 4) / width || payload_len - 4 != *count * width) {
    return dml_set_error(error, DML_INVALID_BOUNDS, 0,
                         kind == DML_DATUM_LIST
                             ? "record_type=datum;detail=list_count_mismatch"
                             : kind == DML_DATUM_SET
                                   ? "record_type=datum;detail=set_count_mismatch"
                                   : "record_type=datum;detail=map_count_mismatch");
  }
  if (kind != DML_DATUM_LIST) {
    size_t stride = width;
    for (size_t i = 1; i < *count; i++) {
      if (memcmp(payload + 4 + (i - 1) * stride,
                 payload + 4 + i * stride, DML_OBJECT_ID_SIZE) >= 0) {
        return dml_set_error(error, DML_INVALID_PAYLOAD, 0,
                             kind == DML_DATUM_SET
                                 ? "record_type=datum;detail=set_not_strictly_sorted"
                                 : "record_type=datum;detail=map_keys_not_strictly_sorted");
      }
    }
  }
  return DML_OK;
}

static dml_status validate_datum(const uint8_t *data, size_t len,
                                 dml_datum_view *view, dml_error *error) {
  uint32_t kind;
  uint64_t payload_len;
  uint64_t payload_ofs;
  size_t count = 0;
  dml_status status;

  if (len < DML_DATUM_PREFIX_SIZE) {
    return dml_set_error(error, DML_INVALID_BOUNDS, 0,
                         "record_type=datum;detail=prefix_too_short");
  }
  kind = dml_read_u32_le(data + 20);
  payload_len = dml_read_u64_le(data + 24);
  payload_ofs = dml_read_u64_le(data + 32);
  if (payload_ofs != DML_DATUM_PREFIX_SIZE || payload_len != len - DML_DATUM_PREFIX_SIZE) {
    return dml_set_error(error, DML_INVALID_BOUNDS, 0,
                         "record_type=datum;detail=payload_bounds");
  }
  if (kind < DML_DATUM_NULL || kind > DML_DATUM_MAP) {
    return dml_set_error(error, DML_INVALID_KIND, 0,
                         "record_type=datum;detail=kind");
  }
  const uint8_t *payload = data + DML_DATUM_PREFIX_SIZE;
  if (kind == DML_DATUM_NULL && payload_len != 0) {
    return dml_set_error(error, DML_INVALID_PAYLOAD, 0,
                         "record_type=datum;detail=null_payload");
  }
  if (kind == DML_DATUM_BOOL &&
      (payload_len != 1 || (payload[0] != 0 && payload[0] != 1))) {
    return dml_set_error(error, DML_INVALID_PAYLOAD, 0,
                         "record_type=datum;detail=bool_payload");
  }
  if (kind == DML_DATUM_I64 && payload_len != 8) {
    return dml_set_error(error, DML_INVALID_PAYLOAD, 0,
                         "record_type=datum;detail=i64_payload");
  }
  if (kind == DML_DATUM_F64) {
    if (payload_len != 8) {
      return dml_set_error(error, DML_INVALID_PAYLOAD, 0,
                           "record_type=datum;detail=f64_payload");
    }
    uint64_t bits = dml_read_u64_le(payload);
    if (bits == UINT64_C(0x8000000000000000) ||
        (((bits >> 52) & 0x7ff) == 0x7ff && (bits & UINT64_C(0xfffffffffffff)) != 0 &&
         bits != UINT64_C(0x7ff8000000000000))) {
      return dml_set_error(error, DML_INVALID_PAYLOAD, 0,
                           "record_type=datum;detail=f64_noncanonical");
    }
  }
  if (kind == DML_DATUM_STRING &&
      (status = validate_text(payload, (size_t)payload_len, error)) != DML_OK) {
    return status;
  }
  if (kind == DML_DATUM_URI) {
    dml_buffer canonical = {0};
    status = dml_uri_canonicalize(payload, (size_t)payload_len, &canonical, error);
    if (status != DML_OK) {
      return status;
    }
    if (canonical.len != payload_len || memcmp(canonical.data, payload, canonical.len) != 0) {
      dml_buffer_free(&canonical);
      return dml_set_error(error, DML_INVALID_PAYLOAD, 0,
                           "record_type=datum;detail=uri_not_canonical");
    }
    dml_buffer_free(&canonical);
  }
  if (kind >= DML_DATUM_LIST) {
    status = validate_composite(kind, payload, (size_t)payload_len, &count, error);
    if (status != DML_OK) {
      return status;
    }
  }
  if (view != NULL) {
    view->record = data;
    view->record_len = len;
    view->payload = payload;
    view->payload_len = (size_t)payload_len;
    view->kind = (dml_datum_kind)kind;
    view->count = count;
  }
  return DML_OK;
}

dml_status dml_record_validate(const uint8_t *data, size_t len, dml_error *error) {
  uint16_t type;
  dml_status status;
  dml_error_clear(error);
  status = dml_validate_envelope(data, len, &type, error);
  if (status != DML_OK) {
    return status;
  }
  if (type == DML_REC_META) {
    if (len != DML_META_SIZE) {
      return dml_set_error(error, DML_INVALID_BOUNDS, 0,
                           "record_type=meta;detail=record_size");
    }
    if (dml_read_u32_le(data + 20) != DML_SCHEMA_VERSION) {
      return dml_set_error(error, DML_UNSUPPORTED_SCHEMA, 0,
                           "record_type=meta;detail=schema_version");
    }
    return DML_OK;
  }
  if (type == DML_REC_DATUM) {
    return validate_datum(data, len, NULL, error);
  }
  if (type >= DML_REC_NODE && type <= DML_REC_COMMIT) {
    return dml_validate_object(data, len, type, error);
  }
  return dml_set_error(error, DML_INVALID_KIND, 0,
                       "record_type=unknown;detail=unsupported_type");
}

dml_status dml_datum_decode(const uint8_t *data, size_t len, dml_datum_view *out,
                            dml_error *error) {
  uint16_t type;
  dml_status status;
  if (out == NULL) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "datum view is null");
  }
  memset(out, 0, sizeof(*out));
  dml_error_clear(error);
  status = dml_validate_envelope(data, len, &type, error);
  if (status != DML_OK) {
    return status;
  }
  if (type != DML_REC_DATUM) {
    return dml_set_error(error, DML_INVALID_KIND, 0,
                         "record_type=datum;detail=record_type");
  }
  return validate_datum(data, len, out, error);
}

static int compare_ids(const void *left, const void *right) {
  return memcmp(left, right, DML_OBJECT_ID_SIZE);
}

static int compare_map_entries(const void *left, const void *right) {
  return memcmp(left, right, DML_OBJECT_ID_SIZE);
}

dml_status dml_datum_encode(const dml_datum_input *input, dml_buffer *out,
                            dml_error *error) {
  dml_buffer normalized = {0};
  size_t payload_len = 0;
  size_t total_len;
  uint8_t *record;

  if (input == NULL || out == NULL || out->data != NULL || out->len != 0) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "invalid datum arguments");
  }
  out->data = NULL;
  out->len = 0;
  dml_error_clear(error);
  if (input->kind < DML_DATUM_NULL || input->kind > DML_DATUM_MAP) {
    return dml_set_error(error, DML_INVALID_KIND, 0,
                         "record_type=datum;detail=kind");
  }
  switch (input->kind) {
    case DML_DATUM_NULL: payload_len = 0; break;
    case DML_DATUM_BOOL: payload_len = 1; break;
    case DML_DATUM_I64:
    case DML_DATUM_F64: payload_len = 8; break;
    case DML_DATUM_BYTES:
      if (input->value.bytes.data == NULL && input->value.bytes.len != 0) {
        return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "invalid byte span");
      }
      payload_len = input->value.bytes.len;
      break;
    case DML_DATUM_STRING:
      if (input->value.bytes.data == NULL && input->value.bytes.len != 0) {
        return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "invalid string span");
      }
      {
        dml_status status = dml_text_normalize(input->value.bytes.data,
                                               input->value.bytes.len,
                                               &normalized, error);
        if (status != DML_OK) return status;
      }
      payload_len = normalized.len;
      break;
    case DML_DATUM_URI:
      {
        dml_status status = dml_uri_canonicalize(input->value.bytes.data,
                                                 input->value.bytes.len,
                                                 &normalized, error);
        if (status != DML_OK) return status;
      }
      if (normalized.len != input->value.bytes.len ||
          memcmp(normalized.data, input->value.bytes.data, normalized.len) != 0) {
        dml_buffer_free(&normalized);
        return dml_set_error(error, DML_INVALID_PAYLOAD, 0,
                             "record_type=datum;detail=uri_not_canonical");
      }
      payload_len = normalized.len;
      break;
    case DML_DATUM_LIST:
    case DML_DATUM_SET:
      if (input->value.ids.items == NULL && input->value.ids.count != 0) {
        return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "invalid id array");
      }
      if (!dml_size_mul(input->value.ids.count, 16, &payload_len) ||
          !dml_size_add(payload_len, 4, &payload_len) || input->value.ids.count > UINT32_MAX) {
        return dml_set_error(error, DML_INVALID_BOUNDS, 0, "datum collection too large");
      }
      break;
    case DML_DATUM_MAP:
      if (input->value.map.items == NULL && input->value.map.count != 0) {
        return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "invalid map array");
      }
      if (!dml_size_mul(input->value.map.count, 32, &payload_len) ||
          !dml_size_add(payload_len, 4, &payload_len) || input->value.map.count > UINT32_MAX) {
        return dml_set_error(error, DML_INVALID_BOUNDS, 0, "datum map too large");
      }
      break;
  }
  if (!dml_size_add(DML_DATUM_PREFIX_SIZE, payload_len, &total_len) ||
      total_len > UINT32_MAX) {
    dml_buffer_free(&normalized);
    return dml_set_error(error, DML_INVALID_BOUNDS, 0, "datum record too large");
  }
  record = malloc(total_len);
  if (record == NULL) {
    dml_buffer_free(&normalized);
    return dml_set_error(error, DML_OUT_OF_MEMORY, 0, "allocating datum record");
  }
  dml_encode_header(record, DML_REC_DATUM, (uint32_t)total_len);
  dml_write_u32_le(record + 20, input->kind);
  dml_write_u64_le(record + 24, payload_len);
  dml_write_u64_le(record + 32, DML_DATUM_PREFIX_SIZE);
  uint8_t *payload = record + DML_DATUM_PREFIX_SIZE;
  switch (input->kind) {
    case DML_DATUM_NULL: break;
    case DML_DATUM_BOOL: payload[0] = input->value.boolean ? 1 : 0; break;
    case DML_DATUM_I64: dml_write_u64_le(payload, (uint64_t)input->value.i64); break;
    case DML_DATUM_F64: {
      uint64_t bits;
      memcpy(&bits, &input->value.f64, 8);
      if (isnan(input->value.f64)) bits = UINT64_C(0x7ff8000000000000);
      if (bits == UINT64_C(0x8000000000000000)) bits = 0;
      dml_write_u64_le(payload, bits);
      break;
    }
    case DML_DATUM_BYTES:
      if (payload_len != 0) memcpy(payload, input->value.bytes.data, payload_len);
      break;
    case DML_DATUM_STRING:
    case DML_DATUM_URI:
      if (payload_len != 0) memcpy(payload, normalized.data, payload_len);
      break;
    case DML_DATUM_LIST:
    case DML_DATUM_SET:
      dml_write_u32_le(payload, (uint32_t)input->value.ids.count);
      if (input->value.ids.count != 0) {
        memcpy(payload + 4, input->value.ids.items, input->value.ids.count * 16);
        if (input->kind == DML_DATUM_SET) {
          qsort(payload + 4, input->value.ids.count, 16, compare_ids);
        }
      }
      break;
    case DML_DATUM_MAP:
      dml_write_u32_le(payload, (uint32_t)input->value.map.count);
      if (input->value.map.count != 0) {
        memcpy(payload + 4, input->value.map.items, input->value.map.count * 32);
        qsort(payload + 4, input->value.map.count, 32, compare_map_entries);
      }
      break;
  }
  dml_buffer_free(&normalized);
  dml_status status = validate_datum(record, total_len, NULL, error);
  if (status != DML_OK) {
    free(record);
    return status;
  }
  out->data = record;
  out->len = total_len;
  return DML_OK;
}

dml_status dml_datum_view_id(const dml_datum_view *view, size_t index,
                             dml_object_id *out, dml_error *error) {
  if (view == NULL || out == NULL ||
      (view->kind != DML_DATUM_LIST && view->kind != DML_DATUM_SET) ||
      index >= view->count) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "invalid datum id access");
  }
  memcpy(out->bytes, view->payload + 4 + index * 16, 16);
  return DML_OK;
}

dml_status dml_datum_view_map_entry(const dml_datum_view *view, size_t index,
                                    dml_datum_map_entry *out, dml_error *error) {
  if (view == NULL || out == NULL || view->kind != DML_DATUM_MAP || index >= view->count) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "invalid datum map access");
  }
  memcpy(out, view->payload + 4 + index * 32, 32);
  return DML_OK;
}

void dml_buffer_free(dml_buffer *buffer) {
  if (buffer == NULL) {
    return;
  }
  free(buffer->data);
  buffer->data = NULL;
  buffer->len = 0;
}
