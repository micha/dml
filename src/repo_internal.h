#ifndef DML_REPO_INTERNAL_H
#define DML_REPO_INTERNAL_H

#include "dml/repo.h"

dml_status dml_repo_transfer_ready(dml_repo *repo, dml_error *error);

/* Visit the current transaction view in the required mode. Type is zero for
 * an unrecognized key; otherwise suffix follows the object/ref prefix. Bytes
 * are borrowed until the next update or transaction end, including after the
 * cursor closes. The visitor must not update the transaction. */
typedef dml_status (*dml_entry_visitor)(void *context, dml_record_type type,
                                        dml_bytes suffix, dml_bytes record, dml_error *error);
dml_status dml_txn_scan_entries(dml_txn *txn, dml_txn_mode mode, dml_entry_visitor visitor,
                                 void *context, dml_error *error);

/* Internal mark/sweep: caller supplies a writable transaction with supported
 * database flags and poisons it on failure. Only the sweep calls the delete
 * helper, using typed IDs owned by the index, not borrowed storage bytes. */
dml_status dml_txn_sweep_unreachable(dml_txn *txn, size_t *removed, dml_error *error);
dml_status dml_txn_delete_scanned_object(dml_txn *txn, dml_record_type type,
                                          const dml_object_id *id, dml_error *error);

/* Only for read transactions. The validated packed bytes are borrowed until
 * the transaction ends. Object size is checked before hashing or decoding. */
dml_status dml_txn_borrow_object(dml_txn *txn, dml_record_type type, const dml_object_id *id,
                                 size_t max_size, dml_bytes *out, dml_error *error);

/* Internal no-overwrite write. Caller must supply a writable transaction and
 * have validated the record, type, ID, and references. */
dml_status dml_txn_store_validated_object(dml_txn *txn, dml_record_type type,
                                          const dml_object_id *id, dml_bytes record,
                                          dml_error *error);

#endif
