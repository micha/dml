#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <stdint.h>
#include <string.h>

#include "dml/repo.h"
#include "dml/transfer.h"

#ifdef Py_GIL_DISABLED
#error "DML requires a GIL-enabled CPython build"
#endif

/* The private test build adds observations of C output slots on failure. */
#ifdef DML_PRIVATE_REPLAY
#define MODULE_NAME "_dml_core"
#define MODULE_INIT PyInit__dml_core
#else
#define MODULE_NAME "daggerml.core"
#define MODULE_INIT PyInit_core
#endif
#define REPO_CAPSULE MODULE_NAME ".repo"
#define TXN_CAPSULE MODULE_NAME ".txn"
#define VIEW_CAPSULE MODULE_NAME ".object_view"

typedef struct {
  PyObject *error;
} module_state;

typedef struct {
  dml_repo *repo;
  dml_txn *abandoned;
  uint64_t owner_thread;
  bool active;
} repo_handle;

typedef struct {
  dml_txn *txn;
  PyObject *repo;
  uint64_t owner_thread;
} txn_handle;

typedef struct {
  dml_object_view view;
  PyObject *packed;
} object_handle;

static PyObject *raise_status(PyObject *module, dml_status status, const dml_error *error) {
  module_state *state = PyModule_GetState(module);
  PyObject *args = Py_BuildValue("(sis)", dml_status_name(status), error->native_code, error->detail);
  if (args != NULL) {
    PyErr_SetObject(state->error, args);
    Py_DECREF(args);
  }
  return NULL;
}

static uint64_t thread_id(void) {
  return PyThreadState_GetID(PyThreadState_Get());
}

static bool on_owner_thread(uint64_t owner_thread) {
  if (thread_id() == owner_thread) return true;
  PyErr_SetString(PyExc_RuntimeError, "DML handle must be used on its creating thread");
  return false;
}

static void *get_handle(PyObject *owner, const char *name) {
  if (!PyCapsule_IsValid(owner, name)) {
    PyErr_Format(PyExc_TypeError, "expected a %s handle", name);
    return NULL;
  }
  return PyCapsule_GetPointer(owner, name);
}

static repo_handle *get_repo(PyObject *owner) {
  repo_handle *handle = get_handle(owner, REPO_CAPSULE);
  return handle != NULL && on_owner_thread(handle->owner_thread) ? handle : NULL;
}

static txn_handle *get_txn(PyObject *owner) {
  txn_handle *handle = get_handle(owner, TXN_CAPSULE);
  return handle != NULL && on_owner_thread(handle->owner_thread) ? handle : NULL;
}

static void reap_abandoned(repo_handle *handle) {
  if (handle->abandoned == NULL) return;
  dml_txn_abort(&handle->abandoned);
  handle->active = false;
}

static void destroy_repo(PyObject *capsule) {
  repo_handle *handle = PyCapsule_GetPointer(capsule, REPO_CAPSULE);
  if (handle->abandoned == NULL || handle->owner_thread == thread_id()) {
    reap_abandoned(handle);
    if (handle->repo != NULL) dml_repo_close(&handle->repo, NULL);
  } else {
    /* No owner remains to abort this transaction safely. Leave native state
     * alone rather than ending the LMDB transaction from the wrong thread. */
#if PY_VERSION_HEX >= 0x030c0000
    PyObject *saved = PyErr_GetRaisedException();
#else
    PyObject *type, *value, *traceback;
    PyErr_Fetch(&type, &value, &traceback);
#endif
    PyErr_SetString(PyExc_RuntimeError, "DML repository and live transaction abandoned on foreign thread");
    PyErr_WriteUnraisable(NULL);
#if PY_VERSION_HEX >= 0x030c0000
    PyErr_SetRaisedException(saved);
#else
    PyErr_Restore(type, value, traceback);
#endif
  }
  PyMem_Free(handle);
}

static void detach_txn(txn_handle *handle) {
  repo_handle *repo = PyCapsule_GetPointer(handle->repo, REPO_CAPSULE);
  repo->active = false;
  Py_CLEAR(handle->repo);
}

static void destroy_txn(PyObject *capsule) {
  txn_handle *handle = PyCapsule_GetPointer(capsule, TXN_CAPSULE);
  if (handle->txn != NULL) {
    if (handle->owner_thread == thread_id()) {
      dml_txn_abort(&handle->txn);
      detach_txn(handle);
    } else {
      repo_handle *repo = PyCapsule_GetPointer(handle->repo, REPO_CAPSULE);
      repo->abandoned = handle->txn;
    }
  }
  Py_XDECREF(handle->repo);
  PyMem_Free(handle);
}

static void destroy_view(PyObject *capsule) {
  object_handle *handle = PyCapsule_GetPointer(capsule, VIEW_CAPSULE);
  Py_DECREF(handle->packed);
  PyMem_Free(handle);
}

static int read_bytes(PyObject *obj, dml_bytes *out) {
  char *data;
  Py_ssize_t len;
  if (PyBytes_AsStringAndSize(obj, &data, &len) < 0) return 0;
  out->data = (const uint8_t *)data;
  out->len = (size_t)len;
  return 1;
}

