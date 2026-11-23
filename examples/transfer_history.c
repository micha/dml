#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <dml/dml.h>

static const dml_bytes main_ref = {(const uint8_t *)"main", sizeof("main") - 1};
static const dml_bytes staging_ref = {(const uint8_t *)"incoming", sizeof("incoming") - 1};
static const dml_bytes snapshot_name = {(const uint8_t *)"snapshot", sizeof("snapshot") - 1};
static const dml_bytes value_name = {(const uint8_t *)"value", sizeof("value") - 1};

static bool check(dml_status status, const char *operation, const dml_error *error) {
  if (status == DML_OK) return true;
  fprintf(stderr, "%s: %s", operation, dml_status_name(status));
  if (error->detail[0] != '\0') fprintf(stderr, " (%s)", error->detail);
  fputc('\n', stderr);
  return false;
}

static bool same_id(const dml_object_id *left, const dml_object_id *right) {
  return memcmp(left->bytes, right->bytes, sizeof(left->bytes)) == 0;
}

static bool close_repo(dml_repo **repo, dml_error *error) {
  return *repo == NULL || check(dml_repo_close(repo, error), "close repository", error);
}

static bool create_repo(const char *path, dml_repo **repo, dml_error *error) {
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

static bool put_object(dml_txn *txn, const dml_object_input *input, dml_object_id *id,
                       const char *operation, dml_error *error) {
  dml_buffer packed = {0};
  bool ok = check(dml_object_encode(input, &packed, error), "encode object", error) &&
            check(dml_txn_put_object(txn, input->type, packed.data, packed.len, id, error),
                  operation, error);
  dml_buffer_free(&packed);
  return ok;
}

static bool put_i64(dml_txn *txn, int64_t value, dml_object_id *id, dml_error *error) {
  const dml_datum_input input = {.kind = DML_DATUM_I64, .value.i64 = value};
  dml_buffer packed = {0};
  bool ok = check(dml_datum_encode(&input, &packed, error), "encode I64", error) &&
            check(dml_txn_put_datum(txn, packed.data, packed.len, id, error), "store datum", error);
  dml_buffer_free(&packed);
  return ok;
}

static bool write_snapshot(dml_txn *txn, int64_t value, const dml_object_id *parent,
                           dml_object_id *commit, dml_error *error) {
  dml_object_id datum, node, dag, tree;
  if (!put_i64(txn, value, &datum, error)) return false;
  const dml_object_input literal = {.type = DML_REC_NODE, .value.node = {DML_NODE_LITERAL, datum}};
  if (!put_object(txn, &literal, &node, "store literal node", error)) return false;

  const dml_dag_binding binding = {value_name, node};
  const dml_object_input graph = {.type = DML_REC_DAG, .value.dag = {node, &binding, 1}};
  if (!put_object(txn, &graph, &dag, "store DAG", error)) return false;

  const dml_tree_entry entry = {snapshot_name, dag};
  const dml_object_input snapshot = {.type = DML_REC_TREE, .value.tree = {&entry, 1}};
  if (!put_object(txn, &snapshot, &tree, "store tree", error)) return false;

  const dml_object_input revision = {
    .type = DML_REC_COMMIT, .value.commit = {tree, {parent, parent == NULL ? 0 : 1}}
  };
  return put_object(txn, &revision, commit, "store commit", error);
}

static bool write_revision(dml_repo *repo, int64_t value, const dml_object_id *parent,
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

static bool destination_main_missing(dml_repo *repo, dml_error *error) {
  dml_txn *txn = NULL;
  if (!check(dml_txn_begin(repo, DML_TXN_READ, &txn, error), "begin pre-publication read", error)) {
    return false;
  }
  dml_object_id observed;
  dml_status status = dml_txn_ref_get(txn, main_ref, &observed, error);
  dml_txn_abort(&txn);
  if (status == DML_NOT_FOUND) return true;
  if (status == DML_OK) {
    fputs("destination main exists before explicit publication\n", stderr);
    return false;
  }
  return check(status, "check destination main", error);
}

static bool create_ref(dml_repo *repo, dml_bytes ref, const dml_object_id *tip, dml_error *error) {
  dml_txn *txn = NULL;
  bool ok = check(dml_txn_begin(repo, DML_TXN_WRITE, &txn, error), "begin destination write", error) &&
            check(dml_txn_ref_create(txn, ref, tip, error), "create destination ref", error) &&
            check(dml_txn_commit(&txn, error), "commit destination write", error);
  dml_txn_abort(&txn);
  return ok;
}

static bool load_object(dml_txn *txn, dml_record_type type, const dml_object_id *id,
                        dml_buffer *packed, dml_object_view *view, dml_error *error) {
  return check(dml_txn_get_object(txn, type, id, packed, error), "load object", error) &&
         check(dml_object_decode(packed->data, packed->len, view, error), "decode object", error);
}

static bool read_commit(dml_txn *txn, const dml_object_id *id, dml_object_id *tree,
                        dml_object_id *parent, dml_error *error) {
  dml_buffer packed = {0};
  dml_object_view view;
  bool ok = load_object(txn, DML_REC_COMMIT, id, &packed, &view, error);
  if (ok) {
    *tree = view.reference;
    if (parent != NULL) {
      ok = check(dml_object_view_parent(&view, 0, parent, error), "read first parent", error);
    }
  }
  dml_buffer_free(&packed);
  return ok;
}

static bool find_dag(dml_txn *txn, const dml_object_id *tree, dml_object_id *dag, dml_error *error) {
  dml_buffer packed = {0};
  dml_object_view view;
  bool found = false;
  if (load_object(txn, DML_REC_TREE, tree, &packed, &view, error)) {
    for (size_t i = 0; i < view.count; ++i) {
      dml_tree_entry entry;
      if (!check(dml_object_view_entry(&view, i, &entry, error), "decode tree entry", error)) break;
      if (entry.name.len == snapshot_name.len &&
          memcmp(entry.name.data, snapshot_name.data, snapshot_name.len) == 0) {
        *dag = entry.dag;
        found = true;
        break;
      }
    }
    if (!found) fputs("tree has no readable snapshot entry\n", stderr);
  }
  dml_buffer_free(&packed);
  return found;
}

static bool read_literal(dml_txn *txn, const dml_object_id *id, dml_object_id *datum,
                         dml_error *error) {
  dml_buffer packed = {0};
  dml_object_view view;
  bool ok = load_object(txn, DML_REC_NODE, id, &packed, &view, error);
  if (ok && view.node_kind != DML_NODE_LITERAL) {
    fputs("value binding does not select a literal node\n", stderr);
    ok = false;
  }
  if (ok) *datum = view.reference;
  dml_buffer_free(&packed);
  return ok;
}

static bool read_i64(dml_txn *txn, const dml_object_id *id, int64_t *out, dml_error *error) {
  dml_buffer packed = {0};
  dml_datum_view view;
  bool ok = check(dml_txn_get_datum(txn, id, &packed, error), "load datum", error) &&
            check(dml_datum_decode(packed.data, packed.len, &view, error), "decode datum", error);
  if (ok && view.kind != DML_DATUM_I64) {
    fputs("value datum is not I64\n", stderr);
    ok = false;
  }
  if (ok) {
    /* The validated payload is an eight-byte little-endian signed integer. */
    uint64_t bits = 0;
    for (size_t i = 0; i < sizeof(bits); ++i) bits |= (uint64_t)view.payload[i] << (8 * i);
    *out = bits <= INT64_MAX ? (int64_t)bits : -1 - (int64_t)(UINT64_MAX - bits);
  }
  dml_buffer_free(&packed);
  return ok;
}

static bool read_value(dml_txn *txn, const dml_object_id *tree, int64_t *out, dml_error *error) {
  dml_object_id dag, node, datum;
  return find_dag(txn, tree, &dag, error) &&
         check(dml_txn_lookup_node(txn, &dag, value_name, &node, error), "look up value", error) &&
         read_literal(txn, &node, &datum, error) && read_i64(txn, &datum, out, error);
}

static bool verify_history(dml_repo *repo, dml_bytes ref, const dml_object_id *expected_tip,
                            const dml_object_id *expected_parent, int64_t expected_tip_value,
                            int64_t expected_parent_value, dml_error *error) {
  dml_txn *txn = NULL;
  dml_object_id tip, tip_tree, parent, parent_tree;
  bool ok = check(dml_txn_begin(repo, DML_TXN_READ, &txn, error), "begin history read", error) &&
            check(dml_txn_ref_get(txn, ref, &tip, error), "resolve destination ref", error) &&
            read_commit(txn, &tip, &tip_tree, &parent, error);
  if (ok && (!same_id(&tip, expected_tip) || !same_id(&parent, expected_parent))) {
    fputs("destination tip or first parent differs from the source\n", stderr);
    ok = false;
  }
  int64_t tip_value, parent_value;
  if (ok) {
    ok = read_value(txn, &tip_tree, &tip_value, error) &&
         read_commit(txn, &parent, &parent_tree, NULL, error) &&
         read_value(txn, &parent_tree, &parent_value, error);
  }
  dml_txn_abort(&txn);
  if (ok && (tip_value != expected_tip_value || parent_value != expected_parent_value)) {
    fprintf(stderr, "unexpected values: tip = %" PRId64 ", first parent = %" PRId64 "\n",
            tip_value, parent_value);
    return false;
  }
  return ok;
}

int main(int argc, char **argv) {
  if (argc != 3 || argv[1][0] == '\0' || argv[2][0] == '\0' || strcmp(argv[1], argv[2]) == 0) {
    fputs("usage: transfer_history SOURCE_REPO DESTINATION_REPO\n"
          "Use two distinct unused paths with existing parent directories.\n", stderr);
    return EXIT_FAILURE;
  }

  dml_repo *source = NULL, *destination = NULL;
  dml_error error = {0};
  dml_buffer bundle = {0};
  dml_object_id parent, tip, imported;
  const int64_t older_value = 42, newer_value = 43;
  int result = EXIT_FAILURE;

  if (!create_repo(argv[1], &source, &error) ||
      !write_revision(source, older_value, NULL, &parent, &error) ||
      !write_revision(source, newer_value, &parent, &tip, &error) ||
      !check(dml_repo_export_commit(source, &tip, &bundle, &error), "export tip", &error) ||
      !close_repo(&source, &error) || !create_repo(argv[2], &destination, &error)) goto cleanup;

  const dml_bytes input = {bundle.data, bundle.len};
  if (!check(dml_repo_import_commit(destination, input, &imported, &error), "import tip", &error)) {
    goto cleanup;
  }
  if (!same_id(&tip, &imported)) {
    fputs("import returned a different commit ID\n", stderr);
    goto cleanup;
  }
  if (!destination_main_missing(destination, &error) ||
      !create_ref(destination, staging_ref, &imported, &error) || !close_repo(&destination, &error) ||
      !check(dml_repo_open(argv[2], NULL, &destination, &error), "reopen staged destination", &error) ||
      !destination_main_missing(destination, &error) ||
      !verify_history(destination, staging_ref, &tip, &parent, newer_value, older_value, &error)) {
    goto cleanup;
  }
  /* Publish the immutable commit just inspected, not a fresh lookup of the staging ref. */
  if (!create_ref(destination, main_ref, &imported, &error) || !close_repo(&destination, &error) ||
      !check(dml_repo_open(argv[2], NULL, &destination, &error), "reopen published destination", &error) ||
      !verify_history(destination, main_ref, &tip, &parent, newer_value, older_value, &error)) {
    goto cleanup;
  }
  result = EXIT_SUCCESS;

cleanup:
  dml_buffer_free(&bundle);
  if (!close_repo(&source, &error)) result = EXIT_FAILURE;
  if (!close_repo(&destination, &error)) result = EXIT_FAILURE;
  if (result == EXIT_SUCCESS &&
      printf("main = %" PRId64 "\nfirst parent = %" PRId64 "\n", newer_value, older_value) < 0) {
    return EXIT_FAILURE;
  }
  return result;
}
