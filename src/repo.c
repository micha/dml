#include <dirent.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include <lmdb.h>

#include "dml/repo.h"
#include "encoding.h"
#include "error_internal.h"
#include "record_internal.h"

#ifdef _WIN32
#include <direct.h>
#define dml_mkdir(path) _mkdir(path)
#else
#define dml_mkdir(path) mkdir(path, 0777)
#endif

struct dml_repo {
  MDB_env *env;
  MDB_dbi dbi;
  uint32_t schema;
  size_t active_txns;
};

struct dml_txn {
  dml_repo *repo;
  MDB_txn *native;
  dml_txn_mode mode;
  int poisoned;
};

static dml_status storage_error(dml_error *error, int code, const char *context) {
  dml_status status = code == MDB_MAP_FULL ? DML_MAP_FULL : DML_STORAGE_ERROR;
  char detail[128];
  (void)snprintf(detail, sizeof(detail), "%s: %s", context, mdb_strerror(code));
  return dml_set_error(error, status, code, detail);
}

static int path_kind(const char *path, int *is_directory) {
  struct stat info;
  if (stat(path, &info) != 0) {
    return errno == ENOENT ? 0 : -1;
  }
  *is_directory = S_ISDIR(info.st_mode);
  return 1;
}

static int directory_empty(const char *path) {
  DIR *directory = opendir(path);
  struct dirent *entry;
  if (directory == NULL) {
    return -1;
  }
  while ((entry = readdir(directory)) != NULL) {
    if (strcmp(entry->d_name, ".") != 0 && strcmp(entry->d_name, "..") != 0) {
      closedir(directory);
      return 0;
    }
  }
  closedir(directory);
  return 1;
}

static int environment_file_exists(const char *path) {
  size_t len = strlen(path);
  char *file = malloc(len + 10);
  struct stat info;
  int exists;
  if (file == NULL) {
    return -1;
  }
  (void)snprintf(file, len + 10, "%s%cdata.mdb", path,
#ifdef _WIN32
                 '\\'
#else
                 '/'
#endif
  );
  exists = stat(file, &info) == 0;
  free(file);
  return exists;
}

static dml_status validate_schema_value(const MDB_val *value, uint32_t *schema,
                                        dml_error *error) {
  dml_status status = dml_record_validate(value->mv_data, value->mv_size, error);
  if (status != DML_OK) {
    return status;
  }
  if (dml_read_u16_le((const uint8_t *)value->mv_data + 6) != DML_REC_META) {
    return dml_set_error(error, DML_INVALID_KIND, 0,
                         "record_type=meta;detail=record_type");
  }
  *schema = dml_read_u32_le((const uint8_t *)value->mv_data + 20);
  return DML_OK;
}

static dml_status initialize_or_check(dml_repo *repo, int create,
                                      dml_error *error) {
  static const char schema_key[] = "meta/schema";
  uint8_t schema_record[DML_META_SIZE];
  MDB_txn *txn = NULL;
  MDB_val key = {sizeof(schema_key) - 1, (void *)schema_key};
  MDB_val value;
  int code = mdb_txn_begin(repo->env, NULL, create ? 0 : MDB_RDONLY, &txn);
  if (code != MDB_SUCCESS) {
    return storage_error(error, code, "beginning schema transaction");
  }
  code = mdb_dbi_open(txn, NULL, 0, &repo->dbi);
  if (code == MDB_SUCCESS) {
    code = mdb_get(txn, repo->dbi, &key, &value);
  }
  if (code == MDB_NOTFOUND && create) {
    MDB_stat stats;
    code = mdb_stat(txn, repo->dbi, &stats);
    if (code == MDB_SUCCESS && stats.ms_entries != 0) {
      mdb_txn_abort(txn);
      return dml_set_error(error, DML_INVALID_STATE, 0,
                           "repository database has no schema");
    }
    if (code == MDB_SUCCESS) {
      dml_encode_meta(schema_record);
      value.mv_data = schema_record;
      value.mv_size = sizeof(schema_record);
      code = mdb_put(txn, repo->dbi, &key, &value, MDB_NOOVERWRITE);
      if (code == MDB_SUCCESS) repo->schema = DML_SCHEMA_VERSION;
    }
  } else if (code == MDB_SUCCESS) {
    dml_status status = validate_schema_value(&value, &repo->schema, error);
    if (status != DML_OK) {
      mdb_txn_abort(txn);
      return status;
    }
  } else if (code == MDB_NOTFOUND) {
    mdb_txn_abort(txn);
    return dml_set_error(error, DML_NOT_FOUND, code, "repository schema is missing");
  }
  if (code != MDB_SUCCESS) {
    mdb_txn_abort(txn);
    return storage_error(error, code, "accessing repository schema");
  }
  if (create) {
    code = mdb_txn_commit(txn);
    if (code != MDB_SUCCESS) {
      return storage_error(error, code, "committing repository schema");
    }
  } else {
    mdb_txn_abort(txn);
  }
  return DML_OK;
}

