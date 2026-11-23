#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "handoff_request.h"

static const dml_bytes request_pin = {(const uint8_t *)"request-pin", sizeof("request-pin") - 1};
static const dml_bytes incoming = {(const uint8_t *)"incoming", sizeof("incoming") - 1};
static const dml_bytes result_pin = {(const uint8_t *)"result-pin", sizeof("result-pin") - 1};
static const dml_bytes returned = {(const uint8_t *)"returned", sizeof("returned") - 1};

/* Regular binary files only. Bound the read by the bundle format's size limit. */
static bool read_bundle(const char *path, dml_buffer *out) {
  FILE *file = fopen(path, "rb");
  if (file == NULL) {
    perror(path);
    return false;
  }
  long size;
  bool ok = fseek(file, 0, SEEK_END) == 0 && (size = ftell(file)) > 0 &&
            size <= 64L * 1024 * 1024 && fseek(file, 0, SEEK_SET) == 0;
  if (ok) {
    out->len = (size_t)size;
    out->data = malloc(out->len);
    ok = out->data != NULL && fread(out->data, 1, out->len, file) == out->len &&
         fgetc(file) == EOF && !ferror(file);
  }
  if (fclose(file) != 0) ok = false;
  if (!ok) fprintf(stderr, "cannot read nonempty bundle of at most 64 MiB: %s\n", path);
  return ok;
}

static bool write_bundle(const char *path, const dml_buffer *bundle) {
  FILE *file = fopen(path, "wbx");
  if (file == NULL) {
    perror(path);
    return false;
  }
  bool ok = fwrite(bundle->data, 1, bundle->len, file) == bundle->len;
  if (fclose(file) != 0) ok = false;
  if (!ok) fprintf(stderr, "failed to write bundle; discard incomplete file: %s\n", path);
  return ok;
}

static bool export_file(dml_repo *repo, const dml_object_id *root, const char *path, dml_error *error) {
  dml_buffer bundle = {0};
  bool ok = check(dml_repo_export_commit(repo, root, &bundle, error), "export pinned commit", error) &&
            write_bundle(path, &bundle);
  dml_buffer_free(&bundle);
  return ok;
}

static bool stage_file(dml_repo *repo, const char *path, dml_bytes ref, dml_object_id *root,
                       dml_error *error) {
  dml_buffer bundle = {0};
  bool ok = read_bundle(path, &bundle) &&
            check(dml_repo_import_commit_staged(repo, (dml_bytes){bundle.data, bundle.len},
                                                ref, root, error), "stage bundle", error);
  dml_buffer_free(&bundle);
  return ok;
}

static bool pin_new_request(dml_txn *txn, char *const *spec, dml_object_id *id, dml_error *error) {
  const handoff_operation *operation = find_operation(lineage_name(spec[0]));
  if (operation == NULL) {
    fprintf(stderr, "unsupported request operation: %s\n", spec[0]);
    return false;
  }
  const dml_bytes entry = lineage_name(spec[1]), binding = lineage_name(spec[2]);
  dml_object_id snapshot;
  lineage_input input;
  return check(dml_txn_ref_get(txn, main_ref, &snapshot, error), "select main", error) &&
         check(read_selected_input(txn, &snapshot, entry, binding, &input, error), "select request input", error) &&
         check(write_request(txn, &snapshot, operation, entry, binding, id, error), "write request commit", error) &&
         check(dml_txn_ref_create(txn, request_pin, id, error), "pin request", error);
}

static bool select_request(dml_repo *repo, char *const *spec, dml_object_id *id, dml_error *error) {
  dml_txn *txn = NULL;
  if (!check(dml_txn_begin(repo, spec == NULL ? DML_TXN_READ : DML_TXN_WRITE, &txn, error),
             "begin request selection", error)) return false;
  dml_status status = dml_txn_ref_get(txn, request_pin, id, error);
  bool ok;
  if (spec == NULL) {
    ok = check(status, "recover request pin", error);
  } else if (status == DML_OK) {
    fputs("request-pin already exists; omit the operation and selector to resume\n", stderr);
    ok = false;
  } else if (status == DML_NOT_FOUND) {
    ok = pin_new_request(txn, spec, id, error) && check(dml_txn_commit(&txn, error), "commit request pin", error);
  } else {
    ok = check(status, "check existing request pin", error);
  }
  dml_txn_abort(&txn);
  return ok;
}

