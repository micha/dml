#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../examples/transfer_example.h"

/* Public-API fixture driver. Each invocation makes or observes one test checkpoint. */
static bool print_id(const dml_object_id *id, const char *end, dml_error *error) {
  char text[DML_OBJECT_ID_HEX_SIZE + 1];
  return check(dml_object_id_format(id, text, error), "format fixture ID", error) &&
         printf("%s%s", text, end) >= 0;
}

static dml_status write_input_dag(dml_txn *txn, int64_t value, dml_object_id *dag, dml_error *error) {
  const dml_datum_input primary = {.kind = DML_DATUM_I64, .value.i64 = value};
  const dml_datum_input alternate = {.kind = DML_DATUM_I64, .value.i64 = value + 100};
  dml_object_id datum, root, other;
  dml_status status = lineage_put_literal(txn, &primary, &datum, &root, error);
  if (status == DML_OK) status = lineage_put_literal(txn, &alternate, &datum, &other, error);
  if (status != DML_OK) return status;
  const dml_dag_binding bindings[] = {{lineage_name("alternate-value"), other}, {value_name, root}};
  const dml_object_input graph = {.type = DML_REC_DAG, .value.dag = {root, bindings, 2}};
  return lineage_put_object(txn, &graph, dag, error);
}

static bool write_input_tip(dml_repo *repo, const dml_object_id *parent, dml_object_id *tip, dml_error *error) {
  dml_txn *txn = NULL;
  dml_object_id primary, alternate, tree;
  bool ok = check(dml_txn_begin(repo, DML_TXN_WRITE, &txn, error), "begin fixture tip write", error) &&
            check(write_input_dag(txn, 43, &primary, error), "write primary input DAG", error) &&
            check(write_input_dag(txn, 243, &alternate, error), "write alternate input DAG", error);
  if (ok) {
    const dml_tree_entry entries[] = {{lineage_name("alternate-snapshot"), alternate}, {snapshot_name, primary}};
    const dml_object_input snapshot = {.type = DML_REC_TREE, .value.tree = {entries, 2}};
    ok = check(lineage_put_object(txn, &snapshot, &tree, error), "write fixture input tree", error);
  }
  if (ok) {
    const dml_object_input revision = {.type = DML_REC_COMMIT, .value.commit = {tree, {parent, 1}}};
    ok = check(lineage_put_object(txn, &revision, tip, error), "write fixture tip", error) &&
         check(dml_txn_ref_update(txn, main_ref, tip, error), "advance fixture main", error) &&
         check(dml_txn_commit(&txn, error), "commit fixture tip", error);
  }
  dml_txn_abort(&txn);
  return ok;
}

static bool stage_input(dml_repo *repo, const char *path, dml_error *error) {
  uint8_t bytes[4096]; /* The tiny, fixed seed history must fit in this array. */
  FILE *file = fopen(path, "rb");
  if (file == NULL) return false;
  size_t len = fread(bytes, 1, sizeof(bytes), file);
  bool ok = feof(file) && !ferror(file);
  if (fclose(file) != 0) ok = false;
  dml_object_id imported;
  return ok && check(dml_repo_import_commit_staged(repo, (dml_bytes){bytes, len}, lineage_name("incoming"),
                                                   &imported, error), "stage fixture input", error);
}

static bool compete(dml_repo *repo, dml_error *error) {
  dml_txn *txn = NULL;
  dml_buffer packed = {0};
  dml_object_view view;
  dml_object_id original, parent, competitor;
  bool ok = check(dml_txn_begin(repo, DML_TXN_READ, &txn, error), "begin competitor read", error) &&
            check(dml_txn_ref_get(txn, main_ref, &original, error), "read fixture main", error) &&
            check(lineage_get_object(txn, DML_REC_COMMIT, &original, &packed, &view, error), "read main commit", error) &&
            check(dml_object_view_parent(&view, 0, &parent, error), "read fixture parent", error);
  dml_txn_abort(&txn);
  dml_buffer_free(&packed);
  /* A sibling, so the original tip stops being reachable from main. */
  return ok && write_revision(repo, 47, &parent, &competitor, error) && print_id(&competitor, "\n", error);
}

enum { INPUT_BINDING, INPUT_ENTRY, OPERATION, REQUEST_FIELD_COUNT };
static const char *const request_names[] = {"input-binding", "input-entry", "operation"};

typedef struct {
  dml_buffer records[REQUEST_FIELD_COUNT];
  dml_bytes fields[REQUEST_FIELD_COUNT]; /* Borrow the records above. */
  lineage_input input;
} fixture_request;