dml_status dml_repo_open(const char *path, const dml_repo_options *options,
                         dml_repo **out, dml_error *error) {
  dml_repo_options defaults = {false, DML_REPO_DEFAULT_MAP_SIZE};
  dml_repo *repo;
  int exists;
  int is_directory = 0;
  int empty = 0;
  int has_environment = 0;
  int code;
  dml_status status;

  if (out == NULL || *out != NULL || path == NULL || path[0] == '\0') {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "invalid repository path");
  }
  *out = NULL;
  dml_error_clear(error);
  if (options == NULL) {
    options = &defaults;
  }
  if (options->map_size != 0 && options->map_size < 1048576) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0,
                         "repository map size must be at least 1 MiB");
  }
  exists = path_kind(path, &is_directory);
  if (exists < 0 || (exists > 0 && !is_directory)) {
    return dml_set_error(error, DML_STORAGE_ERROR, errno,
                         "repository path is not a directory");
  }
  if (exists == 0) {
    if (!options->create) {
      return dml_set_error(error, DML_NOT_FOUND, ENOENT, "repository path does not exist");
    }
    /* EEXIST here requires another creator between stat and mkdir; no-value race simulation. */
    if (dml_mkdir(path) != 0 &&
        errno != EEXIST) { /* LCOV_EXCL_BR_LINE */
      return dml_set_error(error, DML_STORAGE_ERROR, errno,
                           "creating repository directory failed");
    }
    empty = 1;
  } else {
    empty = directory_empty(path);
    if (empty < 0) {
      return dml_set_error(error, DML_STORAGE_ERROR, errno,
                           "reading repository directory failed");
    }
    has_environment = environment_file_exists(path);
    if (has_environment < 0) {
      return dml_set_error(error, DML_OUT_OF_MEMORY, 0,
                           "checking repository environment failed");
    }
    if (!empty && !has_environment) {
      return dml_set_error(error, DML_INVALID_STATE, 0,
                           "nonempty directory is not an LMDB environment");
    }
    if (empty && !options->create) {
      return dml_set_error(error, DML_NOT_FOUND, 0, "repository directory is empty");
    }
  }
  repo = calloc(1, sizeof(*repo));
  if (repo == NULL) {
    return dml_set_error(error, DML_OUT_OF_MEMORY, 0, "allocating repository handle");
  }
  code = mdb_env_create(&repo->env);
  if (code == MDB_SUCCESS) {
    code = mdb_env_set_mapsize(repo->env,
                               options->map_size == 0 ? DML_REPO_DEFAULT_MAP_SIZE
                                                      : options->map_size);
  }
  if (code == MDB_SUCCESS) {
    code = mdb_env_open(repo->env, path, 0, 0664);
  }
  if (code != MDB_SUCCESS) {
    if (repo->env != NULL) mdb_env_close(repo->env);
    free(repo);
    return storage_error(error, code, "opening LMDB environment");
  }
  status = initialize_or_check(repo, options->create, error);
  if (status != DML_OK) {
    mdb_env_close(repo->env);
    free(repo);
    return status;
  }
  *out = repo;
  return DML_OK;
}

dml_status dml_repo_schema(dml_repo *repo, uint32_t *out, dml_error *error) {
  if (repo == NULL || out == NULL) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "invalid schema arguments");
  }
  *out = repo->schema;
  return DML_OK;
}

