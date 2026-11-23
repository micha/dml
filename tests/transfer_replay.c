#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <lmdb.h>

#include "../examples/lineage.h"

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

static dml_status add_one(int64_t input, int64_t *output);

static dml_object_id retention_snapshot(dml_txn *txn, const dml_object_id *parent) {
  bool selected = parent != NULL;
  dml_object_id scalar = number(txn, selected ? "selected_datum" : "base_datum", selected ? 45 : 41);
  dml_object_id literal = node(txn, selected ? "selected_node" : "base_node", DML_NODE_LITERAL, scalar);
  dml_dag_binding binding = {name("z-bound"), literal};
  dml_tree_entry entry = {name("all"), dag(txn, selected ? "selected_dag" : "base_dag", literal, &binding, 1)};
  dml_object_id snapshot = tree(txn, selected ? "selected_tree" : "base_tree", &entry, 1);
  return commit(txn, selected ? "selected" : "base", snapshot, parent, selected ? 1 : 0);
}

static void seed_retention(dml_repo *repo) {
  dml_txn *txn = NULL;
  require_ok(dml_txn_begin(repo, DML_TXN_WRITE, &txn, NULL), "beginning retention fixture");
  dml_object_id base = retention_snapshot(txn, NULL);
  dml_object_id selected = retention_snapshot(txn, &base);
  require_ok(dml_txn_commit(&txn, NULL), "committing retention fixture inputs");

  lineage_input input;
  require_ok(dml_txn_begin(repo, DML_TXN_READ, &txn, NULL), "reading retention fixture input");
  require_ok(lineage_read_input(txn, &selected, name("all"), name("z-bound"), &input, NULL),
             "selecting retention fixture input");
  dml_txn_abort(&txn);

  lineage_candidate result = {0};
  require_ok(lineage_record(repo, &input, name("example.add-one@1"), add_one, &result, NULL),
             "recording retention fixture result");
  require_ok(result.completion, "committing retention fixture result");
  announce("output_datum", "datums", result.output_datum);
  announce("output_node", "nodes", result.output_node);
  announce("implementation_datum", "datums", result.implementation_datum);
  announce("implementation_node", "nodes", result.implementation_node);
  announce("result_dag", "dags", result.dag);
  announce("result_tree", "trees", result.tree);
  announce("result", "commits", result.commit);
}

