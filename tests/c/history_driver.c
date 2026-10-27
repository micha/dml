#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "dml/dml.h"
#include "../../src/encoding.h"

#define REQUIRE(expression) do { \
  dml_status result = (expression); \
  if (result != DML_OK) { fprintf(stderr, "%s: %s\n", dml_status_name(result), error.detail); goto done; } \
} while (0)
#define CHECK(expression) do { \
  if (!(expression)) { fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #expression); goto done; } \
} while (0)

static dml_bytes name(const char *text) {
  return (dml_bytes){(const uint8_t *)text, strlen(text)};
}

static void print_id(const dml_object_id *id) {
  char hex[33];
  (void)dml_object_id_format(id, hex, NULL);
  puts(hex);
}

static dml_status store(dml_txn *txn, const dml_object_input *input, dml_object_id *id,
                         dml_error *error) {
  dml_buffer packed = {0}, fetched = {0};
  dml_object_id again;
  dml_status status = dml_object_encode(input, &packed, error);
  if (status == DML_OK) status = dml_txn_put_object(txn, input->type, packed.data, packed.len, id, error);
  if (status == DML_OK) status = dml_txn_put_object(txn, input->type, packed.data, packed.len, &again, error);
  if (status == DML_OK && memcmp(id, &again, sizeof(again)) != 0) status = DML_INTEGRITY_ERROR;
  if (status == DML_OK) status = dml_txn_get_object(txn, input->type, id, &fetched, error);
  if (status == DML_OK && (packed.len != fetched.len || memcmp(packed.data, fetched.data, packed.len) != 0)) {
    status = DML_INTEGRITY_ERROR;
  }
  dml_buffer_free(&packed);
  dml_buffer_free(&fetched);
  return status;
}

static dml_status snapshot(dml_txn *txn, int64_t value, const dml_object_id *parent,
                            dml_object_id ids[5], dml_error *error) {
  dml_buffer packed = {0};
  dml_datum_input datum = {.kind = DML_DATUM_I64, .value.i64 = value};
  dml_status status = dml_datum_encode(&datum, &packed, error);
  if (status == DML_OK) status = dml_txn_put_datum(txn, packed.data, packed.len, &ids[0], error);
  dml_buffer_free(&packed);
  if (status != DML_OK) return status;
  dml_object_input input = {.type = DML_REC_NODE, .value.node = {DML_NODE_LITERAL, ids[0]}};
  status = store(txn, &input, &ids[1], error);
  if (status != DML_OK) return status;
  input = (dml_object_input){.type = DML_REC_DAG, .value.dag.root = ids[1]};
  status = store(txn, &input, &ids[2], error);
  if (status != DML_OK) return status;
  dml_tree_entry entry = {name("example"), ids[2]};
  input.type = DML_REC_TREE;
  input.value.tree.items = &entry;
  input.value.tree.count = 1;
  status = store(txn, &input, &ids[3], error);
  if (status != DML_OK) return status;
  input.type = DML_REC_COMMIT;
  input.value.commit.tree = ids[3];
  input.value.commit.parents = (dml_id_array){parent, parent == NULL ? 0 : 1};
  return store(txn, &input, &ids[4], error);
}

static int write_snapshot(int argc, char **argv) {
  dml_repo *repo = NULL;
  dml_txn *txn = NULL;
  dml_error error = {0};
  dml_repo_options options = {true, 0};
  dml_object_id parent, ids[5], ignored;
  int exit_code = 1;
  if (argc != 7) return 2;
  REQUIRE(dml_repo_open(argv[2], &options, &repo, &error));
  REQUIRE(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error));
  const dml_object_id *parent_ptr = NULL;
  if (strcmp(argv[4], "none") != 0) {
    REQUIRE(dml_object_id_parse(argv[4], strlen(argv[4]), &parent, &error));
    parent_ptr = &parent;
  }
  REQUIRE(snapshot(txn, strtoll(argv[3], NULL, 10), parent_ptr, ids, &error));
  dml_bytes ref = name(argv[5]);
  if (strcmp(argv[6], "create") == 0) REQUIRE(dml_txn_ref_create(txn, ref, &ids[4], &error));
  else REQUIRE(dml_txn_ref_update(txn, ref, &ids[4], &error));
  REQUIRE(dml_txn_ref_get(txn, ref, &ignored, &error));
  CHECK(memcmp(&ignored, &ids[4], sizeof(ignored)) == 0);
  for (size_t i = 0; i < 5; i++) print_id(&ids[i]);
  if (strcmp(argv[6], "abort") == 0) dml_txn_abort(&txn);
  else if (strcmp(argv[6], "poison") == 0) {
    CHECK(dml_txn_ref_create(txn, ref, &ids[4], &error) == DML_INVALID_STATE);
    CHECK(dml_txn_ref_update(txn, ref, &ids[4], &error) == DML_INVALID_STATE);
    CHECK(dml_txn_commit(&txn, &error) == DML_INVALID_STATE && txn == NULL);
  } else REQUIRE(dml_txn_commit(&txn, &error));
  REQUIRE(dml_repo_close(&repo, &error));
  exit_code = 0;
