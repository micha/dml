#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>

#include <lmdb.h>

static bool write_hex(const MDB_val *value) {
  static const char digits[] = "0123456789abcdef";
  const unsigned char *bytes = value->mv_data;
  for (size_t i = 0; i < value->mv_size; ++i) {
    if (fputc(digits[bytes[i] >> 4], stdout) == EOF ||
        fputc(digits[bytes[i] & 0x0f], stdout) == EOF) {
      return false;
    }
  }
  return true;
}

static bool scan(MDB_cursor *cursor) {
  MDB_val key;
  MDB_val value;
  int code = mdb_cursor_get(cursor, &key, &value, MDB_FIRST);
  /* Emit every raw entry in the main database, in LMDB key order. */
  while (code == MDB_SUCCESS) {
    if (!write_hex(&key) || fputc(' ', stdout) == EOF ||
        !write_hex(&value) || fputc('\n', stdout) == EOF) {
      perror("writing inventory");
      return false;
    }
    code = mdb_cursor_get(cursor, &key, &value, MDB_NEXT);
  }
  if (code != MDB_NOTFOUND) {
    fprintf(stderr, "scanning LMDB inventory: %s\n", mdb_strerror(code));
    return false;
  }
  if (fflush(stdout) == EOF) {
    perror("flushing inventory");
    return false;
  }
  return true;
}

int main(int argc, char **argv) {
  if (argc != 2) {
    fprintf(stderr, "usage: lmdb_inventory REPO\n");
    return EXIT_FAILURE;
  }

  MDB_env *env = NULL;
  MDB_txn *txn = NULL;
  MDB_cursor *cursor = NULL;
  MDB_dbi dbi;
  int code = mdb_env_create(&env);
  if (code == MDB_SUCCESS) code = mdb_env_open(env, argv[1], MDB_RDONLY, 0);
  if (code == MDB_SUCCESS) code = mdb_txn_begin(env, NULL, MDB_RDONLY, &txn);
  if (code == MDB_SUCCESS) code = mdb_dbi_open(txn, NULL, 0, &dbi);
  if (code == MDB_SUCCESS) code = mdb_cursor_open(txn, dbi, &cursor);

  bool success = false;
  if (code == MDB_SUCCESS) {
    success = scan(cursor);
  } else {
    fprintf(stderr, "opening read-only LMDB inventory for '%s': %s\n", argv[1],
            mdb_strerror(code));
  }
  if (cursor != NULL) mdb_cursor_close(cursor);
  if (txn != NULL) mdb_txn_abort(txn);
  if (env != NULL) mdb_env_close(env);
  return success ? EXIT_SUCCESS : EXIT_FAILURE;
}
