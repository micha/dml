#ifndef DML_REPO_H
#define DML_REPO_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "dml/error.h"
#include "dml/record.h"

typedef struct dml_repo dml_repo;
typedef struct dml_txn dml_txn;

typedef struct {
  bool create;
  size_t map_size;
} dml_repo_options;

typedef enum {
  DML_TXN_READ = 1,
  DML_TXN_WRITE = 2
} dml_txn_mode;

/* Calls using one repository and its transactions require external
 * synchronization. A transaction must be used and ended by its creating
 * thread. Separate processes may open the same repository. */

#define DML_REPO_DEFAULT_MAP_SIZE (64u * 1024u * 1024u)

/* Repository and transaction output slots must initially be null. */
dml_status dml_repo_open(const char *path, const dml_repo_options *options,
                         dml_repo **out, dml_error *error);
dml_status dml_repo_schema(dml_repo *repo, uint32_t *out, dml_error *error);
dml_status dml_txn_begin(dml_repo *repo, dml_txn_mode mode, dml_txn **out,
                         dml_error *error);
dml_status dml_txn_put_datum(dml_txn *txn, const uint8_t *data, size_t len,
                             dml_object_id *out, dml_error *error);
dml_status dml_txn_get_datum(dml_txn *txn, const dml_object_id *id,
                             dml_buffer *out, dml_error *error);
/* Commit consumes the handle on success or failure; abort is null-safe. */
dml_status dml_txn_commit(dml_txn **txn, dml_error *error);
void dml_txn_abort(dml_txn **txn);
dml_status dml_repo_close(dml_repo **repo, dml_error *error);

#endif
