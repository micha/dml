#include <errno.h>
#include <inttypes.h>
#include <locale.h>
#include <math.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "dml/dml.h"

typedef struct { char *data; size_t len, capacity; int failed; } Text;
typedef struct { dml_object_id id; int leave; dml_record_type type; } Work;
typedef struct { dml_object_id id; int active; dml_record_type type; } Seen;

static int grow(Text *text, size_t extra) {
  if (text->failed) return 0;
  if (extra > SIZE_MAX - text->len - 1) { text->failed = 1; return 0; }
  size_t need = text->len + extra + 1;
  if (need <= text->capacity) return 1;
  size_t capacity = need < 1024 ? 1024 : need;
  char *data = realloc(text->data, capacity);
  if (!data) { text->failed = 1; return 0; }
  text->data = data; text->capacity = capacity;
  return 1;
}

static void raw(Text *text, const char *data, size_t len) {
  if (!grow(text, len)) return;
  memcpy(text->data + text->len, data, len);
  text->len += len; text->data[text->len] = '\0';
}

static void add(Text *text, const char *data) { raw(text, data, strlen(data)); }

static void number(Text *text, size_t value) {
  char buffer[32]; snprintf(buffer, sizeof(buffer), "%zu", value); add(text, buffer);
}

static void quote(Text *text, const uint8_t *data, size_t len) {
  add(text, "\"");
  for (size_t i = 0; i < len; i++) {
    unsigned char c = data[i];
    if (c == '"' || c == '\\') { add(text, "\\"); raw(text, (const char *)&data[i], 1); }
    else if (c < 0x20 || c == 0x7f) {
      char escaped[7]; snprintf(escaped, sizeof(escaped), "\\u%04x", c); add(text, escaped);
    /* Inputs are validated UTF-8 or fixed ASCII diagnostics. A C2 lead has a
     * following continuation byte; avoid interpreting C1 terminal controls. */
    } else if (c == 0xc2 && data[i + 1] <= 0x9f) {
      char escaped[7]; snprintf(escaped, sizeof(escaped), "\\u%04x", data[++i]); add(text, escaped);
    } else raw(text, (const char *)&data[i], 1);
  }
  add(text, "\"");
}

static void string(Text *text, const char *data) { quote(text, (const uint8_t *)data, strlen(data)); }

static void id(Text *text, const dml_object_id *value) {
  char buffer[33]; dml_object_id_format(value, buffer, NULL); string(text, buffer);
}

static void parents(Text *text, const dml_object_view *view) {
  add(text, "[");
  for (size_t i = 0; i < view->count; i++) {
    dml_object_id parent; dml_object_view_parent(view, i, &parent, NULL);
    if (i) add(text, ",");
    id(text, &parent);
  }
  add(text, "]");
}

static uint64_t little64(const uint8_t *data) {
  uint64_t bits = 0;
  for (unsigned i = 0; i < 8; i++) bits |= (uint64_t)data[i] << (8 * i);
  return bits;
}

static size_t utf8_prefix(const uint8_t *data, size_t len, size_t max, size_t *count) {
  size_t prefix = len; *count = 0;
  for (size_t i = 0; i < len; i++) {
    if ((data[i] & 0xc0) != 0x80) {
      if (*count == max) prefix = i;
      ++*count;
    }
  }
  return prefix;
}

