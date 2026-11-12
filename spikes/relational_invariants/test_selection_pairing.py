"""Broader authority negatives, unchanged existing assertion bodies/HOST fixtures."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_pairing import trace, double, selection, expected_file, exchange_runtime, producer, paired
import test_reuse_selection_records as records


@pytest.mark.parametrize('role,mode', [
    ('S','missing'), ('S','extra'), ('S','root'), ('S','role'), ('S','literal-node'),
    ('S','subdag-node'), ('S','datum-kind'), ('S','F-short'), ('S','F-long'),
    ('V','missing'), ('V','extra'), ('V','root'), ('V','subdag-node'), ('V','datum-kind'), ('V','oversized'),
])
def test_existing_selection_validation_shapes(double, selection, trace, request, role, mode):
    paired(trace, request, records.test_native_exact_fields_roots_node_datum_and_completion_bounds_before_Q,
           double, selection, role, mode)


@pytest.mark.parametrize('field', ['attempt','result','request','completion','expected','job','observation'])
def test_existing_partial_matching_producer_swap(double, selection, trace, request, field):
    paired(trace, request, records.test_typed_complete_partial_swap_to_another_matching_success_rejects,
           double, selection, field)


@pytest.mark.parametrize('field', ['intent','binding','inputs'])
def test_existing_native_claim_swap(double, selection, trace, request, field):
    paired(trace, request, records.test_complete_valid_S_computation_claim_swap_rejected_against_public_fields,
           double, selection, field)


@pytest.mark.parametrize('field,value', [
    ('token','0'*32), ('commit','0'*32), ('selected_commit','0'*32), ('pre_dispatch','0'*32),
    ('request_id','q-'+'0'*32), ('attempt_id','a-'+'0'*32), ('phase','initial'),
])
def test_existing_receipt_claim_swap(double, selection, trace, request, field, value):
    paired(trace, request, records.test_partial_stored_V_receipt_claim_swap_public_inspector_rejects,
           double, selection, field, value)
