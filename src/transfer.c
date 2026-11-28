#include <stdlib.h>
#include <string.h>

#include <xxhash.h>

#include "dml/transfer.h"
#include "encoding.h"
#include "error_internal.h"
#include "object_internal.h"
#include "record_internal.h"
#include "repo_internal.h"

#define BUNDLE_HEADER_SIZE 28u
#define BUNDLE_FRAME_HEADER_SIZE 24u
#define BUNDLE_VERSION 1u
#define BUNDLE_MAX_SIZE (64u * 1024u * 1024u)
#define BUNDLE_MAX_RECORD_SIZE (16u * 1024u * 1024u)
#define BUNDLE_MAX_RECORDS 262144u

static const uint8_t bundle_magic[] = {'D', 'M', 'L', 'B'};

typedef struct {
  dml_object_id id;
  dml_record_type type;
  dml_bytes record;
  size_t wire_offset; /* Assigned in export postorder. */
  bool reachable;     /* Marked from the root during import. */
  bool must_exist;    /* In the current ref's closure during guarded import. */
} bundle_entry;

typedef struct {
  bundle_entry *entries;
  size_t count;
  size_t capacity;
  uint32_t *slots; /* Entry index + 1; zero is empty. */
  size_t slot_count;
} bundle_index;

typedef struct {
  size_t entry;
  dml_object_refs refs;
} export_frame;

typedef struct {
  bundle_index index;
  export_frame *stack;
  size_t depth;
  size_t stack_capacity;
  size_t size;        /* Includes frames still being visited. */
  size_t next_offset; /* End of frames finished in postorder. */
} export_walk;

static dml_status fail(dml_error *error, dml_status status, const char *detail) {
  return dml_set_error(error, status, 0, detail);
}

static bool id_equal(const dml_object_id *left, const dml_object_id *right) {
  return memcmp(left->bytes, right->bytes, DML_OBJECT_ID_SIZE) == 0;
}

static void index_free(bundle_index *index) {
  free(index->entries);
  free(index->slots);
}

static size_t index_slot(const bundle_index *index, dml_record_type type,
                         const dml_object_id *id) {
  size_t mask = index->slot_count - 1;
  size_t slot = (size_t)XXH64(id->bytes, DML_OBJECT_ID_SIZE, type) & mask;
  while (index->slots[slot] != 0) {
    const bundle_entry *entry = &index->entries[index->slots[slot] - 1];
    if (entry->type == type && id_equal(&entry->id, id)) break;
    slot = (slot + 1) & mask;
  }
  return slot;
}

static size_t index_find(const bundle_index *index, dml_record_type type, const dml_object_id *id) {
  if (index->slot_count == 0) return SIZE_MAX;
  uint32_t entry = index->slots[index_slot(index, type, id)];
  return entry == 0 ? SIZE_MAX : (size_t)entry - 1;
}

/* Both append-only arrays are bounded by the bundle's maximum record count. */
static void *grow_array(void *data, size_t *capacity, size_t item_size) {
  size_t next = *capacity == 0 ? 16 : *capacity * 2;
  size_t bytes;
  if (!dml_size_mul(next, item_size, &bytes)) return NULL;
  void *grown = realloc(data, bytes);
  if (grown != NULL) *capacity = next;
  return grown;
}

/* Append a previously absent typed ID. Keep the probe table at most half full. */
static dml_status index_add(bundle_index *index, bundle_entry entry, dml_error *error) {
  if (index->count == index->capacity) {
    bundle_entry *entries = grow_array(index->entries, &index->capacity, sizeof(*entries));
    if (entries == NULL) return fail(error, DML_OUT_OF_MEMORY, "growing bundle entries");
    index->entries = entries;
  }
  if (index->count == index->slot_count / 2) {
    size_t count = index->slot_count == 0 ? 32 : index->slot_count * 2;
    uint32_t *slots = calloc(count, sizeof(*slots));
    if (slots == NULL) return fail(error, DML_OUT_OF_MEMORY, "growing bundle index");
    free(index->slots);
    index->slots = slots;
    index->slot_count = count;
    for (size_t i = 0; i < index->count; i++) {
      const bundle_entry *old = &index->entries[i];
      index->slots[index_slot(index, old->type, &old->id)] = (uint32_t)(i + 1);
    }
  }
  size_t slot = index_slot(index, entry.type, &entry.id);
  index->entries[index->count++] = entry;
  index->slots[slot] = (uint32_t)index->count;
  return DML_OK;
}

