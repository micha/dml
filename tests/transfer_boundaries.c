#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <lmdb.h>

#include "dml/dml.h"

#define MIB (1024u * 1024u)
#define HEADER_SIZE 28u
#define FRAME_SIZE 24u
#define MAX_FRAMES 262144u

#define CHECK(condition) do { \
  if (!(condition)) { fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #condition); exit(EXIT_FAILURE); } \
} while (0)

static void expect(dml_status actual, dml_status expected, const char *operation) {
  if (actual == expected) return;
  fprintf(stderr, "%s: expected %s, got %s\n", operation, dml_status_name(expected), dml_status_name(actual));
  exit(EXIT_FAILURE);
}

#define OK(expr) expect((expr), DML_OK, #expr)

typedef struct {
  dml_object_id root;
  dml_object_id small;
  dml_object_id bytes;
  dml_buffer packed_bytes;
} fixture;

static dml_repo *open_repo(const char *path, bool create, size_t map_size) {
  dml_repo *repo = NULL;
  const dml_repo_options options = {create, map_size};
  OK(dml_repo_open(path, &options, &repo, NULL));
  return repo;
}

static dml_object_id put_object(dml_txn *txn, dml_object_input object) {
  dml_buffer packed = {0};
  dml_object_id id;
  OK(dml_object_encode(&object, &packed, NULL));
  OK(dml_txn_put_object(txn, object.type, packed.data, packed.len, &id, NULL));
  dml_buffer_free(&packed);
  return id;
}

static dml_object_id put_datum(dml_txn *txn, dml_datum_input datum) {
  dml_buffer packed = {0};
  dml_object_id id;
  OK(dml_datum_encode(&datum, &packed, NULL));
  OK(dml_txn_put_datum(txn, packed.data, packed.len, &id, NULL));
  dml_buffer_free(&packed);
  return id;
}

static fixture populate(dml_repo *repo, size_t bytes_size) {
  fixture result = {0};
  dml_txn *txn = NULL;
  OK(dml_txn_begin(repo, DML_TXN_WRITE, &txn, NULL));
  result.small = put_datum(txn, (dml_datum_input){.kind = DML_DATUM_I64, .value.i64 = 1234});
  uint8_t *zeros = calloc(bytes_size, 1);
  CHECK(zeros != NULL);
  const dml_datum_input value = {.kind = DML_DATUM_BYTES, .value.bytes = {zeros, bytes_size}};
  OK(dml_datum_encode(&value, &result.packed_bytes, NULL));
  free(zeros);
  OK(dml_txn_put_datum(txn, result.packed_bytes.data, result.packed_bytes.len, &result.bytes, NULL));
  const dml_object_id children[] = {result.small, result.bytes};
  dml_object_id list = put_datum(txn, (dml_datum_input){.kind = DML_DATUM_LIST, .value.ids = {children, 2}});
  dml_object_id node = put_object(txn, (dml_object_input){.type = DML_REC_NODE, .value.node = {DML_NODE_LITERAL, list}});
  dml_object_id dag = put_object(txn, (dml_object_input){.type = DML_REC_DAG, .value.dag.root = node});
  const dml_tree_entry entry = {{(const uint8_t *)"path", 4}, dag};
  dml_object_id tree = put_object(txn, (dml_object_input){.type = DML_REC_TREE, .value.tree = {&entry, 1}});
  result.root = put_object(txn, (dml_object_input){.type = DML_REC_COMMIT, .value.commit.tree = tree});
  OK(dml_txn_commit(&txn, NULL));
  return result;
}

static void write_u32(uint8_t *data, uint32_t value) {
  for (size_t i = 0; i < 4; i++) data[i] = (uint8_t)(value >> (i * 8));
}

static void header(uint8_t *data, const dml_object_id *root, uint32_t count) {
  memcpy(data, "DMLB\1\0\0\0", 8);
  memcpy(data + 8, root->bytes, sizeof(root->bytes));
  write_u32(data + 24, count);
}

static void datum_frame(uint8_t *data, const dml_object_id *id, const dml_buffer *record) {
  data[0] = DML_REC_DATUM;
  write_u32(data + 4, (uint32_t)record->len);
  memcpy(data + 8, id->bytes, sizeof(id->bytes));
  memcpy(data + FRAME_SIZE, record->data, record->len);
}

/* Choose a legal input order with one successful insert before map exhaustion.
 * The export contract does not prescribe which independent datum comes first. */
