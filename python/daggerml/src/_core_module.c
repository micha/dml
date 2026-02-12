#define PY_SSIZE_T_CLEAN
#define Py_LIMITED_API 0x03080000

#include <Python.h>

static const char *dml_version(void) {
  return "0.1.0";
}

static PyObject *py_dml_version(PyObject *self, PyObject *args) {
  (void)self;
  (void)args;
  return PyUnicode_FromString(dml_version());
}

static PyMethodDef core_methods[] = {
  {
    "dml_version",
    py_dml_version,
    METH_NOARGS,
    "Return the DaggerML core version.",
  },
  {NULL, NULL, 0, NULL},
};

static struct PyModuleDef core_module = {
  PyModuleDef_HEAD_INIT,
  "_core",
  NULL,
  -1,
  core_methods,
};

PyMODINIT_FUNC PyInit__core(void) {
  return PyModule_Create(&core_module);
}
