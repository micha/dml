#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include <lmdb.h>
#include <uriparser/Uri.h>

#include "dml/dml.h"
#include "fault_control.h"

#ifdef _WIN32
#include <direct.h>
#include <process.h>
#define make_directory(path) _mkdir(path)
#define remove_directory(path) _rmdir(path)
#define process_id _getpid
#else
#include <unistd.h>
#define make_directory(path) mkdir(path, 0700)
#define remove_directory(path) rmdir(path)
#define process_id getpid
#endif

#define CHECK(expression) do { \
  if (!(expression)) { fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #expression); return 1; } \
} while (0)

static char root[96];
static size_t repositories;

static void repository_path(char path[128]) {
  (void)snprintf(path, 128, "%s/repo-%zu", root, repositories++);
}

static void cleanup(void) {
  for (size_t i = 0; i < repositories; i++) {
    char path[160];
    (void)snprintf(path, sizeof(path), "%s/repo-%zu/data.mdb", root, i);
    (void)remove(path);
    (void)snprintf(path, sizeof(path), "%s/repo-%zu/lock.mdb", root, i);
    (void)remove(path);
    (void)snprintf(path, sizeof(path), "%s/repo-%zu", root, i);
    (void)remove_directory(path);
  }
  (void)remove_directory(root);
}

static int test_codec_allocations(void) {
  dml_error error;
  dml_object_id ids[2] = {{{1}}, {{2}}};
  dml_datum_map_entry map = {ids[0], ids[1]};
  static const uint8_t text[] = "hello";
  static const uint8_t uri[] = "http://example.com/a/%2F?q=x";
  for (int kind = DML_DATUM_NULL; kind <= DML_DATUM_MAP; kind++) {
    dml_datum_input input = {.kind = (dml_datum_kind)kind};
    if (kind == DML_DATUM_BOOL) input.value.boolean = true;
    if (kind == DML_DATUM_I64) input.value.i64 = 42;
    if (kind == DML_DATUM_F64) input.value.f64 = 1.25;
    if (kind >= DML_DATUM_BYTES && kind <= DML_DATUM_URI) {
      input.value.bytes = (dml_bytes){kind == DML_DATUM_URI ? uri : text,
                                    kind == DML_DATUM_URI ? sizeof(uri) - 1 : sizeof(text) - 1};
    }
    if (kind == DML_DATUM_LIST || kind == DML_DATUM_SET) input.value.ids = (dml_id_array){ids, 2};
    if (kind == DML_DATUM_MAP) input.value.map = (dml_map_array){&map, 1};
    size_t successful_nth = 0;
    for (size_t nth = 1; nth < 12; nth++) {
      dml_buffer out = {0};
      dml_test_fail(DML_TEST_ALLOCATE, nth, 0);
      dml_status status = dml_datum_encode(&input, &out, &error);
      if (dml_test_failures() == 0) {
        CHECK(status == DML_OK && out.data != NULL);
        dml_buffer_free(&out);
        successful_nth = nth;
        break;
      }
      CHECK(status == DML_OUT_OF_MEMORY && error.code == status);
      CHECK(out.data == NULL && out.len == 0);
    }
    CHECK(successful_nth > 1);
  }
  dml_test_reset();
  dml_tree_entry entry = {{text, sizeof(text) - 1}, ids[0]};
  for (int type = DML_REC_NODE; type <= DML_REC_COMMIT; type++) {
    dml_object_input input = {.type = (dml_record_type)type};
    if (type == DML_REC_NODE) input.value.node.kind = DML_NODE_LITERAL;
    if (type == DML_REC_TREE) { input.value.tree.items = &entry; input.value.tree.count = 1; }
    if (type == DML_REC_COMMIT) input.value.commit.parents = (dml_id_array){ids, 2};
    size_t allocations = type == DML_REC_TREE ? 2 : 1;
    for (size_t nth = 1; nth <= allocations; nth++) {
      dml_buffer out = {0};
      dml_test_fail(DML_TEST_ALLOCATE, nth, 0);
      CHECK(dml_object_encode(&input, &out, &error) == DML_OUT_OF_MEMORY);
      CHECK(dml_test_failures() == 1 && out.data == NULL && out.len == 0);
    }
  }
  dml_test_reset();
  dml_buffer packed = {0};
  dml_datum_input input = {.kind = DML_DATUM_STRING, .value.bytes = {text, sizeof(text) - 1}};
  for (size_t nth = 1; nth <= 2; nth++) {
    dml_test_fail(DML_TEST_TEXT, nth, 0);
    CHECK(dml_datum_encode(&input, &packed, &error) == DML_OUT_OF_MEMORY);
    CHECK(dml_test_failures() == 1 && packed.data == NULL && packed.len == 0);
  }
  dml_test_reset();
  input.kind = DML_DATUM_I64; input.value.i64 = 42;
  CHECK(dml_datum_encode(&input, &packed, &error) == DML_OK);
  dml_object_id id;
  dml_test_fail(DML_TEST_ALLOCATE, 1, 0);
  CHECK(dml_object_id_compute(packed.data, packed.len, &id, &error) == DML_OUT_OF_MEMORY);
  CHECK(dml_test_failures() == 1);
  dml_buffer_free(&packed);
  dml_test_reset();
  return 0;
}

