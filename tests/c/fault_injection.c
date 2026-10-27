#define DML_TEST_IMPLEMENTATION
#include "fault_injection.h"

static dml_test_fault selected;
static size_t remaining;
static size_t failures;
static int failure_code;
static int collide_hash;

void dml_test_hash_collision(int enabled) {
  collide_hash = enabled;
}

XXH128_hash_t dml_test_hash(const void *data, size_t len) {
  if (collide_hash) return (XXH128_hash_t){0, 0};
  return XXH3_128bits(data, len);
}

void dml_test_fail(dml_test_fault fault, size_t nth, int code) {
  selected = fault;
  remaining = nth;
  failures = 0;
  failure_code = code;
}

void dml_test_reset(void) {
  dml_test_fail(DML_TEST_NO_FAULT, 0, 0);
}

size_t dml_test_failures(void) {
  return failures;
}

static int fail(dml_test_fault fault) {
  if (selected != fault || remaining == 0 || --remaining != 0) return 0;
  failures++;
  selected = DML_TEST_NO_FAULT;
  return 1;
}

void *dml_test_malloc(size_t size) {
  return fail(DML_TEST_ALLOCATE) ? NULL : malloc(size);
}

void *dml_test_calloc(size_t count, size_t size) {
  return fail(DML_TEST_ALLOCATE) ? NULL : calloc(count, size);
}

utf8proc_ssize_t dml_test_text(const utf8proc_uint8_t *text, utf8proc_ssize_t len,
                              utf8proc_uint8_t **out, utf8proc_option_t options) {
  if (fail(DML_TEST_TEXT)) return UTF8PROC_ERROR_NOMEM;
  return utf8proc_map(text, len, out, options);
}

int dml_test_uri_parse(UriUriA *uri, const char *first, const char *last, const char **error) {
  if (fail(DML_TEST_URI_PARSE)) return failure_code;
  return uriParseSingleUriExA(uri, first, last, error);
}

int dml_test_uri_normalize(UriUriA *uri, unsigned int mask) {
  if (fail(DML_TEST_URI_NORMALIZE)) return failure_code;
  return uriNormalizeSyntaxExA(uri, mask);
}

int dml_test_uri_size(const UriUriA *uri, int *size) {
  if (fail(DML_TEST_URI_SIZE)) return failure_code;
  return uriToStringCharsRequiredA(uri, size);
}

int dml_test_uri_write(char *out, const UriUriA *uri, int size, int *written) {
  if (fail(DML_TEST_URI_WRITE)) return failure_code;
  return uriToStringA(out, uri, size, written);
}

int dml_test_env_create(MDB_env **env) {
  if (fail(DML_TEST_ENV_CREATE)) return failure_code;
  return mdb_env_create(env);
}

int dml_test_env_size(MDB_env *env, size_t size) {
  if (fail(DML_TEST_ENV_SIZE)) return failure_code;
  return mdb_env_set_mapsize(env, size);
}

int dml_test_env_open(MDB_env *env, const char *path, unsigned int flags, mdb_mode_t mode) {
  if (fail(DML_TEST_ENV_OPEN)) return failure_code;
  return mdb_env_open(env, path, flags, mode);
}

int dml_test_txn_begin(MDB_env *env, MDB_txn *parent, unsigned int flags, MDB_txn **txn) {
  if (fail(DML_TEST_TXN_BEGIN)) return failure_code;
  return mdb_txn_begin(env, parent, flags, txn);
}

int dml_test_dbi_open(MDB_txn *txn, const char *name, unsigned int flags, MDB_dbi *dbi) {
  if (fail(DML_TEST_DBI_OPEN)) return failure_code;
  return mdb_dbi_open(txn, name, flags, dbi);
}

int dml_test_get(MDB_txn *txn, MDB_dbi dbi, MDB_val *key, MDB_val *value) {
  if (fail(DML_TEST_GET)) return failure_code;
  return mdb_get(txn, dbi, key, value);
}

int dml_test_put(MDB_txn *txn, MDB_dbi dbi, MDB_val *key, MDB_val *value, unsigned int flags) {
  if (fail(DML_TEST_PUT)) return failure_code;
  return mdb_put(txn, dbi, key, value, flags);
}

int dml_test_stat(MDB_txn *txn, MDB_dbi dbi, MDB_stat *stats) {
  if (fail(DML_TEST_STAT)) return failure_code;
  return mdb_stat(txn, dbi, stats);
}

int dml_test_commit(MDB_txn *txn) {
  if (fail(DML_TEST_COMMIT)) {
    /* LMDB consumes the native transaction on commit failure too. */
    mdb_txn_abort(txn);
    return failure_code;
  }
  return mdb_txn_commit(txn);
}
