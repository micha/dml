#define PY_SSIZE_T_CLEAN
#define Py_LIMITED_API 0x03080000
#include <Python.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "dml/dml.h"

#ifdef DML_PY_FAULTS
#include "python_faults.h"
#define CORE_NAME "_core_fault"
#define CORE_INIT PyInit__core_fault
#else
#define CORE_NAME "_core"
#define CORE_INIT PyInit__core
#endif

typedef struct Txn Txn;
typedef struct { dml_repo *ptr; unsigned long thread; size_t active; Txn *pending; } Repo;
struct Txn { dml_txn *ptr; PyObject *owner; unsigned long thread; Txn *next; };

/* The GIL serializes queue updates. No native transaction is ended on a foreign
 * thread. This queue belongs to one repository, not a global handle registry. */
static void reap(Repo *repo) {
  while (repo->pending) {
    Txn *txn = repo->pending;
    repo->pending = txn->next;
    dml_txn_abort(&txn->ptr);
    repo->active--;
    free(txn);
  }
}

static PyObject *fail(dml_status status, dml_error *error) {
  PyObject *args = Py_BuildValue("sis", dml_status_name(status), error->native_code, error->detail);
  if (args) {
    PyErr_SetObject(PyExc_RuntimeError, args);
    Py_DECREF(args);
  }
  return NULL;
}

static int same_thread(unsigned long thread) {
  if (thread == PyThread_get_thread_ident()) return 1;
  PyErr_SetString(PyExc_RuntimeError, "native handle belongs to another thread");
  return 0;
}

static Repo *repo_handle(PyObject *obj) {
  Repo *repo = PyCapsule_GetPointer(obj, "daggerml.repo");
  if (!repo || !same_thread(repo->thread)) return NULL;
  reap(repo);
  if (!repo->ptr) { PyErr_SetString(PyExc_RuntimeError, "repository is closed"); return NULL; }
  return repo;
}

static Txn *txn_handle(PyObject *obj) {
  Txn *txn = PyCapsule_GetPointer(obj, "daggerml.txn");
  if (!txn || !same_thread(txn->thread)) return NULL;
  if (!txn->ptr) { PyErr_SetString(PyExc_RuntimeError, "transaction has ended"); return NULL; }
  return txn;
}

static void repo_destroy(PyObject *obj) {
  Repo *repo = PyCapsule_GetPointer(obj, "daggerml.repo");
  if (repo->pending && repo->thread != PyThread_get_thread_ident()) {
    /* No owner-thread invocation remains available. Deliberately leak native
     * resources rather than violate LMDB transaction thread affinity. */
    if (PyErr_WarnEx(PyExc_ResourceWarning,
        "DML owner dropped on foreign thread with pending transactions; native resources abandoned", 1) < 0)
      PyErr_WriteUnraisable(Py_None);
    return;
  }
  reap(repo);
  dml_error error;
  dml_repo_close(&repo->ptr, &error);
  free(repo);
}

static void txn_destroy(PyObject *obj) {
  Txn *txn = PyCapsule_GetPointer(obj, "daggerml.txn");
  Repo *repo = PyCapsule_GetPointer(txn->owner, "daggerml.repo");
  PyObject *owner = txn->owner;
  if (txn->ptr && txn->thread != PyThread_get_thread_ident()) {
    txn->owner = NULL;
    txn->next = repo->pending;
    repo->pending = txn;
  } else {
    if (txn->ptr) { dml_txn_abort(&txn->ptr); repo->active--; }
    free(txn);
  }
  Py_DECREF(owner);
}

static int as_id(PyObject *obj, dml_object_id *id) {
  char *data;
  Py_ssize_t len;
  if (PyBytes_AsStringAndSize(obj, &data, &len) < 0) return 0;
  if (len != 16) { PyErr_SetString(PyExc_ValueError, "ID requires 16 bytes"); return 0; }
  memcpy(id->bytes, data, 16);
  return 1;
}

static Py_ssize_t tuple_count(PyObject *value) {
  if (!PyTuple_Check(value)) { PyErr_SetString(PyExc_TypeError, "expected tuple"); return -1; }
  return PyTuple_Size(value);
}

static PyObject *id_bytes(const dml_object_id *id) {
  return PyBytes_FromStringAndSize((const char *)id->bytes, 16);
}

static PyObject *buffer_bytes(dml_buffer *buffer) {
  PyObject *result = PyBytes_FromStringAndSize((const char *)buffer->data, (Py_ssize_t)buffer->len);
  dml_buffer_free(buffer);
  return result;
}