done:
  dml_txn_abort(&txn);
  if (repo != NULL) (void)dml_repo_close(&repo, NULL);
  return exit_code;
}

static int inspect(int argc, char **argv) {
  dml_repo *repo = NULL;
  dml_txn *txn = NULL;
  dml_buffer packed = {0};
  dml_object_view view;
  dml_object_id id;
  dml_error error = {0};
  int exit_code = 1;
  if (argc != 5) return 2;
  REQUIRE(dml_repo_open(argv[2], NULL, &repo, &error));
  REQUIRE(dml_txn_begin(repo, DML_TXN_READ, &txn, &error));
  if (strcmp(argv[3], "ref") == 0) REQUIRE(dml_txn_ref_get(txn, name(argv[4]), &id, &error));
  else REQUIRE(dml_object_id_parse(argv[4], strlen(argv[4]), &id, &error));
  print_id(&id);
  REQUIRE(dml_txn_get_object(txn, DML_REC_COMMIT, &id, &packed, &error));
  REQUIRE(dml_object_decode(packed.data, packed.len, &view, &error));
  id = view.reference;
  printf("%zu\n", view.count);
  for (size_t i = 0; i < view.count; i++) {
    dml_object_id parent;
    REQUIRE(dml_object_view_parent(&view, i, &parent, &error));
    print_id(&parent);
  }
  dml_buffer_free(&packed);
  REQUIRE(dml_txn_get_object(txn, DML_REC_TREE, &id, &packed, &error));
  REQUIRE(dml_object_decode(packed.data, packed.len, &view, &error));
  CHECK(view.count == 1);
  dml_tree_entry entry;
  REQUIRE(dml_object_view_entry(&view, 0, &entry, &error));
  CHECK(entry.name.len == 7 && memcmp(entry.name.data, "example", 7) == 0);
  id = entry.dag;
  dml_buffer_free(&packed);
  for (int type = DML_REC_DAG; type >= DML_REC_NODE; type--) {
    REQUIRE(dml_txn_get_object(txn, (dml_record_type)type, &id, &packed, &error));
    REQUIRE(dml_object_decode(packed.data, packed.len, &view, &error));
    id = view.reference;
    dml_buffer_free(&packed);
  }
  REQUIRE(dml_txn_get_datum(txn, &id, &packed, &error));
  dml_datum_view datum;
  REQUIRE(dml_datum_decode(packed.data, packed.len, &datum, &error));
  CHECK(datum.kind == DML_DATUM_I64);
  uint64_t bits = dml_read_u64_le(datum.payload);
  int64_t value;
  memcpy(&value, &bits, sizeof(value));
  printf("%" PRId64 "\n", value);
  exit_code = 0;
done:
  dml_buffer_free(&packed);
  dml_txn_abort(&txn);
  if (repo != NULL) (void)dml_repo_close(&repo, NULL);
  return exit_code;
}