static void datum(Text *text, const dml_datum_view *view, int preview) {
  static const char *kinds[] = {"null", "bool", "i64", "f64", "bytes", "string", "uri", "list", "set", "map"};
  add(text, "{\"kind\":"); string(text, kinds[view->kind - 1]); add(text, ",\"value\":");
  int truncated = 0; size_t total = 0;
  switch (view->kind) {
    case DML_DATUM_NULL: add(text, "null"); break;
    case DML_DATUM_BOOL: add(text, view->payload[0] ? "true" : "false"); break;
    case DML_DATUM_I64: {
      uint64_t bits = little64(view->payload); int64_t value; memcpy(&value, &bits, 8);
      char buffer[32]; snprintf(buffer, sizeof(buffer), "%" PRId64, value); string(text, buffer); break;
    }
    case DML_DATUM_F64: {
      uint64_t bits = little64(view->payload); double value; memcpy(&value, &bits, 8);
      char buffer[64];
      if (isnan(value)) strcpy(buffer, "nan");
      else if (isinf(value)) strcpy(buffer, signbit(value) ? "-inf" : "inf");
      else snprintf(buffer, sizeof(buffer), "%.17g", value);
      string(text, buffer); break;
    }
    case DML_DATUM_BYTES: {
      total = view->payload_len;
      size_t count = preview && total > 32 ? 32 : total; truncated = count < total;
      add(text, "\"");
      for (size_t i = 0; i < count; i++) { char hex[3]; snprintf(hex, sizeof(hex), "%02x", view->payload[i]); add(text, hex); }
      add(text, "\",\"encoding\":\"hex\""); break;
    }
    case DML_DATUM_STRING: case DML_DATUM_URI: {
      size_t count = utf8_prefix(view->payload, view->payload_len, preview ? 80 : SIZE_MAX, &total);
      truncated = count < view->payload_len; quote(text, view->payload, count); break;
    }
    default: {
      total = view->count;
      size_t count = preview && total > 8 ? 8 : total; truncated = count < total;
      add(text, "[");
      for (size_t i = 0; i < count; i++) {
        if (i) add(text, ",");
        if (view->kind == DML_DATUM_MAP) {
          dml_datum_map_entry entry; dml_datum_view_map_entry(view, i, &entry, NULL);
          add(text, "{\"key\":"); id(text, &entry.key); add(text, ",\"value\":"); id(text, &entry.value); add(text, "}");
        } else { dml_object_id value; dml_datum_view_id(view, i, &value, NULL); id(text, &value); }
      }
      add(text, "]"); break;
    }
  }
  if (preview) {
    add(text, ",\"truncated\":"); add(text, truncated ? "true" : "false");
    if (view->kind >= DML_DATUM_BYTES) { add(text, ",\"total_count\":"); number(text, total); }
  }
  add(text, "}");
}

static dml_status load(dml_txn *txn, dml_record_type type, const dml_object_id *value,
                       dml_buffer *buffer, dml_object_view *view, dml_error *error) {
  dml_status status = dml_txn_get_object(txn, type, value, buffer, error);
  if (status == DML_OK) status = dml_object_decode(buffer->data, buffer->len, view, error);
  return status;
}

static void node_fields(Text *text, const dml_object_view *view) {
  add(text, view->node_kind == DML_NODE_LITERAL
      ? "\"kind\":\"literal\",\"datum\":" : "\"kind\":\"subdag\",\"dag\":");
  id(text, &view->reference);
}

static void dag_fields(Text *text, const dml_object_view *view) {
  add(text, "\"root\":"); id(text, &view->reference); add(text, ",\"bindings\":[");
  for (size_t i = 0; i < view->count; i++) {
    dml_dag_binding binding; dml_object_view_binding(view, i, &binding, NULL);
    if (i) add(text, ",");
    add(text, "{\"name\":"); quote(text, binding.name.data, binding.name.len);
    add(text, ",\"node\":"); id(text, &binding.node); add(text, "}");
  }
  add(text, "]");
}

static dml_status literal_preview(Text *text, dml_txn *txn, const dml_object_id *value,
                                  dml_error *error) {
  dml_buffer buffer = {0}; dml_datum_view view;
  dml_status status = dml_txn_get_datum(txn, value, &buffer, error);
  if (status == DML_OK) status = dml_datum_decode(buffer.data, buffer.len, &view, error);
  if (status == DML_OK) { add(text, ",\"preview\":"); datum(text, &view, 1); }
  dml_buffer_free(&buffer);
  return status;
}

static dml_status show(Text *text, dml_txn *txn, dml_record_type type,
                       const dml_object_id *value, const char *type_name, int json, dml_error *error) {
  dml_buffer buffer = {0}; dml_status status;
  add(text, "{\"command\":\"show\",\"type\":"); string(text, type_name); add(text, ",\"id\":"); id(text, value);
  if (type == DML_REC_DATUM) {
    status = dml_txn_get_datum(txn, value, &buffer, error);
    if (status == DML_OK) {
      dml_datum_view view; status = dml_datum_decode(buffer.data, buffer.len, &view, error);
      if (status == DML_OK) { add(text, ",\"datum\":"); datum(text, &view, !json); }
    }
  } else {
    dml_object_view view; status = load(txn, type, value, &buffer, &view, error);
    if (status == DML_OK) {
      if (type == DML_REC_NODE) { add(text, ","); node_fields(text, &view); }
      else if (type == DML_REC_DAG) { add(text, ","); dag_fields(text, &view); }
      else if (type == DML_REC_COMMIT) { add(text, ",\"tree\":"); id(text, &view.reference); add(text, ",\"parents\":"); parents(text, &view); }
      else {
        add(text, ",\"entries\":[");
        for (size_t i = 0; i < view.count; i++) {
          dml_tree_entry entry; dml_object_view_entry(&view, i, &entry, NULL);
          if (i) add(text, ",");
          add(text, "{\"name\":"); quote(text, entry.name.data, entry.name.len); add(text, ",\"dag\":"); id(text, &entry.dag); add(text, "}");
        }
        add(text, "]");
      }
    }
  }
  add(text, "}\n"); dml_buffer_free(&buffer); return status;
}

