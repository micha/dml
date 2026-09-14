#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include <uriparser/Uri.h>

#include "dml/record.h"
#include "error_internal.h"

static int ascii_equal_ci(const char *first, const char *last, const char *text) {
  size_t len = (size_t)(last - first);
  if (strlen(text) != len) {
    return 0;
  }
  for (size_t i = 0; i < len; i++) {
    unsigned char value = (unsigned char)first[i];
    if (value >= 'A' && value <= 'Z') {
      value = (unsigned char)(value + ('a' - 'A'));
    }
    if (value != (unsigned char)text[i]) {
      return 0;
    }
  }
  return 1;
}

static int hex_value(uint8_t value) {
  if (value >= '0' && value <= '9') return value - '0';
  if (value >= 'A' && value <= 'F') return value - 'A' + 10;
  if (value >= 'a' && value <= 'f') return value - 'a' + 10;
  return -1;
}

static int is_unreserved(uint8_t value) {
  return (value >= 'A' && value <= 'Z') || (value >= 'a' && value <= 'z') ||
         (value >= '0' && value <= '9') || value == '-' || value == '.' ||
         value == '_' || value == '~';
}

static dml_status normalize_escapes(const uint8_t *data, size_t len,
                                    char **out, size_t *out_len,
                                    dml_error *error) {
  static const char hex[] = "0123456789ABCDEF";
  char *result = malloc(len + 1);
  size_t written = 0;
  if (result == NULL) {
    return dml_set_error(error, DML_OUT_OF_MEMORY, 0, "allocating URI input");
  }
  for (size_t i = 0; i < len; i++) {
    if (data[i] != '%') {
      result[written++] = (char)data[i];
      continue;
    }
    if (len - i < 3 || hex_value(data[i + 1]) < 0 || hex_value(data[i + 2]) < 0) {
      free(result);
      return dml_set_error(error, DML_INVALID_PAYLOAD, 0,
                           "record_type=datum;detail=uri_syntax");
    }
    uint8_t decoded = (uint8_t)((hex_value(data[i + 1]) << 4) | hex_value(data[i + 2]));
    if (is_unreserved(decoded)) {
      result[written++] = (char)decoded;
    } else {
      result[written++] = '%';
      result[written++] = hex[decoded >> 4];
      result[written++] = hex[decoded & 15];
    }
    i += 2;
  }
  result[written] = '\0';
  *out = result;
  *out_len = written;
  return DML_OK;
}

dml_status dml_uri_canonicalize(const uint8_t *data, size_t len, dml_buffer *out,
                                dml_error *error) {
  UriUriA uri;
  const char *error_pos = NULL;
  char *normalized_input = NULL;
  size_t normalized_len = 0;
  char *result = NULL;
  int chars_required;
  int chars_written;
  int status;
  unsigned int normalization_mask;
  dml_status dml_result;

  if (out == NULL || out->data != NULL || out->len != 0 ||
      (data == NULL && len != 0)) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "invalid URI arguments");
  }
  out->data = NULL;
  out->len = 0;
  dml_error_clear(error);
  if (len == 0 || len > (size_t)PTRDIFF_MAX) {
    return dml_set_error(error, DML_INVALID_PAYLOAD, 0,
                         "record_type=datum;detail=uri_not_absolute");
  }
  for (size_t i = 0; i < len; i++) {
    if (data[i] == 0 || data[i] > 0x7f) {
      return dml_set_error(error, DML_INVALID_PAYLOAD, 0,
                           "record_type=datum;detail=uri_not_ascii");
    }
  }
  dml_result = normalize_escapes(data, len, &normalized_input, &normalized_len,
                                 error);
  if (dml_result != DML_OK) return dml_result;
  status = uriParseSingleUriExA(&uri, normalized_input,
                                normalized_input + normalized_len, &error_pos);
  if (status != URI_SUCCESS) {
    free(normalized_input);
    return dml_set_error(error, DML_INVALID_PAYLOAD, status,
                         "record_type=datum;detail=uri_syntax");
  }
  if (uri.scheme.first == NULL || uri.scheme.first == uri.scheme.afterLast) {
    uriFreeUriMembersA(&uri);
    free(normalized_input);
    return dml_set_error(error, DML_INVALID_PAYLOAD, 0,
                         "record_type=datum;detail=uri_not_absolute");
  }
  if (ascii_equal_ci(uri.scheme.first, uri.scheme.afterLast, "dml")) {
    uriFreeUriMembersA(&uri);
    free(normalized_input);
    return dml_set_error(error, DML_INVALID_PAYLOAD, 0,
                         "record_type=datum;detail=uri_reserved_scheme");
  }
  normalization_mask = URI_NORMALIZE_SCHEME | URI_NORMALIZE_USER_INFO |
                       URI_NORMALIZE_HOST | URI_NORMALIZE_QUERY |
                       URI_NORMALIZE_FRAGMENT;
  if (uri.hostText.first != NULL || uri.absolutePath) {
    normalization_mask |= URI_NORMALIZE_PATH;
  }
  status = uriNormalizeSyntaxExA(&uri, normalization_mask);
  if (status != URI_SUCCESS ||
      uriToStringCharsRequiredA(&uri, &chars_required) != URI_SUCCESS ||
      chars_required < 0) {
    uriFreeUriMembersA(&uri);
    free(normalized_input);
    return dml_set_error(error, status == URI_ERROR_MALLOC ? DML_OUT_OF_MEMORY
                                                           : DML_INVALID_PAYLOAD,
                         status, "record_type=datum;detail=uri_normalization");
  }
  result = malloc((size_t)chars_required + 1);
  if (result == NULL) {
    uriFreeUriMembersA(&uri);
    free(normalized_input);
    return dml_set_error(error, DML_OUT_OF_MEMORY, 0, "allocating canonical URI");
  }
  status = uriToStringA(result, &uri, chars_required + 1, &chars_written);
  uriFreeUriMembersA(&uri);
  free(normalized_input);
  if (status != URI_SUCCESS) {
    free(result);
    return dml_set_error(error, DML_INVALID_PAYLOAD, status,
                         "record_type=datum;detail=uri_serialization");
  }
  out->data = (uint8_t *)result;
  out->len = (size_t)chars_required;
  return DML_OK;
}