static int read_id(PyObject *obj, dml_object_id *id) {
  dml_bytes bytes;
  if (!read_bytes(obj, &bytes)) return 0;
  if (bytes.len != sizeof(id->bytes)) {
    PyErr_SetString(PyExc_ValueError, "object ID must contain 16 bytes");
    return 0;
  }
  memcpy(id->bytes, bytes.data, bytes.len);
  return 1;
}

static PyObject *id_bytes(const dml_object_id *id) {
  return PyBytes_FromStringAndSize((const char *)id->bytes, sizeof(id->bytes));
}

static PyObject *take_buffer(dml_buffer *buffer) {
  PyObject *result;
  if ((buffer->data == NULL) != (buffer->len == 0)) {
    PyErr_SetString(PyExc_RuntimeError, "DML returned an inconsistent buffer");
    result = NULL;
  } else if (buffer->len > (size_t)PY_SSIZE_T_MAX) {
    PyErr_SetString(PyExc_OverflowError, "record exceeds Python bytes size");
    result = NULL;
  } else {
    result = PyBytes_FromStringAndSize((const char *)buffer->data, (Py_ssize_t)buffer->len);
  }
  dml_buffer_free(buffer);
  return result;
}

static PyObject *repo_open(PyObject *self, PyObject *args) {
  PyObject *path, *create, *size = NULL;
  if (!PyArg_ParseTuple(args, "OO|O:repo_open", &path, &create, &size)) return NULL;
  if (!PyBool_Check(create)) {
    PyErr_SetString(PyExc_TypeError, "create must be a bool");
    return NULL;
  }
  dml_repo_options options = {.create = create == Py_True};
  if (size != NULL) {
    options.map_size = PyLong_AsSize_t(size);
    if (PyErr_Occurred()) return NULL;
  }
  PyObject *encoded;
  if (!PyUnicode_FSConverter(path, &encoded)) return NULL;
  repo_handle *handle = PyMem_Calloc(1, sizeof(*handle));
  if (handle == NULL) {
    Py_DECREF(encoded);
    return PyErr_NoMemory();
  }
  handle->owner_thread = thread_id();
  PyObject *capsule = PyCapsule_New(handle, REPO_CAPSULE, destroy_repo);
  if (capsule == NULL) {
    Py_DECREF(encoded);
    PyMem_Free(handle);
    return NULL;
  }
  dml_error error = {0};
  dml_status status = dml_repo_open(PyBytes_AS_STRING(encoded), &options, &handle->repo, &error);
  Py_DECREF(encoded);
  if (status != DML_OK) {
    Py_DECREF(capsule);
    return raise_status(self, status, &error);
  }
  return capsule;
}

static PyObject *repo_close(PyObject *self, PyObject *capsule) {
  repo_handle *handle = get_repo(capsule);
  if (handle == NULL) return NULL;
  reap_abandoned(handle);
  dml_error error = {0};
  dml_status status = dml_repo_close(&handle->repo, &error);
  if (status != DML_OK) return raise_status(self, status, &error);
  Py_RETURN_NONE;
}

static PyObject *txn_begin(PyObject *self, PyObject *args) {
  PyObject *owner;
  int mode;
  if (!PyArg_ParseTuple(args, "Oi", &owner, &mode)) return NULL;
  repo_handle *repo = get_repo(owner);
  if (repo == NULL) return NULL;
  reap_abandoned(repo);
  if (repo->active) {
    PyErr_SetString(PyExc_RuntimeError, "end the active transaction before beginning another");
    return NULL;
  }
  txn_handle *handle = PyMem_Calloc(1, sizeof(*handle));
  if (handle == NULL) return PyErr_NoMemory();
  handle->owner_thread = repo->owner_thread;
  PyObject *capsule = PyCapsule_New(handle, TXN_CAPSULE, destroy_txn);
  if (capsule == NULL) {
    PyMem_Free(handle);
    return NULL;
  }
  dml_error error = {0};
  dml_status status = dml_txn_begin(repo->repo, (dml_txn_mode)mode, &handle->txn, &error);
  if (status != DML_OK) {
    Py_DECREF(capsule);
    return raise_status(self, status, &error);
  }
  repo->active = true;
  handle->repo = Py_NewRef(owner);
  return capsule;
}

static PyObject *txn_commit(PyObject *self, PyObject *capsule) {
  txn_handle *handle = get_txn(capsule);
  if (handle == NULL) return NULL;
  dml_error error = {0};
  dml_status status = dml_txn_commit(&handle->txn, &error);
  if (handle->repo != NULL) detach_txn(handle);
  if (status != DML_OK) return raise_status(self, status, &error);
  Py_RETURN_NONE;
}

static PyObject *txn_abort(PyObject *self, PyObject *capsule) {
  (void)self;
  txn_handle *handle = get_txn(capsule);
  if (handle == NULL) return NULL;
  dml_txn_abort(&handle->txn);
  if (handle->repo != NULL) detach_txn(handle);
  Py_RETURN_NONE;
}