static int test_uri_failures(void) {
  static const uint8_t uri[] = "http://example.com/a/b?q=x";
  dml_error error;
  dml_buffer out = {0};
  const dml_test_fault operations[] = {DML_TEST_URI_PARSE, DML_TEST_URI_NORMALIZE,
                                      DML_TEST_URI_SIZE, DML_TEST_URI_WRITE};
  for (size_t i = 0; i < sizeof(operations) / sizeof(operations[0]); i++) {
    size_t calls = operations[i] == DML_TEST_URI_PARSE ? 2 : 1;
    for (size_t nth = 1; nth <= calls; nth++) {
      int injected_code = operations[i] == DML_TEST_URI_SIZE ? URI_ERROR_OUTPUT_TOO_LARGE : URI_ERROR_MALLOC;
      dml_test_fail(operations[i], nth, injected_code);
      dml_status status = dml_uri_canonicalize(uri, sizeof(uri) - 1, &out, &error);
      CHECK(status == (operations[i] == DML_TEST_URI_WRITE || operations[i] == DML_TEST_URI_SIZE
                       ? DML_INVALID_PAYLOAD : DML_OUT_OF_MEMORY));
      CHECK(dml_test_failures() == 1 && out.data == NULL && out.len == 0);
      CHECK(error.native_code == injected_code);
    }
  }
  dml_test_fail(DML_TEST_URI_PARSE, 2, URI_ERROR_SYNTAX);
  CHECK(dml_uri_canonicalize(uri, sizeof(uri) - 1, &out, &error) == DML_INVALID_PAYLOAD);
  CHECK(dml_test_failures() == 1 && out.data == NULL && out.len == 0);
  dml_test_reset();
  return 0;
}