static void free_request(fixture_request *request) {
  for (size_t i = 0; i < REQUEST_FIELD_COUNT; ++i) dml_buffer_free(&request->records[i]);
}

/* Inspect the stored objects without invoking the workflow's request decoder. */
static dml_status read_request(dml_txn *txn, const dml_object_id *id, fixture_request *request,
                               dml_error *error) {
  dml_buffer packed = {0};
  dml_object_view graph;
  dml_object_id tree, parent, dag;
  dml_status status = lineage_read_revision(txn, id, &tree, &parent, error);
  if (status == DML_OK) status = lineage_find_dag(txn, &tree, lineage_name("request-v1"), true, &dag, error);
  if (status == DML_OK) status = lineage_get_object(txn, DML_REC_DAG, &dag, &packed, &graph, error);
  if (status == DML_OK && graph.count != REQUEST_FIELD_COUNT) {
    status = lineage_error(DML_INVALID_PAYLOAD, "expected three fixture request bindings", error);
  }
  for (size_t i = 0; status == DML_OK && i < REQUEST_FIELD_COUNT; ++i) {
    dml_object_id node, datum;
    dml_datum_view view;
    status = dml_txn_lookup_node(txn, &dag, lineage_name(request_names[i]), &node, error);
    if (status == DML_OK && i == OPERATION && !same_id(&node, &graph.reference)) {
      status = lineage_error(DML_INVALID_PAYLOAD, "request operation is not the fixture DAG root", error);
    }
    if (status == DML_OK) {
      status = lineage_get_literal(txn, &node, DML_DATUM_STRING, &datum, &request->records[i], &view, error);
      if (status == DML_OK) request->fields[i] = (dml_bytes){view.payload, view.payload_len};
    }
  }
  dml_buffer_free(&packed);
  if (status == DML_OK) {
    status = lineage_read_input(txn, &parent, request->fields[INPUT_ENTRY], request->fields[INPUT_BINDING],
                                &request->input, error);
  }
  return status;
}

static bool observe_request(dml_txn *txn, dml_bytes ref, dml_error *error) {
  dml_object_id id;
  fixture_request observed = {0};
  bool ok = check(dml_txn_ref_get(txn, ref, &id, error), "read fixture request ref", error) &&
            check(read_request(txn, &id, &observed, error), "read fixture request", error);
  if (ok) {
    const dml_bytes operation = observed.fields[OPERATION], entry = observed.fields[INPUT_ENTRY],
                    binding = observed.fields[INPUT_BINDING];
    ok = print_id(&id, " ", error) && print_id(&observed.input.commit, " ", error) &&
         print_id(&observed.input.datum, " ", error) &&
         printf("%" PRId64 " %.*s %.*s %.*s\n", observed.input.value,
                (int)operation.len, (const char *)operation.data, (int)entry.len, (const char *)entry.data,
                (int)binding.len, (const char *)binding.data) >= 0;
  }
  free_request(&observed);
  return ok;
}

static bool observe_result(dml_txn *txn, dml_bytes ref, dml_error *error) {
  dml_object_id id, tree, request;
  fixture_request requested = {0};
  lineage_observation observed = {0};
  bool ok = check(dml_txn_ref_get(txn, ref, &id, error), "read fixture result ref", error) &&
            check(lineage_read_revision(txn, &id, &tree, &request, error), "read fixture result commit", error) &&
            check(read_request(txn, &request, &requested, error), "read fixture result request", error) &&
            check(lineage_read_result(txn, &tree, &observed, error), "read fixture lineage", error);
  if (ok) {
    ok = print_id(&id, " ", error) && print_id(&request, " ", error) &&
         print_id(&requested.input.commit, " ", error) && print_id(&requested.input.datum, " ", error) &&
         print_id(&observed.output_datum, " ", error) && print_id(&observed.implementation_datum, " ", error) &&
         printf("%" PRId64 " %" PRId64 " %.*s\n", requested.input.value, observed.output,
                (int)observed.implementation.len, (const char *)observed.implementation.data) >= 0;
  }
  free_request(&requested);
  dml_buffer_free(&observed.implementation_record);
  return ok;
}

