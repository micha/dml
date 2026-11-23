#include <stdlib.h>
#include <string.h>

#include "dml/repo.h"
#include "error_internal.h"
#include "object_internal.h"
#include "repo_internal.h"

typedef enum {
  OBJECT_UNSEEN,
  OBJECT_ACTIVE,
  OBJECT_INTACT,
  OBJECT_BROKEN,
  OBJECT_INVALID
} object_state;

typedef struct {
  dml_record_type type;
  dml_object_id id;
  dml_bytes record;
  object_state state;
  bool reachable;
} checked_object;

typedef struct {
  dml_repo_integrity report;
  bool seen_schema;
  checked_object *objects;
  size_t object_count;
  size_t object_capacity;
  dml_object_id *roots;
  size_t root_count;
  size_t root_capacity;
} integrity_scan;

typedef struct {
  checked_object *object;
  dml_object_refs refs;
  bool broken;
} walk_frame;

static void *grow_array(void *items, size_t item_size, size_t *capacity) {
  if (*capacity > SIZE_MAX / item_size / 2) return NULL;
  size_t next = *capacity == 0 ? 16 : *capacity * 2;
  void *grown = realloc(items, next * item_size);
  if (grown != NULL) *capacity = next;
  return grown;
}

static bool record_has_type(dml_bytes record, dml_record_type type) {
  return record.len >= 8 && dml_read_u16_le(record.data + 6) == type;
}

static dml_status collect_ref(integrity_scan *scan, dml_bytes name, dml_bytes target,
                              dml_error *error) {
  scan->report.refs++;
  if (target.len != DML_OBJECT_ID_SIZE || dml_name_validate(name, NULL) != DML_OK) {
    scan->report.broken_refs++;
    return DML_OK;
  }
  if (scan->root_count == scan->root_capacity) {
    dml_object_id *roots = grow_array(scan->roots, sizeof(*roots), &scan->root_capacity);
    if (roots == NULL) return dml_set_error(error, DML_OUT_OF_MEMORY, 0, "indexing ref targets");
    scan->roots = roots;
  }
  memcpy(scan->roots[scan->root_count++].bytes, target.data, DML_OBJECT_ID_SIZE);
  return DML_OK;
}

static dml_status collect_object(integrity_scan *scan, dml_record_type type, dml_bytes suffix,
                                 dml_bytes record, dml_error *error) {
  checked_object object = {.type = type};
  if (dml_object_id_parse((const char *)suffix.data, suffix.len, &object.id, NULL) != DML_OK) {
    scan->report.invalid_entries++;
    return DML_OK;
  }
  dml_object_id actual;
  dml_status status = record_has_type(record, type)
    ? dml_object_id_compute(record.data, record.len, &actual, error)
    : DML_INVALID_KIND;
  if (status == DML_OUT_OF_MEMORY) return status;
  if (status == DML_OK && memcmp(actual.bytes, object.id.bytes, DML_OBJECT_ID_SIZE) == 0) {
    object.record = record;
  } else {
    object.state = OBJECT_INVALID;
    scan->report.invalid_objects++;
  }
  if (scan->object_count == scan->object_capacity) {
    checked_object *objects = grow_array(scan->objects, sizeof(*objects), &scan->object_capacity);
    if (objects == NULL) return dml_set_error(error, DML_OUT_OF_MEMORY, 0, "indexing repository objects");
    scan->objects = objects;
  }
  scan->objects[scan->object_count++] = object;
  return DML_OK;
}

static dml_status collect_entry(void *context, dml_record_type type, dml_bytes suffix,
                                dml_bytes record, dml_error *error) {
  integrity_scan *scan = context;
  switch (type) {
    case DML_REC_META:
      scan->seen_schema = true;
      if (!record_has_type(record, type) || dml_record_validate(record.data, record.len, NULL) != DML_OK) {
        scan->report.invalid_entries++;
      }
      return DML_OK;
    case DML_REC_REF:
      return collect_ref(scan, suffix, record, error);
    case DML_REC_DATUM:
    case DML_REC_NODE:
    case DML_REC_DAG:
    case DML_REC_TREE:
    case DML_REC_COMMIT:
      return collect_object(scan, type, suffix, record, error);
    default:
      scan->report.invalid_entries++;
      return DML_OK;
  }
}