dml_status dml_txn_begin(dml_repo *repo, dml_txn_mode mode, dml_txn **out,
                         dml_error *error) {
  dml_txn *txn;
  int code;
  if (repo == NULL || out == NULL || *out != NULL ||
      (mode != DML_TXN_READ && mode != DML_TXN_WRITE)) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "invalid transaction arguments");
  }
  *out = NULL;
  txn = calloc(1, sizeof(*txn));
  if (txn == NULL) {
    return dml_set_error(error, DML_OUT_OF_MEMORY, 0, "allocating transaction handle");
  }
  code = mdb_txn_begin(repo->env, NULL, mode == DML_TXN_READ ? MDB_RDONLY : 0,
                       &txn->native);
  if (code != MDB_SUCCESS) {
    free(txn);
    return storage_error(error, code, "beginning transaction");
  }
  txn->repo = repo;
  txn->mode = mode;
  repo->active_txns++;
  *out = txn;
  return DML_OK;
}

static size_t object_key(dml_record_type type, const dml_object_id *id, char key[48]) {
  static const char *const prefixes[] = {
    "objects/datums/", "objects/nodes/", "objects/dags/", "objects/trees/", "objects/commits/"
  };
  const char *prefix = prefixes[type - DML_REC_DATUM];
  size_t prefix_len = strlen(prefix);
  char hex[DML_OBJECT_ID_HEX_SIZE + 1];
  (void)dml_object_id_format(id, hex, NULL);
  memcpy(key, prefix, prefix_len);
  memcpy(key + prefix_len, hex, 32);
  return prefix_len + 32;
}

static dml_status lookup_object(dml_txn *txn, dml_record_type expected, const dml_object_id *id,
                                 MDB_val *value, dml_error *error) {
  char key_bytes[48];
  MDB_val key = {object_key(expected, id, key_bytes), key_bytes};
  uint16_t type;
  dml_object_id actual;
  int code;
  dml_status status;
  code = mdb_get(txn->native, txn->repo->dbi, &key, value);
  if (code == MDB_NOTFOUND) {
    return dml_set_error(error, DML_NOT_FOUND, code, "immutable object was not found");
  }
  if (code != MDB_SUCCESS) {
    return storage_error(error, code, "reading immutable object");
  }
  status = dml_validate_envelope(value->mv_data, value->mv_size, &type, error);
  if (status != DML_OK) {
    return status;
  }
  if (type == DML_REC_TOMBSTONE) {
    const uint8_t *bytes = value->mv_data;
    if (value->mv_size < 36 || dml_read_u64_le(bytes + 24) != 36 ||
        dml_read_u32_le(bytes + 32) != value->mv_size - 36) {
      return dml_set_error(error, DML_INVALID_BOUNDS, 0,
                           "record_type=tombstone;detail=message_bounds");
    }
    return dml_set_error(error, DML_INVALID_PAYLOAD, 0,
                         "record_type=tombstone;detail=excised");
  }
  if (type != expected) {
    return dml_set_error(error, DML_INVALID_KIND, 0,
                         expected == DML_REC_DATUM
                           ? "record_type=datum;detail=composite_ref_not_datum"
                           : "stored object does not have the expected type");
  }
  status = dml_object_id_compute(value->mv_data, value->mv_size, &actual, error);
  if (status != DML_OK) {
    return status;
  }
  if (memcmp(actual.bytes, id->bytes, DML_OBJECT_ID_SIZE) != 0) {
    return dml_set_error(error, DML_INTEGRITY_ERROR, 0,
                         "stored object id does not match its key");
  }
  return DML_OK;
}

static dml_status lookup_datum(dml_txn *txn, const dml_object_id *id,
                               MDB_val *value, dml_error *error) {
  return lookup_object(txn, DML_REC_DATUM, id, value, error);
}

static dml_status validate_references(dml_txn *txn, const uint8_t *data, size_t len,
                                      dml_error *error) {
  dml_datum_view view;
  dml_status status = dml_datum_decode(data, len, &view, error);
  if (status != DML_OK || view.kind < DML_DATUM_LIST) {
    return status;
  }
  for (size_t i = 0; i < view.count; i++) {
    MDB_val ignored;
    if (view.kind == DML_DATUM_MAP) {
      dml_datum_map_entry entry;
      (void)dml_datum_view_map_entry(&view, i, &entry, NULL);
      status = lookup_datum(txn, &entry.key, &ignored, error);
      if (status == DML_NOT_FOUND) {
        status = dml_set_error(error, DML_INVALID_KIND, 0,
                               "record_type=datum;detail=composite_ref_not_datum");
      }
      if (status != DML_OK) return status;
      status = lookup_datum(txn, &entry.value, &ignored, error);
    } else {
      dml_object_id id;
      (void)dml_datum_view_id(&view, i, &id, NULL);
      status = lookup_datum(txn, &id, &ignored, error);
    }
    if (status == DML_NOT_FOUND) {
      status = dml_set_error(error, DML_INVALID_KIND, 0,
                             "record_type=datum;detail=composite_ref_not_datum");
    }
    if (status != DML_OK) return status;
  }
  return DML_OK;
}

