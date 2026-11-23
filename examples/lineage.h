#ifndef DML_EXAMPLE_LINEAGE_H
#define DML_EXAMPLE_LINEAGE_H

#include <stdio.h>
#include <string.h>

#include <dml/dml.h>

/* Application convention, not a DML codec or execution API. */
typedef struct {
  dml_object_id commit;
  dml_object_id datum;
  int64_t value;
} lineage_input;

typedef struct {
  dml_object_id output_datum, output_node, implementation_datum, implementation_node;
  dml_object_id dag, tree, commit;
  bool attempted_commit;
  dml_status completion;
} lineage_candidate;

typedef struct {
  dml_object_id commit, output_datum, implementation_datum;
  lineage_input input;
  int64_t output;
  dml_buffer implementation_record;
  dml_bytes implementation; /* Borrows implementation_record. */
} lineage_observation;

typedef dml_status (*lineage_compute)(int64_t input, int64_t *output);

static dml_bytes lineage_name(const char *text) {
  return (dml_bytes){(const uint8_t *)text, strlen(text)};
}

static bool lineage_equal(dml_bytes left, dml_bytes right) {
  return left.len == right.len && (left.len == 0 || memcmp(left.data, right.data, left.len) == 0);
}

static dml_status lineage_error(dml_status status, const char *detail, dml_error *error) {
  if (error != NULL) {
    dml_error_clear(error);
    error->code = status;
    snprintf(error->detail, sizeof(error->detail), "%s", detail);
  }
  return status;
}

static dml_status lineage_get_object(dml_txn *txn, dml_record_type type, const dml_object_id *id,
                                     dml_buffer *packed, dml_object_view *view, dml_error *error) {
  dml_status status = dml_txn_get_object(txn, type, id, packed, error);
  return status == DML_OK ? dml_object_decode(packed->data, packed->len, view, error) : status;
}

static dml_status lineage_find_dag(dml_txn *txn, const dml_object_id *tree, dml_bytes name,
                                   bool single_entry, dml_object_id *dag, dml_error *error) {
  dml_buffer packed = {0};
  dml_object_view view;
  dml_status status = lineage_get_object(txn, DML_REC_TREE, tree, &packed, &view, error);
  if (status == DML_OK && single_entry && view.count != 1) {
    status = lineage_error(DML_INVALID_PAYLOAD, "expected one lineage tree entry", error);
  }
  for (size_t i = 0; status == DML_OK && i < view.count; ++i) {
    dml_tree_entry entry;
    status = dml_object_view_entry(&view, i, &entry, error);
    if (status == DML_OK && lineage_equal(entry.name, name)) {
      *dag = entry.dag;
      dml_buffer_free(&packed);
      return DML_OK;
    }
  }
  dml_buffer_free(&packed);
  return status == DML_OK ? lineage_error(DML_NOT_FOUND, "tree entry is absent", error) : status;
}

static dml_status lineage_get_literal(dml_txn *txn, const dml_object_id *node,
                                      dml_datum_kind kind, dml_object_id *datum,
                                      dml_buffer *packed, dml_datum_view *view, dml_error *error) {
  dml_buffer literal = {0};
  dml_object_view object;
  dml_status status = lineage_get_object(txn, DML_REC_NODE, node, &literal, &object, error);
  if (status == DML_OK && object.node_kind != DML_NODE_LITERAL) {
    status = lineage_error(DML_INVALID_KIND, "expected a literal node", error);
  }
  if (status == DML_OK) status = dml_txn_get_datum(txn, &object.reference, packed, error);
  if (status == DML_OK) status = dml_datum_decode(packed->data, packed->len, view, error);
  if (status == DML_OK && view->kind != kind) {
    status = lineage_error(DML_INVALID_KIND, "unexpected lineage datum kind", error);
  }
  if (status == DML_OK) *datum = object.reference;
  dml_buffer_free(&literal);
  return status;
}

static dml_status lineage_read_number(dml_txn *txn, const dml_object_id *node,
                                      dml_object_id *datum, int64_t *value, dml_error *error) {
  dml_buffer packed = {0};
  dml_datum_view view;
  dml_status status = lineage_get_literal(txn, node, DML_DATUM_I64, datum, &packed, &view, error);
  if (status == DML_OK) {
    uint64_t bits = 0;
    for (size_t i = 0; i < sizeof(bits); ++i) bits |= (uint64_t)view.payload[i] << (8 * i);
    *value = bits <= INT64_MAX ? (int64_t)bits : -1 - (int64_t)(UINT64_MAX - bits);
  }
  dml_buffer_free(&packed);
  return status;
}

