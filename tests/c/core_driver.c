#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "dml/dml.h"

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

static int fail(dml_status status, const dml_error *error) {
  fprintf(stderr, "%s: %s\n", dml_status_name(status),
          error == NULL ? "" : error->detail);
  return 1;
}

static int read_all(dml_buffer *buffer) {
  size_t capacity = 4096;
  buffer->data = malloc(capacity);
  buffer->len = 0;
  if (buffer->data == NULL) return 0;
  for (;;) {
    size_t count;
    if (buffer->len == capacity) {
      uint8_t *larger;
      capacity *= 2;
      larger = realloc(buffer->data, capacity);
      if (larger == NULL) return 0;
      buffer->data = larger;
    }
    count = fread(buffer->data + buffer->len, 1, capacity - buffer->len, stdin);
    buffer->len += count;
    if (count == 0) return !ferror(stdin);
  }
}

static int write_buffer(const dml_buffer *buffer) {
  return fwrite(buffer->data, 1, buffer->len, stdout) == buffer->len ? 0 : 1;
}

static uint64_t read_u64(const uint8_t *data) {
  uint64_t value = 0;
  for (unsigned int i = 0; i < 8; i++) value |= (uint64_t)data[i] << (i * 8);
  return value;
}

static int command_encode(const char *kind_text) {
  dml_buffer input_bytes = {0};
  dml_buffer record = {0};
  dml_datum_input input = {0};
  dml_error error;
  dml_status status;
  long kind = strtol(kind_text, NULL, 10);
  if (!read_all(&input_bytes)) return 1;
  input.kind = (dml_datum_kind)kind;
  if (kind == DML_DATUM_BOOL) {
    if (input_bytes.len != 1) return 2;
    input.value.boolean = input_bytes.data[0] != 0;
  } else if (kind == DML_DATUM_I64 || kind == DML_DATUM_F64) {
    uint64_t bits;
    if (input_bytes.len != 8) return 2;
    bits = read_u64(input_bytes.data);
    if (kind == DML_DATUM_I64) input.value.i64 = (int64_t)bits;
    else memcpy(&input.value.f64, &bits, 8);
  } else if (kind == DML_DATUM_LIST || kind == DML_DATUM_SET) {
    if (input_bytes.len % 16 != 0) return 2;
    input.value.ids.items = (const dml_object_id *)input_bytes.data;
    input.value.ids.count = input_bytes.len / 16;
  } else if (kind == DML_DATUM_MAP) {
    if (input_bytes.len % 32 != 0) return 2;
    input.value.map.items = (const dml_datum_map_entry *)input_bytes.data;
    input.value.map.count = input_bytes.len / 32;
  } else {
    input.value.bytes.data = input_bytes.data;
    input.value.bytes.len = input_bytes.len;
  }
  status = dml_datum_encode(&input, &record, &error);
  free(input_bytes.data);
  if (status != DML_OK) return fail(status, &error);
  int result = write_buffer(&record);
  dml_buffer_free(&record);
  return result;
}

static int command_record(const char *command) {
  dml_buffer record = {0};
  dml_error error;
  dml_status status;
  if (!read_all(&record)) return 1;
  if (strcmp(command, "validate") == 0) {
    status = dml_record_validate(record.data, record.len, &error);
    free(record.data);
    return status == DML_OK ? 0 : fail(status, &error);
  }
  if (strcmp(command, "decode") == 0) {
    dml_datum_view view;
    status = dml_datum_decode(record.data, record.len, &view, &error);
    free(record.data);
    if (status != DML_OK) return fail(status, &error);
    printf("%u %zu %zu\n", (unsigned int)view.kind, view.count, view.payload_len);
    return 0;
  }
  dml_object_id id;
  char hex[33];
  status = dml_datum_id(record.data, record.len, &id, &error);
  free(record.data);
  if (status != DML_OK) return fail(status, &error);
  (void)dml_object_id_format(&id, hex, NULL);
  puts(hex);
  return 0;
}

static int command_uri(void) {
  dml_buffer input = {0};
  dml_buffer output = {0};
  dml_error error;
  dml_status status;
  if (!read_all(&input)) return 1;
  status = dml_uri_canonicalize(input.data, input.len, &output, &error);
  free(input.data);
  if (status != DML_OK) return fail(status, &error);
  int result = write_buffer(&output);
  dml_buffer_free(&output);
  return result;
}

