#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <stdint.h>
#include <string.h>

#include "dml/transfer.h"

/* Private, single-threaded replay binding. Each entry point calls one core
 * operation; destructors and result conversion only manage ownership. */
#define REPO_CAPSULE "_dml_core.repo"
#define TXN_CAPSULE "_dml_core.txn"
#define VIEW_CAPSULE "_dml_core.object_view"

typedef struct {
  dml_txn *txn;
  PyObject *repo;
} txn_handle;

typedef struct {
  dml_object_view view;
  PyObject *packed;
} object_handle;

static PyObject *raise_status(dml_status status, const dml_error *error) {
  PyObject *args = Py_BuildValue("(sis)", dml_status_name(status), error->native_code, error->detail);
  if (args != NULL) {
    PyErr_SetObject(PyExc_RuntimeError, args);
    Py_DECREF(args);
  }
  return NULL;
}

static void destroy_repo(PyObject *capsule) {
  dml_repo **repo = PyCapsule_GetPointer(capsule, REPO_CAPSULE);
  if (*repo != NULL) dml_repo_close(repo, NULL);
  PyMem_Free(repo);
}

static void destroy_txn(PyObject *capsule) {
  txn_handle *handle = PyCapsule_GetPointer(capsule, TXN_CAPSULE);
  if (handle->txn != NULL) dml_txn_abort(&handle->txn);
  Py_DECREF(handle->repo);
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
  (void)self;
  const char *path;
  int create;
  if (!PyArg_ParseTuple(args, "sp", &path, &create)) return NULL;
  dml_repo **repo = PyMem_Calloc(1, sizeof(*repo));
  if (repo == NULL) return PyErr_NoMemory();
  PyObject *capsule = PyCapsule_New(repo, REPO_CAPSULE, destroy_repo);
  if (capsule == NULL) {
    PyMem_Free(repo);
    return NULL;
  }
  const dml_repo_options options = {.create = create != 0};
  dml_error error = {0};
  dml_status status = dml_repo_open(path, &options, repo, &error);
  if (status != DML_OK) {
    Py_DECREF(capsule);
    return raise_status(status, &error);
  }
  return capsule;
}

static PyObject *repo_close(PyObject *self, PyObject *capsule) {
  (void)self;
  dml_repo **repo = PyCapsule_GetPointer(capsule, REPO_CAPSULE);
  if (repo == NULL) return NULL;
  dml_error error = {0};
  dml_status status = dml_repo_close(repo, &error);
  if (status != DML_OK) return raise_status(status, &error);
  if (*repo != NULL) {
    PyErr_SetString(PyExc_RuntimeError, "repo_close did not consume the repository");
    return NULL;
  }
  Py_RETURN_NONE;
}

static PyObject *txn_begin(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *owner;
  int mode;
  if (!PyArg_ParseTuple(args, "Oi", &owner, &mode)) return NULL;
  dml_repo **repo = PyCapsule_GetPointer(owner, REPO_CAPSULE);
  if (repo == NULL) return NULL;
  txn_handle *handle = PyMem_Calloc(1, sizeof(*handle));
  if (handle == NULL) return PyErr_NoMemory();
  PyObject *capsule = PyCapsule_New(handle, TXN_CAPSULE, destroy_txn);
  if (capsule == NULL) {
    PyMem_Free(handle);
    return NULL;
  }
  handle->repo = Py_NewRef(owner);
  dml_error error = {0};
  dml_status status = dml_txn_begin(*repo, (dml_txn_mode)mode, &handle->txn, &error);
  if (status != DML_OK) {
    Py_DECREF(capsule);
    return raise_status(status, &error);
  }
  return capsule;
}

static PyObject *txn_commit(PyObject *self, PyObject *capsule) {
  (void)self;
  txn_handle *handle = PyCapsule_GetPointer(capsule, TXN_CAPSULE);
  if (handle == NULL) return NULL;
  dml_error error = {0};
  dml_status status = dml_txn_commit(&handle->txn, &error);
  if (handle->txn != NULL) {
    PyErr_SetString(PyExc_RuntimeError, "txn_commit did not consume the transaction");
    return NULL;
  }
  if (status != DML_OK) return raise_status(status, &error);
  Py_RETURN_NONE;
}

static PyObject *txn_abort(PyObject *self, PyObject *capsule) {
  (void)self;
  txn_handle *handle = PyCapsule_GetPointer(capsule, TXN_CAPSULE);
  if (handle == NULL) return NULL;
  dml_txn_abort(&handle->txn);
  if (handle->txn != NULL) {
    PyErr_SetString(PyExc_RuntimeError, "txn_abort did not consume the transaction");
    return NULL;
  }
  Py_RETURN_NONE;
}