static int test_initialization_failures(void) {
  const dml_test_fault operations[] = {DML_TEST_ENV_CREATE, DML_TEST_ENV_SIZE, DML_TEST_ENV_OPEN,
    DML_TEST_TXN_BEGIN, DML_TEST_DBI_OPEN, DML_TEST_GET, DML_TEST_PUT, DML_TEST_STAT, DML_TEST_COMMIT};
  dml_repo_options options = {true, 0};
  dml_error error;
  for (size_t i = 0; i < sizeof(operations) / sizeof(operations[0]); i++) {
    char path[128]; repository_path(path);
    dml_repo *repo = NULL;
    dml_test_fail(operations[i], 1, EIO);
    CHECK(dml_repo_open(path, &options, &repo, &error) == DML_STORAGE_ERROR);
    CHECK(dml_test_failures() == 1 && repo == NULL && error.native_code == EIO);
    dml_test_reset();
    CHECK(dml_repo_open(path, &options, &repo, &error) == DML_OK);
    CHECK(dml_repo_close(&repo, &error) == DML_OK);
  }
  char path[128]; repository_path(path);
  for (size_t nth = 1; nth <= 3; nth++) {
    dml_repo *repo = NULL;
    dml_test_fail(DML_TEST_ALLOCATE, nth, 0);
    dml_status status = dml_repo_open(path, &options, &repo, &error);
    if (dml_test_failures() == 1) CHECK(status == DML_OUT_OF_MEMORY && repo == NULL);
    else { CHECK(status == DML_OK); CHECK(dml_repo_close(&repo, &error) == DML_OK); }
  }
  dml_test_reset();
  return 0;
}

static int test_storage_failures(void) {
  char path[128]; repository_path(path);
  dml_repo_options options = {true, 0};
  dml_repo *repo = NULL;
  dml_txn *txn = NULL;
  dml_error error;
  dml_buffer packed = {0}, out = {0};
  dml_datum_input input = {.kind = DML_DATUM_I64, .value.i64 = 42};
  dml_object_id id;
  CHECK(dml_repo_open(path, &options, &repo, &error) == DML_OK);
  dml_test_fail(DML_TEST_ALLOCATE, 1, 0);
  CHECK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error) == DML_OUT_OF_MEMORY && txn == NULL);
  dml_test_fail(DML_TEST_TXN_BEGIN, 1, EIO);
  CHECK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error) == DML_STORAGE_ERROR && txn == NULL);
  dml_test_reset();
  CHECK(dml_datum_encode(&input, &packed, &error) == DML_OK);
  CHECK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error) == DML_OK);
  CHECK(dml_txn_put_datum(txn, packed.data, packed.len, &id, &error) == DML_OK);
  CHECK(dml_txn_commit(&txn, &error) == DML_OK);
  CHECK(dml_txn_begin(repo, DML_TXN_READ, &txn, &error) == DML_OK);
  dml_test_fail(DML_TEST_GET, 1, EIO);
  CHECK(dml_txn_get_datum(txn, &id, &out, &error) == DML_STORAGE_ERROR);
  CHECK(out.data == NULL && out.len == 0);
  for (size_t nth = 1; nth <= 2; nth++) {
    dml_test_fail(DML_TEST_ALLOCATE, nth, 0);
    CHECK(dml_txn_get_datum(txn, &id, &out, &error) == DML_OUT_OF_MEMORY);
    CHECK(dml_test_failures() == 1 && out.data == NULL && out.len == 0);
  }
  dml_test_reset();
  dml_txn_abort(&txn);
  for (int scenario = 0; scenario < 3; scenario++) {
    CHECK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error) == DML_OK);
    if (scenario == 0) {
      dml_test_fail(DML_TEST_PUT, 1, EIO);
      CHECK(dml_txn_put_datum(txn, packed.data, packed.len, &id, &error) == DML_STORAGE_ERROR);
    } else if (scenario == 1) {
      dml_test_fail(DML_TEST_ALLOCATE, 1, 0);
      CHECK(dml_txn_put_datum(txn, packed.data, packed.len, &id, &error) == DML_OUT_OF_MEMORY);
    } else {
      CHECK(dml_txn_put_datum(txn, packed.data, packed.len, &id, &error) == DML_OK);
      dml_test_fail(DML_TEST_COMMIT, 1, EIO);
      CHECK(dml_txn_commit(&txn, &error) == DML_STORAGE_ERROR && txn == NULL);
      continue;
    }
    CHECK(dml_txn_commit(&txn, &error) == DML_INVALID_STATE && txn == NULL);
  }
  dml_test_reset();
  dml_buffer_free(&packed);
  input.kind = DML_DATUM_STRING; input.value.bytes = (dml_bytes){(const uint8_t *)"text", 4};
  CHECK(dml_datum_encode(&input, &packed, &error) == DML_OK);
  CHECK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error) == DML_OK);
  CHECK(dml_txn_put_datum(txn, packed.data, packed.len, &id, &error) == DML_OK);
  CHECK(dml_txn_commit(&txn, &error) == DML_OK);
  CHECK(dml_txn_begin(repo, DML_TXN_READ, &txn, &error) == DML_OK);
  dml_test_fail(DML_TEST_TEXT, 2, 0);
  CHECK(dml_txn_get_datum(txn, &id, &out, &error) == DML_OUT_OF_MEMORY);
  CHECK(dml_test_failures() == 1 && out.data == NULL && out.len == 0);
  dml_test_reset(); dml_txn_abort(&txn); dml_buffer_free(&packed);
  CHECK(dml_repo_close(&repo, &error) == DML_OK);
  return 0;
}