static int read_map_input(PyObject *value, dml_map_array *map, void **allocated) {
  bool tuple = PyTuple_Check(value);
  if (!tuple && !PyList_Check(value)) {
    PyErr_SetString(PyExc_TypeError, "map entries must be a list or tuple");
    return 0;
  }
  Py_ssize_t count = tuple ? PyTuple_GET_SIZE(value) : PyList_GET_SIZE(value);
  if (count == 0) return 1;
  dml_datum_map_entry *entries = PyMem_Calloc((size_t)count, sizeof(*entries));
  if (entries == NULL) {
    PyErr_NoMemory();
    return 0;
  }
  *allocated = entries;
  for (Py_ssize_t i = 0; i < count; i++) {
    PyObject *pair = tuple ? PyTuple_GET_ITEM(value, i) : PyList_GET_ITEM(value, i);
    if (!PyTuple_Check(pair) || PyTuple_GET_SIZE(pair) != 2) {
      PyErr_SetString(PyExc_TypeError, "each map entry must be a (key ID, value ID) tuple");
      return 0;
    }
    if (!read_id(PyTuple_GET_ITEM(pair, 0), &entries[i].key) ||
        !read_id(PyTuple_GET_ITEM(pair, 1), &entries[i].value)) return 0;
  }
  *map = (dml_map_array){.items = entries, .count = (size_t)count};
  return 1;
}

static int read_list_input(PyObject *value, dml_id_array *list, void **allocated) {
  bool tuple = PyTuple_Check(value);
  if (!tuple && !PyList_Check(value)) {
    PyErr_SetString(PyExc_TypeError, "list members must be a list or tuple");
    return 0;
  }
  Py_ssize_t count = tuple ? PyTuple_GET_SIZE(value) : PyList_GET_SIZE(value);
  if (count == 0) return 1;
  dml_object_id *ids = PyMem_Calloc((size_t)count, sizeof(*ids));
  if (ids == NULL) {
    PyErr_NoMemory();
    return 0;
  }
  *allocated = ids;
  for (Py_ssize_t i = 0; i < count; i++) {
    PyObject *item = tuple ? PyTuple_GET_ITEM(value, i) : PyList_GET_ITEM(value, i);
    if (!read_id(item, &ids[i])) return 0;
  }
  *list = (dml_id_array){.items = ids, .count = (size_t)count};
  return 1;
}

static PyObject *datum_encode(PyObject *self, PyObject *args) {
  int kind;
  PyObject *value;
  if (!PyArg_ParseTuple(args, "iO", &kind, &value)) return NULL;
  dml_datum_input input = {.kind = (dml_datum_kind)kind};
  void *allocated = NULL;
  if (kind == DML_DATUM_NULL) {
    if (value != Py_None) {
      PyErr_SetString(PyExc_TypeError, "NULL datum value must be None");
      return NULL;
    }
  } else if (kind == DML_DATUM_I64) {
    long long number = PyLong_AsLongLong(value);
    if (number == -1 && PyErr_Occurred()) return NULL;
    input.value.i64 = (int64_t)number;
  } else if (kind == DML_DATUM_STRING || kind == DML_DATUM_URI) {
    if (!read_bytes(value, &input.value.bytes)) return NULL;
  } else if (kind == DML_DATUM_LIST) {
    if (!read_list_input(value, &input.value.ids, &allocated)) {
      PyMem_Free(allocated);
      return NULL;
    }
  } else if (kind == DML_DATUM_MAP) {
    if (!read_map_input(value, &input.value.map, &allocated)) {
      PyMem_Free(allocated);
      return NULL;
    }
  } else {
    PyErr_SetString(PyExc_ValueError, "unsupported datum encoder kind");
    return NULL;
  }
  dml_buffer packed = {0};
  dml_error error = {0};
  dml_status status = dml_datum_encode(&input, &packed, &error);
  PyMem_Free(allocated);
  return status == DML_OK ? take_buffer(&packed) : raise_status(self, status, &error);
}

static int read_named_id(PyObject *args, Py_ssize_t index, dml_bytes *name, dml_object_id *target) {
  return read_bytes(PyTuple_GET_ITEM(args, index), name) && read_id(PyTuple_GET_ITEM(args, index + 1), target);
}

static int read_dag_input(PyObject *args, dml_object_input *input, void **allocated) {
  if (!read_id(PyTuple_GET_ITEM(args, 1), &input->value.dag.root)) return 0;
  Py_ssize_t count = (PyTuple_GET_SIZE(args) - 2) / 2;
  if (count == 0) return 1;
  dml_dag_binding *bindings = PyMem_Calloc((size_t)count, sizeof(*bindings));
  if (bindings == NULL) {
    PyErr_NoMemory();
    return 0;
  }
  *allocated = bindings;
  for (Py_ssize_t i = 0; i < count; i++) {
    if (!read_named_id(args, 2 + 2 * i, &bindings[i].name, &bindings[i].node)) return 0;
  }
  input->value.dag.items = bindings;
  input->value.dag.count = (size_t)count;
  return 1;
}

static int read_tree_input(PyObject *args, dml_object_input *input, void **allocated) {
  Py_ssize_t count = (PyTuple_GET_SIZE(args) - 1) / 2;
  if (count == 0) return 1;
  dml_tree_entry *entries = PyMem_Calloc((size_t)count, sizeof(*entries));
  if (entries == NULL) {
    PyErr_NoMemory();
    return 0;
  }
  *allocated = entries;
  for (Py_ssize_t i = 0; i < count; i++) {
    if (!read_named_id(args, 1 + 2 * i, &entries[i].name, &entries[i].dag)) return 0;
  }
  input->value.tree.items = entries;
  input->value.tree.count = (size_t)count;
  return 1;
}