static dml_status validate_object_references(dml_txn *txn, dml_record_type type,
                                             const uint8_t *data, size_t len,
                                             dml_error *error) {
  if (type == DML_REC_DATUM) return validate_references(txn, data, len, error);
  dml_object_view view;
  dml_status status = dml_object_decode(data, len, &view, error);
  if (status != DML_OK) return status; /* LCOV_EXCL_BR_LINE: caller already checked type, encoding and ID. */
  MDB_val ignored;
  if (type != DML_REC_TREE) {
    dml_record_type referenced_type = type == DML_REC_NODE
                                    ? (view.node_kind == DML_NODE_LITERAL ? DML_REC_DATUM : DML_REC_DAG)
                                  : type == DML_REC_DAG ? DML_REC_NODE : DML_REC_TREE;
    status = lookup_object(txn, referenced_type, &view.reference, &ignored, error);
    if (status != DML_OK) return status;
  }
  for (size_t i = 0; i < view.count; i++) {
    dml_object_id id;
    if (type == DML_REC_TREE) {
      dml_tree_entry entry;
      (void)dml_object_view_entry(&view, i, &entry, NULL);
      id = entry.dag;
    } else if (type == DML_REC_DAG) {
      dml_dag_binding binding;
      (void)dml_object_view_binding(&view, i, &binding, NULL);
      id = binding.node;
    } else {
      (void)dml_object_view_parent(&view, i, &id, NULL);
    }
    dml_record_type target_type = type == DML_REC_TREE ? DML_REC_DAG
                               : type == DML_REC_DAG ? DML_REC_NODE : DML_REC_COMMIT;
    status = lookup_object(txn, target_type, &id, &ignored, error);
    if (status != DML_OK) return status;
  }
  return DML_OK;
}

static dml_status put_object(dml_txn *txn, dml_record_type type,
                              const uint8_t *data, size_t len,
                              dml_object_id *out, dml_error *error) {
  char key_bytes[48];
  MDB_val key = {0, key_bytes};
  MDB_val value = {len, (void *)data};
  MDB_val existing;
  dml_status status;
  int code;
  if (txn == NULL || txn->mode != DML_TXN_WRITE || txn->poisoned) {
    return dml_set_error(error, DML_INVALID_STATE, 0, "transaction is not writable");
  }
  if (out == NULL) {
    txn->poisoned = 1;
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "object id output is null");
  }
  status = dml_object_id_compute(data, len, out, error);
  if (status == DML_OK && dml_read_u16_le(data + 6) != type) {
    status = dml_set_error(error, DML_INVALID_KIND, 0, "object does not have the expected type");
  }
  if (status == DML_OK) status = validate_object_references(txn, type, data, len, error);
  if (status != DML_OK) {
    txn->poisoned = 1;
    return status;
  }
  key.mv_size = object_key(type, out, key_bytes);
  code = mdb_put(txn->native, txn->repo->dbi, &key, &value, MDB_NOOVERWRITE);
  if (code == MDB_KEYEXIST) {
    status = lookup_object(txn, type, out, &existing, error);
    if (status == DML_OK &&
        (existing.mv_size != len || memcmp(existing.mv_data, data, len) != 0)) {
      status = dml_set_error(error, DML_INTEGRITY_ERROR, 0,
                             "object id collision or stored corruption");
    }
    if (status != DML_OK) txn->poisoned = 1;
    return status;
  }
  if (code != MDB_SUCCESS) {
    txn->poisoned = 1;
    return storage_error(error, code, "storing immutable object");
  }
  return DML_OK;
}

