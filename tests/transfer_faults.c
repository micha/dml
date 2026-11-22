#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "dml/dml.h"

static size_t fail_at;
static size_t allocation_count;

static bool fail_allocation(void) {
  return fail_at != 0 && ++allocation_count == fail_at;
}

/* Only the test copies of the transfer and object modules call these functions. */
void *dml_fault_malloc(size_t size) {
  return fail_allocation() ? NULL : malloc(size);
}

void *dml_fault_calloc(size_t count, size_t size) {
  return fail_allocation() ? NULL : calloc(count, size);
}

void *dml_fault_realloc(void *old, size_t size) {
  return fail_allocation() ? NULL : realloc(old, size);
}

static void require(bool condition, const char *description) {
  if (condition) return;
  fprintf(stderr, "%s\n", description);
  exit(EXIT_FAILURE);
}

static void require_status(dml_status actual, dml_status expected, const dml_error *error,
                            const char *operation) {
  if (actual == expected) return;
  fprintf(stderr, "%s: expected %s, got %s (%s)\n", operation, dml_status_name(expected),
          dml_status_name(actual), error->detail);
  exit(EXIT_FAILURE);
}

static dml_object_id put(dml_txn *txn, dml_object_input input) {
  dml_error error = {0};
  dml_buffer packed = {0};
  require_status(dml_object_encode(&input, &packed, &error), DML_OK, &error, "encoding fixture");
  dml_object_id id;
  require_status(dml_txn_put_object(txn, input.type, packed.data, packed.len, &id, &error),
                 DML_OK, &error, "writing fixture");
  dml_buffer_free(&packed);
  return id;
}

static dml_object_id populate(dml_repo *repo, dml_object_id *tree) {
  dml_error error = {0};
  dml_txn *txn = NULL;
  require_status(dml_txn_begin(repo, DML_TXN_WRITE, &txn, &error), DML_OK, &error, "starting fixture");
  *tree = put(txn, (dml_object_input){.type = DML_REC_TREE});
  dml_object_input input = {.type = DML_REC_COMMIT, .value.commit.tree = *tree};

  /* Enough live export frames and indexed entries to exercise growth. */
  dml_object_id chain[48];
  for (size_t i = 0; i < sizeof(chain) / sizeof(*chain); i++) {
    chain[i] = put(txn, input);
    input.value.commit.parents = (dml_id_array){&chain[i], 1};
  }
  dml_object_id parents[33];
  for (size_t i = 0; i < sizeof(parents) / sizeof(*parents); i++) parents[i] = chain[47 - i];
  input.value.commit.parents = (dml_id_array){parents, sizeof(parents) / sizeof(*parents)};
  dml_object_id root = put(txn, input);
  require_status(dml_txn_commit(&txn, &error), DML_OK, &error, "committing fixture");

  dml_buffer packed = {0};
  require_status(dml_object_encode(&input, &packed, &error), DML_OK, &error, "encoding wide commit");
  allocation_count = 0;
  fail_at = 1;
  dml_status status = dml_record_validate(packed.data, packed.len, &error);
  fail_at = 0;
  require_status(status, DML_OUT_OF_MEMORY, &error, "injecting wide parent validation failure");
  dml_object_view view;
  require_status(dml_object_decode(packed.data, packed.len, &view, &error), DML_OK, &error,
                 "decoding wide commit");
  require(view.count == sizeof(parents) / sizeof(*parents), "parent count changed");
  for (size_t i = 0; i < view.count; i++) {
    dml_object_id id;
    require_status(dml_object_view_parent(&view, i, &id, &error), DML_OK, &error, "reading parent");
    require(memcmp(id.bytes, parents[i].bytes, sizeof(id.bytes)) == 0, "parent order changed");
  }
  dml_buffer_free(&packed);
  parents[32] = parents[0];
  require_status(dml_object_encode(&input, &packed, &error), DML_INVALID_PAYLOAD, &error,
                 "rejecting nonadjacent duplicate in wide commit");
  require(packed.data == NULL && packed.len == 0, "failed wide commit encode changed the output");
  return root;
}