static dml_status push_export(dml_txn *txn, export_walk *walk, dml_record_type type,
                              const dml_object_id *id, dml_error *error) {
  if (walk->index.count == BUNDLE_MAX_RECORDS) {
    return fail(error, DML_INVALID_BOUNDS, "commit closure exceeds bundle record count limit");
  }
  bundle_entry entry = {.id = *id, .type = type};
  dml_status status = dml_txn_borrow_object(txn, type, id, BUNDLE_MAX_RECORD_SIZE,
                                            &entry.record, error);
  if (status != DML_OK) return status;
  size_t frame_size = BUNDLE_FRAME_HEADER_SIZE + entry.record.len;
  if (frame_size > BUNDLE_MAX_SIZE - walk->size) {
    return fail(error, DML_INVALID_BOUNDS, "commit closure exceeds bundle size limit");
  }
  if (walk->depth == walk->stack_capacity) {
    export_frame *stack = grow_array(walk->stack, &walk->stack_capacity, sizeof(*stack));
    if (stack == NULL) return fail(error, DML_OUT_OF_MEMORY, "growing bundle traversal stack");
    walk->stack = stack;
  }
  status = index_add(&walk->index, entry, error);
  if (status != DML_OK) return status;
  export_frame *frame = &walk->stack[walk->depth++];
  frame->entry = walk->index.count - 1;
  dml_object_refs_init(&frame->refs, entry.record.data, type);
  walk->size += frame_size;
  return DML_OK;
}

static dml_status walk_export(dml_txn *txn, export_walk *walk, const dml_object_id *root,
                              dml_error *error) {
  dml_status status = push_export(txn, walk, DML_REC_COMMIT, root, error);
  if (status != DML_OK) return status;
  while (walk->depth != 0) {
    export_frame *frame = &walk->stack[walk->depth - 1];
    dml_record_type type;
    dml_object_id id;
    if (!dml_object_refs_next(&frame->refs, &type, &id)) {
      bundle_entry *entry = &walk->index.entries[frame->entry];
      entry->wire_offset = walk->next_offset;
      walk->next_offset += BUNDLE_FRAME_HEADER_SIZE + entry->record.len;
      walk->depth--;
      continue;
    }
    size_t existing = index_find(&walk->index, type, &id);
    if (existing == SIZE_MAX) {
      status = push_export(txn, walk, type, &id, error);
      if (status != DML_OK) return status;
    } else if (walk->index.entries[existing].wire_offset == 0) {
      return fail(error, DML_INTEGRITY_ERROR, "cycle in commit closure");
    }
  }
  return DML_OK;
}

static dml_status write_bundle(const export_walk *walk, const dml_object_id *root,
                               dml_buffer *out, dml_error *error) {
  uint8_t *data = malloc(walk->size);
  if (data == NULL) return fail(error, DML_OUT_OF_MEMORY, "allocating commit bundle");
  memcpy(data, bundle_magic, sizeof(bundle_magic));
  dml_write_u32_le(data + 4, BUNDLE_VERSION);
  memcpy(data + 8, root->bytes, DML_OBJECT_ID_SIZE);
  dml_write_u32_le(data + 24, (uint32_t)walk->index.count);
  for (size_t i = 0; i < walk->index.count; i++) {
    const bundle_entry *entry = &walk->index.entries[i];
    uint8_t *frame = data + entry->wire_offset;
    dml_write_u16_le(frame, (uint16_t)entry->type);
    dml_write_u16_le(frame + 2, 0);
    dml_write_u32_le(frame + 4, (uint32_t)entry->record.len);
    memcpy(frame + 8, entry->id.bytes, DML_OBJECT_ID_SIZE);
    memcpy(frame + BUNDLE_FRAME_HEADER_SIZE, entry->record.data, entry->record.len);
  }
  *out = (dml_buffer){data, walk->size};
  return DML_OK;
}

