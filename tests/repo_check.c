#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <lmdb.h>

#include "dml/repo.h"

#define CHECK(condition) do { \
  if (!(condition)) { \
    fprintf(stderr, "repo_check:%d: %s\n", __LINE__, #condition); \
    exit(EXIT_FAILURE); \
  } \
} while (0)
#define OK(call) do { \
  dml_status check_status = (call); \
  if (check_status != DML_OK) { \
    fprintf(stderr, "repo_check:%d: %s returned %s\n", __LINE__, #call, dml_status_name(check_status)); \
    exit(EXIT_FAILURE); \
  } \
} while (0)

static size_t allocation_limit;
static size_t allocation_count;

void *dml_check_fault_malloc(size_t size) {
  if (++allocation_count == allocation_limit) return NULL;
  return malloc(size);
}

void *dml_check_fault_realloc(void *items, size_t size) {
  if (++allocation_count == allocation_limit) return NULL;
  return realloc(items, size);
}

typedef struct {
  dml_record_type type;
  dml_object_id id;
} typed_id;

typedef struct {
  dml_object_id leaf;
  dml_object_id staged;
  typed_id detached[5];
  typed_id loose;
} fixture;

typedef struct {
  const typed_id *expected;
  size_t count;
  unsigned seen;
} expected_visits;

static void visit(void *context, dml_record_type type, const dml_object_id *id) {
  expected_visits *visits = context;
  for (size_t i = 0; i < visits->count; i++) {
    if (type == visits->expected[i].type &&
        memcmp(id->bytes, visits->expected[i].id.bytes, DML_OBJECT_ID_SIZE) == 0) {
      CHECK((visits->seen & (1u << i)) == 0);
      visits->seen |= 1u << i;
      return;
    }
  }
  CHECK(!"unexpected unreachable ID");
}

static dml_bytes bytes(const char *text) {
  return (dml_bytes){(const uint8_t *)text, strlen(text)};
}

static dml_object_id put_datum(dml_txn *txn, dml_datum_input input) {
  dml_object_id id;
  dml_buffer packed = {0};
  OK(dml_datum_encode(&input, &packed, NULL));
  OK(dml_txn_put_datum(txn, packed.data, packed.len, &id, NULL));
  dml_buffer_free(&packed);
  return id;
}

static dml_object_id put_number(dml_txn *txn, int64_t value) {
  return put_datum(txn, (dml_datum_input){.kind = DML_DATUM_I64, .value.i64 = value});
}

static dml_object_id put_object(dml_txn *txn, dml_object_input input) {
  dml_object_id id;
  dml_buffer packed = {0};
  OK(dml_object_encode(&input, &packed, NULL));
  OK(dml_txn_put_object(txn, input.type, packed.data, packed.len, &id, NULL));
  dml_buffer_free(&packed);
  return id;
}

static dml_object_id put_node(dml_txn *txn, uint32_t kind, dml_object_id target) {
  return put_object(txn, (dml_object_input){.type = DML_REC_NODE, .value.node = {kind, target}});
}

static dml_object_id put_dag(dml_txn *txn, dml_object_id root,
                              const dml_dag_binding *bindings, size_t count) {
  return put_object(txn, (dml_object_input){.type = DML_REC_DAG, .value.dag = {root, bindings, count}});
}

static dml_object_id put_tree(dml_txn *txn, const dml_tree_entry *entries, size_t count) {
  return put_object(txn, (dml_object_input){.type = DML_REC_TREE, .value.tree = {entries, count}});
}

static dml_object_id put_commit(dml_txn *txn, dml_object_id tree, const dml_object_id *parent) {
  return put_object(txn, (dml_object_input){.type = DML_REC_COMMIT,
                                            .value.commit = {tree, {parent, parent != NULL}}});
}

static void expect_report(dml_repo_integrity actual, dml_repo_integrity expected) {
#define FIELD(name) CHECK(actual.name == expected.name)
  FIELD(refs);
  FIELD(broken_refs);
  FIELD(invalid_entries);
  FIELD(invalid_objects);
  FIELD(reachable_objects);
  FIELD(broken_reachable_edges);
  FIELD(broken_unreachable_edges);
  FIELD(intact_unreachable_objects);
  FIELD(broken_unreachable_objects);
#undef FIELD
}

