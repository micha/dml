#ifndef DML_OBJECT_INTERNAL_H
#define DML_OBJECT_INTERNAL_H

#include <string.h>

#include "dml/object.h"
#include "encoding.h"

/* Cursors borrow the packed bytes of a successfully decoded view. A cursor
 * must not outlive or read past view->count entries in that record. It holds
 * no pointer into the view itself, so moving the view does not invalidate it. */
static inline const uint8_t *dml_named_entries_begin(const dml_object_view *view) {
  if (view->type == DML_REC_TREE) return view->record + 24;
  if (view->type == DML_REC_DAG) return view->record + 40;
  return NULL;
}

static inline void dml_named_entry_next(const uint8_t **cursor, dml_bytes *name,
                                        dml_object_id *id) {
  name->len = dml_read_u32_le(*cursor);
  name->data = *cursor + 4;
  const uint8_t *target = name->data + name->len;
  memcpy(id->bytes, target, DML_OBJECT_ID_SIZE);
  *cursor = target + DML_OBJECT_ID_SIZE;
}

#endif