static dml_status export_bundle(dml_repo *repo, const dml_object_id *root, const dml_bytes *ref_name,
                                dml_buffer *out, dml_error *error) {
  if ((root == NULL && ref_name == NULL) || out == NULL || out->data != NULL || out->len != 0) {
    return fail(error, DML_INVALID_ARGUMENT, "export requires a root and empty output buffer");
  }
  dml_error_clear(error);
  dml_status status = dml_repo_transfer_ready(repo, error);
  dml_txn *txn = NULL;
  if (status == DML_OK) status = dml_txn_begin(repo, DML_TXN_READ, &txn, error);
  if (status != DML_OK) return status;
  dml_object_id selected;
  if (ref_name != NULL) {
    status = dml_txn_read_head_id(txn, *ref_name, &selected, error);
    root = &selected;
  }
  export_walk walk = {.size = BUNDLE_HEADER_SIZE, .next_offset = BUNDLE_HEADER_SIZE};
  if (status == DML_OK) {
    status = walk_export(txn, &walk, root, error);
    if (status == DML_NOT_FOUND && ref_name != NULL) {
      status = fail(error, DML_INTEGRITY_ERROR, "selected ref closure is missing an object");
    }
  }
  if (status == DML_OK) status = write_bundle(&walk, root, out, error);
  free(walk.stack);
  index_free(&walk.index);
  dml_txn_abort(&txn);
  return status;
}

dml_status dml_repo_export_commit(dml_repo *repo, const dml_object_id *root,
                                  dml_buffer *out, dml_error *error) {
  return export_bundle(repo, root, NULL, out, error);
}

dml_status dml_repo_export_ref(dml_repo *repo, dml_bytes ref_name,
                               dml_buffer *out, dml_error *error) {
  return export_bundle(repo, NULL, &ref_name, out, error);
}

static dml_status parse_frame(dml_bytes *tail, bundle_index *index, dml_error *error) {
  if (tail->len < BUNDLE_FRAME_HEADER_SIZE) {
    return fail(error, DML_INVALID_BOUNDS, "truncated bundle frame");
  }
  const uint8_t *frame = tail->data;
  uint16_t type = dml_read_u16_le(frame);
  if (type < DML_REC_DATUM || type > DML_REC_COMMIT) {
    return fail(error, DML_INVALID_KIND, "bundle frame type is not an immutable object");
  }
  if (dml_read_u16_le(frame + 2) != 0) {
    return fail(error, DML_INVALID_HEADER, "bundle frame reserved field is not zero");
  }
  size_t len = dml_read_u32_le(frame + 4);
  if (len < DML_HEADER_SIZE || len > BUNDLE_MAX_RECORD_SIZE ||
      len > tail->len - BUNDLE_FRAME_HEADER_SIZE) {
    return fail(error, DML_INVALID_BOUNDS, "invalid bundle record length");
  }
  bundle_entry entry = {
    .type = (dml_record_type)type, .record = {frame + BUNDLE_FRAME_HEADER_SIZE, len}
  };
  memcpy(entry.id.bytes, frame + 8, DML_OBJECT_ID_SIZE);
  dml_object_id actual;
  dml_status status = dml_object_id_compute(entry.record.data, len, &actual, error);
  if (status != DML_OK) return status;
  if (dml_read_u16_le(entry.record.data + 6) != type) {
    return fail(error, DML_INVALID_KIND, "bundle frame type does not match packed record");
  }
  if (!id_equal(&entry.id, &actual)) {
    return fail(error, DML_INTEGRITY_ERROR, "bundle frame ID does not match packed record");
  }
  if (index_find(index, entry.type, &entry.id) != SIZE_MAX) {
    return fail(error, DML_INVALID_PAYLOAD, "duplicate object in bundle");
  }
  tail->data += BUNDLE_FRAME_HEADER_SIZE + len;
  tail->len -= BUNDLE_FRAME_HEADER_SIZE + len;
  return index_add(index, entry, error);
}