static const dml_repo_integrity sentinel = {.refs = 999, .reachable_objects = 999};

#define CHAIN_LENGTH 64
#define ROOTED_COUNT (1 + CHAIN_LENGTH + 8)

static fixture seed(const char *path) {
  dml_repo *repo = NULL;
  dml_txn *txn = NULL;
  fixture ids = {0};
  OK(dml_repo_open(path, &(dml_repo_options){.create = true}, &repo, NULL));
  dml_repo_integrity report = sentinel;
  expected_visits visits = {0};
  OK(dml_txn_begin(repo, DML_TXN_READ, &txn, NULL));
  CHECK(dml_txn_check_integrity(NULL, &report, visit, &visits, NULL) == DML_INVALID_ARGUMENT);
  expect_report(report, sentinel);
  CHECK(dml_txn_check_integrity(txn, NULL, visit, &visits, NULL) == DML_INVALID_ARGUMENT);
  OK(dml_txn_check_integrity(txn, &report, visit, &visits, NULL));
  expect_report(report, (dml_repo_integrity){0});
  dml_txn_abort(&txn);
  OK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, NULL));
  ids.leaf = put_number(txn, 7);
  dml_object_id tip = ids.leaf;
  for (size_t i = 0; i < CHAIN_LENGTH; i++) {
    tip = put_datum(txn, (dml_datum_input){.kind = DML_DATUM_LIST, .value.ids = {&tip, 1}});
  }
  dml_object_id inner_node = put_node(txn, DML_NODE_LITERAL, tip);
  dml_object_id inner_dag = put_dag(txn, inner_node, NULL, 0);
  dml_object_id subdag = put_node(txn, DML_NODE_SUBDAG, inner_dag);
  dml_dag_binding binding = {bytes("leaf"), put_node(txn, DML_NODE_LITERAL, ids.leaf)};
  dml_object_id outer_dag = put_dag(txn, subdag, &binding, 1);
  dml_tree_entry entry = {bytes("input"), outer_dag};
  dml_object_id tree = put_tree(txn, &entry, 1);
  ids.staged = put_commit(txn, tree, NULL);
  dml_object_id result = put_commit(txn, tree, &ids.staged);
  OK(dml_txn_ref_create(txn, bytes("incoming"), &ids.staged, NULL));
  OK(dml_txn_ref_create(txn, bytes("result-pin"), &result, NULL));
  OK(dml_txn_ref_create(txn, bytes("second-pin"), &result, NULL));

  /* A detached branch can reference retained history without being a root. */
  dml_object_id detached_leaf = put_number(txn, 9);
  dml_object_id detached_node = put_node(txn, DML_NODE_LITERAL, detached_leaf);
  dml_object_id detached_dag = put_dag(txn, detached_node, NULL, 0);
  dml_tree_entry entries[] = {entry, {bytes("side"), detached_dag}};
  dml_object_id detached_tree = put_tree(txn, entries, 2);
  dml_object_id detached_commit = put_commit(txn, detached_tree, &result);
  ids.detached[0] = (typed_id){DML_REC_DATUM, detached_leaf};
  ids.detached[1] = (typed_id){DML_REC_NODE, detached_node};
  ids.detached[2] = (typed_id){DML_REC_DAG, detached_dag};
  ids.detached[3] = (typed_id){DML_REC_TREE, detached_tree};
  ids.detached[4] = (typed_id){DML_REC_COMMIT, detached_commit};
  ids.loose = (typed_id){DML_REC_DATUM, put_number(txn, 11)};

  report = sentinel;
  CHECK(dml_txn_check_integrity(txn, &report, visit, &visits, NULL) == DML_INVALID_STATE);
  expect_report(report, sentinel);
  OK(dml_txn_commit(&txn, NULL)); /* Checker rejection must not poison writes. */

  OK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, NULL));
  OK(dml_txn_ref_delete_expected(txn, bytes("incoming"), &ids.staged, NULL));
  OK(dml_txn_commit(&txn, NULL));
  OK(dml_repo_close(&repo, NULL));
  return ids;
}