static int read_commit_input(PyObject *args, dml_object_input *input, void **allocated) {
  if (!read_id(PyTuple_GET_ITEM(args, 1), &input->value.commit.tree)) return 0;
  Py_ssize_t count = PyTuple_GET_SIZE(args) - 2;
  if (count == 0) return 1;
  dml_object_id *parents = PyMem_Calloc((size_t)count, sizeof(*parents));
  if (parents == NULL) {
    PyErr_NoMemory();
    return 0;
  }
  *allocated = parents;
  for (Py_ssize_t i = 0; i < count; i++) {
    if (!read_id(PyTuple_GET_ITEM(args, 2 + i), &parents[i])) return 0;
  }
  input->value.commit.parents = (dml_id_array){.items = parents, .count = (size_t)count};
  return 1;
}

static int read_object_input(PyObject *args, long type, dml_object_input *input, void **allocated) {
  Py_ssize_t count = PyTuple_GET_SIZE(args) - 1;
  switch (type) {
    case DML_REC_NODE:
      if (count == 1 || count == 2) {
        long kind = count == 1 ? DML_NODE_LITERAL : PyLong_AsLong(PyTuple_GET_ITEM(args, 1));
        if (kind == -1 && PyErr_Occurred()) return 0;
        if (kind != DML_NODE_LITERAL && kind != DML_NODE_SUBDAG) break;
        input->value.node.kind = (uint32_t)kind;
        return read_id(PyTuple_GET_ITEM(args, count), &input->value.node.target);
      }
      break;
    case DML_REC_DAG:
      if (count >= 1 && count % 2 == 1) return read_dag_input(args, input, allocated);
      break;
    case DML_REC_TREE:
      if (count % 2 == 0) return read_tree_input(args, input, allocated);
      break;
    case DML_REC_COMMIT:
      if (count >= 1) return read_commit_input(args, input, allocated);
      break;
  }
  PyErr_SetString(PyExc_ValueError, "unsupported object encoder arguments");
  return 0;
}

/* Borrow Python tuple bytes for names; arrays only live through encoding. */
static PyObject *object_encode(PyObject *self, PyObject *args) {
  if (PyTuple_GET_SIZE(args) == 0) {
    PyErr_SetString(PyExc_TypeError, "object encoder requires a record type");
    return NULL;
  }
  long type = PyLong_AsLong(PyTuple_GET_ITEM(args, 0));
  if (type == -1 && PyErr_Occurred()) return NULL;
  dml_object_input input = {.type = (dml_record_type)type};
  void *allocated = NULL;
  if (!read_object_input(args, type, &input, &allocated)) {
    PyMem_Free(allocated);
    return NULL;
  }
  dml_buffer packed = {0};
  dml_error error = {0};
  dml_status status = dml_object_encode(&input, &packed, &error);
  PyMem_Free(allocated);
  return status == DML_OK ? take_buffer(&packed) : raise_status(self, status, &error);
}

static PyObject *placed_id(PyObject *self, PyObject *result, const dml_object_id *id,
                            dml_status status, const dml_error *error) {
  if (status == DML_OK) {
    memcpy(PyBytes_AS_STRING(result), id->bytes, sizeof(id->bytes));
    return result;
  }
  Py_DECREF(result);
  return raise_status(self, status, error);
}

static PyObject *txn_put_datum(PyObject *self, PyObject *args) {
  PyObject *capsule, *record;
  if (!PyArg_ParseTuple(args, "OO", &capsule, &record)) return NULL;
  txn_handle *handle = get_txn(capsule);
  dml_bytes packed;
  if (handle == NULL || !read_bytes(record, &packed)) return NULL;
  dml_object_id id;
  PyObject *result = PyBytes_FromStringAndSize(NULL, sizeof(id.bytes));
  if (result == NULL) return NULL;
  dml_error error = {0};
  dml_status status = dml_txn_put_datum(handle->txn, packed.data, packed.len, &id, &error);
  return placed_id(self, result, &id, status, &error);
}

static PyObject *txn_put_object(PyObject *self, PyObject *args) {
  PyObject *capsule, *record;
  int type;
  if (!PyArg_ParseTuple(args, "OiO", &capsule, &type, &record)) return NULL;
  txn_handle *handle = get_txn(capsule);
  dml_bytes packed;
  if (handle == NULL || !read_bytes(record, &packed)) return NULL;
  dml_object_id id;
  PyObject *result = PyBytes_FromStringAndSize(NULL, sizeof(id.bytes));
  if (result == NULL) return NULL;
  dml_error error = {0};
  dml_status status = dml_txn_put_object(handle->txn, (dml_record_type)type, packed.data, packed.len,
                                         &id, &error);
  return placed_id(self, result, &id, status, &error);
}

static PyObject *txn_get_object(PyObject *self, PyObject *args) {
  PyObject *capsule, *id_obj;
  int type;
  if (!PyArg_ParseTuple(args, "OiO", &capsule, &type, &id_obj)) return NULL;
  txn_handle *handle = get_txn(capsule);
  dml_object_id id;
  if (handle == NULL || !read_id(id_obj, &id)) return NULL;
  dml_buffer packed = {0};
  dml_error error = {0};
  dml_status status = dml_txn_get_object(handle->txn, (dml_record_type)type, &id, &packed, &error);
  return status == DML_OK ? take_buffer(&packed) : raise_status(self, status, &error);
}