static dml_status validate_closure(bundle_index *index, const dml_object_id *root, dml_error *error) {
  bundle_entry *last = &index->entries[index->count - 1];
  if (last->type != DML_REC_COMMIT) {
    return fail(error, DML_INVALID_PAYLOAD, "last bundle record is not a commit");
  }
  if (!id_equal(&last->id, root)) {
    return fail(error, DML_INTEGRITY_ERROR, "last bundle commit does not match header root ID");
  }
  /* A parent of a frame must occur later in the stream. This reverse pass
   * visits every possible referrer before deciding whether a frame is extra. */
  last->reachable = true;
  for (size_t i = index->count; i != 0;) {
    bundle_entry *entry = &index->entries[--i];
    if (!entry->reachable) {
      return fail(error, DML_INVALID_PAYLOAD, "bundle contains an object outside the root closure");
    }
    dml_object_refs refs;
    dml_record_type type;
    dml_object_id id;
    dml_object_refs_init(&refs, entry->record.data, entry->type);
    while (dml_object_refs_next(&refs, &type, &id)) {
      size_t target = index_find(index, type, &id);
      if (target == SIZE_MAX || target >= i) {
        return fail(error, DML_INVALID_PAYLOAD, "bundle dependency is absent or not earlier than its use");
      }
      index->entries[target].reachable = true;
    }
  }
  return DML_OK;
}

static dml_status parse_bundle(dml_bytes bundle, bundle_index *index, dml_object_id *root,
                               dml_error *error) {
  if (bundle.len < BUNDLE_HEADER_SIZE || bundle.len > BUNDLE_MAX_SIZE) {
    return fail(error, DML_INVALID_BOUNDS, "invalid bundle size");
  }
  if (memcmp(bundle.data, bundle_magic, sizeof(bundle_magic)) != 0 ||
      dml_read_u32_le(bundle.data + 4) != BUNDLE_VERSION) {
    return fail(error, DML_INVALID_HEADER, "invalid bundle magic or version");
  }
  memcpy(root->bytes, bundle.data + 8, DML_OBJECT_ID_SIZE);
  size_t count = dml_read_u32_le(bundle.data + 24);
  dml_bytes tail = {bundle.data + BUNDLE_HEADER_SIZE, bundle.len - BUNDLE_HEADER_SIZE};
  size_t min_frame_size = BUNDLE_FRAME_HEADER_SIZE + DML_HEADER_SIZE;
  if (count == 0 || count > BUNDLE_MAX_RECORDS || count > tail.len / min_frame_size) {
    return fail(error, DML_INVALID_BOUNDS, "invalid bundle record count");
  }
  for (size_t i = 0; i < count; i++) {
    dml_status status = parse_frame(&tail, index, error);
    if (status != DML_OK) return status;
  }
  if (tail.len != 0) return fail(error, DML_INVALID_BOUNDS, "trailing bytes in bundle");
  return validate_closure(index, root, error);
}

typedef struct {
  dml_bytes name;
  bool guarded;
  const dml_object_id *expected;
} bundle_ref;

/* As in validate_closure, visit referrers before dependencies. This subset
 * must already exist byte-for-byte; do not silently repair the old history. */
static dml_status require_old_closure(dml_txn *txn, bundle_index *index, size_t old,
                                      dml_error *error) {
  index->entries[old].must_exist = true;
  for (size_t i = old + 1; i != 0;) {
    const bundle_entry *entry = &index->entries[--i];
    if (!entry->must_exist) continue;
    dml_status status = dml_txn_require_stored_object(txn, entry->type, &entry->id,
                                                      entry->record, error);
    if (status != DML_OK) return status;
    dml_object_refs refs;
    dml_record_type type;
    dml_object_id id;
    dml_object_refs_init(&refs, entry->record.data, entry->type);
    while (dml_object_refs_next(&refs, &type, &id)) {
      size_t target = index_find(index, type, &id); /* Known to be earlier than i. */
      index->entries[target].must_exist = true;
    }
  }
  return DML_OK;
}