static int test_ref_failures(void) {
  char path[128]; repository_path(path);
  dml_repo *repo = NULL;
  dml_txn *txn = NULL;
  dml_repo_options options = {true, 0};
  dml_error error;
  dml_buffer tree = {0}, commit = {0}, datum = {0}, out = {0};
  dml_object_input input = {.type = DML_REC_TREE};
  dml_object_id tree_id, commit_id, target, inserted;
  dml_bytes main_ref = {(const uint8_t *)"main", 4};
  CHECK(dml_repo_open(path, &options, &repo, &error) == DML_OK);
  CHECK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error) == DML_OK);
  CHECK(dml_object_encode(&input, &tree, &error) == DML_OK);
  CHECK(dml_txn_put_object(txn, DML_REC_TREE, tree.data, tree.len, &tree_id, &error) == DML_OK);
  input.type = DML_REC_COMMIT; input.value.commit.tree = tree_id;
  input.value.commit.parents = (dml_id_array){NULL, 0};
  CHECK(dml_object_encode(&input, &commit, &error) == DML_OK);
  CHECK(dml_txn_put_object(txn, DML_REC_COMMIT, commit.data, commit.len, &commit_id, &error) == DML_OK);
  CHECK(dml_txn_ref_create(txn, main_ref, &commit_id, &error) == DML_OK);
  CHECK(dml_txn_commit(&txn, &error) == DML_OK);
  CHECK(dml_txn_begin(repo, DML_TXN_READ, &txn, &error) == DML_OK);
  dml_test_fail(DML_TEST_GET, 1, EIO);
  CHECK(dml_txn_ref_get(txn, main_ref, &target, &error) == DML_STORAGE_ERROR);
  CHECK(dml_test_failures() == 1);
  dml_test_reset(); dml_txn_abort(&txn);
  for (int scenario = 0; scenario < 3; scenario++) {
    dml_datum_input value = {.kind = DML_DATUM_I64, .value.i64 = scenario};
    CHECK(dml_datum_encode(&value, &datum, &error) == DML_OK);
    CHECK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error) == DML_OK);
    CHECK(dml_txn_put_datum(txn, datum.data, datum.len, &inserted, &error) == DML_OK);
    CHECK(dml_txn_ref_update(txn, main_ref, &commit_id, &error) == DML_OK);
    dml_test_fail(scenario == 2 ? DML_TEST_PUT : DML_TEST_GET, scenario == 1 ? 3 : 1, EIO);
    CHECK(dml_txn_ref_update(txn, main_ref, &commit_id, &error) == DML_STORAGE_ERROR);
    CHECK(dml_test_failures() == 1);
    CHECK(dml_txn_put_object(txn, DML_REC_TREE, tree.data, tree.len, &tree_id, &error) == DML_INVALID_STATE);
    CHECK(dml_txn_commit(&txn, &error) == DML_INVALID_STATE && txn == NULL);
    dml_test_reset();
    CHECK(dml_txn_begin(repo, DML_TXN_READ, &txn, &error) == DML_OK);
    CHECK(dml_txn_ref_get(txn, main_ref, &target, &error) == DML_OK);
    CHECK(memcmp(&target, &commit_id, sizeof(target)) == 0);
    CHECK(dml_txn_get_datum(txn, &inserted, &out, &error) == DML_NOT_FOUND);
    dml_txn_abort(&txn); dml_buffer_free(&datum);
  }
  dml_buffer_free(&tree); dml_buffer_free(&commit);
  CHECK(dml_repo_close(&repo, &error) == DML_OK);
  return 0;
}

