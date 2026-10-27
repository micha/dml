#ifndef DML_TEST_FAULT_INJECTION_H
#define DML_TEST_FAULT_INJECTION_H

/* Force-included only when compiling the private test core, never libdml. */
#include <stdlib.h>
#include <lmdb.h>
#include <uriparser/Uri.h>
#include <utf8proc.h>
#include <xxhash.h>
#include "fault_control.h"

void *dml_test_malloc(size_t size);
void *dml_test_calloc(size_t count, size_t size);
utf8proc_ssize_t dml_test_text(const utf8proc_uint8_t *text, utf8proc_ssize_t len,
                              utf8proc_uint8_t **out, utf8proc_option_t options);
int dml_test_uri_parse(UriUriA *uri, const char *first, const char *last, const char **error);
int dml_test_uri_normalize(UriUriA *uri, unsigned int mask);
int dml_test_uri_size(const UriUriA *uri, int *size);
int dml_test_uri_write(char *out, const UriUriA *uri, int size, int *written);
int dml_test_env_create(MDB_env **env);
int dml_test_env_size(MDB_env *env, size_t size);
int dml_test_env_open(MDB_env *env, const char *path, unsigned int flags, mdb_mode_t mode);
int dml_test_txn_begin(MDB_env *env, MDB_txn *parent, unsigned int flags, MDB_txn **txn);
int dml_test_dbi_open(MDB_txn *txn, const char *name, unsigned int flags, MDB_dbi *dbi);
int dml_test_get(MDB_txn *txn, MDB_dbi dbi, MDB_val *key, MDB_val *value);
int dml_test_put(MDB_txn *txn, MDB_dbi dbi, MDB_val *key, MDB_val *value, unsigned int flags);
int dml_test_stat(MDB_txn *txn, MDB_dbi dbi, MDB_stat *stats);
int dml_test_commit(MDB_txn *txn);
XXH128_hash_t dml_test_hash(const void *data, size_t len);

#ifndef DML_TEST_IMPLEMENTATION
#define malloc dml_test_malloc
#define calloc dml_test_calloc
#define utf8proc_map dml_test_text
#define uriParseSingleUriExA dml_test_uri_parse
#define uriNormalizeSyntaxExA dml_test_uri_normalize
#define uriToStringCharsRequiredA dml_test_uri_size
#define uriToStringA dml_test_uri_write
#define mdb_env_create dml_test_env_create
#define mdb_env_set_mapsize dml_test_env_size
#define mdb_env_open dml_test_env_open
#define mdb_txn_begin dml_test_txn_begin
#define mdb_dbi_open dml_test_dbi_open
#define mdb_get dml_test_get
#define mdb_put dml_test_put
#define mdb_stat dml_test_stat
#define mdb_txn_commit dml_test_commit
#define XXH3_128bits dml_test_hash
#endif

#endif
