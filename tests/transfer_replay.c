#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <lmdb.h>

#include "dml/dml.h"

#define SMALL_MAP (1024u * 1024u)

static void require_ok(dml_status status, const char *operation) {
  if (status == DML_OK) return;
  fprintf(stderr, "%s: %s\n", operation, dml_status_name(status));
  exit(EXIT_FAILURE);
}

static void format_id(dml_object_id id, char text[DML_OBJECT_ID_HEX_SIZE + 1]) {
  require_ok(dml_object_id_format(&id, text, NULL), "formatting fixture ID");
}

static void announce(const char *label, const char *kind, dml_object_id id) {
  char text[DML_OBJECT_ID_HEX_SIZE + 1];
  format_id(id, text);
  printf("%s %s %s\n", label, kind, text);
}

static dml_bytes name(const char *text) {
  return (dml_bytes){(const uint8_t *)text, strlen(text)};
}

static dml_object_id datum(dml_txn *txn, const char *label, dml_datum_input input) {
  dml_buffer buffer = {0};
  dml_object_id id;
  require_ok(dml_datum_encode(&input, &buffer, NULL), "encoding fixture datum");
  require_ok(dml_txn_put_datum(txn, buffer.data, buffer.len, &id, NULL), "storing fixture datum");
  dml_buffer_free(&buffer);
  announce(label, "datums", id);
  return id;
}

static dml_object_id number(dml_txn *txn, const char *label, int64_t value) {
  return datum(txn, label, (dml_datum_input){.kind = DML_DATUM_I64, .value.i64 = value});
}

static dml_object_id object(dml_txn *txn, const char *label, const char *kind,
                            dml_object_input input) {
  dml_buffer buffer = {0};
  dml_object_id id;
  require_ok(dml_object_encode(&input, &buffer, NULL), "encoding fixture object");
  require_ok(dml_txn_put_object(txn, input.type, buffer.data, buffer.len, &id, NULL),
             "storing fixture object");
  dml_buffer_free(&buffer);
  announce(label, kind, id);
  return id;
}

static dml_object_id node(dml_txn *txn, const char *label, uint32_t kind, dml_object_id target) {
  return object(txn, label, "nodes", (dml_object_input){
    .type = DML_REC_NODE, .value.node = {kind, target}
  });
}

static dml_object_id dag(dml_txn *txn, const char *label, dml_object_id root,
                         const dml_dag_binding *bindings, size_t count) {
  return object(txn, label, "dags", (dml_object_input){
    .type = DML_REC_DAG, .value.dag = {root, bindings, count}
  });
}

static dml_object_id tree(dml_txn *txn, const char *label, const dml_tree_entry *entries,
                          size_t count) {
  return object(txn, label, "trees", (dml_object_input){
    .type = DML_REC_TREE, .value.tree = {entries, count}
  });
}

static dml_object_id commit(dml_txn *txn, const char *label, dml_object_id snapshot,
                            const dml_object_id *parents, size_t count) {
  return object(txn, label, "commits", (dml_object_input){
    .type = DML_REC_COMMIT, .value.commit = {snapshot, {parents, count}}
  });
}

static dml_object_id one_value_commit(dml_txn *txn, const char *label, dml_object_id value) {
  dml_object_id literal = node(txn, "single_node", DML_NODE_LITERAL, value);
  dml_tree_entry entry = {name("single"), dag(txn, "single_dag", literal, NULL, 0)};
  return commit(txn, label, tree(txn, "single_tree", &entry, 1), NULL, 0);
}

static void seed_source(dml_txn *txn) {
  dml_object_id first = number(txn, "first", 41);
  dml_object_id second = number(txn, "second", 42);
  dml_object_id third = number(txn, "third", 43);
  dml_object_id fourth = number(txn, "fourth", 44);
  dml_object_id fifth = number(txn, "fifth", 45);
  const dml_object_id members[] = {first, first, second};
  const dml_object_id set_members[] = {third, fourth};
  dml_object_id list = datum(txn, "list", (dml_datum_input){
    .kind = DML_DATUM_LIST, .value.ids = {members, 3}
  });
  dml_object_id set = datum(txn, "set", (dml_datum_input){
    .kind = DML_DATUM_SET, .value.ids = {set_members, 2}
  });
  const dml_datum_map_entry pair = {list, set};
  dml_object_id map = datum(txn, "map", (dml_datum_input){
    .kind = DML_DATUM_MAP, .value.map = {&pair, 1}
  });
  dml_object_id literal = node(txn, "literal", DML_NODE_LITERAL, map);
  dml_object_id inner = dag(txn, "inner", literal, NULL, 0);
  dml_object_id nested = node(txn, "nested", DML_NODE_SUBDAG, inner);
  dml_object_id bound = node(txn, "bound", DML_NODE_LITERAL, fifth);
  const dml_dag_binding bindings[] = {{name("z-bound"), bound}, {name("a-alias"), nested}};
  dml_object_id outer = dag(txn, "outer", nested, bindings, 2);
  const dml_tree_entry entries[] = {{name("inner"), inner}, {name("all"), outer}};
  dml_object_id main_tree = tree(txn, "main_tree", entries, 2);
  dml_object_id empty = tree(txn, "empty_tree", NULL, 0);
  dml_object_id ancestor = commit(txn, "ancestor", empty, NULL, 0);
  dml_object_id old_head = commit(txn, "old_head", empty, &ancestor, 1);
  dml_tree_entry parent_entry = {name("inner-only"), inner};
  dml_object_id parent_tree = tree(txn, "parent_tree", &parent_entry, 1);
  dml_object_id other_parent = commit(txn, "other_parent", parent_tree, NULL, 0);
  const dml_object_id parents[] = {other_parent, old_head};
  dml_object_id root = commit(txn, "root", main_tree, parents, 2);
  dml_object_id other = one_value_commit(txn, "other", number(txn, "unreachable", 91));
  require_ok(dml_txn_ref_create(txn, name("main"), &other, NULL), "creating source main ref");
  require_ok(dml_txn_ref_create(txn, name("pinned"), &root, NULL), "creating source pinned ref");
}