static dml_status check_expected(dml_txn *txn, bundle_index *index, const bundle_ref *ref,
                                 dml_error *error) {
  dml_object_id actual;
  dml_status status = dml_txn_read_head_id(txn, ref->name, &actual, error);
  if (status == DML_NOT_FOUND && ref->expected == NULL) {
    dml_error_clear(error);
    return DML_OK;
  }
  if (status == DML_NOT_FOUND || (status == DML_OK &&
      (ref->expected == NULL || !id_equal(&actual, ref->expected)))) {
    return fail(error, DML_INVALID_STATE, "destination ref differs from expectation");
  }
  if (status != DML_OK) return status;
  /* Only a commit can refer to another commit, and only through its parents.
   * Thus commit membership in the exact closure proves all-parent ancestry. */
  size_t old = index_find(index, DML_REC_COMMIT, &actual);
  if (old == SIZE_MAX) return fail(error, DML_INVALID_STATE, "destination ref would not fast-forward");
  return require_old_closure(txn, index, old, error);
}

static dml_status store_bundle(dml_repo *repo, bundle_index *index,
                                const dml_object_id *root, const bundle_ref *ref,
                                dml_error *error) {
  dml_txn *txn = NULL;
  dml_status status = dml_txn_begin(repo, DML_TXN_WRITE, &txn, error);
  const bool replacing = ref != NULL && ref->expected != NULL;
  if (status == DML_OK && ref != NULL && ref->guarded) {
    status = check_expected(txn, index, ref, error);
    if (status == DML_OK && replacing && id_equal(root, ref->expected)) {
      dml_txn_abort(&txn);
      return DML_OK; /* The entire local closure already matches. */
    }
  }
  for (size_t i = 0; status == DML_OK && i < index->count; i++) {
    const bundle_entry *entry = &index->entries[i];
    if (!entry->must_exist) {
      status = dml_txn_store_validated_object(txn, entry->type, &entry->id, entry->record, error);
    }
  }
  if (status == DML_OK && ref != NULL) {
    status = replacing ? dml_txn_ref_update(txn, ref->name, root, error)
                       : dml_txn_ref_create(txn, ref->name, root, error);
  }
  if (status == DML_OK) return dml_txn_commit(&txn, error);
  dml_txn_abort(&txn);
  return status;
}

static dml_status import_bundle(dml_repo *repo, dml_bytes bundle, const bundle_ref *ref,
                                 dml_object_id *out, dml_error *error) {
  if (bundle.data == NULL || out == NULL) {
    return fail(error, DML_INVALID_ARGUMENT, "import requires bundle bytes and root ID output");
  }
  dml_error_clear(error);
  dml_status status = dml_repo_transfer_ready(repo, error);
  if (status == DML_OK && ref != NULL) status = dml_name_validate(ref->name, error);
  if (status != DML_OK) return status;
  bundle_index index = {0};
  dml_object_id root;
  status = parse_bundle(bundle, &index, &root, error);
  if (status == DML_OK) status = store_bundle(repo, &index, &root, ref, error);
  if (status == DML_OK) *out = root;
  index_free(&index);
  return status;
}

dml_status dml_repo_import_commit(dml_repo *repo, dml_bytes bundle,
                                  dml_object_id *out, dml_error *error) {
  return import_bundle(repo, bundle, NULL, out, error);
}

dml_status dml_repo_import_commit_staged(dml_repo *repo, dml_bytes bundle, dml_bytes ref_name,
                                         dml_object_id *out, dml_error *error) {
  const bundle_ref ref = {.name = ref_name};
  return import_bundle(repo, bundle, &ref, out, error);
}

dml_status dml_repo_import_commit_expected(dml_repo *repo, dml_bytes bundle, dml_bytes ref_name,
                                           const dml_object_id *expected, dml_object_id *out,
                                           dml_error *error) {
  const bundle_ref ref = {.name = ref_name, .guarded = true, .expected = expected};
  return import_bundle(repo, bundle, &ref, out, error);
}
