"""Default-safe entrypoint/blocker checks; never launch the installed computation story."""

import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

from test_exchange import ROOT


def load_controller():
    spec = importlib.util.spec_from_file_location("composed_controller_test", ROOT / "tests/composed_nodes/installed_story.py")
    module = importlib.util.module_from_spec(spec)
    saved = list(sys.path)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = saved
    return module


def test_controller_requires_explicit_fresh_root_and_main_does_not_implicitly_launch(monkeypatch, capsys):
    controller = load_controller()
    monkeypatch.setattr(controller, "run", lambda root: pytest.fail("must not implicitly launch"))
    with pytest.raises(ValueError, match="explicit fresh"):
        controller.main(["run"])
    with pytest.raises(SystemExit):
        controller.main(["unknown"])
    monkeypatch.setattr(controller, "metadata_controls", lambda: ([True], {"controlled": True}))
    assert controller.main(["metadata-controls"]) == 0
    assert '"controlled": true' in capsys.readouterr().out


def test_offline_blocker_FIRST_actual_four_rejections_NO_DML_import():
    result = subprocess.run([sys.executable, "-I", str(ROOT / "tests/composed_nodes/offline_read.py"),
                             "controls", "unused-root", "unused-helper-dir"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert all('"' + name + '"' in result.stdout for name in ("spawn", "http", "urllib-transport", "connect"))
    assert '"nonexecuting": true' in result.stdout


def test_offline_invalid_mode_rejects_before_loading_helpers():
    result = subprocess.run([sys.executable, "-I", str(ROOT / "tests/composed_nodes/offline_read.py"), "wrong"],
                            capture_output=True, text=True)
    assert result.returncode == 1 and "expected controls|read" in result.stderr


def test_mutation_controller_requires_NEW_explicit_output_no_default_invocation():
    result = subprocess.run([sys.executable, "-I", str(ROOT / "tests/composed_nodes/mutations.py")],
                            capture_output=True, text=True)
    assert result.returncode == 1 and "explicit NEW owned" in result.stderr