static void require_object(dml_repo *repo, dml_record_type type, const dml_object_id *id,
                           dml_status expected) {
  dml_error error = {0};
  dml_txn *txn = NULL;
  dml_buffer packed = {0};
  require_status(dml_txn_begin(repo, DML_TXN_READ, &txn, &error), DML_OK, &error,
                 "starting verification transaction");
  require_status(dml_txn_get_object(txn, type, id, &packed, &error), expected, &error,
                 "verifying object presence");
  dml_buffer_free(&packed);
  dml_txn_abort(&txn);
}

static dml_buffer check_export_failures(dml_repo *source, const dml_object_id *root) {
  dml_error error = {0};
  dml_buffer bundle = {0};
  for (size_t attempt = 1; attempt < 32; attempt++) {
    allocation_count = 0;
    fail_at = attempt;
    dml_status status = dml_repo_export_commit(source, root, &bundle, &error);
    fail_at = 0;
    if (status == DML_OK) {
      require(attempt > 1 && allocation_count == attempt - 1 && bundle.len != 0,
              "export fault loop did not cover the expected allocation sequence");
      return bundle;
    }
    require_status(status, DML_OUT_OF_MEMORY, &error, "injecting export allocation failure");
    require(bundle.data == NULL && bundle.len == 0, "failed export did not leave an empty result");
    require_object(source, DML_REC_COMMIT, root, DML_OK);
  }
  require(false, "export did not eventually succeed");
  return bundle;
}

static void check_import_failures(dml_repo *dest, dml_bytes bundle, const dml_object_id *root,
                                  const dml_object_id *tree) {
  dml_error error = {0};
  dml_object_id sentinel;
  memset(sentinel.bytes, 0xa5, sizeof(sentinel.bytes));
  for (size_t attempt = 1; attempt < 32; attempt++) {
    allocation_count = 0;
    dml_object_id imported = sentinel;
    fail_at = attempt;
    dml_status status = dml_repo_import_commit(dest, bundle, &imported, &error);
    fail_at = 0;
    if (status == DML_OK) {
      require(attempt > 1 && allocation_count == attempt - 1,
              "import fault loop did not cover the expected allocation sequence");
      require(memcmp(imported.bytes, root->bytes, sizeof(imported.bytes)) == 0, "import changed root ID");
      require_object(dest, DML_REC_COMMIT, root, DML_OK);
      return;
    }
    require_status(status, DML_OUT_OF_MEMORY, &error, "injecting import allocation failure");
    require(memcmp(imported.bytes, sentinel.bytes, sizeof(imported.bytes)) == 0,
            "failed import changed the result ID");
    require_object(dest, DML_REC_COMMIT, root, DML_NOT_FOUND);
    require_object(dest, DML_REC_TREE, tree, DML_NOT_FOUND);
  }
  require(false, "import did not eventually succeed");
}

int main(int argc, char **argv) {
  require(argc == 3, "usage: transfer_faults SOURCE DESTINATION");
  dml_error error = {0};
  dml_repo *source = NULL;
  dml_repo *dest = NULL;
  dml_repo_options options = {.create = true};
  require_status(dml_repo_open(argv[1], &options, &source, &error), DML_OK, &error, "opening source");
  require_status(dml_repo_open(argv[2], &options, &dest, &error), DML_OK, &error, "opening destination");
  dml_object_id tree;
  dml_object_id root = populate(source, &tree);
  dml_buffer bundle = check_export_failures(source, &root);
  check_import_failures(dest, (dml_bytes){bundle.data, bundle.len}, &root, &tree);
  dml_buffer_free(&bundle);
  require_status(dml_repo_close(&dest, &error), DML_OK, &error, "closing destination");
  require_status(dml_repo_close(&source, &error), DML_OK, &error, "closing source");
  return EXIT_SUCCESS;
}
