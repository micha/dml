# Records and datums

Status: implemented datum codec and record identity, record format 1.

## Authority boundary

This document owns the implemented datum kinds, packed encoding, canonicalization,
record hashing, value-buffer ownership and error representation in this as-built
specification. For persistence, reference validation and transaction ownership, see
[repository.md](repository.md). For implementation status, see [README.md](README.md).

Normative sections describe current code. No computational identity mask or general
node identity API is implied by the datum ID API.

## Datum model

A datum MUST be one of these kinds:

| Kind | Value / payload |
| --- | --- |
| NULL | Empty payload |
| BOOL | One byte, 0 or 1 |
| I64 | Eight-byte signed integer representation |
| F64 | Eight-byte IEEE-754 binary64 |
| BYTES | Uninterpreted bytes |
| STRING | UTF-8 normalized to NFC |
| URI | Canonical absolute URI text |
| LIST | Ordered datum-ID sequence; duplicates allowed |
| SET | Sorted unique datum IDs |
| MAP | Sorted unique key-datum-ID / value-datum-ID pairs |

Composite values reference datum IDs, not arbitrary node or object IDs. Codec
validation checks structure; repository validation checks that those references
resolve. See [repository.md](repository.md#writes-and-reference-validation).

LIST order MUST be preserved. The encoder sorts SET and MAP entries; duplicate SET
items or MAP keys MUST be rejected, not silently removed. MAP keys may be any datum
kind; they are not restricted to string names.

## Packed representation

Integer fields MUST use little-endian encoding, without native C structure padding.

The record envelope is 20 bytes:

| Offset | Field | Width |
| --- | --- | --- |
| 0 | Magic `0x314c4d44` | u32 |
| 4 | Record format version, currently 1 | u16 |
| 6 | Record type; datum is 2, metadata is 1 | u16 |
| 8 | Total record length | u32 |
| 12 | Reserved flags, zero | u32 |
| 16 | Checksum, zero | u32 |

The datum prefix extends the envelope to 40 bytes:

| Offset | Field | Width |
| --- | --- | --- |
| 20 | Datum kind, 1 through 10 in table order above | u32 |
| 24 | Payload length | u64 |
| 32 | Payload offset, exactly 40 | u64 |

The payload MUST occupy the complete remainder of the record. Gaps, trailing bytes,
unsupported versions, nonzero reserved envelope fields and inconsistent lengths
MUST be rejected.

Collections begin with a u32 count followed by 16-byte IDs (LIST/SET) or 32-byte
key/value ID pairs (MAP). SET ordering and MAP-key ordering use lexicographic ID
bytes. IDs in stored SETs and MAP keys MUST be strictly increasing.

`dml_record_validate()` currently supports metadata and datums only. Recognized
record-type constants do not confer validation support for other object classes.
Repository metadata uses the envelope plus a u32 schema version, currently 1.

## Text, numbers and URIs

- The STRING encoder normalizes valid UTF-8 to NFC. Validation of an already packed
  STRING MUST reject non-NFC text rather than silently changing its record.
- F64 encoding normalizes negative zero to positive zero and all NaNs to bits
  `0x7ff8000000000000`. Packed validation MUST reject noncanonical forms.
- URI input MUST be absolute RFC 3986 syntax, ASCII, free of NUL and not use the
  reserved `dml` scheme. Raw non-ASCII input and relative references are rejected.
- `dml_uri_canonicalize()` provides canonicalization. It lowercases scheme/host,
  normalizes percent escapes and hierarchical dot segments, while preserving
  significant delimiters, query order, fragments and explicit ports. It does not
  infer scheme-specific equivalence such as default-port removal.
- The URI datum encoder requires input already in that canonical form; it MUST
  reject an input changed by canonicalization. This differs from STRING encoding.

URI equality concerns the recorded reference, not captured external bytes or proof
of external availability.

## Record identity

`dml_datum_id()` validates a datum record and hashes a copy with the envelope's
magic, total-length and checksum fields zeroed. Record type, format version, datum
kind and payload still contribute. The algorithm is unseeded XXH3-128; the result
is 16 canonical bytes, high 64 bits followed by low 64 bits, each big-endian.

Text formatting uses 32 lowercase hex characters. Parsing MUST reject other lengths
and uppercase/nonhex text.

This describes the current full-record hashing domain. Header-field zeroing is an
encoding rule, not a researcher-controlled identity mask. Hashes do not authenticate
writers, establish scientific validity or prove complete environment capture.

## C API ownership

Public declarations are in [record.h](../../include/dml/record.h).

- `dml_datum_encode()`, `dml_uri_canonicalize()` and repository datum reads return
  owned `dml_buffer` allocations. The caller MUST release them with
  `dml_buffer_free()`.
- Output buffers MUST initially be empty. `dml_buffer_free()` is null-safe and
  clears the buffer.
- `dml_datum_decode()` produces a borrowed view. The caller MUST keep the original
  packed bytes alive and unchanged while using it or its element accessors.

## Errors

The API returns `dml_status`. Optional caller-owned `dml_error` records contain a
status, native code and a fixed 128-byte detail field; they require no error-path
allocation. The public status enumeration is in [error.h](../../include/dml/error.h).

Codec failures distinguish invalid header, bounds, kind, payload and UTF-8, plus
argument and allocation failures. Where record validation uses structured details,
they have the form `record_type=<type>;detail=<reason>`; API argument errors need
not use that form. Unknown general record types report an unsupported-type error.

## Implementation evidence

- [record.c](../../src/record.c): encoding, decoding and validation.
- [object_id.c](../../src/object_id.c): hashing and ID text conversion.
- [text.c](../../src/text.c) and [uri.c](../../src/uri.c): normalization boundaries.
- [C record tests](../../tests/c/test_record.c) and
  [failure tests](../../tests/c/test_record_failure.c).
- [Native-driver property tests and golden vectors](../../tests/python/test_records_hypothesis.py).

These links identify evidence; this documentation pass did not rerun the suite.
