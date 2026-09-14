#include <stdlib.h>
#include <string.h>

#include <xxhash.h>

#include "dml/record.h"
#include "error_internal.h"

dml_status dml_datum_id(const uint8_t *data, size_t len, dml_object_id *out,
                        dml_error *error) {
  uint8_t *masked;
  XXH128_canonical_t canonical;
  dml_status status;
  if (out == NULL) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "object id output is null");
  }
  status = dml_record_validate(data, len, error);
  if (status != DML_OK) {
    return status;
  }
  if (len < 8 || data[6] != DML_REC_DATUM || data[7] != 0) {
    return dml_set_error(error, DML_INVALID_KIND, 0,
                         "record_type=datum;detail=record_type");
  }
  masked = malloc(len);
  if (masked == NULL) {
    return dml_set_error(error, DML_OUT_OF_MEMORY, 0, "allocating hash domain");
  }
  memcpy(masked, data, len);
  memset(masked, 0, 4);
  memset(masked + 8, 0, 4);
  memset(masked + 16, 0, 4);
  XXH128_canonicalFromHash(&canonical, XXH3_128bits(masked, len));
  free(masked);
  memcpy(out->bytes, canonical.digest, DML_OBJECT_ID_SIZE);
  return DML_OK;
}

dml_status dml_object_id_format(const dml_object_id *id,
                                char out[DML_OBJECT_ID_HEX_SIZE + 1],
                                dml_error *error) {
  static const char hex[] = "0123456789abcdef";
  if (id == NULL || out == NULL) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "invalid object id format arguments");
  }
  for (size_t i = 0; i < DML_OBJECT_ID_SIZE; i++) {
    out[i * 2] = hex[id->bytes[i] >> 4];
    out[i * 2 + 1] = hex[id->bytes[i] & 15];
  }
  out[DML_OBJECT_ID_HEX_SIZE] = '\0';
  return DML_OK;
}

dml_status dml_object_id_parse(const char *text, size_t len, dml_object_id *out,
                               dml_error *error) {
  if (text == NULL || out == NULL || len != DML_OBJECT_ID_HEX_SIZE) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "object id must be 32 lowercase hex bytes");
  }
  for (size_t i = 0; i < DML_OBJECT_ID_SIZE; i++) {
    unsigned char high = (unsigned char)text[i * 2];
    unsigned char low = (unsigned char)text[i * 2 + 1];
    if (!((high >= '0' && high <= '9') || (high >= 'a' && high <= 'f')) ||
        !((low >= '0' && low <= '9') || (low >= 'a' && low <= 'f'))) {
      return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "object id must be 32 lowercase hex bytes");
    }
    high = high <= '9' ? high - '0' : high - 'a' + 10;
    low = low <= '9' ? low - '0' : low - 'a' + 10;
    out->bytes[i] = (uint8_t)((high << 4) | low);
  }
  return DML_OK;
}
