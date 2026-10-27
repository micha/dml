#ifndef DML_PYTHON_FAULTS_H
#define DML_PYTHON_FAULTS_H

#include <stdarg.h>
#include "fault_control.h"

/* Private extension only. Return failures at the binding allocation boundary,
 * preserving CPython's reference-stealing contracts before injecting failure. */
static int py_fault_kind;
static size_t py_fault_nth;
static int py_fault(int kind) {
  if (py_fault_kind != kind || !py_fault_nth) return 0;
  if (--py_fault_nth) return 0;
  py_fault_kind = 0;
  return 1;
}
static void *test_calloc(size_t count, size_t size) {
  return py_fault(1) ? NULL : calloc(count, size);
}
static PyObject *test_result(PyObject *result) {
  if (py_fault(2)) { Py_XDECREF(result); return PyErr_NoMemory(); }
  return result;
}
static PyObject *test_build(const char *format, ...) {
  va_list args; va_start(args, format);
  PyObject *result = Py_VaBuildValue(format, args);
  va_end(args);
  return test_result(result);
}
static PyObject *test_capsule(void *p, const char *name, PyCapsule_Destructor destructor) {
  if (py_fault(2)) return PyErr_NoMemory();
  return PyCapsule_New(p, name, destructor);
}
static PyObject *py_set_fault(PyObject *self, PyObject *args) {
  (void)self;
  int kind; Py_ssize_t nth;
  if (!PyArg_ParseTuple(args, "in", &kind, &nth)) return NULL;
  py_fault_kind = kind; py_fault_nth = (size_t)nth;
  Py_RETURN_NONE;
}
static PyObject *py_native_fault(PyObject *self, PyObject *args) {
  (void)self;
  int op, code; Py_ssize_t nth;
  if (!PyArg_ParseTuple(args, "ini", &op, &nth, &code)) return NULL;
  dml_test_fail((dml_test_fault)op, (size_t)nth, code);
  Py_RETURN_NONE;
}

#define calloc test_calloc
#define PyCapsule_New test_capsule
#define Py_BuildValue test_build
#define PyBytes_FromStringAndSize(data, len) test_result(PyBytes_FromStringAndSize(data, len))
#define PyUnicode_FromString(data) test_result(PyUnicode_FromString(data))
#define PyUnicode_DecodeUTF8(data, len, errors) test_result(PyUnicode_DecodeUTF8(data, len, errors))
#define PyUnicode_AsUTF8String(data) test_result(PyUnicode_AsUTF8String(data))
#define PyTuple_New(count) test_result(PyTuple_New(count))
#define PyBool_FromLong(value) test_result(PyBool_FromLong(value))
#define PyLong_FromLongLong(value) test_result(PyLong_FromLongLong(value))
#define PyLong_FromUnsignedLong(value) test_result(PyLong_FromUnsignedLong(value))
#define PyFloat_FromDouble(value) test_result(PyFloat_FromDouble(value))

#endif