typedef dml_status (*ref_write_fn)(dml_txn *, dml_bytes, const dml_object_id *, dml_error *);

static PyObject *ref_write(PyObject *self, PyObject *args, ref_write_fn write) {
  PyObject *capsule, *name_obj, *id_obj;
  if (!PyArg_ParseTuple(args, "OOO", &capsule, &name_obj, &id_obj)) return NULL;
  txn_handle *handle = get_txn(capsule);
  dml_bytes name;
  dml_object_id id;
  if (handle == NULL || !read_bytes(name_obj, &name) || !read_id(id_obj, &id)) return NULL;
  dml_error error = {0};
  dml_status status = write(handle->txn, name, &id, &error);
  if (status != DML_OK) return raise_status(self, status, &error);
  Py_RETURN_NONE;
}

static PyObject *txn_ref_create(PyObject *self, PyObject *args) {
  return ref_write(self, args, dml_txn_ref_create);
}

static PyObject *txn_ref_update(PyObject *self, PyObject *args) {
  return ref_write(self, args, dml_txn_ref_update);
}

static PyObject *txn_ref_delete_expected(PyObject *self, PyObject *args) {
  return ref_write(self, args, dml_txn_ref_delete_expected);
}

static PyObject *txn_ref_get(PyObject *self, PyObject *args) {
  PyObject *capsule, *name_obj;
  if (!PyArg_ParseTuple(args, "OO", &capsule, &name_obj)) return NULL;
  txn_handle *handle = get_txn(capsule);
  dml_bytes name;
  if (handle == NULL || !read_bytes(name_obj, &name)) return NULL;
  dml_object_id id;
  dml_error error = {0};
  dml_status status = dml_txn_ref_get(handle->txn, name, &id, &error);
  return status == DML_OK ? id_bytes(&id) : raise_status(self, status, &error);
}

static PyObject *object_decode(PyObject *self, PyObject *record) {
  dml_bytes packed;
  if (!read_bytes(record, &packed)) return NULL;
  object_handle *handle = PyMem_Malloc(sizeof(*handle));
  if (handle == NULL) return PyErr_NoMemory();
  /* A bytes subclass could refer back to the capsule, hiding a cycle from GC. */
  handle->packed = PyBytes_CheckExact(record) ? Py_NewRef(record) :
    PyBytes_FromStringAndSize((const char *)packed.data, (Py_ssize_t)packed.len);
  if (handle->packed == NULL) {
    PyMem_Free(handle);
    return NULL;
  }
  dml_error error = {0};
  const uint8_t *data = (const uint8_t *)PyBytes_AS_STRING(handle->packed);
  dml_status status = dml_object_decode(data, packed.len, &handle->view, &error);
  if (status != DML_OK) {
    Py_DECREF(handle->packed);
    PyMem_Free(handle);
    return raise_status(self, status, &error);
  }
  PyObject *capsule = PyCapsule_New(handle, VIEW_CAPSULE, destroy_view);
  if (capsule == NULL) {
    Py_DECREF(handle->packed);
    PyMem_Free(handle);
    return NULL;
  }
  PyObject *reference = id_bytes(&handle->view.reference);
  PyObject *count = PyLong_FromSize_t(handle->view.count);
  PyObject *result = NULL;
  if (reference != NULL && count != NULL) result = PyTuple_Pack(3, capsule, reference, count);
  Py_XDECREF(count);
  Py_XDECREF(reference);
  Py_DECREF(capsule);
  return result;
}

static PyObject *object_view_parent(PyObject *self, PyObject *args) {
  PyObject *capsule;
  Py_ssize_t index;
  if (!PyArg_ParseTuple(args, "On", &capsule, &index)) return NULL;
  object_handle *handle = get_handle(capsule, VIEW_CAPSULE);
  if (handle == NULL) return NULL;
  if (index < 0) {
    PyErr_SetString(PyExc_ValueError, "parent index must be nonnegative");
    return NULL;
  }
  dml_object_id id;
  dml_error error = {0};
  dml_status status = dml_object_view_parent(&handle->view, (size_t)index, &id, &error);
  return status == DML_OK ? id_bytes(&id) : raise_status(self, status, &error);
}

#ifdef DML_PRIVATE_REPLAY
static PyObject *output_result(dml_status status, PyObject *output) {
  if (output == NULL) return NULL;
  return Py_BuildValue("(sN)", dml_status_name(status), output);
}

static PyObject *repo_import_commit(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *capsule, *bundle_obj;
  if (!PyArg_ParseTuple(args, "OO:repo_import_commit", &capsule, &bundle_obj)) return NULL;
  repo_handle *repo = get_repo(capsule);
  dml_bytes bundle;
  if (repo == NULL || !read_bytes(bundle_obj, &bundle)) return NULL;
  dml_object_id root;
  memset(root.bytes, 0xa5, sizeof(root.bytes));
  dml_status status = dml_repo_import_commit(repo->repo, bundle, &root, NULL);
  return output_result(status, id_bytes(&root));
}

