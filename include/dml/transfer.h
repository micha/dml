#ifndef DML_TRANSFER_H
#define DML_TRANSFER_H

#include "dml/repo.h"

/* Export the exact transitive dependencies of a commit, including the commit.
 * The repository must have no active transactions. Output must be empty;
 * failures leave it empty. The caller frees the result with dml_buffer_free(). */
dml_status dml_repo_export_commit(dml_repo *repo, const dml_object_id *root,
                                  dml_buffer *out, dml_error *error);

/* Import a self-contained commit bundle atomically, without changing refs.
 * The repository must have no active transactions. The input is borrowed for
 * the call. The root ID is written only after successful commit. */
dml_status dml_repo_import_commit(dml_repo *repo, dml_bytes bundle,
                                  dml_object_id *out, dml_error *error);

/* Import and create a local ref to the bundle root in one write transaction.
 * Uses the same bundle, handle and output rules as unpinned import. The name
 * must satisfy dml_name_validate(); an existing ref is never replaced, even if
 * it already targets the root. Failure leaves objects, refs and out unchanged. */
dml_status dml_repo_import_commit_staged(dml_repo *repo, dml_bytes bundle, dml_bytes ref_name,
                                         dml_object_id *out, dml_error *error);

#endif