static dml_status snapshot_entry(Text *text, dml_txn *txn, const dml_tree_entry *entry, dml_error *error) {
  dml_buffer dag = {0}, node = {0}; dml_object_view dag_view, node_view;
  dml_status status = load(txn, DML_REC_DAG, &entry->dag, &dag, &dag_view, error);
  if (status != DML_OK) goto done;
  status = load(txn, DML_REC_NODE, &dag_view.reference, &node, &node_view, error);
  if (status != DML_OK) goto done;
  add(text, "{\"name\":"); quote(text, entry->name.data, entry->name.len);
  add(text, ",\"dag\":"); id(text, &entry->dag); add(text, ",\"root\":"); id(text, &dag_view.reference);
  add(text, ",\"root_node\":{"); node_fields(text, &node_view); add(text, "}");
  if (node_view.node_kind == DML_NODE_LITERAL) {
    add(text, ",\"datum\":"); id(text, &node_view.reference);
    status = literal_preview(text, txn, &node_view.reference, error);
  }
  add(text, "}");
done:
  dml_buffer_free(&dag); dml_buffer_free(&node); return status;
}

static dml_status snapshot(Text *text, dml_txn *txn, const dml_object_id *start, size_t limit, dml_error *error) {
  dml_buffer commit = {0}, tree = {0}; dml_object_view commit_view, tree_view;
  dml_status status = load(txn, DML_REC_COMMIT, start, &commit, &commit_view, error);
  if (status != DML_OK) goto done;
  status = load(txn, DML_REC_TREE, &commit_view.reference, &tree, &tree_view, error);
  if (status != DML_OK) goto done;
  add(text, "{\"command\":\"snapshot\",\"commit\":"); id(text, start);
  add(text, ",\"tree\":"); id(text, &commit_view.reference); add(text, ",\"parents\":"); parents(text, &commit_view);
  add(text, ",\"entry_count\":"); number(text, tree_view.count); add(text, ",\"entries\":[");
  size_t count = tree_view.count < limit ? tree_view.count : limit;
  for (size_t i = 0; i < count; i++) {
    dml_tree_entry entry; dml_object_view_entry(&tree_view, i, &entry, NULL);
    if (i) add(text, ",");
    status = snapshot_entry(text, txn, &entry, error); if (status != DML_OK) goto done;
  }
  add(text, "],\"truncated\":"); add(text, count < tree_view.count ? "true" : "false"); add(text, "}\n");
done:
  dml_buffer_free(&commit); dml_buffer_free(&tree); return status;
}