static PyObject *repo_export_ref(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *capsule, *name_obj;
  if (!PyArg_ParseTuple(args, "OO:repo_export_ref", &capsule, &name_obj)) return NULL;
  repo_handle *repo = get_repo(capsule);
  dml_bytes name;
  if (repo == NULL || !read_bytes(name_obj, &name)) return NULL;
  dml_buffer packed = {0};
  dml_status status = dml_repo_export_ref(repo->repo, name, &packed, NULL);
  return output_result(status, take_buffer(&packed));
}

static PyObject *repo_import_commit_expected(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *capsule, *bundle_obj, *name_obj, *expected_obj;
  if (!PyArg_ParseTuple(args, "OOOO:repo_import_commit_expected",
                        &capsule, &bundle_obj, &name_obj, &expected_obj)) return NULL;
  repo_handle *repo = get_repo(capsule);
  dml_bytes bundle, name;
  dml_object_id expected, root;
  if (repo == NULL || !read_bytes(bundle_obj, &bundle) || !read_bytes(name_obj, &name) ||
      (expected_obj != Py_None && !read_id(expected_obj, &expected))) return NULL;
  memset(root.bytes, 0xa5, sizeof(root.bytes));
  dml_status status = dml_repo_import_commit_expected(repo->repo, bundle, name,
      expected_obj == Py_None ? NULL : &expected, &root, NULL);
  return output_result(status, id_bytes(&root));
}
#endif

static PyObject *repo_export_commit(PyObject *self, PyObject *args) {
  PyObject *capsule, *root_obj;
  if (!PyArg_ParseTuple(args, "OO:repo_export_commit", &capsule, &root_obj)) return NULL;
  repo_handle *repo = get_repo(capsule);
  dml_object_id root;
  if (repo == NULL || !read_id(root_obj, &root)) return NULL;
  dml_buffer packed = {0};
  dml_error error = {0};
  dml_status status = dml_repo_export_commit(repo->repo, &root, &packed, &error);
#ifdef DML_PRIVATE_REPLAY
  (void)self;
  return output_result(status, take_buffer(&packed));
#else
  if (status != DML_OK) {
    dml_buffer_free(&packed);
    return raise_status(self, status, &error);
  }
  return take_buffer(&packed);
#endif
}

static PyObject *repo_import_commit_staged(PyObject *self, PyObject *args) {
  PyObject *capsule, *bundle_obj, *name_obj;
  if (!PyArg_ParseTuple(args, "OOO:repo_import_commit_staged", &capsule, &bundle_obj, &name_obj)) return NULL;
  repo_handle *repo = get_repo(capsule);
  dml_bytes bundle, name;
  if (repo == NULL || !read_bytes(bundle_obj, &bundle) || !read_bytes(name_obj, &name)) return NULL;
  dml_object_id root;
  dml_error error = {0};
#ifdef DML_PRIVATE_REPLAY
  memset(root.bytes, 0xa5, sizeof(root.bytes));
#else
  /* Reserve the receipt before the core can commit the import. */
  PyObject *result = PyBytes_FromStringAndSize(NULL, sizeof(root.bytes));
  if (result == NULL) return NULL;
#endif
  dml_status status = dml_repo_import_commit_staged(repo->repo, bundle, name, &root, &error);
#ifdef DML_PRIVATE_REPLAY
  (void)self;
  return output_result(status, id_bytes(&root));
#else
  if (status != DML_OK) {
    Py_DECREF(result);
    return raise_status(self, status, &error);
  }
  memcpy(PyBytes_AS_STRING(result), root.bytes, sizeof(root.bytes));
  return result;
#endif
}

static PyObject *txn_collect_garbage(PyObject *self, PyObject *capsule) {
  txn_handle *handle = get_txn(capsule);
  if (handle == NULL) return NULL;
  size_t removed = 123456789; /* Sentinel observed by private replay on failure. */
  dml_error error = {0};
  dml_status status = dml_txn_collect_garbage(handle->txn, &removed, &error);
#ifdef DML_PRIVATE_REPLAY
  (void)self;
  return output_result(status, PyLong_FromSize_t(removed));
#else
  return status == DML_OK ? PyLong_FromSize_t(removed) : raise_status(self, status, &error);
#endif
}

static PyObject *txn_get_datum(PyObject *self, PyObject *args) {
  PyObject *capsule, *id_obj;
  if (!PyArg_ParseTuple(args, "OO", &capsule, &id_obj)) return NULL;
  txn_handle *handle = get_txn(capsule);
  dml_object_id id;
  if (handle == NULL || !read_id(id_obj, &id)) return NULL;
  dml_buffer packed = {0};
  dml_error error = {0};
  dml_status status = dml_txn_get_datum(handle->txn, &id, &packed, &error);
  return status == DML_OK ? take_buffer(&packed) : raise_status(self, status, &error);
}

static PyObject *datum_decode(PyObject *self, PyObject *record) {
  dml_bytes packed;
  if (!read_bytes(record, &packed)) return NULL;
  dml_datum_view view;
  dml_error error = {0};
  dml_status status = dml_datum_decode(packed.data, packed.len, &view, &error);
  if (status != DML_OK) return raise_status(self, status, &error);
  return Py_BuildValue("(y#i)", (const char *)view.payload, (Py_ssize_t)view.payload_len, (int)view.kind);
}

