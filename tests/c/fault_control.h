#ifndef DML_TEST_FAULT_CONTROL_H
#define DML_TEST_FAULT_CONTROL_H

#include <stddef.h>

typedef enum {
  DML_TEST_NO_FAULT,
  DML_TEST_ALLOCATE,
  DML_TEST_TEXT,
  DML_TEST_URI_PARSE,
  DML_TEST_URI_NORMALIZE,
  DML_TEST_URI_SIZE,
  DML_TEST_URI_WRITE,
  DML_TEST_ENV_CREATE,
  DML_TEST_ENV_SIZE,
  DML_TEST_ENV_OPEN,
  DML_TEST_TXN_BEGIN,
  DML_TEST_DBI_OPEN,
  DML_TEST_GET,
  DML_TEST_PUT,
  DML_TEST_STAT,
  DML_TEST_COMMIT
} dml_test_fault;

/* One-shot failure on the nth matching call. State exists only in the test binary. */
void dml_test_fail(dml_test_fault fault, size_t nth, int code);
void dml_test_reset(void);
size_t dml_test_failures(void);
/* Simulate a content-hash collision; do not claim a real XXH3 collision. */
void dml_test_hash_collision(int enabled);

#endif