static bool read_fixture(dml_repo *repo, const char *command, const char *argument, dml_error *error) {
  dml_txn *txn = NULL;
  if (!check(dml_txn_begin(repo, DML_TXN_READ, &txn, error), "begin fixture read", error)) return false;
  bool ok;
  if (strcmp(command, "ref") == 0) {
    dml_object_id id;
    dml_status status = dml_txn_ref_get(txn, lineage_name(argument), &id, error);
    ok = status == DML_NOT_FOUND ? puts("missing") >= 0 :
         check(status, "read fixture ref", error) && print_id(&id, "\n", error);
  } else if (strcmp(command, "datum") == 0) {
    dml_object_id id;
    dml_buffer packed = {0};
    ok = check(dml_object_id_parse(argument, strlen(argument), &id, error), "parse fixture datum", error);
    if (ok) {
      dml_status status = dml_txn_get_datum(txn, &id, &packed, error);
      ok = status == DML_NOT_FOUND ? puts("missing") >= 0 :
           check(status, "read fixture datum", error) && puts("present") >= 0;
    }
    dml_buffer_free(&packed);
  } else if (strcmp(command, "request") == 0) {
    ok = observe_request(txn, lineage_name(argument), error);
  } else {
    ok = observe_result(txn, lineage_name(argument), error);
  }
  dml_txn_abort(&txn);
  return ok;
}

static bool mutate_fixture(dml_repo *repo, const char *command, char **args, dml_error *error) {
  dml_txn *txn = NULL;
  if (!check(dml_txn_begin(repo, DML_TXN_WRITE, &txn, error), "begin fixture mutation", error)) return false;
  bool ok;
  if (strcmp(command, "collect") == 0) {
    size_t removed;
    ok = check(dml_txn_collect_garbage(txn, &removed, error), "collect fixture garbage", error) &&
         check(dml_txn_commit(&txn, error), "commit fixture collection", error) &&
         printf("%zu\n", removed) >= 0;
  } else if (strcmp(command, "orphan") == 0) {
    const dml_datum_input datum = {.kind = DML_DATUM_I64, .value.i64 = -999};
    dml_buffer packed = {0};
    dml_object_id id;
    ok = check(dml_datum_encode(&datum, &packed, error), "encode orphan datum", error) &&
         check(dml_txn_put_datum(txn, packed.data, packed.len, &id, error), "store orphan datum", error) &&
         check(dml_txn_commit(&txn, error), "commit fixture orphan", error) && print_id(&id, "\n", error);
    dml_buffer_free(&packed);
  } else {
    dml_object_id id;
    ok = check(dml_object_id_parse(args[1], strlen(args[1]), &id, error), "parse replacement ref target", error) &&
         check(dml_txn_ref_update(txn, lineage_name(args[0]), &id, error), "retarget fixture ref", error) &&
         check(dml_txn_commit(&txn, error), "commit fixture retarget", error);
  }
  dml_txn_abort(&txn);
  return ok;
}

static bool export_fixture(dml_repo *repo, const dml_object_id *id, const char *path, dml_error *error) {
  dml_buffer bundle = {0};
  bool ok = check(dml_repo_export_commit(repo, id, &bundle, error), "export fixture bundle", error);
  if (ok) {
    FILE *file = fopen(path, "wbx");
    if (file == NULL) {
      perror(path);
      ok = false;
    } else {
      ok = fwrite(bundle.data, 1, bundle.len, file) == bundle.len;
      if (fclose(file) != 0) ok = false;
      if (!ok) fprintf(stderr, "cannot write fixture bundle: %s\n", path);
    }
  }
  dml_buffer_free(&bundle);
  return ok && print_id(id, "\n", error);
}

static bool forge_result(dml_repo *repo, const char *path, dml_error *error) {
  dml_txn *txn = NULL;
  dml_object_id parent;
  lineage_candidate candidate = {0};
  /* The scalar output is correct for the default request, but the claimed operation is not. */
  bool ok = check(dml_txn_begin(repo, DML_TXN_WRITE, &txn, error), "begin fixture result write", error) &&
            check(dml_txn_ref_get(txn, lineage_name("incoming"), &parent, error), "read fixture request parent", error) &&
            check(lineage_write_candidate(txn, &parent, 44, lineage_name("example.subtract-one@1"),
                                          &candidate, error), "write fixture result", error) &&
            check(dml_txn_ref_create(txn, lineage_name("fixture-result"), &candidate.commit, error),
                  "pin fixture result", error) &&
            check(dml_txn_commit(&txn, error), "commit fixture result", error);
  dml_txn_abort(&txn);
  return ok && export_fixture(repo, &candidate.commit, path, error);
}