static void small_frame_first(dml_buffer *wire, const fixture *source) {
  uint8_t *first = wire->data + HEADER_SIZE;
  const size_t large_size = FRAME_SIZE + source->packed_bytes.len;
  uint8_t small[FRAME_SIZE + 40u + sizeof(int64_t)];
  CHECK(wire->len >= HEADER_SIZE + large_size + sizeof(small));
  if (memcmp(first + 8, source->small.bytes, sizeof(source->small.bytes)) == 0) return;
  CHECK(memcmp(first + 8, source->bytes.bytes, sizeof(source->bytes.bytes)) == 0);
  CHECK(memcmp(first + large_size + 8, source->small.bytes, sizeof(source->small.bytes)) == 0);
  memcpy(small, first + large_size, sizeof(small));
  memmove(first + sizeof(small), first, large_size);
  memcpy(first, small, sizeof(small));
}

static void import_rejected(dml_repo *repo, dml_bytes input, dml_status status) {
  dml_object_id out, sentinel;
  memset(sentinel.bytes, 0xa5, sizeof(sentinel.bytes));
  out = sentinel;
  expect(dml_repo_import_commit(repo, input, &out, NULL), status, "rejecting boundary bundle");
  CHECK(memcmp(out.bytes, sentinel.bytes, sizeof(out.bytes)) == 0);
}

static void check_limits(dml_repo *repo, const fixture *oversize) {
  size_t size = HEADER_SIZE + FRAME_SIZE + oversize->packed_bytes.len;
  uint8_t *input = calloc(size, 1);
  CHECK(input != NULL);
  header(input, &oversize->root, 1);
  datum_frame(input + HEADER_SIZE, &oversize->bytes, &oversize->packed_bytes);
  import_rejected(repo, (dml_bytes){input, size}, DML_INVALID_BOUNDS);
  free(input);

  dml_buffer small = {0};
  OK(dml_datum_encode(&(dml_datum_input){.kind = DML_DATUM_I64, .value.i64 = 1234}, &small, NULL));
  const size_t width = FRAME_SIZE + small.len;
  size = HEADER_SIZE + (MAX_FRAMES + 1u) * width;
  input = calloc(size, 1);
  CHECK(input != NULL);
  header(input, &oversize->root, MAX_FRAMES + 1u);
  datum_frame(input + HEADER_SIZE, &oversize->small, &small);
  for (size_t i = 1; i <= MAX_FRAMES; ++i) {
    memcpy(input + HEADER_SIZE + i * width, input + HEADER_SIZE, width);
  }
  import_rejected(repo, (dml_bytes){input, size}, DML_INVALID_BOUNDS);
  free(input);

  size = 64u * MIB + 1u;
  input = calloc(size, 1);
  CHECK(input != NULL);
  header(input, &oversize->root, 2);
  datum_frame(input + HEADER_SIZE, &oversize->small, &small);
  memcpy(input + HEADER_SIZE + width, input + HEADER_SIZE, width);
  import_rejected(repo, (dml_bytes){input, size}, DML_INVALID_BOUNDS);
  free(input);
  dml_buffer_free(&small);
}

static void require_schema_only(dml_repo *repo) {
  dml_txn *txn = NULL;
  dml_repo_integrity report;
  OK(dml_txn_begin(repo, DML_TXN_READ, &txn, NULL));
  OK(dml_txn_check_integrity(txn, &report, NULL, NULL, NULL));
  CHECK(report.refs == 0 && report.reachable_objects == 0 && report.intact_unreachable_objects == 0 &&
        report.broken_unreachable_objects == 0 && report.invalid_entries == 0 && report.invalid_objects == 0);
  dml_txn_abort(&txn);
}

