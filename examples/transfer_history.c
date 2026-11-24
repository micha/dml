#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "transfer_example.h"

static const dml_bytes staging_ref = {(const uint8_t *)"incoming", sizeof("incoming") - 1};
static const dml_bytes returned_ref = {(const uint8_t *)"returned", sizeof("returned") - 1};
static const dml_bytes pin_ref = {(const uint8_t *)"result-pin", sizeof("result-pin") - 1};

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

static bool release_ref(dml_repo *repo, dml_bytes ref, const dml_object_id *expected, dml_error *error) {
  dml_txn *txn = NULL;
  bool ok = check(dml_txn_begin(repo, DML_TXN_WRITE, &txn, error), "begin staging release", error) &&
            check(dml_txn_ref_delete_expected(txn, ref, expected, error), "release inspected staging ref", error) &&
            check(dml_txn_commit(&txn, error), "commit staging release", error);
  dml_txn_abort(&txn);
  return ok;
}

static bool collect_retained(dml_repo *repo, const char *path, dml_error *error) {
  dml_txn *txn = NULL;
  size_t removed;
  bool ok = check(dml_txn_begin(repo, DML_TXN_WRITE, &txn, error), "begin collection", error) &&
            check(dml_txn_collect_garbage(txn, &removed, error), "collect unreachable objects", error);
  if (ok && removed != 0) {
    fprintf(stderr, "%s: expected a fully retained repository, found %zu unreachable objects\n", path, removed);
    ok = false;
  }
  if (ok) ok = check(dml_txn_commit(&txn, error), "commit collection", error);
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
  return check(lineage_record(*repo, &input->commit, input->value, implementation_id(), add_one, candidate, error),
               "record result", error) &&
         check(candidate->completion, "commit result and pin", error) && close_repo(repo, error) &&
         check(dml_repo_open(path, NULL, repo, error), "reopen result repository", error) &&
         verify_lineage(*repo, pin_ref, pinned, input, candidate, error) && ref_missing(*repo, main_ref, error);
}

static bool return_result(dml_repo **source, const char *path, dml_repo *destination,
                          const dml_object_id *pinned, const lineage_candidate *candidate,
                          const lineage_input *input, bool collect, dml_error *error) {
  dml_buffer bundle = {0};
  dml_object_id inspected;
  bool ok = check(dml_repo_export_commit(destination, pinned, &bundle, error), "export pinned result", error) &&
            check(dml_repo_open(path, NULL, source, error), "open original source", error) &&
            check(dml_repo_import_commit_staged(*source, (dml_bytes){bundle.data, bundle.len},
                                                returned_ref, &inspected, error),
                  "import and stage result in source", error);
  dml_buffer_free(&bundle);
  if (!ok || (collect && !collect_retained(*source, path, error)) || !ref_missing(*source, pin_ref, error) ||
      !verify_lineage(*source, (dml_bytes){0}, &inspected, input, candidate, error)) return false;

  /* The original source main was the input tip. Compare and update atomically;
   * publish the ID we inspected, not a fresh ref lookup. */
  dml_txn *txn = NULL;
  lineage_publication publication;
  return check(dml_txn_begin(*source, DML_TXN_WRITE, &txn, error), "begin result publication", error) &&
         check(lineage_publish_expected(&txn, main_ref, &input->commit, &inspected, &publication, error),
               "publish inspected result", error) &&
         release_ref(*source, returned_ref, &inspected, error) && close_repo(source, error) &&
         check(dml_repo_open(path, NULL, source, error), "reopen published source", error) &&
         ref_missing(*source, returned_ref, error) &&
         verify_lineage(*source, main_ref, &inspected, input, candidate, error);
}

static bool release_staging(dml_repo **repo, const char *path, const lineage_input *input,
                            const lineage_candidate *candidate, dml_error *error) {
  dml_object_id pinned;
  return release_ref(*repo, staging_ref, &input->commit, error) && close_repo(repo, error) &&
         check(dml_repo_open(path, NULL, repo, error), "reopen after staging release", error) &&
         ref_missing(*repo, staging_ref, error) && ref_missing(*repo, main_ref, error) &&
         verify_lineage(*repo, pin_ref, &pinned, input, candidate, error);
}

static bool collect_and_verify(dml_repo **repo, const char *path, dml_bytes ref,
                               const lineage_input *input, const lineage_candidate *candidate,
                               dml_error *error) {
  dml_object_id tip;
  return collect_retained(*repo, path, error) && close_repo(repo, error) &&
         check(dml_repo_open(path, NULL, repo, error), "reopen after collection", error) &&
         verify_lineage(*repo, ref, &tip, input, candidate, error);
}

int main(int argc, char **argv) {
  const bool round_trip = argc > 1 && strcmp(argv[1], "--round-trip") == 0;
  const bool collect = round_trip && argc > 2 && strcmp(argv[2], "--collect") == 0;
  const bool record_lineage = round_trip || (argc > 1 && strcmp(argv[1], "--lineage") == 0);
  const int first_path = collect ? 3 : record_lineage ? 2 : 1;
  if (argc != first_path + 2 || argv[first_path][0] == '\0' || argv[first_path + 1][0] == '\0' ||
      strcmp(argv[first_path], argv[first_path + 1]) == 0) {
    fputs("usage: transfer_history [--lineage | --round-trip [--collect]] SOURCE_REPO DESTINATION_REPO\n"
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
  if (!check(dml_repo_import_commit_staged(destination, input, staging_ref, &imported, &error),
             "import and stage tip", &error)) {
    goto cleanup;
  }
  if (!same_id(&tip, &imported)) {
    fputs("import returned a different commit ID\n", stderr);
    goto cleanup;
  }
  dml_buffer_free(&bundle);
  lineage_input selected;
  if ((collect && !collect_retained(destination, destination_path, &error)) || !close_repo(&destination, &error) ||
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
         (!return_result(&source, source_path, destination, &pinned, &candidate, &selected, collect, &error) ||
          !release_staging(&destination, destination_path, &selected, &candidate, &error)))) {
      goto cleanup;
    }
    if (collect &&
        (!collect_and_verify(&source, source_path, main_ref, &selected, &candidate, &error) ||
         !collect_and_verify(&destination, destination_path, pin_ref, &selected, &candidate, &error))) {
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
      printed = puts("source main = 44\ndestination result-pin = 44\n"
                     "source returned and destination incoming released\n"
                     "input = 43\nimplementation = example.add-one@1");
    } else if (record_lineage) {
      printed = puts("result-pin = 44\ninput = 43\nimplementation = example.add-one@1");
    } else {
      printed = printf("main = %" PRId64 "\nfirst parent = %" PRId64 "\n", newer_value, older_value);
    }
    if (printed < 0 || (collect && puts("collection removed 0 objects from each repository") < 0)) {
      return EXIT_FAILURE;
    }
  }
  return result;
}