static int negative(const char *path) {
  dml_repo *repo = NULL;
  dml_txn *txn = NULL;
  dml_buffer packed = {0}, fetched = {0};
  dml_repo_options options = {true, 0};
  dml_error error = {0};
  dml_object_id ids[5], missing = {{0xff}}, ignored;
  int exit_code = 1;
  REQUIRE(dml_repo_open(path, &options, &repo, &error));
  REQUIRE(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error));
  REQUIRE(snapshot(txn, 42, NULL, ids, &error));
  REQUIRE(dml_txn_ref_create(txn, name("main"), &ids[4], &error));
  REQUIRE(dml_txn_commit(&txn, &error));
  REQUIRE(dml_txn_begin(repo, DML_TXN_READ, &txn, &error));
  CHECK(dml_txn_ref_get(txn, name("absent"), &ignored, &error) == DML_NOT_FOUND);
  CHECK(dml_txn_ref_get(NULL, name("main"), &ignored, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_txn_ref_get(txn, name("main"), NULL, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_txn_ref_get(txn, name("bad/name"), &ignored, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_txn_ref_create(txn, name("other"), &ids[4], &error) == DML_INVALID_STATE);
  CHECK(dml_txn_ref_update(txn, name("main"), &ids[4], &error) == DML_INVALID_STATE);
  CHECK(dml_txn_get_object(txn, DML_REC_REF, &ids[4], &fetched, &error) == DML_INVALID_KIND);
  CHECK(dml_txn_get_object(NULL, DML_REC_COMMIT, &ids[4], &fetched, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_txn_get_object(txn, DML_REC_COMMIT, NULL, &fetched, &error) == DML_INVALID_ARGUMENT);
  CHECK(dml_txn_get_object(txn, DML_REC_COMMIT, &ids[4], NULL, &error) == DML_INVALID_ARGUMENT);
  REQUIRE(dml_txn_get_object(txn, DML_REC_COMMIT, &ids[4], &fetched, &error));
  CHECK(dml_txn_get_object(txn, DML_REC_COMMIT, &ids[4], &fetched, &error) == DML_INVALID_ARGUMENT);
  dml_buffer_free(&fetched);
  CHECK(dml_repo_close(&repo, &error) == DML_INVALID_STATE);
  CHECK(dml_txn_commit(&txn, &error) == DML_INVALID_STATE && txn == NULL);
  CHECK(dml_txn_ref_create(NULL, name("main"), &ids[4], &error) == DML_INVALID_STATE);
  CHECK(dml_txn_put_object(NULL, DML_REC_REF, NULL, 0, &ignored, &error) == DML_INVALID_KIND);
  CHECK(dml_txn_put_object(NULL, DML_REC_NODE, NULL, 0, &ignored, &error) == DML_INVALID_STATE);

  /* Missing and wrong-namespace references at every structural position. */
  for (int scenario = 0; scenario < 10; scenario++) {
    dml_object_input input = {0};
    dml_object_id bad = scenario % 2 == 0 ? missing : ids[0];
    dml_tree_entry entry = {name("example"), bad};
    if (scenario < 2) {
      input.type = DML_REC_NODE;
      input.value.node.kind = DML_NODE_LITERAL;
      input.value.node.target = scenario % 2 == 0 ? missing : ids[4];
    } else if (scenario < 4) { input.type = DML_REC_DAG; input.value.dag.root = bad; }
    else if (scenario < 6) {
      input.type = DML_REC_TREE;
      input.value.tree.items = &entry; input.value.tree.count = 1;
    } else {
      input.type = DML_REC_COMMIT;
      input.value.commit.tree = scenario < 8 ? bad : ids[3];
      input.value.commit.parents = (dml_id_array){scenario < 8 ? NULL : &bad, scenario < 8 ? 0 : 1};
    }
    REQUIRE(dml_object_encode(&input, &packed, &error));
    REQUIRE(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error));
    CHECK(dml_txn_put_object(txn, input.type, packed.data, packed.len, &ignored, &error) == DML_NOT_FOUND);
    CHECK(dml_txn_commit(&txn, &error) == DML_INVALID_STATE && txn == NULL);
    dml_buffer_free(&packed);
  }
  for (int scenario = 0; scenario < 8; scenario++) {
    REQUIRE(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error));
    if (scenario == 0) CHECK(dml_txn_ref_update(txn, name("absent"), &ids[4], &error) == DML_NOT_FOUND);
    if (scenario == 1) CHECK(dml_txn_ref_create(txn, name("main"), &ids[4], &error) == DML_INVALID_STATE);
    if (scenario == 2) CHECK(dml_txn_ref_create(txn, name("bad/name"), &ids[4], &error) == DML_INVALID_ARGUMENT);
    if (scenario == 3) CHECK(dml_txn_ref_update(txn, name("main"), NULL, &error) == DML_INVALID_ARGUMENT);
    if (scenario == 4) CHECK(dml_txn_ref_update(txn, name("main"), &missing, &error) == DML_NOT_FOUND);
    if (scenario == 5) CHECK(dml_txn_ref_update(txn, name("main"), &ids[0], &error) == DML_NOT_FOUND);
    if (scenario == 6) CHECK(dml_txn_put_object(txn, DML_REC_REF, NULL, 0, &ignored, &error) == DML_INVALID_KIND);
    if (scenario == 7) CHECK(dml_txn_put_object(txn, DML_REC_NODE, NULL, 0, NULL, &error) == DML_INVALID_ARGUMENT);
    CHECK(dml_txn_commit(&txn, &error) == DML_INVALID_STATE && txn == NULL);
  }
  dml_object_input input = {.type = DML_REC_DAG, .value.dag.root = ids[1]};
  REQUIRE(dml_object_encode(&input, &packed, &error));
  REQUIRE(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error));
  CHECK(dml_txn_put_object(txn, DML_REC_NODE, packed.data, packed.len, &ignored, &error) == DML_INVALID_KIND);
  CHECK(dml_txn_commit(&txn, &error) == DML_INVALID_STATE);
  dml_buffer_free(&packed);
  REQUIRE(dml_txn_begin(repo, DML_TXN_READ, &txn, &error));
  REQUIRE(dml_txn_ref_get(txn, name("main"), &ignored, &error));
  CHECK(memcmp(&ignored, &ids[4], sizeof(ignored)) == 0);
  dml_txn_abort(&txn);
  REQUIRE(dml_repo_close(&repo, &error));
  exit_code = 0;
done:
  dml_buffer_free(&packed);
  dml_buffer_free(&fetched);
  dml_txn_abort(&txn);
  if (repo != NULL) (void)dml_repo_close(&repo, NULL);
  return exit_code;
}

