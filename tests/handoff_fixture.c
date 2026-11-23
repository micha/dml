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

static bool observe_result(dml_txn *txn, dml_bytes ref, dml_error *error) {
  dml_object_id id;
  lineage_observation observed = {0};
  bool ok = check(dml_txn_ref_get(txn, ref, &id, error), "read fixture result ref", error) &&
            check(lineage_inspect(txn, &id, snapshot_name, value_name, &observed, error),
                  "read fixture result", error);
  if (ok) {
    ok = print_id(&observed.commit, " ", error) && print_id(&observed.input.commit, " ", error) &&
         print_id(&observed.input.datum, " ", error) && print_id(&observed.output_datum, " ", error) &&
         print_id(&observed.implementation_datum, " ", error) &&
         printf("%" PRId64 " %" PRId64 " %.*s\n", observed.input.value, observed.output,
                (int)observed.implementation.len, (const char *)observed.implementation.data) >= 0;
  }
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

int main(int argc, char **argv) {
  if (argc < 3) return EXIT_FAILURE;
  const char *cmd = argv[1], *path = argv[2];
  const bool seed = argc == 4 && strcmp(cmd, "seed") == 0;
  const bool stage = argc == 4 && strcmp(cmd, "stage-input") == 0;
  const bool read = argc == 4 && (strcmp(cmd, "ref") == 0 || strcmp(cmd, "datum") == 0 || strcmp(cmd, "result") == 0);
  const bool mutate = (argc == 3 && (strcmp(cmd, "collect") == 0 || strcmp(cmd, "orphan") == 0)) ||
                      (argc == 5 && strcmp(cmd, "retarget") == 0);
  const bool change = argc == 3 && strcmp(cmd, "compete") == 0;
  if (!seed && !stage && !read && !mutate && !change) return EXIT_FAILURE;

  dml_repo *repo = NULL;
  dml_error error = {0};
  bool ok = seed || stage ? create_repo(path, &repo, &error) :
                           check(dml_repo_open(path, NULL, &repo, &error), path, &error);
  if (ok && seed) {
    dml_object_id parent, tip;
    ok = write_revision(repo, strcmp(argv[3], "alternate") == 0 ? 41 : 42, NULL, &parent, &error) &&
         write_revision(repo, 43, &parent, &tip, &error) && print_id(&tip, "\n", &error) &&
         print_id(&parent, "\n", &error);
  } else if (ok && stage) {
    ok = stage_input(repo, argv[3], &error);
  } else if (ok && read) {
    ok = read_fixture(repo, cmd, argv[3], &error);
  } else if (ok && mutate) {
    ok = mutate_fixture(repo, cmd, argv + 3, &error);
  } else if (ok) {
    ok = compete(repo, &error);
  }
  if (!close_repo(&repo, &error)) ok = false;
  return ok ? EXIT_SUCCESS : EXIT_FAILURE;
}