static int raw_write(const char *path, const char *key_text, const void *data, size_t len, int clear) {
  MDB_env *env = NULL;
  MDB_txn *txn = NULL;
  MDB_dbi dbi;
  MDB_val key = {strlen(key_text), (void *)key_text};
  MDB_val value = {len, (void *)data};
  int code = mdb_env_create(&env);
  if (code == MDB_SUCCESS) code = mdb_env_open(env, path, 0, 0600);
  if (code == MDB_SUCCESS) code = mdb_txn_begin(env, NULL, 0, &txn);
  if (code == MDB_SUCCESS) code = mdb_dbi_open(txn, NULL, 0, &dbi);
  if (code == MDB_SUCCESS && clear) code = mdb_drop(txn, dbi, 0);
  if (code == MDB_SUCCESS && key.mv_size != 0) code = mdb_put(txn, dbi, &key, &value, 0);
  if (txn != NULL) {
    if (code == MDB_SUCCESS) code = mdb_txn_commit(txn);
    else mdb_txn_abort(txn);
  }
  if (env != NULL) mdb_env_close(env);
  return code;
}

static int test_repository_boundaries(void) {
  char path[128]; repository_path(path);
  dml_repo *repo = NULL;
  dml_txn *txn = NULL;
  dml_repo_options options = {true, 0};
  dml_error error;
  uint32_t schema;
  dml_object_id id = {{0}};
  dml_buffer out = {0};
  CHECK(dml_repo_open(NULL, &options, &repo, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_repo_open("", &options, &repo, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_repo_open(path, &options, NULL, &error) == DML_INVALID_ARGUMENT);
  options.map_size = 8;
  CHECK(dml_repo_open(path, &options, &repo, &error) == DML_INVALID_ARGUMENT);
  options.map_size = 0;
  CHECK(dml_repo_open(path, &options, &repo, &error) == DML_OK);
  CHECK(dml_repo_open(path, &options, &repo, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_repo_schema(NULL, &schema, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_repo_schema(repo, NULL, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_txn_begin(NULL, DML_TXN_READ, &txn, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_txn_begin(repo, DML_TXN_READ, NULL, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_txn_begin(repo, (dml_txn_mode)99, &txn, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_txn_begin(repo, DML_TXN_READ, &txn, &error) == DML_OK);
  CHECK(dml_txn_begin(repo, DML_TXN_READ, &txn, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_txn_put_object(txn, DML_REC_DATUM, NULL, 0, &id, &error) == DML_INVALID_KIND);
  CHECK(dml_txn_get_object(txn, DML_REC_DATUM, &id, &out, &error) == DML_INVALID_KIND);
  CHECK(dml_txn_put_object(txn, DML_REC_REF, NULL, 0, &id, &error) == DML_INVALID_KIND);
  CHECK(dml_txn_put_object(txn, DML_REC_NODE, NULL, 0, &id, &error) == DML_INVALID_STATE);
  out.len = 1;
  CHECK(dml_txn_get_datum(txn, &id, &out, &error) == DML_INVALID_ARGUMENT);
  out.len = 0;
  dml_txn_abort(&txn); dml_txn_abort(NULL);
  CHECK(dml_txn_commit(NULL, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_txn_commit(&txn, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_repo_close(NULL, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_repo_close(&repo, &error) == DML_OK);
  dml_test_fail(DML_TEST_ALLOCATE, 1, 0);
  CHECK(dml_repo_open(path, NULL, &repo, &error) == DML_OUT_OF_MEMORY);
  CHECK(dml_test_failures() == 1 && repo == NULL);
  dml_test_reset();
  CHECK(dml_repo_close(&repo, &error) == DML_INVALID_ARGUMENT);
  CHECK(raw_write(path, "", NULL, 0, 1) == MDB_SUCCESS);
  CHECK(dml_repo_open(path, NULL, &repo, &error) == DML_NOT_FOUND);
  CHECK(raw_write(path, "other", "x", 1, 0) == MDB_SUCCESS);
  CHECK(dml_repo_open(path, &options, &repo, &error) == DML_INVALID_STATE);
  CHECK(raw_write(path, "", NULL, 0, 1) == MDB_SUCCESS);
  CHECK(dml_repo_open(path, &options, &repo, &error) == DML_OK);
  CHECK(dml_repo_close(&repo, &error) == DML_OK);
  dml_datum_input input = {.kind = DML_DATUM_NULL};
  CHECK(dml_datum_encode(&input, &out, &error) == DML_OK);
  CHECK(raw_write(path, "meta/schema", out.data, out.len, 0) == MDB_SUCCESS);
  CHECK(dml_repo_open(path, NULL, &repo, &error) == DML_INVALID_KIND);
  dml_buffer_free(&out);
  uint8_t meta[] = {'D','M','L','1',1,0,1,0,24,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0};
  CHECK(raw_write(path, "meta/schema", meta, sizeof(meta), 0) == MDB_SUCCESS);
  CHECK(dml_repo_open(path, NULL, &repo, &error) == DML_UNSUPPORTED_SCHEMA);
  meta[0] = 0;
  CHECK(raw_write(path, "meta/schema", meta, sizeof(meta), 0) == MDB_SUCCESS);
  CHECK(dml_repo_open(path, NULL, &repo, &error) == DML_INVALID_HEADER);
  repository_path(path);
  FILE *file = fopen(path, "wb"); CHECK(file != NULL); CHECK(fclose(file) == 0);
  CHECK(dml_repo_open(path, NULL, &repo, &error) == DML_STORAGE_ERROR);
  CHECK(remove(path) == 0);
  repository_path(path);
  CHECK(make_directory(path) == 0);
  char unrelated[160]; (void)snprintf(unrelated, sizeof(unrelated), "%s/unrelated", path);
  file = fopen(unrelated, "wb"); CHECK(file != NULL); CHECK(fclose(file) == 0);
  CHECK(dml_repo_open(path, &options, &repo, &error) == DML_INVALID_STATE);
  CHECK(remove(unrelated) == 0);
  repository_path(path);
  CHECK(make_directory(path) == 0);
  CHECK(dml_repo_open(path, NULL, &repo, &error) == DML_NOT_FOUND);
#ifndef _WIN32
  if (geteuid() != 0) {
    CHECK(chmod(path, 0) == 0);
    CHECK(dml_repo_open(path, NULL, &repo, &error) == DML_STORAGE_ERROR);
    char child[160]; (void)snprintf(child, sizeof(child), "%s/child", path);
    CHECK(dml_repo_open(child, NULL, &repo, &error) == DML_STORAGE_ERROR);
    CHECK(chmod(path, 0700) == 0);
  }
#endif
  char child[160]; (void)snprintf(child, sizeof(child), "%s/missing/child", path);
  CHECK(dml_repo_open(child, &options, &repo, &error) == DML_STORAGE_ERROR);
  return 0;
}

static int test_maps_and_collisions(void) {
  for (int scenario = 0; scenario < 2; scenario++) {
    char path[128]; repository_path(path);
    dml_repo_options options = {true, 0};
    dml_repo *repo = NULL; dml_txn *txn = NULL;
    dml_error error;
    dml_buffer first = {0}, second = {0}, out = {0};
    dml_datum_input input = {.kind = scenario == 0 ? DML_DATUM_NULL : DML_DATUM_I64, .value.i64 = 42};
    dml_object_id id;
    CHECK(dml_datum_encode(&input, &first, &error) == DML_OK);
    input.kind = DML_DATUM_I64; input.value.i64 = 43;
    CHECK(dml_datum_encode(&input, &second, &error) == DML_OK);
    CHECK(dml_repo_open(path, &options, &repo, &error) == DML_OK);
    CHECK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error) == DML_OK);
    dml_test_hash_collision(1);
    CHECK(dml_txn_put_datum(txn, first.data, first.len, &id, &error) == DML_OK);
    CHECK(dml_txn_commit(&txn, &error) == DML_OK);
    CHECK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error) == DML_OK);
    CHECK(dml_txn_put_datum(txn, second.data, second.len, &id, &error) == DML_INTEGRITY_ERROR);
    CHECK(dml_txn_commit(&txn, &error) == DML_INVALID_STATE);
    CHECK(dml_txn_begin(repo, DML_TXN_READ, &txn, &error) == DML_OK);
    CHECK(dml_txn_get_datum(txn, &id, &out, &error) == DML_OK);
    CHECK(out.len == first.len && memcmp(out.data, first.data, out.len) == 0);
    dml_test_hash_collision(0);
    dml_buffer_free(&first); dml_buffer_free(&second); dml_buffer_free(&out);
    dml_txn_abort(&txn); CHECK(dml_repo_close(&repo, &error) == DML_OK);
  }
  char path[128]; repository_path(path);
  dml_repo_options options = {true, 0};
  dml_repo *repo = NULL; dml_txn *txn = NULL;
  dml_error error;
  dml_buffer packed = {0};
  dml_datum_input scalar = {.kind = DML_DATUM_I64, .value.i64 = 42};
  dml_object_id id, ignored, missing = {{255}};
  CHECK(dml_repo_open(path, &options, &repo, &error) == DML_OK);
  CHECK(dml_datum_encode(&scalar, &packed, &error) == DML_OK);
  CHECK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error) == DML_OK);
  CHECK(dml_txn_put_datum(txn, packed.data, packed.len, &id, &error) == DML_OK);
  CHECK(dml_txn_commit(&txn, &error) == DML_OK); dml_buffer_free(&packed);
  for (int scenario = 0; scenario < 3; scenario++) {
    dml_datum_map_entry entry = {scenario == 0 ? missing : id, scenario == 1 ? missing : id};
    dml_datum_input map = {.kind = DML_DATUM_MAP, .value.map = {&entry, 1}};
    CHECK(dml_datum_encode(&map, &packed, &error) == DML_OK);
    CHECK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error) == DML_OK);
    CHECK(dml_txn_put_datum(txn, packed.data, packed.len, &ignored, &error) ==
          (scenario == 2 ? DML_OK : DML_INVALID_KIND));
    CHECK(dml_txn_commit(&txn, &error) == (scenario == 2 ? DML_OK : DML_INVALID_STATE));
    dml_buffer_free(&packed);
  }
  CHECK(dml_repo_close(&repo, &error) == DML_OK);
  return 0;
}

int main(void) {
  (void)snprintf(root, sizeof(root), "test-fault-data-%ld", (long)process_id());
  if (make_directory(root) != 0) {
    fprintf(stderr, "cannot create test-owned scratch: %s\n", root);
    return 1; /* Never clean a pre-existing directory. */
  }
  int result = test_codec_allocations() || test_uri_failures() ||
               test_initialization_failures() || test_storage_failures() ||
               test_ref_failures() || test_repository_boundaries() || test_maps_and_collisions();
  dml_test_reset();
  cleanup();
  return result;
}