static dml_status get_object(dml_txn *txn, dml_record_type type, const dml_object_id *id,
                              dml_buffer *out, dml_error *error) {
  MDB_val value;
  dml_status status;
  if (txn == NULL || id == NULL || out == NULL || out->data != NULL || out->len != 0) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "invalid object get arguments");
  }
  out->data = NULL;
  out->len = 0;
  status = lookup_object(txn, type, id, &value, error);
  if (status == DML_OK) {
    status = validate_object_references(txn, type, value.mv_data, value.mv_size, error);
  }
  if (status != DML_OK) return status;
  out->data = malloc(value.mv_size);
  if (out->data == NULL) {
    return dml_set_error(error, DML_OUT_OF_MEMORY, 0, "copying stored object");
  }
  memcpy(out->data, value.mv_data, value.mv_size);
  out->len = value.mv_size;
  return DML_OK;
}

dml_status dml_txn_put_datum(dml_txn *txn, const uint8_t *data, size_t len,
                             dml_object_id *out, dml_error *error) {
  return put_object(txn, DML_REC_DATUM, data, len, out, error);
}

dml_status dml_txn_get_datum(dml_txn *txn, const dml_object_id *id,
                             dml_buffer *out, dml_error *error) {
  return get_object(txn, DML_REC_DATUM, id, out, error);
}

dml_status dml_txn_put_object(dml_txn *txn, dml_record_type type,
                               const uint8_t *data, size_t len, dml_object_id *out,
                               dml_error *error) {
  if (type < DML_REC_NODE || type > DML_REC_COMMIT) {
    if (txn != NULL && txn->mode == DML_TXN_WRITE) txn->poisoned = 1;
    return dml_set_error(error, DML_INVALID_KIND, 0, "unsupported object storage type");
  }
  return put_object(txn, type, data, len, out, error);
}

dml_status dml_txn_get_object(dml_txn *txn, dml_record_type type,
                               const dml_object_id *id, dml_buffer *out, dml_error *error) {
  if (type < DML_REC_NODE || type > DML_REC_COMMIT) {
    return dml_set_error(error, DML_INVALID_KIND, 0, "unsupported object storage type");
  }
  return get_object(txn, type, id, out, error);
}

dml_status dml_txn_lookup_node(dml_txn *txn, const dml_object_id *dag,
                               dml_bytes name, dml_object_id *out, dml_error *error) {
  if (txn == NULL || dag == NULL || out == NULL) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "invalid node lookup arguments");
  }
  dml_status status = dml_name_validate(name, error);
  if (status != DML_OK) return status;
  dml_buffer buffer = {0};
  status = dml_txn_get_object(txn, DML_REC_DAG, dag, &buffer, error);
  if (status != DML_OK) return status;
  dml_object_view view;
  (void)dml_object_decode(buffer.data, buffer.len, &view, NULL);
  status = DML_NOT_FOUND;
  for (size_t i = 0; i < view.count; i++) {
    dml_dag_binding binding;
    (void)dml_object_view_binding(&view, i, &binding, NULL);
    if (binding.name.len == name.len && memcmp(binding.name.data, name.data, name.len) == 0) {
      *out = binding.node;
      status = DML_OK;
      break;
    }
  }
  dml_buffer_free(&buffer);
  if (status != DML_OK) return dml_set_error(error, status, 0, "node name was not found in this DAG");
  return DML_OK;
}

static dml_status ref_key(dml_bytes name, char bytes[139], MDB_val *key, dml_error *error) {
  dml_status status = dml_name_validate(name, error);
  if (status != DML_OK) return status;
  memcpy(bytes, "refs/heads/", 11);
  memcpy(bytes + 11, name.data, name.len);
  key->mv_data = bytes;
  key->mv_size = 11 + name.len;
  return DML_OK;
}

static dml_status validate_ref_target(dml_txn *txn, const dml_object_id *id, dml_error *error) {
  MDB_val value;
  dml_status status = lookup_object(txn, DML_REC_COMMIT, id, &value, error);
  if (status == DML_OK) {
    status = validate_object_references(txn, DML_REC_COMMIT, value.mv_data, value.mv_size, error);
  }
  return status;
}