static PyObject *datum_encode(PyObject *self, PyObject *args) {
  (void)self;
  int kind;
  PyObject *value;
  if (!PyArg_ParseTuple(args, "iO", &kind, &value)) return NULL;
  dml_datum_input input = {.kind = (dml_datum_kind)kind};
  if (kind == DML_DATUM_I64) {
    long long number = PyLong_AsLongLong(value);
    if (number == -1 && PyErr_Occurred()) return NULL;
    input.value.i64 = (int64_t)number;
  } else if (kind == DML_DATUM_STRING) {
    if (!read_bytes(value, &input.value.bytes)) return NULL;
  } else {
    PyErr_SetString(PyExc_ValueError, "unsupported datum encoder kind");
    return NULL;
  }
  dml_buffer packed = {0};
  dml_error error = {0};
  dml_status status = dml_datum_encode(&input, &packed, &error);
  return status == DML_OK ? take_buffer(&packed) : raise_status(status, &error);
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
  (void)self;
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
  return status == DML_OK ? take_buffer(&packed) : raise_status(status, &error);
}

static PyObject *txn_put_datum(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *capsule, *record;
  if (!PyArg_ParseTuple(args, "OO", &capsule, &record)) return NULL;
  txn_handle *handle = PyCapsule_GetPointer(capsule, TXN_CAPSULE);
  dml_bytes packed;
  if (handle == NULL || !read_bytes(record, &packed)) return NULL;
  dml_object_id id;
  dml_error error = {0};
  dml_status status = dml_txn_put_datum(handle->txn, packed.data, packed.len, &id, &error);
  return status == DML_OK ? id_bytes(&id) : raise_status(status, &error);
}

static PyObject *txn_put_object(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *capsule, *record;
  int type;
  if (!PyArg_ParseTuple(args, "OiO", &capsule, &type, &record)) return NULL;
  txn_handle *handle = PyCapsule_GetPointer(capsule, TXN_CAPSULE);
  dml_bytes packed;
  if (handle == NULL || !read_bytes(record, &packed)) return NULL;
  dml_object_id id;
  dml_error error = {0};
  dml_status status = dml_txn_put_object(handle->txn, (dml_record_type)type, packed.data, packed.len,
                                         &id, &error);
  return status == DML_OK ? id_bytes(&id) : raise_status(status, &error);
}

static PyObject *txn_get_object(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *capsule, *id_obj;
  int type;
  if (!PyArg_ParseTuple(args, "OiO", &capsule, &type, &id_obj)) return NULL;
  txn_handle *handle = PyCapsule_GetPointer(capsule, TXN_CAPSULE);
  dml_object_id id;
  if (handle == NULL || !read_id(id_obj, &id)) return NULL;
  dml_buffer packed = {0};
  dml_error error = {0};
  dml_status status = dml_txn_get_object(handle->txn, (dml_record_type)type, &id, &packed, &error);
  return status == DML_OK ? take_buffer(&packed) : raise_status(status, &error);
}

typedef dml_status (*ref_write_fn)(dml_txn *, dml_bytes, const dml_object_id *, dml_error *);

static PyObject *ref_write(PyObject *args, ref_write_fn write) {
  PyObject *capsule, *name_obj, *id_obj;
  if (!PyArg_ParseTuple(args, "OOO", &capsule, &name_obj, &id_obj)) return NULL;
  txn_handle *handle = PyCapsule_GetPointer(capsule, TXN_CAPSULE);
  dml_bytes name;
  dml_object_id id;
  if (handle == NULL || !read_bytes(name_obj, &name) || !read_id(id_obj, &id)) return NULL;
  dml_error error = {0};
  dml_status status = write(handle->txn, name, &id, &error);
  if (status != DML_OK) return raise_status(status, &error);
  Py_RETURN_NONE;
}

static PyObject *txn_ref_create(PyObject *self, PyObject *args) {
  (void)self;
  return ref_write(args, dml_txn_ref_create);
}

static PyObject *txn_ref_update(PyObject *self, PyObject *args) {
  (void)self;
  return ref_write(args, dml_txn_ref_update);
}

static PyObject *txn_ref_delete_expected(PyObject *self, PyObject *args) {
  (void)self;
  return ref_write(args, dml_txn_ref_delete_expected);
}

