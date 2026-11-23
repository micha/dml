#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "lineage.h"

static const dml_bytes main_ref = {(const uint8_t *)"main", sizeof("main") - 1};
static const dml_bytes staging_ref = {(const uint8_t *)"incoming", sizeof("incoming") - 1};
static const dml_bytes pin_ref = {(const uint8_t *)"result-pin", sizeof("result-pin") - 1};
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
  return check(lineage_put_object(txn, input, id, error), operation, error);
}

static bool write_snapshot(dml_txn *txn, int64_t value, const dml_object_id *parent,
                           dml_object_id *commit, dml_error *error) {
  dml_object_id datum, node, dag, tree;
  const dml_datum_input number = {.kind = DML_DATUM_I64, .value.i64 = value};
  if (!check(lineage_put_literal(txn, &number, &datum, &node, error), "store input literal", error)) {
    return false;
  }

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

static bool ref_missing(dml_repo *repo, dml_bytes ref, dml_error *error) {
  dml_txn *txn = NULL;
  if (!check(dml_txn_begin(repo, DML_TXN_READ, &txn, error), "begin ref check", error)) return false;
  dml_object_id observed;
  dml_status status = dml_txn_ref_get(txn, ref, &observed, error);
  dml_txn_abort(&txn);
  if (status == DML_NOT_FOUND) return true;
  if (status == DML_OK) {
    fprintf(stderr, "unexpected ref exists: %.*s\n", (int)ref.len, (const char *)ref.data);
    return false;
  }
  return check(status, "check ref absence", error);
}

static bool create_ref(dml_repo *repo, dml_bytes ref, const dml_object_id *tip, dml_error *error) {
  dml_txn *txn = NULL;
  bool ok = check(dml_txn_begin(repo, DML_TXN_WRITE, &txn, error), "begin destination write", error) &&
            check(dml_txn_ref_create(txn, ref, tip, error), "create destination ref", error) &&
            check(dml_txn_commit(&txn, error), "commit destination write", error);
  dml_txn_abort(&txn);
  return ok;
}

static bool read_first_parent(dml_txn *txn, const dml_object_id *id, dml_object_id *parent,
                              dml_error *error) {
  dml_buffer packed = {0};
  dml_object_view view;
  bool ok = check(lineage_get_object(txn, DML_REC_COMMIT, id, &packed, &view, error),
                  "read commit", error) &&
            check(dml_object_view_parent(&view, 0, parent, error), "read first parent", error);
  dml_buffer_free(&packed);
  return ok;
}

static bool verify_history(dml_repo *repo, dml_bytes ref, const dml_object_id *expected_tip,
                            const dml_object_id *expected_parent, int64_t expected_tip_value,
                            int64_t expected_parent_value, lineage_input *selected,
                            dml_error *error) {
  dml_txn *txn = NULL;
  dml_object_id tip, parent;
  bool ok = check(dml_txn_begin(repo, DML_TXN_READ, &txn, error), "begin history read", error) &&
            check(dml_txn_ref_get(txn, ref, &tip, error), "resolve destination ref", error) &&
            read_first_parent(txn, &tip, &parent, error);
  if (ok && (!same_id(&tip, expected_tip) || !same_id(&parent, expected_parent))) {
    fputs("destination tip or first parent differs from the source\n", stderr);
    ok = false;
  }
  lineage_input observed_tip, observed_parent;
  if (ok) {
    ok = check(lineage_read_input(txn, &tip, snapshot_name, value_name, &observed_tip, error),
               "read tip value", error) &&
         check(lineage_read_input(txn, &parent, snapshot_name, value_name, &observed_parent, error),
               "read parent value", error);
  }
  dml_txn_abort(&txn);
  if (ok && (observed_tip.value != expected_tip_value || observed_parent.value != expected_parent_value)) {
    fprintf(stderr, "unexpected values: tip = %" PRId64 ", first parent = %" PRId64 "\n",
            observed_tip.value, observed_parent.value);
    return false;
  }
  if (ok && selected != NULL) *selected = observed_tip;
  return ok;
}

static dml_status add_one(int64_t input, int64_t *output) {
  if (input == INT64_MAX) return DML_INVALID_BOUNDS;
  *output = input + 1;
  return DML_OK;
}

static dml_bytes implementation_id(void) {
  return lineage_name("example.add-one@1");
}

/* Inspect the supplied ID directly unless a local ref is explicitly requested. */
static bool verify_lineage(dml_repo *repo, dml_bytes ref, dml_object_id *tip, const lineage_input *input,
                           const lineage_candidate *candidate, dml_error *error) {
  lineage_observation observed = {0};
  dml_txn *txn = NULL;
  bool ok = check(dml_txn_begin(repo, DML_TXN_READ, &txn, error), "begin lineage read", error);
  if (ok && ref.len != 0) {
    ok = check(dml_txn_ref_get(txn, ref, tip, error), "resolve result ref", error);
  }
  if (ok) {
    ok = check(lineage_inspect(txn, tip, snapshot_name, value_name, &observed, error), "read lineage", error);
  }
  dml_txn_abort(&txn);
  if (ok && (!same_id(&observed.commit, &candidate->commit) ||
             !same_id(&observed.input.commit, &input->commit) ||
             !same_id(&observed.input.datum, &input->datum) || observed.input.value != input->value ||
             !same_id(&observed.output_datum, &candidate->output_datum) || observed.output != 44 ||
             !same_id(&observed.implementation_datum, &candidate->implementation_datum) ||
             !lineage_equal(observed.implementation, implementation_id()))) {
    fputs("persisted result or lineage differs from the recorded computation\n", stderr);
    ok = false;
  }
  if (ok) *tip = observed.commit;
  dml_buffer_free(&observed.implementation_record);
  return ok;
}

static bool run_lineage(dml_repo **repo, const char *path, const lineage_input *input,
                        lineage_candidate *candidate, dml_object_id *pinned, dml_error *error) {
  return check(lineage_record(*repo, input, implementation_id(), add_one, candidate, error),
               "record result", error) &&
         check(candidate->completion, "commit result and pin", error) && close_repo(repo, error) &&
         check(dml_repo_open(path, NULL, repo, error), "reopen result repository", error) &&
         verify_lineage(*repo, pin_ref, pinned, input, candidate, error) && ref_missing(*repo, main_ref, error);
}

static bool return_result(dml_repo **source, const char *path, dml_repo *destination,
                          const dml_object_id *pinned, const lineage_candidate *candidate,
                          const lineage_input *input, dml_error *error) {
  dml_buffer bundle = {0};
  dml_object_id inspected;
  bool ok = check(dml_repo_export_commit(destination, pinned, &bundle, error), "export pinned result", error) &&
            check(dml_repo_open(path, NULL, source, error), "open original source", error) &&
            check(dml_repo_import_commit(*source, (dml_bytes){bundle.data, bundle.len}, &inspected, error),
                  "import result into source", error);
  dml_buffer_free(&bundle);
  if (!ok || !ref_missing(*source, pin_ref, error) ||
      !verify_lineage(*source, (dml_bytes){0}, &inspected, input, candidate, error)) return false;

  /* The original source main was the input tip. Compare and update atomically;
   * publish the ID we inspected, not a fresh ref lookup. */
  dml_txn *txn = NULL;
  lineage_publication publication;
  return check(dml_txn_begin(*source, DML_TXN_WRITE, &txn, error), "begin result publication", error) &&
         check(lineage_publish_expected(&txn, main_ref, &input->commit, &inspected, &publication, error),
               "publish inspected result", error) &&
         close_repo(source, error) &&
         check(dml_repo_open(path, NULL, source, error), "reopen published source", error) &&
         verify_lineage(*source, main_ref, &inspected, input, candidate, error);
}

static bool release_staging(dml_repo **repo, const char *path, const lineage_input *input,
                            const lineage_candidate *candidate, dml_error *error) {
  dml_txn *txn = NULL;
  bool ok = check(dml_txn_begin(*repo, DML_TXN_WRITE, &txn, error), "begin staging release", error) &&
            check(dml_txn_ref_delete_expected(txn, staging_ref, &input->commit, error),
                  "release inspected staging ref", error) &&
            check(dml_txn_commit(&txn, error), "commit staging release", error);
  dml_txn_abort(&txn);
  dml_object_id pinned;
  return ok && close_repo(repo, error) &&
         check(dml_repo_open(path, NULL, repo, error), "reopen after staging release", error) &&
         ref_missing(*repo, staging_ref, error) && ref_missing(*repo, main_ref, error) &&
         verify_lineage(*repo, pin_ref, &pinned, input, candidate, error);
}

int main(int argc, char **argv) {
  const bool round_trip = argc > 1 && strcmp(argv[1], "--round-trip") == 0;
  const bool record_lineage = round_trip || (argc > 1 && strcmp(argv[1], "--lineage") == 0);
  const int first_path = record_lineage ? 2 : 1;
  if (argc != first_path + 2 || argv[first_path][0] == '\0' || argv[first_path + 1][0] == '\0' ||
      strcmp(argv[first_path], argv[first_path + 1]) == 0) {
    fputs("usage: transfer_history [--lineage | --round-trip] SOURCE_REPO DESTINATION_REPO\n"
          "Use two distinct unused paths with existing parent directories.\n", stderr);
    return EXIT_FAILURE;
  }

  dml_repo *source = NULL, *destination = NULL;
  dml_error error = {0};
  dml_buffer bundle = {0};
  dml_object_id parent, tip, imported;
  const int64_t older_value = 42, newer_value = 43;
  int result = EXIT_FAILURE;

  const char *source_path = argv[first_path], *destination_path = argv[first_path + 1];
  if (!create_repo(source_path, &source, &error) ||
      !write_revision(source, older_value, NULL, &parent, &error) ||
      !write_revision(source, newer_value, &parent, &tip, &error) ||
      !check(dml_repo_export_commit(source, &tip, &bundle, &error), "export tip", &error) ||
      !close_repo(&source, &error) || !create_repo(destination_path, &destination, &error)) goto cleanup;

  const dml_bytes input = {bundle.data, bundle.len};
  if (!check(dml_repo_import_commit(destination, input, &imported, &error), "import tip", &error)) {
    goto cleanup;
  }
  if (!same_id(&tip, &imported)) {
    fputs("import returned a different commit ID\n", stderr);
    goto cleanup;
  }
  dml_buffer_free(&bundle);
  lineage_input selected;
  if (!ref_missing(destination, main_ref, &error) ||
      !create_ref(destination, staging_ref, &imported, &error) || !close_repo(&destination, &error) ||
      !check(dml_repo_open(destination_path, NULL, &destination, &error), "reopen staged destination", &error) ||
      !ref_missing(destination, main_ref, &error) ||
      !verify_history(destination, staging_ref, &tip, &parent, newer_value, older_value, &selected, &error)) {
    goto cleanup;
  }
  if (record_lineage) {
    lineage_candidate candidate = {0};
    dml_object_id pinned;
    if (!run_lineage(&destination, destination_path, &selected, &candidate, &pinned, &error) ||
        (round_trip &&
         (!return_result(&source, source_path, destination, &pinned, &candidate, &selected, &error) ||
          !release_staging(&destination, destination_path, &selected, &candidate, &error)))) {
      goto cleanup;
    }
  } else {
    /* Publish the immutable commit just inspected, not a fresh lookup of the staging ref. */
    if (!create_ref(destination, main_ref, &selected.commit, &error) || !close_repo(&destination, &error) ||
        !check(dml_repo_open(destination_path, NULL, &destination, &error), "reopen published destination", &error) ||
        !verify_history(destination, main_ref, &tip, &parent, newer_value, older_value, NULL, &error)) {
      goto cleanup;
    }
  }
  result = EXIT_SUCCESS;

cleanup:
  dml_buffer_free(&bundle);
  if (!close_repo(&source, &error)) result = EXIT_FAILURE;
  if (!close_repo(&destination, &error)) result = EXIT_FAILURE;
  if (result == EXIT_SUCCESS) {
    int printed;
    if (round_trip) {
      printed = puts("source main = 44\ndestination result-pin = 44\ndestination incoming released\n"
                     "input = 43\nimplementation = example.add-one@1");
    } else if (record_lineage) {
      printed = puts("result-pin = 44\ninput = 43\nimplementation = example.add-one@1");
    } else {
      printed = printf("main = %" PRId64 "\nfirst parent = %" PRId64 "\n", newer_value, older_value);
    }
    if (printed < 0) return EXIT_FAILURE;
  }
  return result;
}
