"""ONE shared CONTROL store/portable seed; no E/P/C or process activation in focus."""

import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from incremental.driver import verify_pins
from incremental.records import Store
from incremental.stages import load_dml


@pytest.fixture(autouse=True)
def no_actors(monkeypatch, request):
    if Path(__file__).resolve().parent not in request.node.path.resolve().parents:
        return  # Explicit plugin must not change any ORIGINAL spike assertion execution.
    def forbidden(*args, **kwargs):
        raise AssertionError('focused controller controls cannot launch actors/network')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


@pytest.fixture(scope='session')
def pins():
    return verify_pins(Path(os.environ['INCREMENTAL_PINS']))


@pytest.fixture(scope='session')
def control(pins, tmp_path_factory):
    directory = tmp_path_factory.mktemp('incremental-CONTROL')
    artifacts = directory / 'artifacts'
    artifacts.mkdir()
    dml = load_dml(Path(pins['root']) / 'controller/daggerml', name='incremental_focus_dml')
    store = Store(dml, directory / 'controller.dml', artifacts, 'CONTROL/focused-v1', create=True)
    return store