static dml_status lineage_read_input(dml_txn *txn, const dml_object_id *commit,
                                     dml_bytes entry, dml_bytes binding, lineage_input *out,
                                     dml_error *error) {
  dml_buffer packed = {0};
  dml_object_view revision;
  dml_object_id dag, node;
  dml_status status = lineage_get_object(txn, DML_REC_COMMIT, commit, &packed, &revision, error);
  if (status == DML_OK) status = lineage_find_dag(txn, &revision.reference, entry, false, &dag, error);
  if (status == DML_OK) status = dml_txn_lookup_node(txn, &dag, binding, &node, error);
  if (status == DML_OK) status = lineage_read_number(txn, &node, &out->datum, &out->value, error);
  if (status == DML_OK) out->commit = *commit;
  dml_buffer_free(&packed);
  return status;
}

static dml_status lineage_put_object(dml_txn *txn, const dml_object_input *input,
                                     dml_object_id *id, dml_error *error) {
  dml_buffer packed = {0};
  dml_status status = dml_object_encode(input, &packed, error);
  if (status == DML_OK) status = dml_txn_put_object(txn, input->type, packed.data, packed.len, id, error);
  dml_buffer_free(&packed);
  return status;
}

static dml_status lineage_put_literal(dml_txn *txn, const dml_datum_input *input,
                                      dml_object_id *datum, dml_object_id *node, dml_error *error) {
  dml_buffer packed = {0};
  dml_status status = dml_datum_encode(input, &packed, error);
  if (status == DML_OK) status = dml_txn_put_datum(txn, packed.data, packed.len, datum, error);
  dml_buffer_free(&packed);
  if (status != DML_OK) return status;
  const dml_object_input literal = {.type = DML_REC_NODE, .value.node = {DML_NODE_LITERAL, *datum}};
  return lineage_put_object(txn, &literal, node, error);
}

static bool lineage_identity_valid(dml_bytes identity) {
  if (identity.len == 0 || identity.data == NULL) return false;
  for (size_t i = 0; i < identity.len; ++i) {
    if (identity.data[i] < 0x21 || identity.data[i] > 0x7e) return false;
  }
  return true;
}

static dml_status lineage_write_candidate(dml_txn *txn, const lineage_input *input, int64_t output,
                                          dml_bytes identity, lineage_candidate *out, dml_error *error) {
  const dml_datum_input number = {.kind = DML_DATUM_I64, .value.i64 = output};
  const dml_datum_input implementation = {.kind = DML_DATUM_STRING, .value.bytes = identity};
  dml_status status = lineage_put_literal(txn, &number, &out->output_datum, &out->output_node, error);
  if (status != DML_OK) return status;
  status = lineage_put_literal(txn, &implementation, &out->implementation_datum,
                               &out->implementation_node, error);
  if (status != DML_OK) return status;
  const dml_dag_binding bindings[] = {
    {lineage_name("implementation"), out->implementation_node},
    {lineage_name("output"), out->output_node},
  };
  const dml_object_input dag = {.type = DML_REC_DAG, .value.dag = {out->output_node, bindings, 2}};
  status = lineage_put_object(txn, &dag, &out->dag, error);
  if (status != DML_OK) return status;
  const dml_tree_entry entry = {lineage_name("lineage-v1"), out->dag};
  const dml_object_input tree = {.type = DML_REC_TREE, .value.tree = {&entry, 1}};
  status = lineage_put_object(txn, &tree, &out->tree, error);
  if (status != DML_OK) return status;
  const dml_object_input commit = {.type = DML_REC_COMMIT, .value.commit = {out->tree, {&input->commit, 1}}};
  return lineage_put_object(txn, &commit, &out->commit, error);
}

/* The caller has already selected and read the immutable input. Do not resolve
 * incoming again. Compute before acquiring the write transaction. On success,
 * also check out->completion for the final storage transaction status. */
static dml_status lineage_record(dml_repo *repo, const lineage_input *input, dml_bytes identity,
                                 lineage_compute compute, lineage_candidate *out, dml_error *error) {
  if (!lineage_identity_valid(identity)) {
    return lineage_error(DML_INVALID_ARGUMENT, "expected a nonempty ASCII implementation ID", error);
  }
  int64_t output;
  dml_status status = compute(input->value, &output);
  if (status != DML_OK) return lineage_error(status, "caller computation failed", error);

  dml_txn *txn = NULL;
  status = dml_txn_begin(repo, DML_TXN_WRITE, &txn, error);
  if (status == DML_OK) status = lineage_write_candidate(txn, input, output, identity, out, error);
  if (status == DML_OK) {
    status = dml_txn_ref_create(txn, lineage_name("result-pin"), &out->commit, error);
    out->attempted_commit = true;
    /* Preserve the failure that poisoned the transaction (e.g. a duplicate pin). */
    out->completion = dml_txn_commit(&txn, status == DML_OK ? error : NULL);
  }
  dml_txn_abort(&txn);
  return status;
}