dml_status dml_txn_ref_get(dml_txn *txn, dml_bytes name, dml_object_id *out,
                            dml_error *error) {
  char bytes[139];
  MDB_val key;
  MDB_val value;
  if (txn == NULL || out == NULL) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "invalid ref get arguments");
  }
  dml_status status = ref_key(name, bytes, &key, error);
  if (status != DML_OK) return status;
  int code = mdb_get(txn->native, txn->repo->dbi, &key, &value);
  if (code == MDB_NOTFOUND) return dml_set_error(error, DML_NOT_FOUND, code, "ref was not found");
  if (code != MDB_SUCCESS) return storage_error(error, code, "reading ref");
  if (value.mv_size != 16) return dml_set_error(error, DML_INTEGRITY_ERROR, 0, "invalid ref target size");
  dml_object_id target;
  memcpy(target.bytes, value.mv_data, 16);
  status = validate_ref_target(txn, &target, error);
  if (status == DML_OK) *out = target;
  return status;
}

static dml_status write_ref(dml_txn *txn, dml_bytes name, const dml_object_id *target,
                             int create, dml_error *error) {
  if (txn == NULL || txn->mode != DML_TXN_WRITE || txn->poisoned) {
    return dml_set_error(error, DML_INVALID_STATE, 0, "transaction is not writable");
  }
  char bytes[139];
  MDB_val key;
  MDB_val existing;
  dml_status status = ref_key(name, bytes, &key, error);
  if (status == DML_OK && target == NULL) {
    status = dml_set_error(error, DML_INVALID_ARGUMENT, 0, "ref target is null");
  }
  if (status == DML_OK) status = validate_ref_target(txn, target, error);
  if (status == DML_OK && !create) {
    int code = mdb_get(txn->native, txn->repo->dbi, &key, &existing);
    if (code == MDB_NOTFOUND) status = dml_set_error(error, DML_NOT_FOUND, code, "ref was not found");
    else if (code != MDB_SUCCESS) status = storage_error(error, code, "reading ref before update");
    else if (existing.mv_size != 16) status = dml_set_error(error, DML_INTEGRITY_ERROR, 0, "invalid ref target size");
  }
  if (status == DML_OK) {
    MDB_val value = {16, (void *)target->bytes};
    int code = mdb_put(txn->native, txn->repo->dbi, &key, &value, create ? MDB_NOOVERWRITE : 0);
    if (code == MDB_KEYEXIST) status = dml_set_error(error, DML_INVALID_STATE, code, "ref already exists");
    else if (code != MDB_SUCCESS) status = storage_error(error, code, "storing ref");
  }
  if (status != DML_OK) txn->poisoned = 1;
  return status;
}

dml_status dml_txn_ref_create(dml_txn *txn, dml_bytes name, const dml_object_id *target,
                               dml_error *error) {
  return write_ref(txn, name, target, 1, error);
}

dml_status dml_txn_ref_update(dml_txn *txn, dml_bytes name, const dml_object_id *target,
                               dml_error *error) {
  return write_ref(txn, name, target, 0, error);
}

dml_status dml_txn_commit(dml_txn **txn_ptr, dml_error *error) {
  dml_txn *txn;
  dml_repo *repo;
  int code;
  if (txn_ptr == NULL || *txn_ptr == NULL) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "transaction is null");
  }
  txn = *txn_ptr;
  *txn_ptr = NULL;
  repo = txn->repo;
  if (txn->mode != DML_TXN_WRITE || txn->poisoned) {
    mdb_txn_abort(txn->native);
    repo->active_txns--;
    free(txn);
    return dml_set_error(error, DML_INVALID_STATE, 0,
                         "transaction cannot be committed");
  }
  code = mdb_txn_commit(txn->native);
  repo->active_txns--;
  free(txn);
  if (code != MDB_SUCCESS) {
    return storage_error(error, code, "committing transaction");
  }
  return DML_OK;
}

void dml_txn_abort(dml_txn **txn_ptr) {
  dml_txn *txn;
  if (txn_ptr == NULL || *txn_ptr == NULL) return;
  txn = *txn_ptr;
  *txn_ptr = NULL;
  mdb_txn_abort(txn->native);
  txn->repo->active_txns--;
  free(txn);
}

dml_status dml_repo_close(dml_repo **repo_ptr, dml_error *error) {
  dml_repo *repo;
  if (repo_ptr == NULL || *repo_ptr == NULL) {
    return dml_set_error(error, DML_INVALID_ARGUMENT, 0, "repository is null");
  }
  repo = *repo_ptr;
  if (repo->active_txns != 0) {
    return dml_set_error(error, DML_INVALID_STATE, 0,
                         "repository has active transactions");
  }
  *repo_ptr = NULL;
  mdb_env_close(repo->env);
  free(repo);
  return DML_OK;
}