static PyObject *version(PyObject *self, PyObject *args) {
  (void)self; (void)args;
  return PyUnicode_FromString(dml_version());
}

static PyObject *parse_id(PyObject *self, PyObject *args) {
  (void)self;
  const char *text; Py_ssize_t len;
  dml_object_id id; dml_error error;
  if (!PyArg_ParseTuple(args, "s#", &text, &len)) return NULL;
  dml_status s = dml_object_id_parse(text, (size_t)len, &id, &error);
  if (s != DML_OK) return fail(s, &error);
  return id_bytes(&id);
}

static PyObject *py_canonicalize(PyObject *self, PyObject *args) {
  (void)self;
  const char *text; Py_ssize_t len;
  dml_buffer buffer = {0}; dml_error error;
  if (!PyArg_ParseTuple(args, "s#", &text, &len)) return NULL;
  dml_status s = dml_uri_canonicalize((const uint8_t *)text, (size_t)len, &buffer, &error);
  if (s != DML_OK) return fail(s, &error);
  PyObject *result = PyUnicode_DecodeUTF8((const char *)buffer.data, (Py_ssize_t)buffer.len, "strict");
  dml_buffer_free(&buffer);
  return result;
}

static PyObject *repo_open(PyObject *self, PyObject *args) {
  (void)self;
  const char *path; int create; Py_ssize_t map_size;
  if (!PyArg_ParseTuple(args, "spn", &path, &create, &map_size)) return NULL;
  if (map_size < 0) { PyErr_SetString(PyExc_ValueError, "negative map size"); return NULL; }
  Repo *repo = calloc(1, sizeof(*repo));
  if (!repo) return PyErr_NoMemory();
  repo->thread = PyThread_get_thread_ident();
  dml_repo_options options = {.create = create != 0, .map_size = (size_t)map_size};
  dml_error error;
  dml_status s = dml_repo_open(path, &options, &repo->ptr, &error);
  if (s != DML_OK) { free(repo); return fail(s, &error); }
  PyObject *result = PyCapsule_New(repo, "daggerml.repo", repo_destroy);
  if (!result) { dml_repo_close(&repo->ptr, &error); free(repo); }
  return result;
}

static PyObject *repo_close(PyObject *self, PyObject *obj) {
  (void)self;
  Repo *repo = PyCapsule_GetPointer(obj, "daggerml.repo");
  if (!repo || !same_thread(repo->thread)) return NULL;
  reap(repo);
  dml_error error;
  dml_status s = dml_repo_close(&repo->ptr, &error);
  if (s != DML_OK) return fail(s, &error);
  Py_RETURN_NONE;
}

static PyObject *repo_schema(PyObject *self, PyObject *obj) {
  (void)self;
  Repo *repo = repo_handle(obj); if (!repo) return NULL;
  uint32_t schema; dml_error error;
  dml_status s = dml_repo_schema(repo->ptr, &schema, &error);
  /* Checked live handle and non-null output; this allocation-free query cannot fail. */
  if (s != DML_OK) return fail(s, &error); /* LCOV_EXCL_BR_LINE */
  return PyLong_FromUnsignedLong(schema);
}

static PyObject *txn_begin(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *owner; int write;
  if (!PyArg_ParseTuple(args, "Op", &owner, &write)) return NULL;
  Repo *repo = repo_handle(owner); if (!repo) return NULL;
  if (repo->active) { PyErr_SetString(PyExc_RuntimeError, "repository already has an active transaction"); return NULL; }
  Txn *txn = calloc(1, sizeof(*txn));
  if (!txn) return PyErr_NoMemory();
  txn->thread = PyThread_get_thread_ident();
  dml_error error;
  dml_status s = dml_txn_begin(repo->ptr, write ? DML_TXN_WRITE : DML_TXN_READ, &txn->ptr, &error);
  if (s != DML_OK) { free(txn); return fail(s, &error); }
  repo->active++;
  /* CPython inline refcount branches are dependency implementation, not ownership paths. */
  Py_INCREF(owner); /* LCOV_EXCL_BR_LINE */
  txn->owner = owner;
  PyObject *result = PyCapsule_New(txn, "daggerml.txn", txn_destroy);
  if (!result) { dml_txn_abort(&txn->ptr); repo->active--; Py_DECREF(owner); free(txn); }
  return result;
}

