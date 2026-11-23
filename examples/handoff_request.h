#ifndef DML_HANDOFF_REQUEST_H
#define DML_HANDOFF_REQUEST_H

#include "transfer_example.h"

/* Application convention over ordinary commits, not a new DML record type. */
typedef struct {
  const char *id;
  lineage_compute compute;
} handoff_operation;

typedef struct {
  const handoff_operation *operation;
  lineage_input input;
} handoff_request;

static dml_status subtract_one(int64_t input, int64_t *output) {
  if (input == INT64_MIN) return DML_INVALID_BOUNDS;
  *output = input - 1;
  return DML_OK;
}

static const handoff_operation *find_operation(dml_bytes id) {
  static const handoff_operation operations[] = {
    {"example.add-one@1", add_one},
    {"example.subtract-one@1", subtract_one},
  };
  for (size_t i = 0; i < sizeof(operations) / sizeof(*operations); ++i) {
    if (lineage_equal(id, lineage_name(operations[i].id))) return &operations[i];
  }
  return NULL;
}

/* These names are in packed lexicographic order. */
enum { REQUEST_BINDING, REQUEST_ENTRY, REQUEST_OPERATION, REQUEST_FIELDS };
static const char *const request_fields[REQUEST_FIELDS] = {"input-binding", "input-entry", "operation"};

static dml_status read_selected_input(dml_txn *txn, const dml_object_id *snapshot,
                                      dml_bytes entry, dml_bytes binding, lineage_input *out,
                                      dml_error *error) {
  dml_status status = dml_name_validate(entry, error);
  if (status == DML_OK) status = dml_name_validate(binding, error);
  if (status != DML_OK) return status;
  return lineage_read_input(txn, snapshot, entry, binding, out, error);
}

static dml_status write_request(dml_txn *txn, const dml_object_id *input,
                                const handoff_operation *operation, dml_bytes entry, dml_bytes binding,
                                dml_object_id *out, dml_error *error) {
  const dml_bytes fields[REQUEST_FIELDS] = {binding, entry, lineage_name(operation->id)};
  dml_dag_binding bindings[REQUEST_FIELDS];
  for (size_t i = 0; i < REQUEST_FIELDS; ++i) {
    const dml_datum_input field = {.kind = DML_DATUM_STRING, .value.bytes = fields[i]};
    dml_object_id datum;
    bindings[i].name = lineage_name(request_fields[i]);
    dml_status status = lineage_put_literal(txn, &field, &datum, &bindings[i].node, error);
    if (status != DML_OK) return status;
  }
  const dml_object_input graph = {
    .type = DML_REC_DAG, .value.dag = {bindings[REQUEST_OPERATION].node, bindings, REQUEST_FIELDS}
  };
  dml_object_id dag, tree;
  dml_status status = lineage_put_object(txn, &graph, &dag, error);
  if (status != DML_OK) return status;
  const dml_tree_entry request = {lineage_name("request-v1"), dag};
  const dml_object_input snapshot = {.type = DML_REC_TREE, .value.tree = {&request, 1}};
  status = lineage_put_object(txn, &snapshot, &tree, error);
  if (status != DML_OK) return status;
  const dml_object_input commit = {.type = DML_REC_COMMIT, .value.commit = {tree, {input, 1}}};
  return lineage_put_object(txn, &commit, out, error);
}

static dml_status read_request_fields(dml_txn *txn, const dml_object_id *tree,
                                       dml_buffer records[REQUEST_FIELDS], dml_bytes fields[REQUEST_FIELDS],
                                       dml_error *error) {
  dml_buffer packed = {0};
  dml_object_id dag;
  dml_object_view graph;
  dml_status status = lineage_find_dag(txn, tree, lineage_name("request-v1"), true, &dag, error);
  if (status == DML_OK) status = lineage_get_object(txn, DML_REC_DAG, &dag, &packed, &graph, error);
  if (status == DML_OK && graph.count != REQUEST_FIELDS) {
    status = lineage_error(DML_INVALID_PAYLOAD, "expected three request bindings", error);
  }
  for (size_t i = 0; status == DML_OK && i < REQUEST_FIELDS; ++i) {
    dml_dag_binding binding;
    status = dml_object_view_binding(&graph, i, &binding, error);
    if (status != DML_OK) break;
    if (!lineage_equal(binding.name, lineage_name(request_fields[i])) ||
        (i == REQUEST_OPERATION && !same_id(&binding.node, &graph.reference))) {
      status = lineage_error(DML_INVALID_PAYLOAD, "expected input selectors and rooted operation", error);
      break;
    }
    dml_object_id datum;
    dml_datum_view view;
    status = lineage_get_literal(txn, &binding.node, DML_DATUM_STRING, &datum, &records[i], &view, error);
    if (status == DML_OK) fields[i] = (dml_bytes){view.payload, view.payload_len};
  }
  dml_buffer_free(&packed);
  return status;
}

static dml_status read_request(dml_txn *txn, const dml_object_id *id, handoff_request *out,
                               dml_error *error) {
  dml_object_id tree, parent;
  dml_status status = lineage_read_revision(txn, id, &tree, &parent, error);
  if (status != DML_OK) return status;

  dml_buffer records[REQUEST_FIELDS] = {0};
  dml_bytes fields[REQUEST_FIELDS];
  handoff_request request;
  status = read_request_fields(txn, &tree, records, fields, error);
  if (status == DML_OK) {
    request.operation = find_operation(fields[REQUEST_OPERATION]);
    if (request.operation == NULL) {
      status = lineage_error(DML_INVALID_PAYLOAD, "unsupported request operation", error);
    }
  }
  if (status == DML_OK) {
    status = read_selected_input(txn, &parent, fields[REQUEST_ENTRY], fields[REQUEST_BINDING],
                                 &request.input, error);
  }
  for (size_t i = 0; i < REQUEST_FIELDS; ++i) dml_buffer_free(&records[i]);
  if (status == DML_OK) *out = request;
  return status;
}

#endif
