#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#ifdef _WIN32
#include <direct.h>
#endif

#include "dml/repo.h"

static dml_bytes bytes(const char *text) {
  return (dml_bytes){.data = (const uint8_t *)text, .len = strlen(text)};
}

static int make_fixture_directory(const char *path) {
  /* Never open a preexisting repository for fixture creation. */
#ifdef _WIN32
  return _mkdir(path);
#else
  return mkdir(path, 0777);
#endif
}

static bool check_status(dml_status status, const dml_error *error, const char *operation) {
  if (status == DML_OK) return true;
  fprintf(stderr, "%s: %s (%d): %s\n", operation, dml_status_name(status),
          error->native_code, error->detail);
  return false;
}

static dml_status put_object(dml_txn *txn, const dml_object_input *input,
                             dml_object_id *id, dml_error *error) {
  dml_buffer record = {0};
  dml_status status = dml_object_encode(input, &record, error);
  if (status == DML_OK) {
    status = dml_txn_put_object(txn, input->type, record.data, record.len, id, error);
  }
  dml_buffer_free(&record);
  return status;
}

static bool seed_dag(dml_txn *txn, dml_object_id *id, dml_error *error) {
  const dml_datum_input datum = {.kind = DML_DATUM_I64, .value.i64 = 42};
  dml_buffer record = {0};
  dml_object_input node = {.type = DML_REC_NODE, .value.node.kind = DML_NODE_LITERAL};
  dml_object_input dag = {.type = DML_REC_DAG};
  bool stored = check_status(dml_datum_encode(&datum, &record, error), error, "encoding datum") &&
                check_status(dml_txn_put_datum(txn, record.data, record.len, &node.value.node.target,
                                               error), error, "storing datum") &&
                check_status(put_object(txn, &node, &dag.value.dag.root, error), error, "storing node") &&
                check_status(put_object(txn, &dag, id, error), error, "storing DAG");
  dml_buffer_free(&record);
  return stored;
}

static bool print_id(const dml_object_id *id) {
  char text[DML_OBJECT_ID_HEX_SIZE + 1];
  return dml_object_id_format(id, text, NULL) == DML_OK && printf(" %s", text) >= 0;
}

static bool seed_fixture(dml_repo *repo) {
  dml_txn *txn = NULL;
  dml_error error = {0};
  if (!check_status(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error), &error, "beginning fixture")) {
    return false;
  }

  const dml_object_input tree = {.type = DML_REC_TREE};
  dml_object_input commit = {.type = DML_REC_COMMIT};
  dml_object_id a, b, dag;
  bool seeded = check_status(put_object(txn, &tree, &commit.value.commit.tree, &error),
                             &error, "storing fixture tree") &&
                check_status(put_object(txn, &commit, &a, &error), &error, "storing fixture commit A");
  if (seeded) {
    /* Child B differs from its parent A while sharing the same tree. */
    commit.value.commit.parents = (dml_id_array){.items = &a, .count = 1};
    seeded = check_status(put_object(txn, &commit, &b, &error), &error, "storing fixture commit B") &&
             seed_dag(txn, &dag, &error);
  }
  if (!seeded) {
    dml_txn_abort(&txn);
    return false;
  }
  return check_status(dml_txn_commit(&txn, &error), &error, "committing fixture") &&
         printf("READY") >= 0 && print_id(&a) && print_id(&b) &&
         print_id(&commit.value.commit.tree) && print_id(&dag) && puts("") != EOF;
}

static bool parse_id(const char *text, dml_object_id *id) {
  dml_error error = {0};
  return check_status(dml_object_id_parse(text, strlen(text), id, &error), &error, "parsing ID");
}

static bool create_ref(dml_repo *repo, const char *name, const char *target_text) {
  dml_txn *txn = NULL;
  dml_error error = {0};
  dml_object_id target;
  if (!parse_id(target_text, &target) ||
      !check_status(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error), &error, "beginning ref create")) {
    return false;
  }
  dml_status create = dml_txn_ref_create(txn, bytes(name), &target, NULL);
  dml_status completed = dml_txn_commit(&txn, NULL);
  return printf("CREATE %s %s\n", dml_status_name(create), dml_status_name(completed)) >= 0;
}