static dml_status traverse(Text *text, dml_txn *txn, const dml_object_id *start,
                            size_t limit, int graph, dml_error *error) {
  Work *work = malloc(sizeof(*work)); Seen *seen = NULL;
  size_t work_count = 1, seen_count = 0; int truncated = 0;
  dml_buffer buffer = {0}; dml_status status = DML_OK;
  if (!work) return DML_OUT_OF_MEMORY;
  work[0] = (Work){*start, 0, graph ? DML_REC_DAG : DML_REC_COMMIT};
  add(text, "{\"command\":"); string(text, graph ? "walk" : "log");
  add(text, ",\"start\":"); id(text, start); add(text, graph ? ",\"records\":[" : ",\"commits\":[");
  while (work_count) {
    Work item = work[--work_count]; size_t index;
    for (index = 0; index < seen_count; index++) {
      if (seen[index].type == item.type && memcmp(seen[index].id.bytes, item.id.bytes, 16) == 0) break;
    }
    if (item.leave) { seen[index].active = 0; continue; }
    if (index < seen_count) {
      if (seen[index].active) {
        status = DML_INTEGRITY_ERROR;
        strcpy(error->detail, graph ? "cycle in traversed DAG structure" : "cycle in traversed commit history");
        goto done;
      }
      continue;
    }
    if (seen_count == limit) { truncated = 1; break; }
    dml_object_view view;
    status = load(txn, item.type, &item.id, &buffer, &view, error);
    if (status != DML_OK) goto done;
    size_t children = view.count;
    if (item.type == DML_REC_DAG) children++;
    if (item.type == DML_REC_NODE) children = view.node_kind == DML_NODE_SUBDAG ? 1 : 0;
    /* Requires exabytes of already-allocated traversal state on the supported
     * 64-bit matrix; checked growth and actual allocation failures remain tested. */
    if (children > (SIZE_MAX / sizeof(*work)) - work_count - 1 || seen_count == SIZE_MAX / sizeof(*seen)) { /* LCOV_EXCL_BR_LINE */
      status = DML_OUT_OF_MEMORY; goto done; /* LCOV_EXCL_LINE */
    }
    Work *new_work = realloc(work, (work_count + children + 1) * sizeof(*work));
    if (!new_work) { status = DML_OUT_OF_MEMORY; goto done; }
    work = new_work;
    Seen *new_seen = realloc(seen, (seen_count + 1) * sizeof(*seen));
    if (!new_seen) { status = DML_OUT_OF_MEMORY; goto done; }
    seen = new_seen; seen[seen_count] = (Seen){item.id, 1, item.type};
    if (seen_count++) add(text, ",");
    add(text, "{");
    if (graph) { add(text, "\"type\":"); string(text, item.type == DML_REC_DAG ? "dag" : "node"); add(text, ","); }
    add(text, "\"id\":"); id(text, &item.id); add(text, ",");
    work[work_count++] = (Work){item.id, 1, item.type};
    if (item.type == DML_REC_DAG) {
      dag_fields(text, &view);
      for (size_t i = view.count; i > 0; i--) {
        dml_dag_binding binding; dml_object_view_binding(&view, i - 1, &binding, NULL);
        work[work_count++] = (Work){binding.node, 0, DML_REC_NODE};
      }
      work[work_count++] = (Work){view.reference, 0, DML_REC_NODE};
    } else if (item.type == DML_REC_NODE) {
      node_fields(text, &view);
      if (view.node_kind == DML_NODE_SUBDAG) work[work_count++] = (Work){view.reference, 0, DML_REC_DAG};
      else {
        status = literal_preview(text, txn, &view.reference, error);
        if (status != DML_OK) goto done;
      }
    } else {
      add(text, "\"tree\":"); id(text, &view.reference); add(text, ",\"parents\":"); parents(text, &view);
      for (size_t i = view.count; i > 0; i--) {
        dml_object_id parent; dml_object_view_parent(&view, i - 1, &parent, NULL);
        work[work_count++] = (Work){parent, 0, DML_REC_COMMIT};
      }
    }
    add(text, "}");
    dml_buffer_free(&buffer);
  }
  add(text, "],\"truncated\":"); add(text, truncated ? "true" : "false"); add(text, "}\n");
done:
  free(work); free(seen); dml_buffer_free(&buffer); return status;
}

/* A readable structured layout shares exactly the JSON fields, but displays one
 * field/entry per indented line. Quoted previews never contain terminal controls. */
static int human_output(const Text *text, const char *title) {
  if (fprintf(stdout, "%s\n", title) < 0) return 0;
  int quoted = 0, escaped = 0; size_t depth = 0;
  for (size_t i = 0; i < text->len; i++) {
    char c = text->data[i];
    if (quoted) {
      if (putchar(c) == EOF) return 0;
      if (escaped) escaped = 0;
      else if (c == '\\') escaped = 1;
      else if (c == '"') quoted = 0;
      continue;
    }
    if (c == '"') quoted = 1;
    if (c == '{' || c == '[') {
      if (putchar(c) == EOF || putchar('\n') == EOF) return 0;
      depth++;
    } else if (c == '}' || c == ']') {
      depth--;
      if (putchar('\n') == EOF) return 0;
      for (size_t j = 0; j < depth; j++) if (fputs("  ", stdout) < 0) return 0;
      if (putchar(c) == EOF) return 0;
      continue;
    } else if (c == ',') {
      if (fputs(",\n", stdout) < 0) return 0;
    } else if (c == ':') {
      if (fputs(": ", stdout) < 0) return 0;
      continue;
    } else {
      if (putchar(c) == EOF) return 0;
      continue;
    }
    for (size_t j = 0; j < depth; j++) if (fputs("  ", stdout) < 0) return 0;
  }
  return 1;
}

