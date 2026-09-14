#include "encoding.h"

#include <stdint.h>

bool dml_size_add(size_t left, size_t right, size_t *out) {
  if (right > SIZE_MAX - left) {
    return false;
  }
  *out = left + right;
  return true;
}

bool dml_size_mul(size_t left, size_t right, size_t *out) {
  if (left != 0 && right > SIZE_MAX / left) {
    return false;
  }
  *out = left * right;
  return true;
}

uint16_t dml_read_u16_le(const uint8_t *data) {
  return (uint16_t)data[0] | ((uint16_t)data[1] << 8);
}

uint32_t dml_read_u32_le(const uint8_t *data) {
  return (uint32_t)data[0] | ((uint32_t)data[1] << 8) |
         ((uint32_t)data[2] << 16) | ((uint32_t)data[3] << 24);
}

uint64_t dml_read_u64_le(const uint8_t *data) {
  uint64_t value = 0;
  for (unsigned int i = 0; i < 8; i++) {
    value |= (uint64_t)data[i] << (i * 8);
  }
  return value;
}

void dml_write_u16_le(uint8_t *data, uint16_t value) {
  data[0] = (uint8_t)value;
  data[1] = (uint8_t)(value >> 8);
}

void dml_write_u32_le(uint8_t *data, uint32_t value) {
  for (unsigned int i = 0; i < 4; i++) {
    data[i] = (uint8_t)(value >> (i * 8));
  }
}

void dml_write_u64_le(uint8_t *data, uint64_t value) {
  for (unsigned int i = 0; i < 8; i++) {
    data[i] = (uint8_t)(value >> (i * 8));
  }
}