static void inspect_clean(const char *path, const fixture *ids) {
  dml_repo *repo = NULL;
  dml_txn *txn = NULL;
  OK(dml_repo_open(path, NULL, &repo, NULL));
  OK(dml_txn_begin(repo, DML_TXN_READ, &txn, NULL));
  dml_object_id ref;
  CHECK(dml_txn_ref_get(txn, bytes("incoming"), &ref, NULL) == DML_NOT_FOUND);

  typed_id expected[] = {ids->detached[0], ids->detached[1], ids->detached[2],
                         ids->detached[3], ids->detached[4], ids->loose};
  expected_visits visits = {expected, 6, 0};
  dml_repo_integrity report;
  OK(dml_txn_check_integrity(txn, &report, visit, &visits, NULL));
  expect_report(report, (dml_repo_integrity){.refs = 2, .reachable_objects = ROOTED_COUNT,
                                            .intact_unreachable_objects = 6});
  CHECK(visits.seen == (1u << visits.count) - 1);
  dml_txn_abort(&txn);
  OK(dml_repo_close(&repo, NULL));
}

static void raw_put(MDB_txn *txn, MDB_dbi dbi, const char *key, dml_bytes value) {
  MDB_val native_key = {strlen(key), (void *)key};
  MDB_val native_value = {value.len, (void *)value.data};
  CHECK(mdb_put(txn, dbi, &native_key, &native_value, 0) == MDB_SUCCESS);
}

static void make_key(char *out, const char *prefix, const dml_object_id *id) {
  size_t len = strlen(prefix);
  memcpy(out, prefix, len);
  OK(dml_object_id_format(id, out + len, NULL));
}

/* Corruption unavailable from public writes: missing, wrong ID, wrong type,
 * malformed encoding, namespace/key errors, and unsound refs. */
static void damage(const char *path, const fixture *ids) {
  dml_buffer record = {0};
  const dml_datum_input other = {.kind = DML_DATUM_I64, .value.i64 = 11};
  OK(dml_datum_encode(&other, &record, NULL));
  MDB_env *env = NULL;
  MDB_txn *txn = NULL;
  MDB_dbi dbi;
  CHECK(mdb_env_create(&env) == MDB_SUCCESS);
  CHECK(mdb_env_open(env, path, 0, 0) == MDB_SUCCESS);
  CHECK(mdb_txn_begin(env, NULL, 0, &txn) == MDB_SUCCESS);
  CHECK(mdb_dbi_open(txn, NULL, 0, &dbi) == MDB_SUCCESS);
  char key[64];
  make_key(key, "objects/datums/", &ids->leaf);
  MDB_val dead_key = {strlen(key), key};
  CHECK(mdb_del(txn, dbi, &dead_key, NULL) == MDB_SUCCESS);
  make_key(key, "objects/datums/", &ids->detached[0].id);
  raw_put(txn, dbi, key, (dml_bytes){record.data, record.len});
  make_key(key, "objects/commits/", &ids->loose.id);
  raw_put(txn, dbi, key, (dml_bytes){record.data, record.len});
  dml_object_id missing = {0};
  record.data[0] ^= 1;
  make_key(key, "objects/datums/", &missing);
  raw_put(txn, dbi, key, (dml_bytes){record.data, record.len});
  raw_put(txn, dbi, "objects/datums/not-an-id", bytes("irrelevant"));
  raw_put(txn, dbi, "unknown/key", bytes("irrelevant"));
  raw_put(txn, dbi, "refs/heads/bad/name", (dml_bytes){ids->detached[4].id.bytes, DML_OBJECT_ID_SIZE});
  raw_put(txn, dbi, "refs/heads/short", bytes("short"));
  raw_put(txn, dbi, "refs/heads/dangling", (dml_bytes){missing.bytes, DML_OBJECT_ID_SIZE});
  raw_put(txn, dbi, "refs/heads/wrong-kind", (dml_bytes){ids->loose.id.bytes, DML_OBJECT_ID_SIZE});
  CHECK(mdb_txn_commit(txn) == MDB_SUCCESS);
  mdb_env_close(env);
  dml_buffer_free(&record);
}