static bool make_or_recover_result(dml_repo *repo, const dml_object_id *imported, dml_object_id *result,
                                   dml_error *error) {
  dml_txn *txn = NULL;
  if (!check(dml_txn_begin(repo, DML_TXN_READ, &txn, error), "begin worker read", error)) return false;
  dml_object_id request;
  if (imported != NULL) {
    request = *imported;
  } else {
    dml_status status = dml_txn_ref_get(txn, result_pin, result, error);
    if (status != DML_NOT_FOUND) {
      dml_txn_abort(&txn);
      return check(status, "recover result pin", error);
    }
    if (!check(dml_txn_ref_get(txn, incoming, &request, error), "recover staged input", error)) {
      dml_txn_abort(&txn);
      return false;
    }
  }
  handoff_request selected;
  bool ok = check(read_request(txn, &request, &selected, error), "read exact computation request", error);
  dml_txn_abort(&txn);
  if (!ok) return false;

  lineage_candidate candidate = {0};
  if (!check(lineage_record(repo, &request, selected.input.value, lineage_name(selected.operation->id),
                            selected.operation->compute, &candidate, error), "record result", error) ||
      !check(candidate.completion, "commit result pin", error)) return false;
  *result = candidate.commit;
  return true;
}

static bool work(dml_repo *repo, const char *request_path, const char *result_path, dml_error *error) {
  dml_object_id imported, result;
  return (request_path == NULL || stage_file(repo, request_path, incoming, &imported, error)) &&
         make_or_recover_result(repo, request_path == NULL ? NULL : &imported, &result, error) &&
         export_file(repo, &result, result_path, error);
}

static bool inspect_result_tree(dml_txn *txn, const dml_object_id *tree, const dml_object_id *request_id,
                                lineage_observation *observation, dml_error *error) {
  handoff_request request;
  if (!check(read_request(txn, request_id, &request, error), "inspect computation request", error) ||
      !check(lineage_read_result(txn, tree, observation, error), "inspect result tree", error)) return false;
  if (!lineage_equal(observation->implementation, lineage_name(request.operation->id))) {
    fputs("result implementation does not match the requested operation\n", stderr);
    return false;
  }
  observation->input = request.input;
  return true;
}

static bool inspect_return(dml_repo *repo, const dml_object_id *imported, dml_object_id *request,
                           lineage_observation *observation, dml_error *error) {
  dml_txn *txn = NULL;
  dml_object_id tree, parent;
  bool ok = check(dml_txn_begin(repo, DML_TXN_READ, &txn, error), "begin result inspection", error) &&
            check(dml_txn_ref_get(txn, request_pin, request, error), "resolve original request pin", error) &&
            check(dml_txn_ref_get(txn, returned, &observation->commit, error), "resolve staged result", error);
  if (ok && imported != NULL && !same_id(&observation->commit, imported)) {
    fputs("returned ref changed after staging\n", stderr);
    ok = false;
  }
  if (ok) {
    ok = check(lineage_read_revision(txn, &observation->commit, &tree, &parent, error),
               "inspect exact result commit", error);
  }
  if (ok && !same_id(&parent, request)) {
    fputs("result parent does not match the original request\n", stderr);
    ok = false;
  }
  if (ok) ok = inspect_result_tree(txn, &tree, request, observation, error);
  dml_txn_abort(&txn);
  return ok;
}

static bool publish_inspected(dml_repo *repo, const dml_object_id *input,
                              const dml_object_id *request, const dml_object_id *result, dml_error *error) {
  dml_txn *txn = NULL;
  dml_object_id actual;
  bool ok = check(dml_txn_begin(repo, DML_TXN_WRITE, &txn, error), "begin publication", error) &&
            check(dml_txn_ref_get(txn, main_ref, &actual, error), "resolve main for publication", error);
  if (ok && !same_id(&actual, input)) {
    fputs("main no longer points to the original input snapshot\n", stderr);
    ok = false;
  }
  if (ok) {
    /* A moved or missing staging ref aborts the update too. No separate source
     * cleanup step is needed after a successful publication. */
    ok = check(dml_txn_ref_update(txn, main_ref, result, error), "publish inspected result", error) &&
         check(dml_txn_ref_delete_expected(txn, returned, result, error), "release returned", error) &&
         check(dml_txn_ref_delete_expected(txn, request_pin, request, error), "release request pin", error) &&
         check(dml_txn_commit(&txn, error), "commit publication and source cleanup", error);
  }
  dml_txn_abort(&txn);
  return ok;
}

