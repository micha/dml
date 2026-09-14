#ifndef DML_RECORD_INTERNAL_H
#define DML_RECORD_INTERNAL_H

#include <stddef.h>
#include <stdint.h>

#include "dml/record.h"

#define DML_HEADER_SIZE 20
#define DML_DATUM_PREFIX_SIZE 40
#define DML_META_SIZE 24

dml_status dml_validate_envelope(const uint8_t *data, size_t len,
                                 uint16_t *type, dml_error *error);
void dml_encode_meta(uint8_t out[DML_META_SIZE]);

#endif