/* Raw LMDB access is confined to corrupt fixture setup and exact readback. */
static void raw_row(const char *path, const char *prefix, const dml_object_id *id,
                    const dml_buffer *replacement, bool verify) {
  char key_data[64];
  size_t size = strlen(prefix);
  CHECK(size + DML_OBJECT_ID_HEX_SIZE + 1 <= sizeof(key_data));
  memcpy(key_data, prefix, size);
  OK(dml_object_id_format(id, key_data + size, NULL));
  MDB_env *env = NULL;
  MDB_txn *txn = NULL;
  MDB_dbi dbi;
  CHECK(mdb_env_create(&env) == MDB_SUCCESS);
  unsigned int mode = verify ? MDB_RDONLY : 0;
  CHECK(mdb_env_open(env, path, mode, 0) == MDB_SUCCESS);
  CHECK(mdb_txn_begin(env, NULL, mode, &txn) == MDB_SUCCESS);
  CHECK(mdb_dbi_open(txn, NULL, 0, &dbi) == MDB_SUCCESS);
  MDB_val key = {size + DML_OBJECT_ID_HEX_SIZE, key_data};
  if (verify) {
    MDB_stat stats;
    MDB_val actual;
    CHECK(mdb_stat(txn, dbi, &stats) == MDB_SUCCESS && stats.ms_entries == 2);
    CHECK(mdb_get(txn, dbi, &key, &actual) == MDB_SUCCESS && actual.mv_size == replacement->len &&
          memcmp(actual.mv_data, replacement->data, actual.mv_size) == 0);
    mdb_txn_abort(txn);
  } else {
    if (replacement == NULL) {
      CHECK(mdb_del(txn, dbi, &key, NULL) == MDB_SUCCESS);
    } else {
      MDB_val value = {replacement->len, replacement->data};
      CHECK(mdb_put(txn, dbi, &key, &value, MDB_NOOVERWRITE) == MDB_SUCCESS);
    }
    CHECK(mdb_txn_commit(txn) == MDB_SUCCESS);
  }
  mdb_env_close(env);
}

int main(int argc, char **argv) {
  CHECK(argc == 4);
  dml_repo *source = open_repo(argv[1], true, 0);
  dml_repo *oversize = open_repo(argv[2], true, 0);
  dml_repo *dest = open_repo(argv[3], true, MIB);
  fixture large = populate(source, 2u * MIB);
  fixture extra_large = populate(oversize, 16u * MIB);
  dml_buffer wire = {0}, empty = {0};
  OK(dml_repo_export_commit(source, &large.root, &wire, NULL));
  small_frame_first(&wire, &large);
  import_rejected(dest, (dml_bytes){wire.data, wire.len}, DML_MAP_FULL);
  require_schema_only(dest);
  expect(dml_repo_export_commit(oversize, &extra_large.root, &empty, NULL), DML_INVALID_BOUNDS, "oversize export");
  CHECK(empty.data == NULL && empty.len == 0);
  check_limits(dest, &extra_large);
  require_schema_only(dest);
  OK(dml_repo_close(&oversize, NULL));
  OK(dml_repo_close(&dest, NULL));

  dml_buffer dirty = {malloc(1), 1};
  CHECK(dirty.data != NULL);
  dirty.data[0] = 42;
  uint8_t *original = dirty.data;
  expect(dml_repo_export_commit(source, &large.root, &dirty, NULL), DML_INVALID_ARGUMENT, "dirty export");
  CHECK(dirty.data == original && dirty.len == 1 && dirty.data[0] == 42);
  dml_buffer_free(&dirty);

  /* All dependency frames precede the conflicting root: a late failure must
   * roll back their inserts without overwriting the existing wrong bytes. */
  dml_buffer conflict = {0};
  OK(dml_object_encode(&(dml_object_input){.type = DML_REC_COMMIT}, &conflict, NULL));
  raw_row(argv[3], "objects/commits/", &large.root, &conflict, false);
  dest = open_repo(argv[3], false, 0);
  import_rejected(dest, (dml_bytes){wire.data, wire.len}, DML_INTEGRITY_ERROR);
  OK(dml_repo_close(&dest, NULL));
  raw_row(argv[3], "objects/commits/", &large.root, &conflict, true);
  raw_row(argv[3], "objects/commits/", &large.root, NULL, false);
  dml_buffer_free(&conflict);
  dest = open_repo(argv[3], false, 0);
  dml_object_id imported;
  OK(dml_repo_import_commit(dest, (dml_bytes){wire.data, wire.len}, &imported, NULL));
  CHECK(memcmp(imported.bytes, large.root.bytes, sizeof(imported.bytes)) == 0);
  OK(dml_repo_close(&dest, NULL));

  OK(dml_repo_close(&source, NULL));
  raw_row(argv[1], "objects/datums/", &large.small, NULL, false);
  source = open_repo(argv[1], false, 0);
  expect(dml_repo_export_commit(source, &large.root, &empty, NULL), DML_NOT_FOUND, "missing transitive edge");
  CHECK(empty.data == NULL && empty.len == 0);
  OK(dml_repo_close(&source, NULL));
  dml_buffer_free(&wire);
  dml_buffer_free(&large.packed_bytes);
  dml_buffer_free(&extra_large.packed_bytes);
  return EXIT_SUCCESS;
}
