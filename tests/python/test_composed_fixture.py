"""Default-safe controller census/intent checks. NO Docker/service startup."""

import importlib.util
from pathlib import Path
import sys

import pytest

from test_exchange import ROOT


def controller():
    # Fixture support only imported; main/start never invoked.
    path = str(ROOT / "tests/floci")
    original = list(sys.path)
    names = (
        "fixture",
        "integration",
        "retained_integration",
        "loss_integration",
        "composed_app",
    )
    modules = {name: sys.modules.get(name) for name in names}
    # Floci and SSH controllers deliberately use script-local import names. Keep
    # test-only imports scoped; never poison later SSH imports with Floci aliases.
    for name in names:
        sys.modules.pop(name, None)
    try:
        sys.path.insert(0, path)
        spec = importlib.util.spec_from_file_location(
            "composed_controller", ROOT / "tests/floci/composed_integration.py"
        )
        result = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(result)
        return result
    finally:
        sys.path[:] = original
        for name, previous in modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


@pytest.mark.parametrize(
    "argv",
    [
        ["/opt/dml/bin/python", "-m", "daggerml.exchange_worker", "/tmp/workspace"],
        ["/opt/dml/bin/python", "/tmp/dml-local-owned/entry.py", "/tmp/worker.dml"],
    ],
)
def test_real_nul_argv_computation_is_not_missed(argv):
    row = "\0".join(argv) + "\0"
    assert controller().computational_cmdlines([row]) == [row]


def test_census_distinguishes_innocent_component_paths_not_escape_strings():
    rows = [
        "python\0/opt/fixture/retain.py\0",
        "python\0-m\0unrelated.daggerml.exchange_worker\0",
        "python\0/tmp/entry.py-not-computation\0",
        "python\0/tmp/daggerml.exchange_worker/data\0",
        "python\\x00-m\\x00daggerml.exchange_worker\\x00",
    ]
    assert controller().computational_cmdlines(rows) == []


def test_private_controller_import_restores_shared_script_aliases():
    names = (
        "fixture",
        "integration",
        "retained_integration",
        "loss_integration",
        "composed_app",
    )
    before = {name: sys.modules.get(name) for name in names}
    path = list(sys.path)
    controller()
    assert {name: sys.modules.get(name) for name in names} == before
    assert sys.path == path