static bool publish(dml_repo *repo, const char *result_path, dml_error *error) {
  dml_object_id imported, request;
  lineage_observation observation = {0};
  bool ok = (result_path == NULL || stage_file(repo, result_path, returned, &imported, error)) &&
            inspect_return(repo, result_path == NULL ? NULL : &imported, &request, &observation, error) &&
            publish_inspected(repo, &observation.input.commit, &request, &observation.commit, error);
  if (ok) {
    printf("published result: input = %" PRId64 ", output = %" PRId64 "\n",
           observation.input.value, observation.output);
  }
  dml_buffer_free(&observation.implementation_record);
  return ok;
}

static bool release_input(dml_repo *repo, dml_error *error) {
  dml_txn *txn = NULL;
  dml_object_id pinned, tree, request;
  lineage_observation observation = {0};
  /* Keep the result's retention root stable from inspection through release. */
  bool ok = check(dml_txn_begin(repo, DML_TXN_WRITE, &txn, error), "begin input cleanup", error) &&
            check(dml_txn_ref_get(txn, result_pin, &pinned, error), "resolve result pin", error) &&
            check(lineage_read_revision(txn, &pinned, &tree, &request, error), "read result parent", error) &&
            inspect_result_tree(txn, &tree, &request, &observation, error) &&
            check(dml_txn_ref_delete_expected(txn, incoming, &request, error),
                  "release inspected staging ref", error) &&
            check(dml_txn_commit(&txn, error), "commit input cleanup", error);
  dml_txn_abort(&txn);
  dml_buffer_free(&observation.implementation_record);
  return ok;
}

int main(int argc, char **argv) {
  const char *command = argc > 1 ? argv[1] : "";
  const bool requester = strcmp(command, "request") == 0 && (argc == 4 || argc == 7);
  const bool worker = strcmp(command, "work") == 0 && (argc == 4 || argc == 5);
  const bool stage = strcmp(command, "stage-result") == 0 && argc == 4;
  const bool publisher = strcmp(command, "publish") == 0 && (argc == 3 || argc == 4);
  const bool release = strcmp(command, "release-input") == 0 && argc == 3;
  if (!requester && !worker && !stage && !publisher && !release) {
    fputs("usage:\n"
          "  provenance_handoff request SOURCE REQUEST [OPERATION TREE-ENTRY BINDING]\n"
          "  provenance_handoff work WORKER RESULT [REQUEST]\n"
          "  provenance_handoff stage-result SOURCE RESULT\n"
          "  provenance_handoff publish SOURCE [RESULT]\n"
          "  provenance_handoff release-input WORKER\n", stderr);
    return EXIT_FAILURE;
  }
  const char *path = argv[2];
  dml_repo *repo = NULL;
  dml_error error = {0};
  bool ok = worker && argc == 5 ? create_repo(path, &repo, &error) :
                                  check(dml_repo_open(path, NULL, &repo, &error), path, &error);
  if (ok) {
    dml_object_id root;
    if (requester) ok = select_request(repo, argc == 7 ? argv + 4 : NULL, &root, &error) &&
                        export_file(repo, &root, argv[3], &error);
    else if (worker) ok = work(repo, argc == 5 ? argv[4] : NULL, argv[3], &error);
    else if (stage) ok = stage_file(repo, argv[3], returned, &root, &error);
    else if (publisher) ok = publish(repo, argc == 4 ? argv[3] : NULL, &error);
    else ok = release_input(repo, &error);
  }
  if (!close_repo(&repo, &error)) ok = false;
  return ok ? EXIT_SUCCESS : EXIT_FAILURE;
}
