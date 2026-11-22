#include <errno.h>
#include <inttypes.h>
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
  dml_object_id historical_literal = node(txn, "historical_literal", DML_NODE_LITERAL, first);
  dml_dag_binding historical_binding = {name("z-bound"), historical_literal};
  dml_object_id historical_dag = dag(txn, "historical_dag", historical_literal,
                                     &historical_binding, 1);
  dml_tree_entry parent_entry = {name("all"), historical_dag};
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

static void publish_main(dml_repo *repo, const char *target_hex) {
  dml_object_id target;
  require_ok(dml_object_id_parse(target_hex, strlen(target_hex), &target, NULL),
             "parsing imported commit ID");
  dml_txn *txn = NULL;
  require_ok(dml_txn_begin(repo, DML_TXN_WRITE, &txn, NULL), "beginning publication transaction");
  dml_status updated = dml_txn_ref_update(txn, name("main"), &target, NULL);
  dml_status committed = dml_txn_commit(&txn, NULL);
  printf("%s\n%s\n", dml_status_name(updated), dml_status_name(committed));
}

static void read_main(dml_repo *repo) {
  dml_txn *txn = NULL;
  require_ok(dml_txn_begin(repo, DML_TXN_READ, &txn, NULL), "beginning readback transaction");
  dml_object_id target;
  memset(target.bytes, 0xa5, sizeof(target.bytes));
  dml_status resolved = dml_txn_ref_get(txn, name("main"), &target, NULL);
  char text[DML_OBJECT_ID_HEX_SIZE + 1];
  format_id(target, text);
  printf("%s %s\n", dml_status_name(resolved), text);
  dml_buffer packed = {0};
  const char *read_status = "none";
  if (resolved == DML_OK) {
    dml_status status = dml_txn_get_object(txn, DML_REC_COMMIT, &target, &packed, NULL);
    read_status = dml_status_name(status);
  }
  dml_txn_abort(&txn);
  printf("%s ", read_status);
  for (size_t i = 0; i < packed.len; ++i) printf("%02x", (unsigned)packed.data[i]);
  printf("\n");
  dml_buffer_free(&packed);
}

static dml_status get_object_view(dml_txn *txn, dml_record_type type, const dml_object_id *id,
                                  dml_buffer *packed, dml_object_view *view) {
  dml_status status = dml_txn_get_object(txn, type, id, packed, NULL);
  if (status != DML_OK) return status;
  return dml_object_decode(packed->data, packed->len, view, NULL);
}

static dml_status read_object_reference(dml_txn *txn, dml_record_type type, const dml_object_id *id,
                                        dml_object_id *reference, uint32_t *node_kind) {
  dml_buffer packed = {0};
  dml_object_view view;
  dml_status status = get_object_view(txn, type, id, &packed, &view);
  if (status == DML_OK) {
    *reference = view.reference;
    if (node_kind != NULL) *node_kind = view.node_kind;
  }
  dml_buffer_free(&packed);
  return status;
}

static dml_status find_tree_entry(const dml_object_view *tree_view, dml_bytes entry_name,
                                  dml_object_id *dag_id) {
  for (size_t i = 0; i < tree_view->count; ++i) {
    dml_tree_entry entry;
    dml_status status = dml_object_view_entry(tree_view, i, &entry, NULL);
    if (status != DML_OK) return status;
    if (entry.name.len == entry_name.len &&
        memcmp(entry.name.data, entry_name.data, entry_name.len) == 0) {
      *dag_id = entry.dag;
      return DML_OK;
    }
  }
  return DML_NOT_FOUND;
}

typedef struct {
  const char *stage;
  dml_object_id head;
  dml_object_id parent;
  dml_object_id datum_id;
  dml_datum_kind kind;
  int64_t value;
} value_observation;

static dml_status read_parent(dml_txn *txn, size_t index, value_observation *out) {
  dml_buffer packed = {0};
  dml_object_view view;
  out->stage = "head_commit";
  dml_status status = get_object_view(txn, DML_REC_COMMIT, &out->head, &packed, &view);
  if (status == DML_OK) {
    out->stage = "parent";
    status = dml_object_view_parent(&view, index, &out->parent, NULL);
  }
  dml_buffer_free(&packed);
  return status;
}

static dml_status read_tree_dag(dml_txn *txn, const dml_object_id *commit_id, dml_bytes entry_name,
                                dml_object_id *dag_id, value_observation *out) {
  out->stage = "commit";
  dml_object_id tree_id;
  dml_status status = read_object_reference(txn, DML_REC_COMMIT, commit_id, &tree_id, NULL);
  if (status != DML_OK) return status;

  dml_buffer packed = {0};
  dml_object_view view;
  out->stage = "tree";
  status = get_object_view(txn, DML_REC_TREE, &tree_id, &packed, &view);
  if (status == DML_OK) {
    out->stage = "tree_entry";
    status = dml_name_validate(entry_name, NULL);
    if (status == DML_OK) status = find_tree_entry(&view, entry_name, dag_id);
  }
  dml_buffer_free(&packed);
  return status;
}

/* The public datum view exposes the validated I64 payload in little-endian order. */
static int64_t read_i64(const uint8_t *payload) {
  uint64_t bits = 0;
  for (size_t i = 0; i < sizeof(bits); ++i) bits |= (uint64_t)payload[i] << (i * 8);
  return bits <= INT64_MAX ? (int64_t)bits : -1 - (int64_t)(UINT64_MAX - bits);
}