static int map_full(const char *path) {
  dml_repo *repo = NULL;
  dml_txn *txn = NULL;
  dml_repo_options options = {true, 1024 * 1024};
  dml_error error = {0};
  dml_buffer packed = {0}, fetched = {0};
  dml_object_id first[5], discarded[5], large_id, target;
  size_t size = 2 * 1024 * 1024;
  uint8_t *bytes = malloc(size);
  int exit_code = 1;
  CHECK(bytes != NULL);
  memset(bytes, 42, size);
  REQUIRE(dml_repo_open(path, &options, &repo, &error));
  REQUIRE(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error));
  REQUIRE(snapshot(txn, 42, NULL, first, &error));
  REQUIRE(dml_txn_ref_create(txn, name("main"), &first[4], &error));
  REQUIRE(dml_txn_commit(&txn, &error));
  REQUIRE(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error));
  REQUIRE(snapshot(txn, 43, &first[4], discarded, &error));
  REQUIRE(dml_txn_ref_update(txn, name("main"), &discarded[4], &error));
  dml_datum_input input = {.kind = DML_DATUM_BYTES, .value.bytes = {bytes, size}};
  REQUIRE(dml_datum_encode(&input, &packed, &error));
  CHECK(dml_txn_put_datum(txn, packed.data, packed.len, &large_id, &error) == DML_MAP_FULL);
  CHECK(dml_txn_commit(&txn, &error) == DML_INVALID_STATE && txn == NULL);
  REQUIRE(dml_txn_begin(repo, DML_TXN_READ, &txn, &error));
  REQUIRE(dml_txn_ref_get(txn, name("main"), &target, &error));
  CHECK(memcmp(&target, &first[4], sizeof(target)) == 0);
  CHECK(dml_txn_get_object(txn, DML_REC_COMMIT, &discarded[4], &fetched, &error) == DML_NOT_FOUND);
  CHECK(dml_txn_get_datum(txn, &large_id, &fetched, &error) == DML_NOT_FOUND);
  dml_txn_abort(&txn);
  REQUIRE(dml_repo_close(&repo, &error));
  /* Reopening with a larger map lets the caller retry the entire batch. */
  options.create = false;
  options.map_size = 8 * 1024 * 1024;
  REQUIRE(dml_repo_open(path, &options, &repo, &error));
  REQUIRE(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error));
  REQUIRE(snapshot(txn, 43, &first[4], discarded, &error));
  REQUIRE(dml_txn_put_datum(txn, packed.data, packed.len, &large_id, &error));
  REQUIRE(dml_txn_ref_update(txn, name("main"), &discarded[4], &error));
  REQUIRE(dml_txn_commit(&txn, &error));
  REQUIRE(dml_repo_close(&repo, &error));
  exit_code = 0;
done:
  free(bytes);
  dml_buffer_free(&packed);
  dml_buffer_free(&fetched);
  dml_txn_abort(&txn);
  if (repo != NULL) (void)dml_repo_close(&repo, NULL);
  return exit_code;
}

int main(int argc, char **argv) {
  if (argc >= 2 && strcmp(argv[1], "snapshot") == 0) return write_snapshot(argc, argv);
  if (argc >= 2 && strcmp(argv[1], "inspect") == 0) return inspect(argc, argv);
  if (argc == 3 && strcmp(argv[1], "map-full") == 0) return map_full(argv[2]);
  if (argc == 3 && strcmp(argv[1], "negative") == 0) return negative(argv[2]);
  return 2;
}