static int command_repo_init(const char *path) {
  dml_repo_options options = {true, 0};
  dml_repo *repo = NULL;
  dml_error error;
  dml_status status = dml_repo_open(path, &options, &repo, &error);
  if (status != DML_OK) return fail(status, &error);
  return dml_repo_close(&repo, &error) == DML_OK ? 0 : 1;
}

static int command_repo_get(const char *path, const char *hex) {
  dml_repo_options options = {false, 0};
  dml_object_id id;
  dml_repo *repo = NULL;
  dml_txn *txn = NULL;
  dml_buffer record = {0};
  dml_error error;
  dml_status status = dml_object_id_parse(hex, strlen(hex), &id, &error);
  if (status == DML_OK) status = dml_repo_open(path, &options, &repo, &error);
  if (status == DML_OK) status = dml_txn_begin(repo, DML_TXN_READ, &txn, &error);
  if (status == DML_OK) status = dml_txn_get_datum(txn, &id, &record, &error);
  if (status != DML_OK) {
    dml_txn_abort(&txn);
    if (repo != NULL) (void)dml_repo_close(&repo, NULL);
    return fail(status, &error);
  }
  int result = write_buffer(&record);
  dml_buffer_free(&record);
  dml_txn_abort(&txn);
  (void)dml_repo_close(&repo, NULL);
  return result;
}

static uint32_t read_u32(const uint8_t *data) {
  return (uint32_t)data[0] | ((uint32_t)data[1] << 8) |
         ((uint32_t)data[2] << 16) | ((uint32_t)data[3] << 24);
}

static int command_repo_put_batch(const char *path, int commit) {
  dml_repo_options options = {false, 0};
  dml_repo *repo = NULL;
  dml_txn *txn = NULL;
  dml_buffer framed = {0};
  dml_error error;
  dml_status status = dml_repo_open(path, &options, &repo, &error);
  size_t offset = 0;
  if (status == DML_OK) status = dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error);
  if (status == DML_OK && !read_all(&framed)) status = DML_STORAGE_ERROR;
  while (status == DML_OK && offset < framed.len) {
    dml_object_id id;
    char hex[33];
    uint32_t len;
    if (framed.len - offset < 4) {
      status = DML_INVALID_BOUNDS;
      error.code = status;
      (void)snprintf(error.detail, sizeof(error.detail), "truncated batch frame");
      break;
    }
    len = read_u32(framed.data + offset);
    offset += 4;
    if (len > framed.len - offset) {
      status = DML_INVALID_BOUNDS;
      error.code = status;
      (void)snprintf(error.detail, sizeof(error.detail), "truncated batch record");
      break;
    }
    status = dml_txn_put_datum(txn, framed.data + offset, len, &id, &error);
    offset += len;
    if (status == DML_OK) {
      (void)dml_object_id_format(&id, hex, NULL);
      puts(hex);
    }
  }
  free(framed.data);
  if (status == DML_OK && commit) status = dml_txn_commit(&txn, &error);
  else dml_txn_abort(&txn);
  if (repo != NULL) (void)dml_repo_close(&repo, NULL);
  return status == DML_OK ? 0 : fail(status, &error);
}

int main(int argc, char **argv) {
#ifdef _WIN32
  (void)_setmode(_fileno(stdin), _O_BINARY);
  (void)_setmode(_fileno(stdout), _O_BINARY);
#endif
  if (argc == 3 && strcmp(argv[1], "encode") == 0) return command_encode(argv[2]);
  if (argc == 2 && (strcmp(argv[1], "validate") == 0 || strcmp(argv[1], "decode") == 0 ||
                    strcmp(argv[1], "id") == 0))
    return command_record(argv[1]);
  if (argc == 2 && strcmp(argv[1], "normalize-uri") == 0) return command_uri();
  if (argc == 3 && strcmp(argv[1], "repo-init") == 0) return command_repo_init(argv[2]);
  if (argc == 4 && strcmp(argv[1], "repo-get") == 0) return command_repo_get(argv[2], argv[3]);
  if (argc == 4 && strcmp(argv[1], "repo-put-batch") == 0 &&
      (strcmp(argv[3], "commit") == 0 || strcmp(argv[3], "abort") == 0))
    return command_repo_put_batch(argv[2], strcmp(argv[3], "commit") == 0);
  fprintf(stderr,
          "usage: test_core_driver "
          "<encode|validate|decode|id|normalize-uri|repo-init|repo-put-batch|repo-get> ...\n");
  return 2;
}