static void seed_large(dml_txn *txn, size_t size) {
  uint8_t *bytes = calloc(size, 1);
  if (bytes == NULL) {
    perror("allocating large fixture datum");
    exit(EXIT_FAILURE);
  }
  dml_object_id small = number(txn, "small", 1234);
  dml_object_id large = datum(txn, "large", (dml_datum_input){
    .kind = DML_DATUM_BYTES, .value.bytes = {bytes, size}
  });
  free(bytes);
  const dml_object_id children[] = {small, large};
  dml_object_id list = datum(txn, "list", (dml_datum_input){
    .kind = DML_DATUM_LIST, .value.ids = {children, 2}
  });
  one_value_commit(txn, "root", list);
}

static void seed(dml_repo *repo, const char *profile) {
  dml_txn *txn = NULL;
  require_ok(dml_txn_begin(repo, DML_TXN_WRITE, &txn, NULL), "beginning fixture transaction");
  if (strcmp(profile, "source") == 0) {
    seed_source(txn);
  } else if (strcmp(profile, "large") == 0 || strcmp(profile, "oversize") == 0) {
    size_t mib = strcmp(profile, "large") == 0 ? 2u : 16u;
    seed_large(txn, mib * 1024u * 1024u);
  } else {
    dml_object_id keep = one_value_commit(txn, "keep", number(txn, "marker", 777));
    require_ok(dml_txn_ref_create(txn, name("main"), &keep, NULL), "creating destination main ref");
  }
  require_ok(dml_txn_commit(&txn, NULL), "committing fixture transaction");
}

static dml_buffer read_bundle(const char *path) {
  FILE *file = fopen(path, "rb");
  if (file == NULL || fseek(file, 0, SEEK_END) != 0) {
    perror("opening input bundle");
    exit(EXIT_FAILURE);
  }
  long size = ftell(file);
  if (size < 0 || fseek(file, 0, SEEK_SET) != 0) {
    perror("sizing input bundle");
    exit(EXIT_FAILURE);
  }
  dml_buffer bundle = {.data = malloc(size == 0 ? 1 : (size_t)size), .len = (size_t)size};
  if (bundle.data == NULL || fread(bundle.data, 1, bundle.len, file) != bundle.len ||
      fclose(file) != 0) {
    perror("reading input bundle");
    exit(EXIT_FAILURE);
  }
  return bundle;
}

static void write_bundle(const char *path, const dml_buffer *bundle) {
  FILE *file = fopen(path, "wb");
  if (file == NULL || fwrite(bundle->data, 1, bundle->len, file) != bundle->len ||
      fclose(file) != 0) {
    perror("writing output bundle");
    exit(EXIT_FAILURE);
  }
}

static void export_bundle(dml_repo *repo, const char *root_hex, const char *path, const char *mode) {
  dml_buffer output = {0};
  bool dirty = strcmp(mode, "dirty") == 0;
  if (dirty) {
    output.data = malloc(1);
    if (output.data == NULL) {
      perror("allocating output sentinel");
      exit(EXIT_FAILURE);
    }
    output.data[0] = 42;
    output.len = 1;
  }
  uint8_t *original = output.data;
  dml_object_id root;
  require_ok(dml_object_id_parse(root_hex, strlen(root_hex), &root, NULL), "parsing export root");
  dml_status status = dml_repo_export_commit(repo, &root, &output, NULL);
  const char *shape = "other";
  if (output.len == 0 && output.data == NULL) {
    shape = "empty";
  } else if (dirty && output.data == original && output.len == 1 && output.data[0] == 42) {
    shape = "unchanged";
  } else if (output.len > 0 && output.data != NULL) {
    shape = "buffer";
    if (status == DML_OK) write_bundle(path, &output);
  }
  dml_buffer_free(&output);
  printf("%s %s\n", dml_status_name(status), shape);
}