static dml_status lineage_read_result(dml_txn *txn, const dml_object_id *tree,
                                      lineage_observation *out, dml_error *error) {
  dml_object_id dag;
  dml_status status = lineage_find_dag(txn, tree, lineage_name("lineage-v1"), true, &dag, error);
  dml_buffer packed = {0};
  dml_object_view graph;
  dml_dag_binding implementation, output;
  if (status == DML_OK) status = lineage_get_object(txn, DML_REC_DAG, &dag, &packed, &graph, error);
  if (status == DML_OK && graph.count != 2) {
    status = lineage_error(DML_INVALID_PAYLOAD, "expected two lineage bindings", error);
  }
  /* Packed bindings are sorted by name. Validate names before freeing the view. */
  if (status == DML_OK) status = dml_object_view_binding(&graph, 0, &implementation, error);
  if (status == DML_OK) status = dml_object_view_binding(&graph, 1, &output, error);
  if (status == DML_OK && (!lineage_equal(implementation.name, lineage_name("implementation")) ||
                           !lineage_equal(output.name, lineage_name("output")) ||
                           memcmp(output.node.bytes, graph.reference.bytes, sizeof(output.node.bytes)) != 0)) {
    status = lineage_error(DML_INVALID_PAYLOAD, "expected implementation and rooted output bindings", error);
  }
  dml_buffer_free(&packed);
  if (status == DML_OK) status = lineage_read_number(txn, &output.node, &out->output_datum, &out->output, error);
  if (status != DML_OK) return status;
  dml_datum_view identity;
  status = lineage_get_literal(txn, &implementation.node, DML_DATUM_STRING, &out->implementation_datum,
                               &out->implementation_record, &identity, error);
  if (status != DML_OK) return status;
  out->implementation = (dml_bytes){identity.payload, identity.payload_len};
  return lineage_identity_valid(out->implementation) ? DML_OK :
    lineage_error(DML_INVALID_PAYLOAD, "lineage implementation ID is not nonempty ASCII", error);
}

/* The caller supplies the exact commit and input path. Reading is not execution. */
static dml_status lineage_inspect(dml_txn *txn, const dml_object_id *commit, dml_bytes entry,
                                  dml_bytes binding, lineage_observation *out, dml_error *error) {
  lineage_observation observed = {.commit = *commit};
  dml_buffer packed = {0};
  dml_object_view revision;
  dml_object_id parent;
  dml_status status = lineage_get_object(txn, DML_REC_COMMIT, commit, &packed, &revision, error);
  if (status == DML_OK && revision.count != 1) {
    status = lineage_error(DML_INVALID_PAYLOAD, "expected exactly one lineage input commit", error);
  }
  if (status == DML_OK) status = dml_object_view_parent(&revision, 0, &parent, error);
  if (status == DML_OK) status = lineage_read_input(txn, &parent, entry, binding, &observed.input, error);
  if (status == DML_OK) status = lineage_read_result(txn, &revision.reference, &observed, error);
  dml_buffer_free(&packed);
  if (status == DML_OK) *out = observed;
  else dml_buffer_free(&observed.implementation_record);
  return status;
}

typedef struct {
  dml_object_id actual;
  dml_status get, update, completion;
  bool attempted_update;
} lineage_publication;

/* Caller-side conditional update; the supplied write transaction is consumed. */
static dml_status lineage_publish_expected(dml_txn **txn, dml_bytes ref,
                                           const dml_object_id *expected, const dml_object_id *target,
                                           lineage_publication *out, dml_error *error) {
  *out = (lineage_publication){0};
  out->get = dml_txn_ref_get(*txn, ref, &out->actual, error);
  if (out->get != DML_OK || memcmp(out->actual.bytes, expected->bytes, sizeof(expected->bytes)) != 0) {
    dml_txn_abort(txn);
    return out->get != DML_OK ? out->get :
      lineage_error(DML_INVALID_STATE, "ref no longer points to the expected commit", error);
  }
  out->attempted_update = true;
  out->update = dml_txn_ref_update(*txn, ref, target, error);
  out->completion = dml_txn_commit(txn, out->update == DML_OK ? error : NULL);
  return out->update == DML_OK ? out->completion : out->update;
}

#endif