static const char *usage =
  "usage: dml [--json] --repo PATH COMMAND\n"
  "  dml --version|-V | --help\n"
  "  ref get NAME\n"
  "  show datum|node|dag|tree|commit ID\n"
  "  snapshot (--ref NAME | --commit ID) [--limit N]\n"
  "  lookup DAG_ID NAME\n"
  "  walk DAG_ID [--limit N]\n"
  "  log (--ref NAME | --commit ID) [--limit N]\n";

static int diagnostic(int json, dml_status status, const dml_error *error, int parser) {
  if (!json) fprintf(stderr, "%s: %s\n", dml_status_name(status), error->detail);
  else {
    Text text = {0}; add(&text, "{\"error\":{\"code\":"); string(&text, dml_status_name(status));
    add(&text, ",\"native_code\":");
    if (parser) add(&text, "null");
    else { char code[32]; snprintf(code, sizeof(code), "%d", error->native_code); add(&text, code); }
    add(&text, ",\"detail\":"); string(&text, error->detail); add(&text, "}}\n");
    if (!text.failed) fwrite(text.data, 1, text.len, stderr);
    else fputs("{\"error\":{\"code\":\"out_of_memory\",\"native_code\":0,\"detail\":\"diagnostic allocation failed\"}}\n", stderr);
    free(text.data);
  }
  return parser ? 2 : 1;
}

