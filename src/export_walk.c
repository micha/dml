#include "export_walk.h"

#include <stdlib.h>
#include <string.h>

#include <xxhash.h>

#include "error_internal.h"

typedef struct {
  dml_record_type type;
  dml_object_id id;
} export_key;

typedef enum { UNSEEN = 0, ACTIVE, COMPLETED } visit_state;

typedef struct {
  export_key key;
  visit_state state;
} visit_entry;

typedef struct {
  export_key key;
  dml_buffer record;
  union {
    dml_datum_view datum;
    dml_object_view object;
  } view;
  size_t next_edge;
} export_frame;

typedef struct {
  export_frame *stack;
  size_t depth;
  size_t stack_capacity;
  visit_entry *visits;
  size_t visit_capacity;
  dml_export_rows rows;
  size_t row_capacity;
  size_t total_bytes;
} export_walk;

static size_t grown_capacity(size_t capacity, size_t item_size) {
  size_t max = SIZE_MAX / item_size;
  if (capacity == 0) return max >= 8 ? 8 : 0;
  return capacity <= max / 2 ? capacity * 2 : 0;
}

static void *grow_array(void *array, size_t *capacity, size_t item_size) {
  size_t next = grown_capacity(*capacity, item_size);
  if (next == 0) return NULL;
  void *grown = realloc(array, next * item_size);
  if (grown != NULL) *capacity = next;
  return grown;
}

/* No deletion; slots stop a probe at an empty entry. Capacity is a power of two. */
static visit_entry *visit_slot(visit_entry *entries, size_t capacity, const export_key *key) {
  size_t mask = capacity - 1;
  size_t index = (size_t)XXH64(key->id.bytes, DML_OBJECT_ID_SIZE, key->type) & mask;
  while (entries[index].state != UNSEEN) {
    if (entries[index].key.type == key->type &&
        memcmp(entries[index].key.id.bytes, key->id.bytes, DML_OBJECT_ID_SIZE) == 0) {
      break;
    }
    index = (index + 1) & mask;
  }
  return &entries[index];
}

static bool grow_visits(export_walk *walk) {
  size_t next = grown_capacity(walk->visit_capacity, sizeof(*walk->visits));
  if (next == 0) return false;
  visit_entry *entries = calloc(next, sizeof(*entries));
  if (entries == NULL) return false;
  for (size_t i = 0; i < walk->visit_capacity; i++) {
    visit_entry *entry = &walk->visits[i];
    if (entry->state != UNSEEN) {
      *visit_slot(entries, next, &entry->key) = *entry;
    }
  }
  free(walk->visits);
  walk->visits = entries;
  walk->visit_capacity = next;
  return true;
}

static dml_status reject(dml_export_failure *failure, dml_export_failure reason, dml_status status,
                         const char *detail, dml_error *error) {
  *failure = reason;
  return dml_set_error(error, status, 0, detail);
}

static dml_status read_frame(dml_txn *txn, export_frame *frame, const dml_export_limits *limits,
                             size_t total_bytes, dml_export_failure *failure, dml_error *error) {
  const export_key *key = &frame->key;
  dml_buffer *record = &frame->record;
  dml_status status = key->type == DML_REC_DATUM
                      ? dml_txn_get_datum(txn, &key->id, record, error)
                      : dml_txn_get_object(txn, key->type, &key->id, record, error);
  if (status != DML_OK) return status;
  if (record->len > limits->max_record_bytes) {
    return reject(failure, DML_EXPORT_RECORD_LIMIT, DML_INVALID_BOUNDS,
                  "packed record exceeds profile limit", error);
  }
  if (record->len > limits->max_packed_bytes - total_bytes) {
    return reject(failure, DML_EXPORT_PACKED_LIMIT, DML_INVALID_BOUNDS,
                  "total packed bytes exceed profile limit", error);
  }
  if (key->type == DML_REC_DATUM) {
    return dml_datum_decode(record->data, record->len, &frame->view.datum, error);
  }
  return dml_object_decode(record->data, record->len, &frame->view.object, error);
}

static size_t edge_count(const export_frame *frame) {
  switch (frame->key.type) {
    case DML_REC_DATUM:
      return frame->view.datum.count * (frame->view.datum.kind == DML_DATUM_MAP ? 2 : 1);
    case DML_REC_NODE: return 1;
    case DML_REC_TREE: return frame->view.object.count;
    case DML_REC_DAG: return 1 + frame->view.object.count;
    case DML_REC_COMMIT: return 1 + frame->view.object.count;
    default: return 0; /* All frames come from typed commit roots and decoded edges. */
  }
}

static dml_status read_datum_edge(const dml_datum_view *view, size_t index, export_key *out,
                                  dml_error *error) {
  out->type = DML_REC_DATUM;
  if (view->kind != DML_DATUM_MAP) return dml_datum_view_id(view, index, &out->id, error);
  dml_datum_map_entry entry;
  dml_status status = dml_datum_view_map_entry(view, index / 2, &entry, error);
  if (status == DML_OK) out->id = index % 2 == 0 ? entry.key : entry.value;
  return status;
}