static bool publish(dml_repo *repo, const char *name, const char *parent_text, const char *dag_text,
                    const char *finish, const char *extra_name) {
  dml_txn *txn = NULL;
  dml_error error = {0};
  dml_object_id parent, commit_id = {0};
  dml_tree_entry entry = {.name = bytes("snapshot")};
  if (!parse_id(parent_text, &parent) || !parse_id(dag_text, &entry.dag) ||
      !check_status(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error), &error, "beginning publication")) {
    return false;
  }

  const dml_object_input tree = {.type = DML_REC_TREE, .value.tree = {.items = &entry, .count = 1}};
  dml_object_input commit = {.type = DML_REC_COMMIT,
                             .value.commit.parents = {.items = &parent, .count = 1}};
  dml_status tree_status = put_object(txn, &tree, &commit.value.commit.tree, NULL);
  dml_status put_status = put_object(txn, &commit, &commit_id, NULL);
  dml_status update = dml_txn_ref_update(txn, bytes(name), &commit_id, NULL);
  const char *extra = *extra_name ?
    dml_status_name(dml_txn_ref_update(txn, bytes(extra_name), &commit_id, NULL)) : "none";
  const char *completion;
  if (strcmp(finish, "abort") == 0) {
    dml_txn_abort(&txn);
    completion = txn == NULL ? "aborted" : "active";
  } else {
    completion = dml_status_name(dml_txn_commit(&txn, NULL));
  }
  return printf("PUBLISH %s %s %s %s %s", dml_status_name(tree_status), dml_status_name(put_status),
                dml_status_name(update), extra, completion) >= 0 &&
         print_id(&commit.value.commit.tree) && print_id(&commit_id) && puts("") != EOF;
}

static bool print_commit(const dml_object_view *view) {
  if (!print_id(&view->reference)) return false;
  for (size_t i = 0; i < view->count; i++) {
    dml_object_id parent;
    dml_error error = {0};
    if (!check_status(dml_object_view_parent(view, i, &parent, &error), &error, "reading parent") ||
        !print_id(&parent)) {
      return false;
    }
  }
  return true;
}

static bool read_ref(dml_repo *repo, const char *name) {
  dml_txn *txn = NULL;
  dml_error error = {0};
  if (!check_status(dml_txn_begin(repo, DML_TXN_READ, &txn, &error), &error, "beginning ref read")) {
    return false;
  }
  dml_object_id tip = {0};
  dml_buffer record = {0};
  dml_object_view view = {0};
  dml_status get_ref = dml_txn_ref_get(txn, bytes(name), &tip, NULL);
  const char *get_object = "none", *decode = "none";
  if (get_ref == DML_OK) {
    dml_status get = dml_txn_get_object(txn, DML_REC_COMMIT, &tip, &record, NULL);
    get_object = dml_status_name(get);
    if (get == DML_OK) decode = dml_status_name(dml_object_decode(record.data, record.len, &view, NULL));
  }
  bool printed = printf("READ %s %s %s", dml_status_name(get_ref), get_object, decode) >= 0 &&
                 print_id(&tip) && print_commit(&view) && puts("") != EOF;
  dml_buffer_free(&record);
  dml_txn_abort(&txn);
  return printed;
}

int main(int argc, char **argv) {
  bool seed = argc == 3 && strcmp(argv[1], "seed") == 0;
  bool create = argc == 5 && strcmp(argv[1], "create") == 0;
  bool write = argc == 8 && strcmp(argv[1], "publish") == 0 &&
               (strcmp(argv[6], "commit") == 0 || strcmp(argv[6], "abort") == 0);
  bool read = argc == 4 && strcmp(argv[1], "read") == 0;
  if (!seed && !create && !write && !read) {
    fprintf(stderr, "usage: ref_replay seed NEW_REPO | create REPO NAME TARGET |\n"
                    "       publish REPO NAME PARENT DAG commit|abort EXTRA_NAME | read REPO NAME\n");
    return EXIT_FAILURE;
  }
  if (seed && make_fixture_directory(argv[2]) != 0) {
    perror("creating new fixture directory");
    return EXIT_FAILURE;
  }

  const dml_repo_options options = {.create = seed};
  dml_repo *repo = NULL;
  dml_error error = {0};
  if (!check_status(dml_repo_open(argv[2], &options, &repo, &error), &error, "opening repository")) {
    return EXIT_FAILURE;
  }
  bool success;
  if (seed) success = seed_fixture(repo);
  else if (create) success = create_ref(repo, argv[3], argv[4]);
  else if (write) success = publish(repo, argv[3], argv[4], argv[5], argv[6], argv[7]);
  else success = read_ref(repo, argv[3]);
  bool closed = check_status(dml_repo_close(&repo, &error), &error, "closing repository");
  if (fflush(stdout) == EOF) {
    perror("writing replay response");
    return EXIT_FAILURE;
  }
  return success && closed ? EXIT_SUCCESS : EXIT_FAILURE;
}