static void inspect_damaged(const char *path, const fixture *ids) {
  dml_repo *repo = NULL;
  dml_txn *txn = NULL;
  OK(dml_repo_open(path, NULL, &repo, NULL));
  OK(dml_txn_begin(repo, DML_TXN_READ, &txn, NULL));
  expected_visits visits = {&ids->loose, 1, 0};
  dml_repo_integrity report;
  dml_error error;
  allocation_count = 0;
  OK(dml_txn_check_integrity(txn, &report, visit, &visits, &error));
  const size_t successful_count = allocation_count;
  CHECK(error.code == DML_OK);
  expect_report(report, (dml_repo_integrity){.refs = 6, .broken_refs = 4,
                                            .invalid_entries = 2, .invalid_objects = 3,
                                            .reachable_objects = ROOTED_COUNT - 1,
                                            .broken_reachable_edges = 2, .broken_unreachable_edges = 1,
                                            .intact_unreachable_objects = 1, .broken_unreachable_objects = 4});
  CHECK(visits.seen == 1);

  /* Fail every checker-owned heap allocation (index growth, ID hash, stack). */
  CHECK(successful_count > ROOTED_COUNT);
  for (size_t fail = 1; fail <= successful_count; fail++) {
    allocation_limit = fail;
    allocation_count = 0;
    visits.seen = 0;
    report = sentinel;
    CHECK(dml_txn_check_integrity(txn, &report, visit, &visits, &error) == DML_OUT_OF_MEMORY);
    CHECK(error.code == DML_OUT_OF_MEMORY && error.detail[0] != '\0');
    CHECK(visits.seen == 0);
    expect_report(report, sentinel);
  }
  allocation_limit = 0;
  dml_buffer record = {0};
  OK(dml_txn_get_datum(txn, &ids->loose.id, &record, NULL));
  dml_buffer_free(&record);
  dml_txn_abort(&txn);
  OK(dml_repo_close(&repo, NULL));
}

static dml_buffer read_data_file(const char *path) {
  char file_path[4096];
  int len = snprintf(file_path, sizeof(file_path), "%s/data.mdb", path);
  CHECK(len > 0 && (size_t)len < sizeof(file_path));
  FILE *file = fopen(file_path, "rb");
  CHECK(file != NULL);
  CHECK(fseek(file, 0, SEEK_END) == 0);
  long size = ftell(file);
  CHECK(size > 0 && fseek(file, 0, SEEK_SET) == 0);
  dml_buffer data = {malloc((size_t)size), (size_t)size};
  CHECK(data.data != NULL);
  CHECK(fread(data.data, 1, data.len, file) == data.len);
  CHECK(fclose(file) == 0);
  return data;
}

static void expect_unchanged(const char *path, dml_buffer before) {
  dml_buffer after = read_data_file(path);
  CHECK(before.len == after.len && memcmp(before.data, after.data, before.len) == 0);
  dml_buffer_free(&before);
  dml_buffer_free(&after);
}

static void check_broken_ref_release(const char *path, const fixture *ids) {
  dml_repo *repo = NULL;
  dml_txn *txn = NULL;
  OK(dml_repo_open(path, NULL, &repo, NULL));
  OK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, NULL));
  CHECK(dml_txn_ref_delete_expected(txn, bytes("short"), &ids->staged, NULL) == DML_INTEGRITY_ERROR);
  CHECK(dml_txn_commit(&txn, NULL) == DML_INVALID_STATE);
  OK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, NULL));
  dml_object_id missing = {0};
  OK(dml_txn_ref_delete_expected(txn, bytes("dangling"), &missing, NULL));
  OK(dml_txn_commit(&txn, NULL));
  OK(dml_txn_begin(repo, DML_TXN_READ, &txn, NULL));
  dml_repo_integrity report;
  OK(dml_txn_check_integrity(txn, &report, NULL, NULL, NULL));
  CHECK(report.refs == 5 && report.broken_refs == 3);
  dml_txn_abort(&txn);
  OK(dml_repo_close(&repo, NULL));
}

int main(int argc, char **argv) {
  CHECK(argc == 2);
  const char *path = argv[1];
  fixture ids = seed(path);
  dml_buffer before = read_data_file(path);
  inspect_clean(path, &ids);
  expect_unchanged(path, before);
  damage(path, &ids);
  before = read_data_file(path);
  inspect_damaged(path, &ids);
  expect_unchanged(path, before);
  check_broken_ref_release(path, &ids);
  return EXIT_SUCCESS;
}