static dml_status read_edge(export_frame *frame, export_key *out, dml_error *error) {
  size_t index = frame->next_edge++;
  const dml_object_view *view = &frame->view.object;
  switch (frame->key.type) {
    case DML_REC_DATUM:
      return read_datum_edge(&frame->view.datum, index, out, error);
    case DML_REC_NODE:
      *out = (export_key){view->node_kind == DML_NODE_LITERAL ? DML_REC_DATUM : DML_REC_DAG,
                          view->reference};
      return DML_OK;
    case DML_REC_DAG: {
      out->type = DML_REC_NODE;
      if (index == 0) {
        out->id = view->reference;
        return DML_OK;
      }
      dml_dag_binding binding;
      dml_status status = dml_object_view_binding(view, index - 1, &binding, error);
      if (status == DML_OK) out->id = binding.node;
      return status;
    }
    case DML_REC_TREE: {
      dml_tree_entry entry;
      dml_status status = dml_object_view_entry(view, index, &entry, error);
      if (status == DML_OK) *out = (export_key){DML_REC_DAG, entry.dag};
      return status;
    }
    case DML_REC_COMMIT:
      if (index == 0) {
        *out = (export_key){DML_REC_TREE, view->reference};
        return DML_OK;
      }
      out->type = DML_REC_COMMIT;
      return dml_object_view_parent(view, index - 1, &out->id, error);
    default:
      return dml_set_error(error, DML_INVALID_STATE, 0, "unexpected export frame type");
  }
}

static dml_status push_frame(export_walk *walk, dml_txn *txn, const export_key *key,
                             const dml_export_limits *limits, dml_export_failure *failure,
                             dml_error *error) {
  if (walk->visit_capacity != 0) {
    visit_state state = visit_slot(walk->visits, walk->visit_capacity, key)->state;
    if (state == COMPLETED) return DML_OK;
    if (state == ACTIVE) {
      return reject(failure, DML_EXPORT_CYCLE, DML_INTEGRITY_ERROR,
                    "cycle in reached object graph", error);
    }
  }
  size_t visited = walk->depth + walk->rows.count;
  if (visited >= limits->max_objects) {
    return reject(failure, DML_EXPORT_OBJECT_LIMIT, DML_INVALID_BOUNDS,
                  "object count exceeds profile limit", error);
  }
  export_frame frame = {.key = *key};
  dml_status status = read_frame(txn, &frame, limits, walk->total_bytes, failure, error);
  if (status == DML_OK && visited >= walk->visit_capacity / 2 && !grow_visits(walk)) {
    status = dml_set_error(error, DML_OUT_OF_MEMORY, 0, "growing export visited table");
  }
  if (status == DML_OK && walk->depth == walk->stack_capacity) {
    export_frame *grown = grow_array(walk->stack, &walk->stack_capacity, sizeof(*grown));
    if (grown == NULL) {
      status = dml_set_error(error, DML_OUT_OF_MEMORY, 0, "growing export stack");
    } else {
      walk->stack = grown;
    }
  }
  if (status != DML_OK) {
    dml_buffer_free(&frame.record);
    return status;
  }
  walk->total_bytes += frame.record.len;
  *visit_slot(walk->visits, walk->visit_capacity, key) = (visit_entry){*key, ACTIVE};
  walk->stack[walk->depth++] = frame;
  return DML_OK;
}

static dml_status finish_frame(export_walk *walk, const export_frame *frame, dml_error *error) {
  if (walk->rows.count == walk->row_capacity) {
    dml_export_row *grown = grow_array(walk->rows.items, &walk->row_capacity, sizeof(*grown));
    if (grown == NULL) return dml_set_error(error, DML_OUT_OF_MEMORY, 0, "growing export rows");
    walk->rows.items = grown;
  }
  visit_slot(walk->visits, walk->visit_capacity, &frame->key)->state = COMPLETED;
  walk->rows.items[walk->rows.count++] = (dml_export_row){frame->key.type, frame->key.id, frame->record};
  walk->depth--;
  return DML_OK;
}

void dml_export_rows_free(dml_export_rows *rows) {
  if (rows == NULL) return;
  for (size_t i = 0; i < rows->count; i++) dml_buffer_free(&rows->items[i].record);
  free(rows->items);
  *rows = (dml_export_rows){0};
}

dml_status dml_export_walk(dml_txn *txn, const dml_object_id *root,
                           const dml_export_limits *limits, dml_export_rows *out,
                           dml_export_failure *failure, dml_error *error) {
  if (failure != NULL) *failure = DML_EXPORT_NONE;
  if (txn == NULL || root == NULL || limits == NULL || failure == NULL || out == NULL ||
      out->items != NULL || out->count != 0) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "invalid export walk arguments");
  }
  dml_error_clear(error);
  export_walk walk = {0};
  export_key key = {DML_REC_COMMIT, *root};
  dml_status status = push_frame(&walk, txn, &key, limits, failure, error);
  /* A frame consumes one child at a time in codec order. A row is not emitted
   * until every outgoing edge is complete; no recursive calls or sibling queue. */
  while (status == DML_OK && walk.depth != 0) {
    export_frame *frame = &walk.stack[walk.depth - 1];
    if (frame->next_edge == edge_count(frame)) {
      status = finish_frame(&walk, frame, error);
    } else {
      status = read_edge(frame, &key, error);
      if (status == DML_OK) status = push_frame(&walk, txn, &key, limits, failure, error);
    }
  }
  for (size_t i = 0; i < walk.depth; i++) dml_buffer_free(&walk.stack[i].record);
  free(walk.stack);
  free(walk.visits);
  if (status == DML_OK) {
    *out = walk.rows;
  } else {
    dml_export_rows_free(&walk.rows);
  }
  return status;
}