static dml_status write_unsupported_request(dml_txn *txn, const dml_object_id *parent,
                                            dml_object_id *commit, dml_error *error) {
  const char *values[] = {"value", "snapshot", "example.unknown@1"};
  dml_dag_binding bindings[REQUEST_FIELD_COUNT];
  for (size_t i = 0; i < REQUEST_FIELD_COUNT; ++i) {
    const dml_datum_input text = {.kind = DML_DATUM_STRING, .value.bytes = lineage_name(values[i])};
    dml_object_id datum;
    bindings[i].name = lineage_name(request_names[i]);
    dml_status status = lineage_put_literal(txn, &text, &datum, &bindings[i].node, error);
    if (status != DML_OK) return status;
  }
  dml_object_id dag, tree;
  const dml_object_input graph = {
    .type = DML_REC_DAG, .value.dag = {bindings[OPERATION].node, bindings, REQUEST_FIELD_COUNT}
  };
  dml_status status = lineage_put_object(txn, &graph, &dag, error);
  if (status != DML_OK) return status;
  const dml_tree_entry entry = {lineage_name("request-v1"), dag};
  const dml_object_input snapshot = {.type = DML_REC_TREE, .value.tree = {&entry, 1}};
  status = lineage_put_object(txn, &snapshot, &tree, error);
  if (status != DML_OK) return status;
  const dml_object_input revision = {.type = DML_REC_COMMIT, .value.commit = {tree, {parent, 1}}};
  return lineage_put_object(txn, &revision, commit, error);
}

static bool forge_request(dml_repo *repo, const char *path, dml_error *error) {
  dml_txn *txn = NULL;
  dml_object_id parent, id;
  bool ok = check(dml_txn_begin(repo, DML_TXN_WRITE, &txn, error), "begin fixture request write", error) &&
            check(dml_txn_ref_get(txn, main_ref, &parent, error), "read fixture input parent", error) &&
            check(write_unsupported_request(txn, &parent, &id, error), "write fixture request", error) &&
            check(dml_txn_ref_create(txn, lineage_name("fixture-request"), &id, error), "pin fixture request", error) &&
            check(dml_txn_commit(&txn, error), "commit fixture request", error);
  dml_txn_abort(&txn);
  return ok && export_fixture(repo, &id, path, error);
}

int main(int argc, char **argv) {
  if (argc < 3) return EXIT_FAILURE;
  const char *cmd = argv[1], *path = argv[2];
  const bool seed = argc == 4 && strcmp(cmd, "seed") == 0;
  const bool stage = argc == 4 && strcmp(cmd, "stage-input") == 0;
  const bool read = argc == 4 && (strcmp(cmd, "ref") == 0 || strcmp(cmd, "datum") == 0 ||
                                  strcmp(cmd, "request") == 0 || strcmp(cmd, "result") == 0);
  const bool fake_request = argc == 4 && strcmp(cmd, "forge-request") == 0;
  const bool fake_result = argc == 4 && strcmp(cmd, "forge-result") == 0;
  const bool mutate = (argc == 3 && (strcmp(cmd, "collect") == 0 || strcmp(cmd, "orphan") == 0)) ||
                      (argc == 5 && strcmp(cmd, "retarget") == 0);
  const bool change = argc == 3 && strcmp(cmd, "compete") == 0;
  if (!seed && !stage && !read && !mutate && !change && !fake_request && !fake_result) return EXIT_FAILURE;

  dml_repo *repo = NULL;
  dml_error error = {0};
  bool ok = seed || stage ? create_repo(path, &repo, &error) :
                           check(dml_repo_open(path, NULL, &repo, &error), path, &error);
  if (ok && seed) {
    dml_object_id parent, tip;
    ok = write_revision(repo, strcmp(argv[3], "alternate") == 0 ? 41 : 42, NULL, &parent, &error) &&
         write_input_tip(repo, &parent, &tip, &error) && print_id(&tip, "\n", &error) &&
         print_id(&parent, "\n", &error);
  } else if (ok && stage) {
    ok = stage_input(repo, argv[3], &error);
  } else if (ok && read) {
    ok = read_fixture(repo, cmd, argv[3], &error);
  } else if (ok && mutate) {
    ok = mutate_fixture(repo, cmd, argv + 3, &error);
  } else if (ok && fake_request) {
    ok = forge_request(repo, argv[3], &error);
  } else if (ok && fake_result) {
    ok = forge_result(repo, argv[3], &error);
  } else if (ok) {
    ok = compete(repo, &error);
  }
  if (!close_repo(&repo, &error)) ok = false;
  return ok ? EXIT_SUCCESS : EXIT_FAILURE;
}
