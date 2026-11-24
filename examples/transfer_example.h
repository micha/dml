#ifndef DML_TRANSFER_EXAMPLE_H
#define DML_TRANSFER_EXAMPLE_H

#include "lineage.h"

static const dml_bytes main_ref = {(const uint8_t *)"main", sizeof("main") - 1};
static const dml_bytes snapshot_name = {(const uint8_t *)"snapshot", sizeof("snapshot") - 1};
static const dml_bytes value_name = {(const uint8_t *)"value", sizeof("value") - 1};

static inline bool check(dml_status status, const char *operation, const dml_error *error) {
  if (status == DML_OK) return true;
  fprintf(stderr, "%s: %s", operation, dml_status_name(status));
  if (error->detail[0] != '\0') fprintf(stderr, " (%s)", error->detail);
  fputc('\n', stderr);
  return false;
}

static inline bool same_id(const dml_object_id *left, const dml_object_id *right) {
  return memcmp(left->bytes, right->bytes, sizeof(left->bytes)) == 0;
}

static inline bool close_repo(dml_repo **repo, dml_error *error) {
  return *repo == NULL || check(dml_repo_close(repo, error), "close repository", error);
}

static inline bool create_repo(const char *path, dml_repo **repo, dml_error *error) {
  /* Refuse an existing DML repository, including a path alias. This is not an
   * exclusive filesystem create: callers supply unused paths. */
  dml_status status = dml_repo_open(path, NULL, repo, error);
  if (status == DML_OK) {
    fprintf(stderr, "repository already exists: %s\n", path);
    return false;
  }
  if (status != DML_NOT_FOUND) return check(status, path, error);
  const dml_repo_options options = {.create = true};
  return check(dml_repo_open(path, &options, repo, error), path, error);
}

static inline bool write_snapshot(dml_txn *txn, int64_t value, const dml_object_id *parent,
                                  dml_object_id *commit, dml_error *error) {
  dml_object_id datum, node, dag, tree;
  const dml_datum_input number = {.kind = DML_DATUM_I64, .value.i64 = value};
  if (!check(lineage_put_literal(txn, &number, &datum, &node, error), "store input literal", error)) {
    return false;
  }

  const dml_dag_binding binding = {value_name, node};
  const dml_object_input graph = {.type = DML_REC_DAG, .value.dag = {node, &binding, 1}};
  if (!check(lineage_put_object(txn, &graph, &dag, error), "store DAG", error)) return false;

  const dml_tree_entry entry = {snapshot_name, dag};
  const dml_object_input snapshot = {.type = DML_REC_TREE, .value.tree = {&entry, 1}};
  if (!check(lineage_put_object(txn, &snapshot, &tree, error), "store tree", error)) return false;

  const dml_object_input revision = {
    .type = DML_REC_COMMIT, .value.commit = {tree, {parent, parent == NULL ? 0 : 1}}
  };
  return check(lineage_put_object(txn, &revision, commit, error), "store commit", error);
}

static inline bool write_revision(dml_repo *repo, int64_t value, const dml_object_id *parent,
                                  dml_object_id *commit, dml_error *error) {
  dml_txn *txn = NULL;
  bool ok = check(dml_txn_begin(repo, DML_TXN_WRITE, &txn, error), "begin source write", error) &&
            write_snapshot(txn, value, parent, commit, error);
  if (ok) {
    dml_status status = parent == NULL ? dml_txn_ref_create(txn, main_ref, commit, error)
                                       : dml_txn_ref_update(txn, main_ref, commit, error);
    ok = check(status, "set source main", error) &&
         check(dml_txn_commit(&txn, error), "commit source revision", error);
  }
  dml_txn_abort(&txn);
  return ok;
}

static inline dml_status add_one(int64_t input, int64_t *output) {
  if (input == INT64_MAX) return DML_INVALID_BOUNDS;
  *output = input + 1;
  return DML_OK;
}

static inline dml_bytes implementation_id(void) {
  return lineage_name("example.add-one@1");
}

#endif