int main(int argc, char **argv) {
#ifdef SIGPIPE
  signal(SIGPIPE, SIG_IGN);
#endif
  setlocale(LC_NUMERIC, "C");
  if (argc == 2 && (!strcmp(argv[1], "--version") || !strcmp(argv[1], "-V"))) {
    if (puts(dml_version()) < 0 || fflush(stdout) != 0) return 1;
    return 0;
  }
  if (argc == 2 && !strcmp(argv[1], "--help")) {
    if (fputs(usage, stdout) < 0 || fflush(stdout) != 0) return 1;
    return 0;
  }
  int json = 0, index = 1, command = 0; const char *path = NULL, *name = NULL, *type_name = NULL;
  dml_object_id value; dml_record_type type = DML_REC_DATUM; size_t limit = 100;
  dml_error error = {0}; dml_status status = DML_INVALID_ARGUMENT;
  /* Recognize JSON even on malformed global arguments, for structured diagnostics. */
  for (int i = 1; i < argc; i++) if (!strcmp(argv[i], "--json")) json = 1;
  while (index < argc) {
    if (!strcmp(argv[index], "--json")) { index++; continue; }
    if (!strcmp(argv[index], "--repo") && index + 1 < argc && !path) { path = argv[index + 1]; index += 2; continue; }
    break;
  }
  if (!path || index >= argc) goto syntax;
  if (!strcmp(argv[index], "ref")) {
    if (argc - index != 3 || strcmp(argv[index + 1], "get")) goto syntax;
    command = 1; name = argv[index + 2];
  } else if (!strcmp(argv[index], "show")) {
    if (argc - index != 3) goto syntax;
    static const char *types[] = {"datum", "node", "dag", "tree", "commit"};
    type_name = argv[index + 1]; size_t i;
    for (i = 0; i < 5; i++) if (!strcmp(type_name, types[i])) break;
    if (i == 5) goto syntax;
    type = (dml_record_type)(i + 2);
    status = dml_object_id_parse(argv[index + 2], strlen(argv[index + 2]), &value, &error);
    if (status != DML_OK) return diagnostic(json, status, &error, 1);
    command = 2;
  } else if (!strcmp(argv[index], "lookup")) {
    if (argc - index != 3) goto syntax;
    status = dml_object_id_parse(argv[index + 1], strlen(argv[index + 1]), &value, &error);
    if (status != DML_OK) return diagnostic(json, status, &error, 1);
    name = argv[index + 2];
    status = dml_name_validate((dml_bytes){(const uint8_t *)name, strlen(name)}, &error);
    if (status != DML_OK) return diagnostic(json, status, &error, 1);
    command = 5;
  } else if (!strcmp(argv[index], "snapshot") || !strcmp(argv[index], "log") || !strcmp(argv[index], "walk")) {
    command = !strcmp(argv[index], "snapshot") ? 3 : !strcmp(argv[index], "log") ? 4 : 6;
    int selector = 0, have_limit = 0; index++;
    if (command == 6) {
      if (index >= argc) goto syntax;
      status = dml_object_id_parse(argv[index], strlen(argv[index]), &value, &error);
      if (status != DML_OK) return diagnostic(json, status, &error, 1);
      selector = 2; index++;
    }
    while (index < argc) {
      if (index + 1 >= argc) goto syntax;
      if (!strcmp(argv[index], "--ref") && !selector) { name = argv[index + 1]; selector = 1; }
      else if (!strcmp(argv[index], "--commit") && !selector) {
        status = dml_object_id_parse(argv[index + 1], strlen(argv[index + 1]), &value, &error);
        if (status != DML_OK) return diagnostic(json, status, &error, 1);
        selector = 2;
      } else if (!strcmp(argv[index], "--limit") && !have_limit) {
        const char *arg = argv[index + 1];
        if (!*arg) goto syntax;
        for (const char *p = arg; *p; p++) if (*p < '0' || *p > '9') goto syntax;
        errno = 0; char *end; uintmax_t parsed = strtoumax(arg, &end, 10);
        if (errno || parsed == 0) goto syntax;
        /* All bytes were checked as decimal digits before strtoumax. */
        if (*end) goto syntax; /* LCOV_EXCL_BR_LINE */
        /* uintmax_t and size_t both 64-bit on the supported matrix. */
        if (parsed > SIZE_MAX) goto syntax; /* LCOV_EXCL_BR_LINE */
        limit = (size_t)parsed; have_limit = 1;
      } else goto syntax;
      index += 2;
    }
    if (!selector) goto syntax;
  } else goto syntax;
  dml_repo *repo = NULL; dml_txn *txn = NULL; Text text = {0};
  status = dml_repo_open(path, NULL, &repo, &error);
  if (status != DML_OK) goto done;
  status = dml_txn_begin(repo, DML_TXN_READ, &txn, &error);
  if (status != DML_OK) goto done;
  if (name && command != 5) {
    dml_bytes bytes = {(const uint8_t *)name, strlen(name)};
    status = dml_txn_ref_get(txn, bytes, &value, &error);
    if (status != DML_OK) goto done;
  }
  if (command == 1) {
    add(&text, "{\"command\":\"ref-get\",\"name\":"); string(&text, name);
    add(&text, ",\"target\":"); id(&text, &value); add(&text, "}\n");
  } else if (command == 2) status = show(&text, txn, type, &value, type_name, json, &error);
  else if (command == 3) status = snapshot(&text, txn, &value, limit, &error);
  else if (command == 5) {
    dml_object_id node;
    status = dml_txn_lookup_node(txn, &value, (dml_bytes){(const uint8_t *)name, strlen(name)}, &node, &error);
    if (status == DML_OK) {
      add(&text, "{\"command\":\"lookup\",\"dag\":"); id(&text, &value);
      add(&text, ",\"name\":"); string(&text, name); add(&text, ",\"node\":"); id(&text, &node); add(&text, "}\n");
    }
  } else status = traverse(&text, txn, &value, limit, command == 6, &error);
  if (status == DML_OK && text.failed) { status = DML_OUT_OF_MEMORY; strcpy(error.detail, "inspection output allocation failed"); }
done:
  dml_txn_abort(&txn);
  dml_error close_error; dml_status close_status = dml_repo_close(&repo, &close_error);
  /* Abort consumed the only transaction; close of a null/live idle handle succeeds. */
  if (status == DML_OK && close_status != DML_OK) { status = close_status; error = close_error; } /* LCOV_EXCL_BR_LINE */
  if (status == DML_OK) {
    const char *title = command == 1 ? "Ref" : command == 2 ? "Object" : command == 3 ? "Snapshot"
                       : command == 5 ? "Lookup" : command == 6 ? "DAG structure" : "History";
    int written = json ? fwrite(text.data, 1, text.len, stdout) == text.len : human_output(&text, title);
    if (!written || fflush(stdout) != 0) status = DML_STORAGE_ERROR;
    if (status != DML_OK) { error.native_code = errno; strcpy(error.detail, "cannot write inspection output"); }
  }
  free(text.data);
  if (status != DML_OK) return diagnostic(json, status, &error, 0);
  return 0;
syntax:
  strcpy(error.detail, "invalid command, selector or option; use --help");
  if (!json) fputs(usage, stderr);
  return diagnostic(json, DML_INVALID_ARGUMENT, &error, 1);
}