static int compare_objects(const void *left, const void *right) {
  const checked_object *a = left, *b = right;
  if (a->type != b->type) return a->type < b->type ? -1 : 1;
  return memcmp(a->id.bytes, b->id.bytes, DML_OBJECT_ID_SIZE);
}

static checked_object *find_object(integrity_scan *scan, dml_record_type type,
                                   const dml_object_id *id) {
  if (scan->object_count == 0) return NULL;
  checked_object key = {.type = type, .id = *id};
  return bsearch(&key, scan->objects, scan->object_count, sizeof(key), compare_objects);
}

static void start_object(walk_frame *frame, checked_object *object, bool reachable) {
  object->state = OBJECT_ACTIVE;
  object->reachable = reachable;
  *frame = (walk_frame){.object = object};
  dml_object_refs_init(&frame->refs, object->record.data, object->type);
}

/* Roots are walked first, so each source is classified once even when refs or
 * graphs overlap. A back edge breaks the active path; postorder propagates
 * failure to ancestors without counting edges to valid but broken closures. */
static void walk_objects(integrity_scan *scan, walk_frame *stack, checked_object *start,
                         bool reachable) {
  dml_repo_integrity *report = &scan->report;
  size_t *broken_edges = reachable ? &report->broken_reachable_edges : &report->broken_unreachable_edges;
  size_t depth = 1;
  start_object(stack, start, reachable);
  while (depth != 0) {
    walk_frame *frame = &stack[depth - 1];
    dml_record_type type;
    dml_object_id id;
    if (dml_object_refs_next(&frame->refs, &type, &id)) {
      checked_object *target = find_object(scan, type, &id);
      if (target == NULL || target->state == OBJECT_INVALID || target->state == OBJECT_ACTIVE) {
        (*broken_edges)++;
        frame->broken = true;
      } else if (target->state == OBJECT_BROKEN) {
        frame->broken = true;
      } else if (target->state == OBJECT_UNSEEN) {
        start_object(&stack[depth++], target, reachable);
      }
      continue;
    }
    frame->object->state = frame->broken ? OBJECT_BROKEN : OBJECT_INTACT;
    if (reachable) report->reachable_objects++;
    else if (frame->broken) report->broken_unreachable_objects++;
    else report->intact_unreachable_objects++;
    depth--;
    if (frame->broken && depth != 0) stack[depth - 1].broken = true;
  }
}

static dml_status classify_objects(integrity_scan *scan, dml_error *error) {
  walk_frame *stack = NULL;
  if (scan->object_count != 0) {
    if (scan->object_count <= SIZE_MAX / sizeof(*stack)) {
      stack = malloc(scan->object_count * sizeof(*stack));
    }
    if (stack == NULL) return dml_set_error(error, DML_OUT_OF_MEMORY, 0, "allocating integrity walk stack");
    qsort(scan->objects, scan->object_count, sizeof(*scan->objects), compare_objects);
  }
  for (size_t i = 0; i < scan->root_count; i++) {
    checked_object *root = find_object(scan, DML_REC_COMMIT, &scan->roots[i]);
    if (root == NULL || root->state == OBJECT_INVALID) scan->report.broken_refs++;
    else if (root->state == OBJECT_UNSEEN) walk_objects(scan, stack, root, true);
  }
  for (size_t i = 0; i < scan->object_count; i++) {
    checked_object *object = &scan->objects[i];
    if (object->state == OBJECT_UNSEEN) walk_objects(scan, stack, object, false);
  }
  free(stack);
  return DML_OK;
}

dml_status dml_txn_check_integrity(dml_txn *txn, dml_repo_integrity *out,
                                   dml_unreachable_visitor visitor, void *context,
                                   dml_error *error) {
  if (txn == NULL || out == NULL) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "integrity check requires transaction and report");
  }
  integrity_scan scan = {0};
  dml_status status = dml_txn_scan_entries(txn, collect_entry, &scan, error);
  if (status == DML_OK) {
    if (!scan.seen_schema) scan.report.invalid_entries++;
    status = classify_objects(&scan, error);
  }
  if (status == DML_OK) {
    dml_error_clear(error);
    *out = scan.report;
    if (visitor != NULL) {
      for (size_t i = 0; i < scan.object_count; i++) {
        const checked_object *object = &scan.objects[i];
        if (!object->reachable && object->state == OBJECT_INTACT) {
          visitor(context, object->type, &object->id);
        }
      }
    }
  }
  free(scan.objects);
  free(scan.roots);
  return status;
}