static PyObject *datum_member(PyObject *self, const dml_datum_view *view, size_t index) {
  dml_error error = {0};
  if (view->kind == DML_DATUM_LIST) {
    dml_object_id id;
    dml_status status = dml_datum_view_id(view, index, &id, &error);
    return status == DML_OK ? id_bytes(&id) : raise_status(self, status, &error);
  }
  dml_datum_map_entry entry;
  dml_status status = dml_datum_view_map_entry(view, index, &entry, &error);
  if (status != DML_OK) return raise_status(self, status, &error);
  return Py_BuildValue("(y#y#)", (const char *)entry.key.bytes, (Py_ssize_t)sizeof(entry.key.bytes),
                       (const char *)entry.value.bytes, (Py_ssize_t)sizeof(entry.value.bytes));
}

static PyObject *datum_members(PyObject *self, PyObject *record) {
  dml_bytes packed;
  if (!read_bytes(record, &packed)) return NULL;
  dml_datum_view view;
  dml_error error = {0};
  dml_status status = dml_datum_decode(packed.data, packed.len, &view, &error);
  if (status != DML_OK) return raise_status(self, status, &error);
  if (view.kind != DML_DATUM_LIST && view.kind != DML_DATUM_MAP) {
    PyErr_SetString(PyExc_ValueError, "datum members require a LIST or MAP");
    return NULL;
  }
  /* Each validated member occupies bytes in the original Python bytes object. */
  PyObject *members = PyTuple_New((Py_ssize_t)view.count);
  if (members == NULL) return NULL;
  for (size_t i = 0; i < view.count; i++) {
    PyObject *member = datum_member(self, &view, i);
    if (member == NULL) {
      Py_DECREF(members);
      return NULL;
    }
    PyTuple_SET_ITEM(members, (Py_ssize_t)i, member);
  }
  return members;
}

static PyObject *txn_lookup_node(PyObject *self, PyObject *args) {
  PyObject *capsule, *id_obj, *name_obj;
  if (!PyArg_ParseTuple(args, "OOO", &capsule, &id_obj, &name_obj)) return NULL;
  txn_handle *handle = get_txn(capsule);
  dml_object_id dag, node;
  dml_bytes name;
  if (handle == NULL || !read_id(id_obj, &dag) || !read_bytes(name_obj, &name)) return NULL;
  dml_error error = {0};
  dml_status status = dml_txn_lookup_node(handle->txn, &dag, name, &node, &error);
  return status == DML_OK ? id_bytes(&node) : raise_status(self, status, &error);
}

static PyObject *object_view_entry(PyObject *self, PyObject *args) {
  PyObject *capsule;
  Py_ssize_t index;
  if (!PyArg_ParseTuple(args, "On", &capsule, &index)) return NULL;
  object_handle *handle = get_handle(capsule, VIEW_CAPSULE);
  if (handle == NULL) return NULL;
  if (index < 0) {
    PyErr_SetString(PyExc_ValueError, "tree index must be nonnegative");
    return NULL;
  }
  dml_tree_entry entry;
  dml_error error = {0};
  dml_status status = dml_object_view_entry(&handle->view, (size_t)index, &entry, &error);
  if (status != DML_OK) return raise_status(self, status, &error);
  return Py_BuildValue("(y#y#)", (const char *)entry.dag.bytes, (Py_ssize_t)sizeof(entry.dag.bytes),
                       (const char *)entry.name.data, (Py_ssize_t)entry.name.len);
}

#ifdef DML_PRIVATE_REPLAY
typedef struct {
  PyObject *visited;
  bool failed;
} integrity_visitor;

static void observe_unreachable(void *context, dml_record_type type, const dml_object_id *id) {
  integrity_visitor *visitor = context;
  if (visitor->failed) return;
  PyObject *item = Py_BuildValue("(iN)", (int)type, id_bytes(id));
  visitor->failed = item == NULL || PyList_Append(visitor->visited, item) < 0;
  Py_XDECREF(item);
}

static PyObject *txn_check_integrity(PyObject *self, PyObject *capsule) {
  txn_handle *handle = get_txn(capsule);
  if (handle == NULL) return NULL;
  integrity_visitor visitor = {.visited = PyList_New(0)};
  if (visitor.visited == NULL) return NULL;
  dml_repo_integrity report;
  dml_error error = {0};
  dml_status status = dml_txn_check_integrity(handle->txn, &report, observe_unreachable, &visitor, &error);
  if (status != DML_OK || visitor.failed) {
    Py_DECREF(visitor.visited);
    return visitor.failed ? NULL : raise_status(self, status, &error);
  }
  return Py_BuildValue("((KKKKKKKKK)N)", (unsigned long long)report.refs,
                       (unsigned long long)report.broken_refs, (unsigned long long)report.invalid_entries,
                       (unsigned long long)report.invalid_objects, (unsigned long long)report.reachable_objects,
                       (unsigned long long)report.broken_reachable_edges,
                       (unsigned long long)report.broken_unreachable_edges,
                       (unsigned long long)report.intact_unreachable_objects,
                       (unsigned long long)report.broken_unreachable_objects, visitor.visited);
}
#endif