static void import_bundle(dml_repo *repo, const char *path) {
  dml_buffer bundle = read_bundle(path);
  dml_object_id out;
  memset(out.bytes, 0xa5, sizeof(out.bytes));
  dml_status status = dml_repo_import_commit(repo, (dml_bytes){bundle.data, bundle.len}, &out, NULL);
  dml_buffer_free(&bundle);
  char text[DML_OBJECT_ID_HEX_SIZE + 1];
  format_id(out, text);
  printf("%s %s\n", dml_status_name(status), text);
}

/* The public DML API cannot create these corrupt-store fixtures. */
static int alter_inventory(const char *path, const char *key, const char *copy_key) {
  MDB_env *env = NULL;
  MDB_txn *txn = NULL;
  MDB_dbi dbi;
  MDB_val target = {strlen(key), (void *)key};
  int code = mdb_env_create(&env);
  if (code == MDB_SUCCESS) code = mdb_env_open(env, path, 0, 0);
  if (code == MDB_SUCCESS) code = mdb_txn_begin(env, NULL, 0, &txn);
  if (code == MDB_SUCCESS) code = mdb_dbi_open(txn, NULL, 0, &dbi);
  if (code == MDB_SUCCESS && copy_key == NULL) {
    code = mdb_del(txn, dbi, &target, NULL);
  } else if (code == MDB_SUCCESS) {
    MDB_val source = {strlen(copy_key), (void *)copy_key};
    MDB_val value;
    code = mdb_get(txn, dbi, &source, &value);
    if (code == MDB_SUCCESS) {
      void *bytes = malloc(value.mv_size);
      if (bytes == NULL) {
        perror("copying corrupt fixture record");
        exit(EXIT_FAILURE);
      }
      memcpy(bytes, value.mv_data, value.mv_size);
      value.mv_data = bytes;
      code = mdb_put(txn, dbi, &target, &value, 0);
      free(bytes);
    }
  }
  if (code == MDB_SUCCESS) {
    code = mdb_txn_commit(txn);
    txn = NULL;
  }
  if (txn != NULL) mdb_txn_abort(txn);
  if (env != NULL) mdb_env_close(env);
  if (code == MDB_SUCCESS) return EXIT_SUCCESS;
  fprintf(stderr, "altering corrupt fixture: %s\n", mdb_strerror(code));
  return EXIT_FAILURE;
}

int main(int argc, char **argv) {
  if (argc == 4 && strcmp(argv[1], "delete") == 0) {
    return alter_inventory(argv[2], argv[3], NULL);
  }
  if (argc == 5 && strcmp(argv[1], "overwrite") == 0) {
    return alter_inventory(argv[2], argv[3], argv[4]);
  }
  bool create = argc == 4 && strcmp(argv[1], "seed") == 0;
  bool exporting = argc == 6 && strcmp(argv[1], "export") == 0;
  bool importing = argc == 5 && strcmp(argv[1], "import") == 0;
  if (!create && !exporting && !importing) {
    fprintf(stderr, "usage: transfer_replay seed REPO {source|destination|large|oversize}\n"
                    "       transfer_replay export REPO ROOT FILE {normal|busy|dirty}\n"
                    "       transfer_replay import REPO FILE {normal|busy|limited}\n"
                    "       transfer_replay delete REPO OBJECT_KEY\n"
                    "       transfer_replay overwrite REPO OBJECT_KEY COPY_KEY\n");
    return EXIT_FAILURE;
  }
  const char *mode = argv[argc - 1];
  if (create && strcmp(mode, "source") && strcmp(mode, "destination") &&
      strcmp(mode, "large") && strcmp(mode, "oversize")) {
    fprintf(stderr, "unknown fixture profile: %s\n", mode);
    return EXIT_FAILURE;
  }
  bool busy = !create && strcmp(mode, "busy") == 0;
  const dml_repo_options options = {
    .create = create, .map_size = strcmp(mode, "limited") == 0 ? SMALL_MAP : 0
  };
  dml_repo *repo = NULL;
  require_ok(dml_repo_open(argv[2], &options, &repo, NULL), "opening fixture repository");
  dml_txn *txn = NULL;
  if (busy) require_ok(dml_txn_begin(repo, DML_TXN_WRITE, &txn, NULL), "beginning busy transaction");
  if (create) {
    seed(repo, mode);
  } else {
    if (exporting) export_bundle(repo, argv[3], argv[4], mode);
    else import_bundle(repo, argv[3]);
    printf("%s\n", busy ? dml_status_name(dml_txn_commit(&txn, NULL)) : "none");
  }
  require_ok(dml_repo_close(&repo, NULL), "closing fixture repository");
  return ferror(stdout) ? EXIT_FAILURE : EXIT_SUCCESS;
}
