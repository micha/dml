/* Linux/POSIX prerequisite probe. Uses only public DML C interfaces. */
#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#include "dml/dml.h"

static const dml_bytes head = {(const uint8_t *)"main", 4};

#define CHECK(expr) do { \
  if (!(expr)) { \
    fprintf(stderr, "line %d: %s\n", __LINE__, #expr); \
    exit(EXIT_FAILURE); \
  } \
} while (0)

#define OK(expr) do { \
  dml_status status = (expr); \
  if (status != DML_OK) { \
    fprintf(stderr, "line %d: %s: %s\n", __LINE__, dml_status_name(status), error.detail); \
    exit(EXIT_FAILURE); \
  } \
} while (0)

static int same_id(const dml_object_id *left, const dml_object_id *right) {
  return memcmp(left->bytes, right->bytes, DML_OBJECT_ID_SIZE) == 0;
}

static int same_record(const dml_buffer *left, const dml_buffer *right) {
  return left->len == right->len && memcmp(left->data, right->data, left->len) == 0;
}

static void encode_commit(const dml_object_id *tree, const dml_object_id *parent,
                          dml_buffer *packed) {
  dml_error error = {0};
  dml_object_input input = {.type = DML_REC_COMMIT};
  input.value.commit.tree = *tree;
  input.value.commit.parents = (dml_id_array){parent, parent != NULL};
  OK(dml_object_encode(&input, packed, &error));
}

static void publish(const char *path) {
  dml_error error = {0};
  dml_repo *repo = NULL;
  dml_txn *txn = NULL;
  dml_object_id old, newer;
  dml_buffer packed = {0};
  dml_object_view view;
  OK(dml_repo_open(path, NULL, &repo, &error));
  OK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error));
  OK(dml_txn_ref_get(txn, head, &old, &error));
  OK(dml_txn_get_object(txn, DML_REC_COMMIT, &old, &packed, &error));
  OK(dml_object_decode(packed.data, packed.len, &view, &error));
  dml_buffer_free(&packed);
  encode_commit(&view.reference, &old, &packed);
  OK(dml_txn_put_object(txn, DML_REC_COMMIT, packed.data, packed.len, &newer, &error));
  OK(dml_txn_ref_update(txn, head, &newer, &error));
  OK(dml_txn_commit(&txn, &error));
  OK(dml_repo_close(&repo, &error));
  dml_buffer_free(&packed);
}

static pid_t start_writer(const char *path, int *signal_writer) {
  int ready[2];
  CHECK(pipe(ready) == 0);
  pid_t child = fork();
  CHECK(child >= 0);
  if (child == 0) {
    CHECK(close(ready[1]) == 0);
    char signal;
    ssize_t count;
    do { count = read(ready[0], &signal, 1); } while (count == -1 && errno == EINTR);
    CHECK(close(ready[0]) == 0);
    if (count != 1) _exit(EXIT_FAILURE);
    publish(path);
    _exit(EXIT_SUCCESS);
  }
  CHECK(close(ready[0]) == 0);
  *signal_writer = ready[1];
  return child;
}

static void release_writer_and_wait(pid_t child, int signal_writer) {
  ssize_t count;
  do { count = write(signal_writer, "w", 1); } while (count == -1 && errno == EINTR);
  CHECK(count == 1);
  CHECK(close(signal_writer) == 0);
  int status;
  pid_t waited;
  do { waited = waitpid(child, &status, 0); } while (waited == -1 && errno == EINTR);
  CHECK(waited == child && WIFEXITED(status) && WEXITSTATUS(status) == EXIT_SUCCESS);
}

int main(int argc, char **argv) {
  int late_control = argc == 3 && strcmp(argv[2], "--late-control") == 0;
  if (argc != 2 && !late_control) {
    fprintf(stderr, "usage: %s NEW_REPOSITORY_PATH [--late-control]\n", argv[0]);
    return 2;
  }
  const char *path = argv[1];
  if (mkdir(path, 0700) != 0) {
    perror("snapshot probe requires a new repository directory");
    return 2;
  }

  dml_error error = {0};
  dml_repo *repo = NULL;
  dml_txn *txn = NULL;
  dml_repo_options create = {true, 0};
  dml_object_id tree, old, newer, actual;
  dml_object_input empty = {.type = DML_REC_TREE};
  dml_buffer packed = {0}, old_record = {0}, pinned = {0}, fetched = {0};
  OK(dml_repo_open(path, &create, &repo, &error));
  OK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error));
  OK(dml_object_encode(&empty, &packed, &error));
  OK(dml_txn_put_object(txn, DML_REC_TREE, packed.data, packed.len, &tree, &error));
  dml_buffer_free(&packed);
  encode_commit(&tree, NULL, &old_record);
  OK(dml_txn_put_object(txn, DML_REC_COMMIT, old_record.data, old_record.len, &old, &error));
  OK(dml_txn_ref_create(txn, head, &old, &error));
  OK(dml_txn_commit(&txn, &error));
  OK(dml_repo_close(&repo, &error));
  encode_commit(&tree, &old, &packed);
  OK(dml_object_id_compute(packed.data, packed.len, &newer, &error));
  CHECK(!same_id(&old, &newer));

  /* Fork with no LMDB handles open. The writer opens its own repository. */
  int signal_writer;
  pid_t child = start_writer(path, &signal_writer);
  OK(dml_repo_open(path, NULL, &repo, &error));
  if (!late_control) OK(dml_txn_begin(repo, DML_TXN_READ, &txn, &error));
  release_writer_and_wait(child, signal_writer);
  if (late_control) OK(dml_txn_begin(repo, DML_TXN_READ, &txn, &error));
  /* No read before writer commit: pin must be established by begin. */
  OK(dml_txn_ref_get(txn, head, &actual, &error));
  CHECK(same_id(&old, &actual));
  CHECK(dml_txn_get_object(txn, DML_REC_COMMIT, &newer, &fetched, &error) == DML_NOT_FOUND);
  CHECK(fetched.data == NULL && fetched.len == 0);
  CHECK(dml_txn_get_object(txn, DML_REC_TREE, &old, &fetched, &error) == DML_NOT_FOUND);
  OK(dml_txn_get_object(txn, DML_REC_COMMIT, &old, &pinned, &error));
  dml_txn_abort(&txn);

  OK(dml_txn_begin(repo, DML_TXN_READ, &txn, &error));
  OK(dml_txn_ref_get(txn, head, &actual, &error));
  CHECK(same_id(&newer, &actual));
  OK(dml_txn_get_object(txn, DML_REC_COMMIT, &newer, &fetched, &error));
  CHECK(same_record(&packed, &fetched));
  dml_txn_abort(&txn);
  OK(dml_repo_close(&repo, &error));
  CHECK(same_record(&old_record, &pinned));

  dml_buffer_free(&fetched);
  dml_buffer_free(&pinned);
  dml_buffer_free(&old_record);
  dml_buffer_free(&packed);
  puts("PASS: snapshot at begin, typed lookup, owned packed bytes, fresh visibility");
  return EXIT_SUCCESS;
}