static dml_status read_literal_datum(dml_txn *txn, const dml_object_id *node_id,
                                     value_observation *out) {
  out->stage = "node";
  dml_object_id datum_id;
  uint32_t node_kind;
  dml_status status = read_object_reference(txn, DML_REC_NODE, node_id, &datum_id, &node_kind);
  if (status != DML_OK) return status;
  out->stage = "node_kind";
  if (node_kind != DML_NODE_LITERAL) return DML_INVALID_KIND;

  dml_buffer packed = {0};
  out->datum_id = datum_id;
  out->stage = "datum_get";
  status = dml_txn_get_datum(txn, &out->datum_id, &packed, NULL);
  if (status == DML_OK) {
    dml_datum_view datum_view;
    out->stage = "datum_decode";
    status = dml_datum_decode(packed.data, packed.len, &datum_view, NULL);
    if (status == DML_OK) {
      out->kind = datum_view.kind;
      if (out->kind == DML_DATUM_I64) out->value = read_i64(datum_view.payload);
    }
  }
  dml_buffer_free(&packed);
  return status;
}

static dml_status read_value_path(dml_txn *txn, const size_t *parent_index, dml_bytes entry_name,
                                  dml_bytes binding_name, value_observation *out) {
  out->stage = "ref";
  dml_status status = dml_txn_ref_get(txn, name("main"), &out->head, NULL);
  if (status != DML_OK) return status;

  const dml_object_id *commit_id = &out->head;
  if (parent_index != NULL) {
    status = read_parent(txn, *parent_index, out);
    if (status != DML_OK) return status;
    commit_id = &out->parent;
  }
  dml_object_id dag_id, node_id;
  status = read_tree_dag(txn, commit_id, entry_name, &dag_id, out);
  if (status != DML_OK) return status;
  out->stage = "binding";
  status = dml_txn_lookup_node(txn, &dag_id, binding_name, &node_id, NULL);
  if (status != DML_OK) return status;
  return read_literal_datum(txn, &node_id, out);
}

static void read_value(dml_repo *repo, const size_t *parent_index, const char *entry_name,
                       const char *binding_name) {
  value_observation observed = {.stage = "begin"};
  memset(observed.head.bytes, 0xa5, sizeof(observed.head.bytes));
  memset(observed.parent.bytes, 0xa5, sizeof(observed.parent.bytes));
  memset(observed.datum_id.bytes, 0xa5, sizeof(observed.datum_id.bytes));

  dml_txn *txn = NULL;
  dml_status status = dml_txn_begin(repo, DML_TXN_READ, &txn, NULL);
  if (status == DML_OK) {
    status = read_value_path(txn, parent_index, name(entry_name), name(binding_name), &observed);
  }
  dml_txn_abort(&txn);

  char head_hex[DML_OBJECT_ID_HEX_SIZE + 1], datum_hex[DML_OBJECT_ID_HEX_SIZE + 1];
  format_id(observed.head, head_hex);
  format_id(observed.datum_id, datum_hex);
  printf("%s %s %s ", dml_status_name(status), observed.stage, head_hex);
  if (parent_index != NULL) {
    char parent_hex[DML_OBJECT_ID_HEX_SIZE + 1];
    format_id(observed.parent, parent_hex);
    printf("%s ", parent_hex);
  }
  printf("%s %u %" PRId64 "\n", datum_hex, (unsigned)observed.kind, observed.value);
}

static bool parse_parent_index(const char *text, size_t *index) {
  if (*text == '\0' || text[strspn(text, "0123456789")] != '\0') return false;
  errno = 0;
  uintmax_t value = strtoumax(text, NULL, 10);
  if (errno == ERANGE || value > SIZE_MAX) return false;
  *index = (size_t)value;
  return true;
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
  bool publishing = argc == 4 && strcmp(argv[1], "publish_main") == 0;
  bool reading = argc == 3 && strcmp(argv[1], "read_main") == 0;
  bool reading_value = argc == 5 && strcmp(argv[1], "read_value") == 0;
  bool reading_parent = argc == 6 && strcmp(argv[1], "read_parent_value") == 0;
  if (!create && !exporting && !importing && !publishing && !reading &&
      !reading_value && !reading_parent) {
    fprintf(stderr, "usage: transfer_replay seed REPO {source|destination|large|oversize}\n"
                    "       transfer_replay export REPO ROOT FILE {normal|busy|dirty}\n"
                    "       transfer_replay import REPO FILE {normal|busy|limited}\n"
                    "       transfer_replay publish_main REPO TARGET\n"
                    "       transfer_replay read_main REPO\n"
                    "       transfer_replay read_value REPO TREE_ENTRY BINDING\n"
                    "       transfer_replay read_parent_value REPO PARENT_INDEX TREE_ENTRY BINDING\n"
                    "       transfer_replay delete REPO OBJECT_KEY\n"
                    "       transfer_replay overwrite REPO OBJECT_KEY COPY_KEY\n");
    return EXIT_FAILURE;
  }
  size_t parent_index;
  if (reading_parent && !parse_parent_index(argv[3], &parent_index)) {
    fprintf(stderr, "invalid parent index: %s\n", argv[3]);
    return EXIT_FAILURE;
  }
  const char *mode = publishing || reading || reading_value || reading_parent ? "" : argv[argc - 1];
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
  } else if (publishing) {
    publish_main(repo, argv[3]);
  } else if (reading) {
    read_main(repo);
  } else if (reading_value) {
    read_value(repo, NULL, argv[3], argv[4]);
  } else if (reading_parent) {
    read_value(repo, &parent_index, argv[4], argv[5]);
  } else {
    if (exporting) export_bundle(repo, argv[3], argv[4], mode);
    else import_bundle(repo, argv[3]);
    printf("%s\n", busy ? dml_status_name(dml_txn_commit(&txn, NULL)) : "none");
  }
  require_ok(dml_repo_close(&repo, NULL), "closing fixture repository");
  return ferror(stdout) ? EXIT_FAILURE : EXIT_SUCCESS;
}
