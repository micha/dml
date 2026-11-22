#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#ifdef _WIN32
#include <direct.h>
#endif

#include "dml/repo.h"

static int make_fixture_directory(const char *path) {
  /* Never open a preexisting repository for this write test. */
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

static dml_status put_fixture_object(dml_txn *txn, const dml_object_input *input,
                                      dml_object_id *id, dml_error *error) {
  dml_buffer record = {0};
  dml_status status = dml_object_encode(input, &record, error);
  if (status == DML_OK) {
    status = dml_txn_put_object(txn, input->type, record.data, record.len, id, error);
  }
  dml_buffer_free(&record);
  return status;
}

static bool seed_fixture(dml_repo *repo, dml_object_id targets[2]) {
  dml_txn *txn = NULL;
  dml_error error = {0};
  if (!check_status(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error), &error,
                    "beginning fixture transaction")) {
    return false;
  }

  const dml_object_input tree = {.type = DML_REC_TREE};
  dml_object_input commit = {.type = DML_REC_COMMIT};
  bool seeded =
    check_status(put_fixture_object(txn, &tree, &commit.value.commit.tree, &error),
                 &error, "storing fixture tree") &&
    check_status(put_fixture_object(txn, &commit, &targets[0], &error),
                 &error, "storing fixture commit A");
  if (seeded) {
    /* Child B differs from its parent A while sharing the same tree. */
    commit.value.commit.parents = (dml_id_array){.items = &targets[0], .count = 1};
    seeded = check_status(put_fixture_object(txn, &commit, &targets[1], &error),
                          &error, "storing fixture commit B");
  }
  if (!seeded) {
    dml_txn_abort(&txn);
    return false;
  }
  return check_status(dml_txn_commit(&txn, &error), &error, "committing fixture transaction");
}

static bool announce_fixture(const dml_object_id targets[2]) {
  char a[DML_OBJECT_ID_HEX_SIZE + 1];
  char b[DML_OBJECT_ID_HEX_SIZE + 1];
  dml_error error = {0};
  if (!check_status(dml_object_id_format(&targets[0], a, &error), &error, "formatting commit A") ||
      !check_status(dml_object_id_format(&targets[1], b, &error), &error, "formatting commit B")) {
    return false;
  }
  if (printf("READY %s %s\n", a, b) < 0 || fflush(stdout) == EOF) {
    perror("writing READY");
    return false;
  }
  return true;
}

static bool parse_request(const char *line, dml_bytes *name, size_t *target_index) {
  const char *separator = strchr(line, ' ');
  if (separator == NULL || separator == line) return false;
  for (const char *byte = line; byte < separator; ++byte) {
    if (isspace((unsigned char)*byte)) return false;
  }
  if (strcmp(separator + 1, "A\n") == 0) {
    *target_index = 0;
  } else if (strcmp(separator + 1, "B\n") == 0) {
    *target_index = 1;
  } else {
    return false;
  }
  *name = (dml_bytes){.data = (const uint8_t *)line, .len = (size_t)(separator - line)};
  return true;
}

static bool replay_request(dml_repo *repo, dml_bytes name, const dml_object_id *target) {
  dml_txn *txn = NULL;
  dml_error error = {0};
  if (!check_status(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error), &error,
                    "beginning ref transaction")) {
    return false;
  }

  dml_status create = dml_txn_ref_create(txn, name, target, NULL);
  /* Exercise transaction completion even after a failed create. */
  dml_status commit = dml_txn_commit(&txn, NULL);
  if (printf("STEP %s %s\n", dml_status_name(create), dml_status_name(commit)) < 0 ||
      fflush(stdout) == EOF) {
    perror("writing STEP");
    return false;
  }
  return true;
}

static bool replay_requests(dml_repo *repo, const dml_object_id targets[2]) {
  char line[1024];
  while (fgets(line, sizeof(line), stdin) != NULL) {
    dml_bytes name;
    size_t target_index;
    if (!parse_request(line, &name, &target_index)) {
      fprintf(stderr, "expected a request line '<name> <A|B>\\n' (at most %zu bytes)\n",
              sizeof(line) - 1);
      return false;
    }
    if (!replay_request(repo, name, &targets[target_index])) return false;
  }
  if (ferror(stdin)) {
    perror("reading requests");
    return false;
  }
  return true;
}

int main(int argc, char **argv) {
  if (argc != 2) {
    fprintf(stderr, "usage: ref_replay NEW_REPO\n");
    return EXIT_FAILURE;
  }
  if (make_fixture_directory(argv[1]) != 0) {
    perror("creating new fixture directory");
    return EXIT_FAILURE;
  }

  const dml_repo_options options = {.create = true};
  dml_repo *repo = NULL;
  dml_error error = {0};
  if (!check_status(dml_repo_open(argv[1], &options, &repo, &error), &error,
                    "opening fixture repository")) {
    return EXIT_FAILURE;
  }

  dml_object_id targets[2];
  bool success = seed_fixture(repo, targets) && announce_fixture(targets) &&
                 replay_requests(repo, targets);
  if (!check_status(dml_repo_close(&repo, &error), &error, "closing fixture repository")) {
    return EXIT_FAILURE;
  }
  return success ? EXIT_SUCCESS : EXIT_FAILURE;
}
