"""Selected existing assertions plus independent relational counterparts.

Only fixture execution is HOST-substituted; original test-function bodies are called
unchanged. No OS children, original fixture retirement, services or workflow changes.
"""

import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from run import bootstrap
bootstrap()
sys.path.insert(0, str(ROOT / 'tests/python'))

import test_composed_node_calls as composed
import test_intent_scoped_edges as scoped_edges
import test_intent_scoped_reuse as scoped
import test_reuse_selection_records as records
from test_composed_node_calls import initial, upstream, downstream
from test_composed_execution import producer
from test_exchange import exchange_runtime
from test_explicit_reuse import double
from test_implementation_selection import menu
from test_reuse_selection import expected_file
from test_reuse_selection_records import selection
from test_intent_scoped_reuse import indexed

from daggerml import local
from paired_runner import compare
from paired_trace import Trace


@pytest.fixture(autouse=True)
def trace(tmp_path, monkeypatch):
    state = Trace(monkeypatch, tmp_path)
    scratch = tmp_path / 'validation-scratch'
    scratch.mkdir()
    monkeypatch.setattr(tempfile, 'tempdir', str(scratch))
    monkeypatch.setattr(local, '_execute', state.host_execute)
    def forbidden(*args, **kwargs):
        raise AssertionError('paired metadata slice cannot launch OS children or network IO')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    state.scope(monkeypatch, composed.app, 'inspect_composition', 'composition')
    state.scope(monkeypatch, composed.app, '_resolve', 'resolve')
    selection_modules = {id(module): module for module in (composed.app.selection, records.app, scoped.app.selection)}
    for module in selection_modules.values():
        state.scope(monkeypatch, module, '_successful', 'candidate')
        state.scope(monkeypatch, module, 'inspect', 'selection')
        state.scope(monkeypatch, module, 'reuse_selected', 'selection')
        state.transition(monkeypatch, module, 'adopt', 'adopt')
        state.reuse(monkeypatch, module, 'reuse_selected')
    state.transition(monkeypatch, scoped.app, 'remove_entry', 'remove')
    state.transition(monkeypatch, scoped.app, 'select_entry', 'insert')
    state.reuse(monkeypatch, composed.app, 'record_request')
    state.reuse(monkeypatch, scoped.app, 'record_policy_request')
    return state


def paired(trace, request, function, *args, **kwargs):
    trace.begin_body()
    function(*args, **kwargs)  # The unchanged original assertion body, not a transcription.
    trace.end_body()
    result = compare(trace, trace.directory / 'comparison', request.node.nodeid)
    assert result['distinct_scopes'] > 0


@pytest.mark.parametrize('values', [{'a':13,'b':29}, {'a':29,'b':13}], ids=['same-inputs', 'swapped-inputs-equal-result'])
def test_existing_value_hit(downstream, tmp_path, monkeypatch, trace, request, values):
    paired(trace, request, composed.test_full_MAP_value_hit_NEW_requested_chain_OLD_executed_chain_no_job,
           downstream, tmp_path, monkeypatch, values)


def test_existing_value_miss_and_no_auto_adoption(downstream, tmp_path, monkeypatch, trace, request):
    paired(trace, request, composed.test_value_miss_pending_own_Q_and_no_auto_adoption,
           downstream, tmp_path, monkeypatch)


@pytest.mark.parametrize('fault', ['R', 'inner-literal', 'two-parent'])
def test_existing_composition_fault(downstream, tmp_path, monkeypatch, trace, request, fault):
    paired(trace, request, composed.test_composition_actual_parent_slot_S_outerR_same_value_wrong_source_reject,
           downstream, tmp_path, monkeypatch, fault)


@pytest.mark.parametrize('phase', ['initial', 'publication'])
def test_existing_incomplete_attempt(double, expected_file, selection, trace, request, phase):
    paired(trace, request, records.test_nonfinal_packets_never_select_or_adopt,
           double, expected_file, selection, phase)


def test_existing_failure_and_successful_cleanup_failure(double, selection, monkeypatch, trace, request):
    paired(trace, request, records.test_failed_F_evidence_84_and_cleanup_success_policy,
           double, selection, monkeypatch)


def test_existing_adoption_and_sibling_choices(double, selection, trace, request):
    paired(trace, request, records.test_fully_coherent_alternative_selection_and_explicit_adoption_sibling_branches,
           double, selection)


def test_existing_selection_removal_and_reselection(indexed, trace, request):
    paired(trace, request, scoped_edges.test_remove_last_valid_empty_old_proof_no_retarget_no_ban, indexed)


def test_existing_two_attempts_one_request(upstream, tmp_path, monkeypatch, trace, request):
    paired(trace, request, composed.test_two_attempts_ONE_Q_equal_outerR_still_capture_THIS_selected_T,
           upstream, tmp_path, monkeypatch)