static PyObject *txn_ref_get(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *capsule, *name_obj;
  if (!PyArg_ParseTuple(args, "OO", &capsule, &name_obj)) return NULL;
  txn_handle *handle = PyCapsule_GetPointer(capsule, TXN_CAPSULE);
  dml_bytes name;
  if (handle == NULL || !read_bytes(name_obj, &name)) return NULL;
  dml_object_id id;
  dml_error error = {0};
  dml_status status = dml_txn_ref_get(handle->txn, name, &id, &error);
  return status == DML_OK ? id_bytes(&id) : raise_status(status, &error);
}

static PyObject *object_decode(PyObject *self, PyObject *record) {
  (void)self;
  dml_bytes packed;
  if (!read_bytes(record, &packed)) return NULL;
  object_handle *handle = PyMem_Malloc(sizeof(*handle));
  if (handle == NULL) return PyErr_NoMemory();
  dml_error error = {0};
  dml_status status = dml_object_decode(packed.data, packed.len, &handle->view, &error);
  if (status != DML_OK) {
    PyMem_Free(handle);
    return raise_status(status, &error);
  }
  PyObject *capsule = PyCapsule_New(handle, VIEW_CAPSULE, destroy_view);
  if (capsule == NULL) {
    PyMem_Free(handle);
    return NULL;
  }
  handle->packed = Py_NewRef(record);
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
  (void)self;
  PyObject *capsule;
  Py_ssize_t index;
  if (!PyArg_ParseTuple(args, "On", &capsule, &index)) return NULL;
  object_handle *handle = PyCapsule_GetPointer(capsule, VIEW_CAPSULE);
  if (handle == NULL) return NULL;
  if (index < 0) {
    PyErr_SetString(PyExc_ValueError, "parent index must be nonnegative");
    return NULL;
  }
  dml_object_id id;
  dml_error error = {0};
  dml_status status = dml_object_view_parent(&handle->view, (size_t)index, &id, &error);
  return status == DML_OK ? id_bytes(&id) : raise_status(status, &error);
}

static PyObject *output_result(dml_status status, PyObject *output) {
  if (output == NULL) return NULL;
  return Py_BuildValue("(sN)", dml_status_name(status), output);
}

static PyObject *repo_export_commit(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *capsule, *root_obj;
  if (!PyArg_ParseTuple(args, "OO", &capsule, &root_obj)) return NULL;
  dml_repo **repo = PyCapsule_GetPointer(capsule, REPO_CAPSULE);
  dml_object_id root;
  if (repo == NULL || !read_id(root_obj, &root)) return NULL;
  dml_buffer packed = {0};
  dml_status status = dml_repo_export_commit(*repo, &root, &packed, NULL);
  return output_result(status, take_buffer(&packed));
}

static PyObject *import_bundle(PyObject *args, bool staged) {
  PyObject *capsule, *bundle_obj, *name_obj;
  if (!PyArg_ParseTuple(args, staged ? "OOO" : "OO", &capsule, &bundle_obj, &name_obj)) return NULL;
  dml_repo **repo = PyCapsule_GetPointer(capsule, REPO_CAPSULE);
  dml_bytes bundle, name;
  if (repo == NULL || !read_bytes(bundle_obj, &bundle) || (staged && !read_bytes(name_obj, &name)))
    return NULL;
  dml_object_id root;
  memset(root.bytes, 0xa5, sizeof(root.bytes));
  dml_status status = staged ? dml_repo_import_commit_staged(*repo, bundle, name, &root, NULL)
                             : dml_repo_import_commit(*repo, bundle, &root, NULL);
  return output_result(status, id_bytes(&root));
}

static PyObject *repo_import_commit(PyObject *self, PyObject *args) {
  (void)self;
  return import_bundle(args, false);
}

static PyObject *repo_import_commit_staged(PyObject *self, PyObject *args) {
  (void)self;
  return import_bundle(args, true);
}

static PyObject *txn_collect_garbage(PyObject *self, PyObject *capsule) {
  (void)self;
  txn_handle *handle = PyCapsule_GetPointer(capsule, TXN_CAPSULE);
  if (handle == NULL) return NULL;
  size_t removed = 123456789;
  dml_status status = dml_txn_collect_garbage(handle->txn, &removed, NULL);
  return output_result(status, PyLong_FromSize_t(removed));
}

static PyObject *txn_get_datum(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *capsule, *id_obj;
  if (!PyArg_ParseTuple(args, "OO", &capsule, &id_obj)) return NULL;
  txn_handle *handle = PyCapsule_GetPointer(capsule, TXN_CAPSULE);
  dml_object_id id;
  if (handle == NULL || !read_id(id_obj, &id)) return NULL;
  dml_buffer packed = {0};
  dml_error error = {0};
  dml_status status = dml_txn_get_datum(handle->txn, &id, &packed, &error);
  return status == DML_OK ? take_buffer(&packed) : raise_status(status, &error);
}

