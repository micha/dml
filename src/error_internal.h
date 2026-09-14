#ifndef DML_ERROR_INTERNAL_H
#define DML_ERROR_INTERNAL_H

#include "dml/error.h"

dml_status dml_set_error(dml_error *error, dml_status status, int native_code,
                         const char *detail);

#endif