static PyObject *txn_end(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *obj; int commit;
  if (!PyArg_ParseTuple(args, "Op", &obj, &commit)) return NULL;
  Txn *txn = PyCapsule_GetPointer(obj, "daggerml.txn");
  if (!txn || !same_thread(txn->thread)) return NULL;
  dml_error error;
  Repo *repo = PyCapsule_GetPointer(txn->owner, "daggerml.repo");
  int active = txn->ptr != NULL;
  if (commit) {
    dml_status s = dml_txn_commit(&txn->ptr, &error);
    if (active) repo->active--;
    if (s != DML_OK) return fail(s, &error);
  } else {
    dml_txn_abort(&txn->ptr);
    if (active) repo->active--;
  }
  Py_RETURN_NONE;
}

static PyObject *get_record(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *obj, *id_obj; int type;
  if (!PyArg_ParseTuple(args, "OiO", &obj, &type, &id_obj)) return NULL;
  Txn *txn = txn_handle(obj); dml_object_id id;
  if (!txn || !as_id(id_obj, &id)) return NULL;
  dml_buffer buffer = {0}; dml_error error;
  dml_status s = type == DML_REC_DATUM ? dml_txn_get_datum(txn->ptr, &id, &buffer, &error) :
    dml_txn_get_object(txn->ptr, (dml_record_type)type, &id, &buffer, &error);
  if (s != DML_OK) return fail(s, &error);
  return buffer_bytes(&buffer);
}

static PyObject *put_record(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *obj; int type; const char *data; Py_ssize_t len;
  if (!PyArg_ParseTuple(args, "Oiy#", &obj, &type, &data, &len)) return NULL;
  Txn *txn = txn_handle(obj); if (!txn) return NULL;
  dml_object_id id; dml_error error;
  dml_status s = type == DML_REC_DATUM ? dml_txn_put_datum(txn->ptr, (const uint8_t *)data, (size_t)len, &id, &error) :
    dml_txn_put_object(txn->ptr, (dml_record_type)type, (const uint8_t *)data, (size_t)len, &id, &error);
  if (s != DML_OK) return fail(s, &error);
  return id_bytes(&id);
}

static PyObject *ref_op(PyObject *self, PyObject *args) {
  (void)self;
  PyObject *obj, *target; const char *name; Py_ssize_t len; int op;
  if (!PyArg_ParseTuple(args, "Ois#O", &obj, &op, &name, &len, &target)) return NULL;
  Txn *txn = txn_handle(obj); if (!txn) return NULL;
  dml_object_id id; dml_error error;
  dml_bytes bytes = {(const uint8_t *)name, (size_t)len};
  dml_status s;
  if (op == 0) s = dml_txn_ref_get(txn->ptr, bytes, &id, &error);
  else {
    if (!as_id(target, &id)) return NULL;
    s = op == 1 ? dml_txn_ref_create(txn->ptr, bytes, &id, &error) :
      dml_txn_ref_update(txn->ptr, bytes, &id, &error);
  }
  if (s != DML_OK) return fail(s, &error);
  if (op == 0) return id_bytes(&id);
  Py_RETURN_NONE;
}

/* Python passes owned tuples/bytes. All canonicalization is performed by C. */
static PyObject *encode_datum(PyObject *self, PyObject *args) {
  (void)self;
  int kind; PyObject *value;
  if (!PyArg_ParseTuple(args, "iO", &kind, &value)) return NULL;
  dml_datum_input input = {.kind = (dml_datum_kind)kind};
  dml_object_id *ids = NULL; dml_datum_map_entry *entries = NULL;
  PyObject *utf8 = NULL;
  if (kind == DML_DATUM_BOOL) { int b = PyObject_IsTrue(value); if (b < 0) return NULL; input.value.boolean = b != 0; }
  else if (kind == DML_DATUM_I64) { input.value.i64 = PyLong_AsLongLong(value); if (PyErr_Occurred()) return NULL; }
  else if (kind == DML_DATUM_F64) { input.value.f64 = PyFloat_AsDouble(value); if (PyErr_Occurred()) return NULL; }
  else if (kind >= DML_DATUM_BYTES && kind <= DML_DATUM_URI) {
    if (kind != DML_DATUM_BYTES) { utf8 = PyUnicode_AsUTF8String(value); if (!utf8) return NULL; value = utf8; }
    char *data; Py_ssize_t len;
    if (PyBytes_AsStringAndSize(value, &data, &len) < 0) { Py_XDECREF(utf8); return NULL; }
    input.value.bytes = (dml_bytes){(const uint8_t *)data, (size_t)len};
  } else if (kind >= DML_DATUM_LIST && kind <= DML_DATUM_MAP) {
    Py_ssize_t count = tuple_count(value); if (count < 0) return NULL;
    if (kind == DML_DATUM_MAP) {
      entries = calloc((size_t)count + 1, sizeof(*entries));
      if (!entries) return PyErr_NoMemory();
      input.value.map = (dml_map_array){entries, (size_t)count};
    } else {
      ids = calloc((size_t)count + 1, sizeof(*ids));
      if (!ids) return PyErr_NoMemory();
      input.value.ids = (dml_id_array){ids, (size_t)count};
    }
    for (Py_ssize_t i = 0; i < count; i++) {
      PyObject *item = PyTuple_GetItem(value, i);
      if (kind == DML_DATUM_MAP) {
        if (!PyTuple_Check(item) || PyTuple_Size(item) != 2) { PyErr_SetString(PyExc_TypeError, "map pair required"); goto conversion_error; }
        if (!as_id(PyTuple_GetItem(item, 0), &entries[i].key) || !as_id(PyTuple_GetItem(item, 1), &entries[i].value)) goto conversion_error;
      } else if (!as_id(item, &ids[i])) goto conversion_error;
    }
  }
  dml_buffer buffer = {0}; dml_error error;
  dml_status s = dml_datum_encode(&input, &buffer, &error);
  free(ids); free(entries); Py_XDECREF(utf8);
  if (s != DML_OK) return fail(s, &error);
  return buffer_bytes(&buffer);
conversion_error:
  free(ids); free(entries);
  return NULL;
}