static PyObject *datum_decode(PyObject *self, PyObject *record) {
  (void)self;
  dml_bytes packed;
  if (!read_bytes(record, &packed)) return NULL;
  dml_datum_view view;
  dml_error error = {0};
  dml_status status = dml_datum_decode(packed.data, packed.len, &view, &error);
  if (status != DML_OK) return raise_status(status, &error);
  return Py_BuildValue("(y#i)", (const char *)view.payload, (Py_ssize_t)view.payload_len, (int)view.kind);
}

static PyObject *txn_lookup_node(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *capsule, *id_obj, *name_obj;
  if (!PyArg_ParseTuple(args, "OOO", &capsule, &id_obj, &name_obj)) return NULL;
  txn_handle *handle = PyCapsule_GetPointer(capsule, TXN_CAPSULE);
  dml_object_id dag, node;
  dml_bytes name;
  if (handle == NULL || !read_id(id_obj, &dag) || !read_bytes(name_obj, &name)) return NULL;
  dml_error error = {0};
  dml_status status = dml_txn_lookup_node(handle->txn, &dag, name, &node, &error);
  return status == DML_OK ? id_bytes(&node) : raise_status(status, &error);
}

static PyObject *object_view_entry(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *capsule;
  Py_ssize_t index;
  if (!PyArg_ParseTuple(args, "On", &capsule, &index)) return NULL;
  object_handle *handle = PyCapsule_GetPointer(capsule, VIEW_CAPSULE);
  if (handle == NULL) return NULL;
  if (index < 0) {
    PyErr_SetString(PyExc_ValueError, "tree index must be nonnegative");
    return NULL;
  }
  dml_tree_entry entry;
  dml_error error = {0};
  dml_status status = dml_object_view_entry(&handle->view, (size_t)index, &entry, &error);
  if (status != DML_OK) return raise_status(status, &error);
  return Py_BuildValue("(y#y#)", (const char *)entry.dag.bytes, (Py_ssize_t)sizeof(entry.dag.bytes),
                       (const char *)entry.name.data, (Py_ssize_t)entry.name.len);
}

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
  (void)self;
  txn_handle *handle = PyCapsule_GetPointer(capsule, TXN_CAPSULE);
  if (handle == NULL) return NULL;
  integrity_visitor visitor = {.visited = PyList_New(0)};
  if (visitor.visited == NULL) return NULL;
  dml_repo_integrity report;
  dml_error error = {0};
  dml_status status = dml_txn_check_integrity(handle->txn, &report, observe_unreachable, &visitor, &error);
  if (status != DML_OK || visitor.failed) {
    Py_DECREF(visitor.visited);
    return visitor.failed ? NULL : raise_status(status, &error);
  }
  return Py_BuildValue("((KKKKKKKKK)N)", (unsigned long long)report.refs,
                       (unsigned long long)report.broken_refs, (unsigned long long)report.invalid_entries,
                       (unsigned long long)report.invalid_objects, (unsigned long long)report.reachable_objects,
                       (unsigned long long)report.broken_reachable_edges,
                       (unsigned long long)report.broken_unreachable_edges,
                       (unsigned long long)report.intact_unreachable_objects,
                       (unsigned long long)report.broken_unreachable_objects, visitor.visited);
}

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
  {"repo_export_commit", repo_export_commit, METH_VARARGS, NULL},
  {"repo_import_commit", repo_import_commit, METH_VARARGS, NULL},
  {"repo_import_commit_staged", repo_import_commit_staged, METH_VARARGS, NULL},
  {"txn_collect_garbage", txn_collect_garbage, METH_O, NULL},
  {"txn_ref_delete_expected", txn_ref_delete_expected, METH_VARARGS, NULL},
  {"txn_get_datum", txn_get_datum, METH_VARARGS, NULL},
  {"datum_decode", datum_decode, METH_O, NULL},
  {"txn_lookup_node", txn_lookup_node, METH_VARARGS, NULL},
  {"txn_check_integrity", txn_check_integrity, METH_O, NULL},
  {NULL, NULL, 0, NULL},
};

static struct PyModuleDef module = {
  .m_base = PyModuleDef_HEAD_INIT,
  .m_name = "_dml_core",
  .m_doc = "Private DML core bindings for sequential Quint replay.",
  .m_size = -1,
  .m_methods = methods,
};

PyMODINIT_FUNC PyInit__dml_core(void) {
  return PyModule_Create(&module);
}