static PyMethodDef methods[] = {
  {"repo_open", repo_open, METH_VARARGS, NULL},
  {"repo_close", repo_close, METH_O, NULL},
  {"txn_begin", txn_begin, METH_VARARGS, NULL},
  {"txn_commit", txn_commit, METH_O, NULL},
  {"txn_abort", txn_abort, METH_O, NULL},
  {"datum_encode", datum_encode, METH_VARARGS, NULL},
  {"object_encode", object_encode, METH_VARARGS, NULL},
  {"txn_put_datum", txn_put_datum, METH_VARARGS, NULL},
  {"txn_put_object", txn_put_object, METH_VARARGS, NULL},
  {"txn_get_object", txn_get_object, METH_VARARGS, NULL},
  {"txn_ref_create", txn_ref_create, METH_VARARGS, NULL},
  {"txn_ref_update", txn_ref_update, METH_VARARGS, NULL},
  {"txn_ref_get", txn_ref_get, METH_VARARGS, NULL},
  {"object_decode", object_decode, METH_O, NULL},
  {"object_view_parent", object_view_parent, METH_VARARGS, NULL},
  {"object_view_entry", object_view_entry, METH_VARARGS, NULL},
  {"txn_ref_delete_expected", txn_ref_delete_expected, METH_VARARGS, NULL},
  {"txn_get_datum", txn_get_datum, METH_VARARGS, NULL},
  {"datum_decode", datum_decode, METH_O, NULL},
  {"datum_members", datum_members, METH_O, NULL},
  {"txn_lookup_node", txn_lookup_node, METH_VARARGS, NULL},
  {"repo_export_commit", repo_export_commit, METH_VARARGS, NULL},
  {"repo_import_commit_staged", repo_import_commit_staged, METH_VARARGS, NULL},
  {"txn_collect_garbage", txn_collect_garbage, METH_O, NULL},
#ifdef DML_PRIVATE_REPLAY
  {"repo_import_commit", repo_import_commit, METH_VARARGS, NULL},
  {"repo_export_ref", repo_export_ref, METH_VARARGS, NULL},
  {"repo_import_commit_expected", repo_import_commit_expected, METH_VARARGS, NULL},
  {"txn_check_integrity", txn_check_integrity, METH_O, NULL},
#endif
  {NULL, NULL, 0, NULL},
};

static int module_traverse(PyObject *self, visitproc visit, void *arg) {
  module_state *state = PyModule_GetState(self);
  Py_VISIT(state->error);
  return 0;
}

static int module_clear(PyObject *self) {
  module_state *state = PyModule_GetState(self);
  if (state != NULL) Py_CLEAR(state->error);
  return 0;
}

static void module_free(void *self) {
  module_clear(self);
}

static struct PyModuleDef module = {
  .m_base = PyModuleDef_HEAD_INIT,
  .m_name = MODULE_NAME,
  .m_doc = "Direct operations on the DML C core.",
  .m_size = sizeof(module_state),
  .m_methods = methods,
  .m_traverse = module_traverse,
  .m_clear = module_clear,
  .m_free = module_free,
};

PyMODINIT_FUNC MODULE_INIT(void) {
  if (PyInterpreterState_Get() != PyInterpreterState_Main()) {
    PyErr_SetString(PyExc_ImportError, "DML requires the main CPython interpreter");
    return NULL;
  }
  PyObject *self = PyModule_Create(&module);
  if (self == NULL) return NULL;
  module_state *state = PyModule_GetState(self);
  state->error = PyErr_NewException(MODULE_NAME ".Error", PyExc_RuntimeError, NULL);
  if (state->error == NULL || PyModule_AddObjectRef(self, "Error", state->error) < 0 ||
      PyModule_AddIntConstant(self, "TXN_READ", DML_TXN_READ) < 0 ||
      PyModule_AddIntConstant(self, "TXN_WRITE", DML_TXN_WRITE) < 0 ||
      PyModule_AddIntConstant(self, "DATUM_NULL", DML_DATUM_NULL) < 0 ||
      PyModule_AddIntConstant(self, "DATUM_I64", DML_DATUM_I64) < 0 ||
      PyModule_AddIntConstant(self, "DATUM_STRING", DML_DATUM_STRING) < 0 ||
      PyModule_AddIntConstant(self, "DATUM_URI", DML_DATUM_URI) < 0 ||
      PyModule_AddIntConstant(self, "DATUM_LIST", DML_DATUM_LIST) < 0 ||
      PyModule_AddIntConstant(self, "DATUM_MAP", DML_DATUM_MAP) < 0 ||
      PyModule_AddIntConstant(self, "REC_NODE", DML_REC_NODE) < 0 ||
      PyModule_AddIntConstant(self, "REC_DAG", DML_REC_DAG) < 0 ||
      PyModule_AddIntConstant(self, "REC_TREE", DML_REC_TREE) < 0 ||
      PyModule_AddIntConstant(self, "REC_COMMIT", DML_REC_COMMIT) < 0 ||
      PyModule_AddIntConstant(self, "NODE_LITERAL", DML_NODE_LITERAL) < 0 ||
      PyModule_AddIntConstant(self, "NODE_SUBDAG", DML_NODE_SUBDAG) < 0) {
    Py_DECREF(self);
    return NULL;
  }
  return self;
}
