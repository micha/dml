#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <lmdb.h>

#include "dml/dml.h"

#ifdef _WIN32
#include <direct.h>
#define dml_rmdir _rmdir
#else
#include <unistd.h>
#define dml_rmdir rmdir
#endif

#define CHECK(condition)                                                        \
  do {                                                                          \
    if (!(condition)) {                                                         \
      fprintf(stderr, "check failed at %s:%d: %s\n", __FILE__, __LINE__,      \
              #condition);                                                      \
      return 1;                                                                 \
    }                                                                           \
  } while (0)

static const char *repo_path = "test-repository-data";

static void cleanup(void) {
  char path[128];
  (void)snprintf(path, sizeof(path), "%s/data.mdb", repo_path);
  (void)remove(path);
  (void)snprintf(path, sizeof(path), "%s/lock.mdb", repo_path);
  (void)remove(path);
  (void)dml_rmdir(repo_path);
}

static int raw_write(const char *key_text, const void *data, size_t len, int clear) {
  MDB_env *env = NULL;
  MDB_txn *txn = NULL;
  MDB_dbi dbi;
  MDB_val key = {strlen(key_text), (void *)key_text};
  MDB_val value = {len, (void *)data};
  int code = mdb_env_create(&env);
  if (code == MDB_SUCCESS) code = mdb_env_set_mapsize(env, 4 * 1024 * 1024);
  if (code == MDB_SUCCESS) code = mdb_env_open(env, repo_path, 0, 0664);
  if (code == MDB_SUCCESS) code = mdb_txn_begin(env, NULL, 0, &txn);
  if (code == MDB_SUCCESS) code = mdb_dbi_open(txn, NULL, 0, &dbi);
  if (code == MDB_SUCCESS && clear) code = mdb_drop(txn, dbi, 0);
  if (code == MDB_SUCCESS && !clear) code = mdb_put(txn, dbi, &key, &value, 0);
  if (txn != NULL) {
    if (code == MDB_SUCCESS) code = mdb_txn_commit(txn);
    else mdb_txn_abort(txn);
  }
  if (env != NULL) mdb_env_close(env);
  return code;
}

static void write_u16(uint8_t *data, uint16_t value) {
  data[0] = (uint8_t)value;
  data[1] = (uint8_t)(value >> 8);
}

static void write_u32(uint8_t *data, uint32_t value) {
  for (unsigned int i = 0; i < 4; i++) data[i] = (uint8_t)(value >> (i * 8));
}

static void write_u64(uint8_t *data, uint64_t value) {
  for (unsigned int i = 0; i < 8; i++) data[i] = (uint8_t)(value >> (i * 8));
}

static void tombstone(uint8_t *data, size_t len) {
  memset(data, 0, len);
  write_u32(data, 0x314c4d44u);
  write_u16(data + 4, 1);
  write_u16(data + 6, DML_REC_TOMBSTONE);
  write_u32(data + 8, (uint32_t)len);
  if (len >= 36) {
    write_u32(data + 20, 1);
    write_u64(data + 24, 36);
  }
}

int main(void) {
  dml_repo_options create = {true, 4 * 1024 * 1024};
  dml_repo_options open = {false, 4 * 1024 * 1024};
  dml_repo *repo = NULL;
  dml_txn *txn = NULL;
  dml_error error;
  dml_buffer scalar = {0};
  dml_buffer list = {0};
  dml_buffer fetched = {0};
  dml_datum_input input = {.kind = DML_DATUM_I64, .value.i64 = 42};
  dml_object_id scalar_id;
  dml_object_id list_id;
  dml_object_id missing = {{99}};
  char scalar_key[48] = "objects/datums/";
  uint32_t schema;

  cleanup();
  CHECK(dml_repo_open(repo_path, &open, &repo, &error) == DML_NOT_FOUND);
  CHECK(dml_repo_open(repo_path, &create, &repo, &error) == DML_OK);
  CHECK(dml_repo_schema(repo, &schema, &error) == DML_OK && schema == 1);
  CHECK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error) == DML_OK);
  dml_bytes lookup_name = {(const uint8_t *)"a", 1};
  CHECK(dml_txn_lookup_node(NULL, &missing, lookup_name, &list_id, NULL) == DML_INVALID_ARGUMENT);
  CHECK(dml_txn_lookup_node(txn, NULL, lookup_name, &list_id, NULL) == DML_INVALID_ARGUMENT);
  CHECK(dml_txn_lookup_node(txn, &missing, lookup_name, NULL, NULL) == DML_INVALID_ARGUMENT);
  CHECK(dml_txn_lookup_node(txn, &missing, (dml_bytes){NULL, 0}, &list_id, NULL) == DML_INVALID_ARGUMENT);
  CHECK(dml_repo_close(&repo, &error) == DML_INVALID_STATE);
  CHECK(dml_datum_encode(&input, &scalar, &error) == DML_OK);
  CHECK(dml_txn_put_datum(txn, scalar.data, scalar.len, &scalar_id, &error) == DML_OK);
  input.kind = DML_DATUM_LIST;
  input.value.ids.items = &scalar_id;
  input.value.ids.count = 1;
  CHECK(dml_datum_encode(&input, &list, &error) == DML_OK);
  CHECK(dml_txn_put_datum(txn, list.data, list.len, &list_id, &error) == DML_OK);
  CHECK(dml_txn_commit(&txn, &error) == DML_OK && txn == NULL);
  CHECK(dml_repo_close(&repo, &error) == DML_OK && repo == NULL);

  CHECK(dml_repo_open(repo_path, &open, &repo, &error) == DML_OK);
  CHECK(dml_txn_begin(repo, DML_TXN_READ, &txn, &error) == DML_OK);
  CHECK(dml_txn_get_datum(txn, &list_id, &fetched, &error) == DML_OK);
  CHECK(fetched.len == list.len && memcmp(fetched.data, list.data, list.len) == 0);
  dml_buffer_free(&fetched);
  CHECK(dml_txn_commit(&txn, &error) == DML_INVALID_STATE && txn == NULL);

  CHECK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error) == DML_OK);
  input.value.ids.items = &missing;
  CHECK(dml_datum_encode(&input, &fetched, &error) == DML_OK);
  CHECK(dml_txn_put_datum(txn, fetched.data, fetched.len, &missing, &error) ==
        DML_INVALID_KIND);
  CHECK(dml_txn_commit(&txn, &error) == DML_INVALID_STATE && txn == NULL);
  dml_buffer_free(&fetched);

  CHECK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error) == DML_OK);
  CHECK(dml_txn_put_datum(txn, scalar.data, scalar.len, &scalar_id, &error) == DML_OK);
  dml_txn_abort(&txn);
  dml_txn_abort(&txn);
  CHECK(dml_repo_close(&repo, &error) == DML_OK);

  CHECK(raw_write("", NULL, 0, 1) == MDB_SUCCESS);
  CHECK(dml_repo_open(repo_path, &create, &repo, &error) == DML_OK);
  CHECK(dml_repo_schema(repo, &schema, &error) == DML_OK && schema == 1);
  CHECK(dml_repo_close(&repo, &error) == DML_OK);

  char hex[33];
  CHECK(dml_object_id_format(&scalar_id, hex, &error) == DML_OK);
  memcpy(scalar_key + 15, hex, 33);
  uint8_t malformed_tombstone[20];
  tombstone(malformed_tombstone, sizeof(malformed_tombstone));
  CHECK(raw_write(scalar_key, malformed_tombstone, sizeof(malformed_tombstone), 0) ==
        MDB_SUCCESS);
  CHECK(dml_repo_open(repo_path, &open, &repo, &error) == DML_OK);
  CHECK(dml_txn_begin(repo, DML_TXN_READ, &txn, &error) == DML_OK);
  CHECK(dml_txn_get_datum(txn, &scalar_id, &fetched, &error) == DML_INVALID_BOUNDS);
  dml_txn_abort(&txn);
  CHECK(dml_repo_close(&repo, &error) == DML_OK);

  uint8_t valid_tombstone[36];
  tombstone(valid_tombstone, sizeof(valid_tombstone));
  CHECK(raw_write(scalar_key, valid_tombstone, sizeof(valid_tombstone), 0) == MDB_SUCCESS);
  CHECK(dml_repo_open(repo_path, &open, &repo, &error) == DML_OK);
  CHECK(dml_txn_begin(repo, DML_TXN_READ, &txn, &error) == DML_OK);
  CHECK(dml_txn_get_datum(txn, &scalar_id, &fetched, &error) == DML_INVALID_PAYLOAD);
  CHECK(strcmp(error.detail, "record_type=tombstone;detail=excised") == 0);
  dml_txn_abort(&txn);
  CHECK(dml_repo_close(&repo, &error) == DML_OK);
  dml_buffer_free(&scalar);
  dml_buffer_free(&list);
  cleanup();
  return 0;
}
