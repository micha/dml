#ifndef DML_ENCODING_H
#define DML_ENCODING_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

bool dml_size_add(size_t left, size_t right, size_t *out);
bool dml_size_mul(size_t left, size_t right, size_t *out);
uint16_t dml_read_u16_le(const uint8_t *data);
uint32_t dml_read_u32_le(const uint8_t *data);
uint64_t dml_read_u64_le(const uint8_t *data);
void dml_write_u16_le(uint8_t *data, uint16_t value);
void dml_write_u32_le(uint8_t *data, uint32_t value);
void dml_write_u64_le(uint8_t *data, uint64_t value);

#endif