static PyObject *encode_object(PyObject *self, PyObject *args) {
  (void)self;
  int type; PyObject *value, *parents;
  if (!PyArg_ParseTuple(args, "iOO", &type, &value, &parents)) return NULL;
  dml_object_input input = {.type = (dml_record_type)type};
  dml_tree_entry *entries = NULL; dml_object_id *ids = NULL;
  if (type == DML_REC_NODE) {
    input.value.node.kind = DML_NODE_LITERAL;
    if (!as_id(value, &input.value.node.datum)) return NULL;
  } else if (type == DML_REC_DAG) {
    if (!as_id(value, &input.value.root)) return NULL;
  } else if (type == DML_REC_TREE) {
    Py_ssize_t count = tuple_count(value); if (count < 0) return NULL;
    entries = calloc((size_t)count + 1, sizeof(*entries)); if (!entries) return PyErr_NoMemory();
    input.value.tree.items = entries; input.value.tree.count = (size_t)count;
    for (Py_ssize_t i = 0; i < count; i++) {
      PyObject *pair = PyTuple_GetItem(value, i); char *name; Py_ssize_t len;
      if (!PyTuple_Check(pair) || PyTuple_Size(pair) != 2) { PyErr_SetString(PyExc_TypeError, "tree pair required"); goto conversion_error; }
      if (PyBytes_AsStringAndSize(PyTuple_GetItem(pair, 0), &name, &len) < 0 ||
          !as_id(PyTuple_GetItem(pair, 1), &entries[i].dag)) goto conversion_error;
      entries[i].name = (dml_bytes){(const uint8_t *)name, (size_t)len};
    }
  } else if (type == DML_REC_COMMIT) {
    if (!as_id(value, &input.value.commit.tree)) return NULL;
    Py_ssize_t count = tuple_count(parents); if (count < 0) return NULL;
    ids = calloc((size_t)count + 1, sizeof(*ids)); if (!ids) return PyErr_NoMemory();
    input.value.commit.parents = (dml_id_array){ids, (size_t)count};
    for (Py_ssize_t i = 0; i < count; i++) if (!as_id(PyTuple_GetItem(parents, i), &ids[i])) goto conversion_error;
  }
  dml_buffer buffer = {0}; dml_error error;
  dml_status s = dml_object_encode(&input, &buffer, &error);
  free(entries); free(ids);
  if (s != DML_OK) return fail(s, &error);
  return buffer_bytes(&buffer);
conversion_error:
  free(entries); free(ids);
  return NULL;
}

static uint64_t little64(const uint8_t *data) {
  uint64_t bits = 0;
  for (unsigned i = 0; i < 8; i++) bits |= (uint64_t)data[i] << (8 * i);
  return bits;
}