static void seed(dml_repo *repo, const char *profile) {
  if (!strcmp(profile, "retention")) {
    seed_retention(repo);
    return;
  }
  if (!strcmp(profile, "empty")) return;
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

static void write_ref(dml_repo *repo, bool create, const char *ref_name, const char *target_hex) {
  dml_object_id target;
  require_ok(dml_object_id_parse(target_hex, strlen(target_hex), &target, NULL),
             "parsing imported commit ID");
  dml_txn *txn = NULL;
  require_ok(dml_txn_begin(repo, DML_TXN_WRITE, &txn, NULL), "beginning ref write transaction");
  dml_status written = create ? dml_txn_ref_create(txn, name(ref_name), &target, NULL)
                              : dml_txn_ref_update(txn, name(ref_name), &target, NULL);
  dml_status committed = dml_txn_commit(&txn, NULL);
  printf("%s\n%s\n", dml_status_name(written), dml_status_name(committed));
}

static void release_expected(dml_repo *repo, const char *ref, const char *expected_hex, bool commit) {
  dml_object_id expected;
  require_ok(dml_object_id_parse(expected_hex, strlen(expected_hex), &expected, NULL), "parse expected ID");
  dml_txn *txn = NULL;
  require_ok(dml_txn_begin(repo, DML_TXN_WRITE, &txn, NULL), "begin conditional release");
  dml_status removed = dml_txn_ref_delete_expected(txn, name(ref), &expected, NULL);
  const char *completion = commit ? dml_status_name(dml_txn_commit(&txn, NULL)) : "aborted";
  dml_txn_abort(&txn);
  printf("%s\n%s\n", dml_status_name(removed), completion);
}

static dml_status edit_gc_ref(dml_txn *txn, const char *edit, const char *ref_name,
                              const dml_object_id *target) {
  dml_bytes ref = name(ref_name);
  if (!strcmp(edit, "create")) return dml_txn_ref_create(txn, ref, target, NULL);
  if (!strcmp(edit, "update")) return dml_txn_ref_update(txn, ref, target, NULL);
  return dml_txn_ref_delete_expected(txn, ref, target, NULL);
}

static void run_gc_transaction(dml_repo *repo, const char *order, const char *edit,
                               const char *ref_name, const char *target_hex, bool commit_txn) {
  dml_txn *txn = NULL;
  dml_object_id target;
  bool edit_first = !strcmp(order, "before") || !strcmp(order, "only");
  bool edit_after = !strcmp(order, "after");
  if (edit_first || edit_after) {
    require_ok(dml_object_id_parse(target_hex, strlen(target_hex), &target, NULL), "parse GC ref target");
  }
  require_ok(dml_txn_begin(repo, DML_TXN_WRITE, &txn, NULL), "beginning GC transaction");
  const char *edit_status = "none";
  const char *gc_status = "none";
  size_t removed = 123456789;
  if (edit_first) edit_status = dml_status_name(edit_gc_ref(txn, edit, ref_name, &target));
  if (strcmp(order, "only")) gc_status = dml_status_name(dml_txn_collect_garbage(txn, &removed, NULL));
  if (edit_after) edit_status = dml_status_name(edit_gc_ref(txn, edit, ref_name, &target));
  const char *completion = commit_txn ? dml_status_name(dml_txn_commit(&txn, NULL)) : "aborted";
  dml_txn_abort(&txn);
  printf("%s %s %s %zu\n", gc_status, edit_status, completion, removed);
}

static void publish_expected(dml_repo *repo, const char *ref, const char *expected_hex,
                             const char *target_hex) {
  dml_object_id expected, target;
  require_ok(dml_object_id_parse(expected_hex, strlen(expected_hex), &expected, NULL), "parse expected ID");
  require_ok(dml_object_id_parse(target_hex, strlen(target_hex), &target, NULL), "parse inspected ID");
  dml_txn *txn = NULL;
  require_ok(dml_txn_begin(repo, DML_TXN_WRITE, &txn, NULL), "begin conditional publication");
  lineage_publication observed;
  lineage_publish_expected(&txn, name(ref), &expected, &target, &observed, NULL);
  char hex[DML_OBJECT_ID_HEX_SIZE + 1];
  format_id(observed.actual, hex);
  printf("%s %s\n%s %s\n", dml_status_name(observed.get), hex,
         observed.attempted_update ? dml_status_name(observed.update) : "none",
         observed.attempted_update ? dml_status_name(observed.completion) : txn == NULL ? "aborted" : "active");
  dml_txn_abort(&txn);
}

static void print_unreachable(void *context, dml_record_type type, const dml_object_id *id) {
  (void)context;
  char text[DML_OBJECT_ID_HEX_SIZE + 1];
  format_id(*id, text);
  printf("%u %s\n", (unsigned)type, text);
}

static void check_integrity(dml_repo *repo) {
  dml_txn *txn = NULL;
  require_ok(dml_txn_begin(repo, DML_TXN_READ, &txn, NULL), "beginning integrity scan");
  dml_repo_integrity report = {0};
  dml_status status = dml_txn_check_integrity(txn, &report, print_unreachable, NULL, NULL);
  dml_txn_abort(&txn);
  printf("%s %zu %zu %zu %zu %zu %zu %zu %zu %zu\n", dml_status_name(status),
         report.refs, report.broken_refs, report.invalid_entries, report.invalid_objects, report.reachable_objects,
         report.broken_reachable_edges, report.broken_unreachable_edges, report.intact_unreachable_objects,
         report.broken_unreachable_objects);
}

static void read_ref(dml_repo *repo, const char *ref_name) {
  dml_txn *txn = NULL;
  require_ok(dml_txn_begin(repo, DML_TXN_READ, &txn, NULL), "beginning readback transaction");
  dml_object_id target;
  memset(target.bytes, 0xa5, sizeof(target.bytes));
  dml_status resolved = dml_txn_ref_get(txn, name(ref_name), &target, NULL);
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

static dml_status read_value_path(dml_txn *txn, dml_bytes ref_name, const size_t *parent_index,
                                  dml_bytes entry_name, dml_bytes binding_name,
                                  value_observation *out) {
  out->stage = "ref";
  dml_status status = dml_txn_ref_get(txn, ref_name, &out->head, NULL);
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

static void read_value(dml_repo *repo, const char *ref_name, const size_t *parent_index,
                       const char *entry_name, const char *binding_name) {
  value_observation observed = {.stage = "begin"};
  memset(observed.head.bytes, 0xa5, sizeof(observed.head.bytes));
  memset(observed.parent.bytes, 0xa5, sizeof(observed.parent.bytes));
  memset(observed.datum_id.bytes, 0xa5, sizeof(observed.datum_id.bytes));

  dml_txn *txn = NULL;
  dml_status status = dml_txn_begin(repo, DML_TXN_READ, &txn, NULL);
  if (status == DML_OK) {
    status = read_value_path(txn, name(ref_name), parent_index, name(entry_name), name(binding_name),
                             &observed);
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

static dml_status add_one(int64_t input, int64_t *output) {
  if (input == INT64_MAX) return DML_INVALID_BOUNDS;
  *output = input + 1;
  return DML_OK;
}

static dml_status add_two(int64_t input, int64_t *output) {
  if (input > INT64_MAX - 2) return DML_INVALID_BOUNDS;
  *output = input + 2;
  return DML_OK;
}

static void record_lineage(dml_repo *repo, const char *input_hex, const char *mode) {
  dml_object_id selected;
  require_ok(dml_object_id_parse(input_hex, strlen(input_hex), &selected, NULL), "parse input ID");
  bool first = strcmp(mode, "add-one") == 0;
  const dml_bytes identity = name(first ? "example.add-one@1" : "example.add-two@1");
  lineage_input input;
  dml_txn *txn = NULL;
  dml_status status = dml_txn_begin(repo, DML_TXN_READ, &txn, NULL);
  if (status == DML_OK) {
    status = lineage_read_input(txn, &selected, name("all"), name("z-bound"), &input, NULL);
  }
  dml_txn_abort(&txn);
  lineage_candidate candidate = {0};
  if (status == DML_OK) {
    status = lineage_record(repo, &input, identity, first ? add_one : add_two, &candidate, NULL);
  }
  printf("%s %s\n", dml_status_name(status),
         candidate.attempted_commit ? dml_status_name(candidate.completion) : "none");
  const dml_object_id ids[] = {candidate.output_datum, candidate.output_node,
                              candidate.implementation_datum, candidate.implementation_node,
                              candidate.dag, candidate.tree, candidate.commit};
  for (size_t i = 0; i < sizeof(ids) / sizeof(*ids); ++i) {
    char hex[DML_OBJECT_ID_HEX_SIZE + 1];
    format_id(ids[i], hex);
    printf("%s%c", hex, i == sizeof(ids) / sizeof(*ids) - 1 ? '\n' : ' ');
  }
}

static void read_lineage(dml_repo *repo, bool by_ref, const char *selector) {
  lineage_observation observed = {0};
  dml_object_id commit;
  if (!by_ref) {
    require_ok(dml_object_id_parse(selector, strlen(selector), &commit, NULL), "parse result ID");
  }
  dml_txn *txn = NULL;
  dml_status status = dml_txn_begin(repo, DML_TXN_READ, &txn, NULL);
  if (status == DML_OK && by_ref) status = dml_txn_ref_get(txn, name(selector), &commit, NULL);
  if (status == DML_OK) {
    status = lineage_inspect(txn, &commit, name("all"), name("z-bound"), &observed, NULL);
  }
  dml_txn_abort(&txn);

  printf("%s\n", dml_status_name(status));
  const dml_object_id ids[] = {observed.commit, observed.input.commit, observed.input.datum,
                              observed.output_datum, observed.implementation_datum};
  for (size_t i = 0; i < sizeof(ids) / sizeof(*ids); ++i) {
    char hex[DML_OBJECT_ID_HEX_SIZE + 1];
    format_id(ids[i], hex);
    printf("%s ", hex);
  }
  printf("%" PRId64 " %" PRId64 " ", observed.input.value, observed.output);
  if (observed.implementation.len == 0) putchar('-');
  for (size_t i = 0; i < observed.implementation.len; ++i) {
    printf("%02x", (unsigned)observed.implementation.data[i]);
  }
  putchar('\n');
  dml_buffer_free(&observed.implementation_record);
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
  bool creating_ref = argc == 5 && strcmp(argv[1], "create_ref") == 0;
  bool updating_ref = argc == 5 && strcmp(argv[1], "update_ref") == 0;
  bool reading = argc == 4 && strcmp(argv[1], "read_ref") == 0;
  bool reading_value = argc == 6 && strcmp(argv[1], "read_value") == 0;
  bool reading_parent = argc == 7 && strcmp(argv[1], "read_parent_value") == 0;
  bool recording = argc == 5 && strcmp(argv[1], "record_lineage") == 0 &&
                   (strcmp(argv[4], "add-one") == 0 || strcmp(argv[4], "add-two") == 0);
  bool reading_lineage = (argc == 3 || (argc == 5 && (!strcmp(argv[3], "id") || !strcmp(argv[3], "ref")))) &&
                         strcmp(argv[1], "read_lineage") == 0;
  bool publishing = argc == 6 && strcmp(argv[1], "publish_expected") == 0;
  bool releasing = argc == 6 && strcmp(argv[1], "release_expected") == 0 &&
                   (!strcmp(argv[5], "commit") || !strcmp(argv[5], "abort"));
  bool checking = argc == 3 && strcmp(argv[1], "check_integrity") == 0;
  bool collecting = argc == 8 && !strcmp(argv[1], "gc_transaction") &&
                    ((!strcmp(argv[3], "none") && !strcmp(argv[4], "none")) ||
                     ((!strcmp(argv[3], "before") || !strcmp(argv[3], "after") || !strcmp(argv[3], "only")) &&
                      (!strcmp(argv[4], "create") || !strcmp(argv[4], "update") || !strcmp(argv[4], "delete")))) &&
                    (!strcmp(argv[7], "commit") || !strcmp(argv[7], "abort"));
  if (!create && !exporting && !importing && !creating_ref && !updating_ref && !reading && !reading_value &&
      !reading_parent && !recording && !reading_lineage && !publishing && !releasing && !checking && !collecting) {
    fprintf(stderr, "usage: transfer_replay seed REPO {source|destination|large|oversize|retention|empty}\n"
                    "       transfer_replay export REPO ROOT FILE {normal|busy|dirty}\n"
                    "       transfer_replay import REPO FILE {normal|busy|limited}\n"
                    "       transfer_replay {create_ref|update_ref} REPO REF TARGET\n"
                    "       transfer_replay read_ref REPO REF\n"
                    "       transfer_replay read_value REPO REF TREE_ENTRY BINDING\n"
                    "       transfer_replay read_parent_value REPO REF PARENT_INDEX TREE_ENTRY BINDING\n"
                    "       transfer_replay record_lineage REPO INPUT_ID {add-one|add-two}\n"
                    "       transfer_replay read_lineage REPO [id COMMIT_ID | ref REF]\n"
                    "       transfer_replay publish_expected REPO REF EXPECTED_ID TARGET_ID\n"
                    "       transfer_replay release_expected REPO REF EXPECTED_ID {commit|abort}\n"
                    "       transfer_replay check_integrity REPO\n"
                    "       transfer_replay gc_transaction REPO ORDER EDIT REF TARGET {commit|abort}\n"
                    "       transfer_replay delete REPO OBJECT_KEY\n"
                    "       transfer_replay overwrite REPO OBJECT_KEY COPY_KEY\n");
    return EXIT_FAILURE;
  }
  size_t parent_index;
  if (reading_parent && !parse_parent_index(argv[4], &parent_index)) {
    fprintf(stderr, "invalid parent index: %s\n", argv[4]);
    return EXIT_FAILURE;
  }
  const char *mode = create || exporting || importing ? argv[argc - 1] : "";
  if (create && strcmp(mode, "source") && strcmp(mode, "destination") &&
      strcmp(mode, "large") && strcmp(mode, "oversize") && strcmp(mode, "retention") && strcmp(mode, "empty")) {
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
  } else if (creating_ref || updating_ref) {
    write_ref(repo, creating_ref, argv[3], argv[4]);
  } else if (reading) {
    read_ref(repo, argv[3]);
  } else if (reading_value) {
    read_value(repo, argv[3], NULL, argv[4], argv[5]);
  } else if (reading_parent) {
    read_value(repo, argv[3], &parent_index, argv[5], argv[6]);
  } else if (recording) {
    record_lineage(repo, argv[3], argv[4]);
  } else if (reading_lineage) {
    read_lineage(repo, argc == 3 || strcmp(argv[3], "ref") == 0, argc == 3 ? "result-pin" : argv[4]);
  } else if (publishing) {
    publish_expected(repo, argv[3], argv[4], argv[5]);
  } else if (releasing) {
    release_expected(repo, argv[3], argv[4], strcmp(argv[5], "commit") == 0);
  } else if (checking) {
    check_integrity(repo);
  } else if (collecting) {
    run_gc_transaction(repo, argv[3], argv[4], argv[5], argv[6], !strcmp(argv[7], "commit"));
  } else {
    if (exporting) export_bundle(repo, argv[3], argv[4], mode);
    else import_bundle(repo, argv[3]);
    printf("%s\n", busy ? dml_status_name(dml_txn_commit(&txn, NULL)) : "none");
  }
  require_ok(dml_repo_close(&repo, NULL), "closing fixture repository");
  return ferror(stdout) ? EXIT_FAILURE : EXIT_SUCCESS;
}