static PyObject *decode_datum(PyObject *self, PyObject *args) {
  (void)self;
  const char *data; Py_ssize_t len;
  if (!PyArg_ParseTuple(args, "y#", &data, &len)) return NULL;
  dml_datum_view view; dml_error error;
  dml_status s = dml_datum_decode((const uint8_t *)data, (size_t)len, &view, &error);
  if (s != DML_OK) return fail(s, &error);
  PyObject *value = NULL;
  switch (view.kind) {
    case DML_DATUM_NULL: /* CPython inline immortal check attributed here. LCOV_EXCL_BR_LINE */
      Py_INCREF(Py_None); /* CPython immortality branch. LCOV_EXCL_BR_LINE */
      value = Py_None;
      break;
    case DML_DATUM_BOOL: value = PyBool_FromLong(view.payload[0]); break;
    case DML_DATUM_I64: { uint64_t bits = little64(view.payload); int64_t signed_bits; memcpy(&signed_bits, &bits, 8); value = PyLong_FromLongLong(signed_bits); break; }
    case DML_DATUM_F64: { uint64_t bits = little64(view.payload); double number; memcpy(&number, &bits, 8); value = PyFloat_FromDouble(number); break; }
    case DML_DATUM_BYTES: value = PyBytes_FromStringAndSize((const char *)view.payload, (Py_ssize_t)view.payload_len); break;
    case DML_DATUM_STRING: case DML_DATUM_URI: value = PyUnicode_DecodeUTF8((const char *)view.payload, (Py_ssize_t)view.payload_len, "strict"); break;
    default:
      value = PyTuple_New((Py_ssize_t)view.count); if (!value) return NULL;
      for (size_t i = 0; i < view.count; i++) {
        PyObject *item;
        if (view.kind == DML_DATUM_MAP) {
          dml_datum_map_entry entry;
          dml_datum_view_map_entry(&view, i, &entry, &error);
          item = Py_BuildValue("NN", id_bytes(&entry.key), id_bytes(&entry.value));
        } else {
          dml_object_id id;
          dml_datum_view_id(&view, i, &id, &error);
          item = id_bytes(&id);
        }
        if (!item) { Py_DECREF(value); return NULL; }
        PyTuple_SetItem(value, (Py_ssize_t)i, item);
      }
  }
  if (!value) return NULL;
  return Py_BuildValue("iN", (int)view.kind, value);
}

static PyObject *decode_object(PyObject *self, PyObject *args) {
  (void)self;
  const char *data; Py_ssize_t len;
  if (!PyArg_ParseTuple(args, "y#", &data, &len)) return NULL;
  dml_object_view view; dml_error error;
  dml_status s = dml_object_decode((const uint8_t *)data, (size_t)len, &view, &error);
  if (s != DML_OK) return fail(s, &error);
  PyObject *items = PyTuple_New((Py_ssize_t)view.count); if (!items) return NULL;
  for (size_t i = 0; i < view.count; i++) {
    PyObject *item;
    if (view.type == DML_REC_TREE) {
      dml_tree_entry entry; dml_object_view_entry(&view, i, &entry, &error);
      item = Py_BuildValue("NN", PyUnicode_DecodeUTF8((const char *)entry.name.data, (Py_ssize_t)entry.name.len, "strict"), id_bytes(&entry.dag));
    } else {
      dml_object_id id; dml_object_view_parent(&view, i, &id, &error); item = id_bytes(&id);
    }
    if (!item) { Py_DECREF(items); return NULL; }
    PyTuple_SetItem(items, (Py_ssize_t)i, item);
  }
  return Py_BuildValue("NN", id_bytes(&view.reference), items);
}

static PyMethodDef methods[] = {
#ifdef DML_PY_FAULTS
  {"set_fault", py_set_fault, METH_VARARGS, NULL},
  {"native_fault", py_native_fault, METH_VARARGS, NULL},
#endif
  {"dml_version", version, METH_NOARGS, NULL},
  {"parse_id", parse_id, METH_VARARGS, NULL},
  {"canonicalize_uri", py_canonicalize, METH_VARARGS, NULL},
  {"repo_open", repo_open, METH_VARARGS, NULL},
  {"repo_close", repo_close, METH_O, NULL},
  {"repo_schema", repo_schema, METH_O, NULL},
  {"txn_begin", txn_begin, METH_VARARGS, NULL},
  {"txn_end", txn_end, METH_VARARGS, NULL},
  {"get_record", get_record, METH_VARARGS, NULL},
  {"put_record", put_record, METH_VARARGS, NULL},
  {"ref_op", ref_op, METH_VARARGS, NULL},
  {"encode_datum", encode_datum, METH_VARARGS, NULL},
  {"encode_object", encode_object, METH_VARARGS, NULL},
  {"decode_datum", decode_datum, METH_VARARGS, NULL},
  {"decode_object", decode_object, METH_VARARGS, NULL},
  {NULL, NULL, 0, NULL},
};
static struct PyModuleDef module = {PyModuleDef_HEAD_INIT, CORE_NAME, NULL, -1, methods, NULL, NULL, NULL, NULL};
PyMODINIT_FUNC CORE_INIT(void) { return PyModule_Create(&module); }
