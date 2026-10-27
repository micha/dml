import importlib
import os
from pathlib import Path
import shutil
import sys
import types

import pytest

import daggerml_cli.main as cli_main

ROOT = Path(__file__).resolve().parents[2]
BIN = Path(os.environ.get("DML_BIN", ROOT / "build/check/dml")).resolve()


def test_forwarding_real_binary_path_spaces_and_no_path_recursion(tmp_path, monkeypatch, capfd):
    package = tmp_path / "package with spaces"
    binary_dir = package / "_bin"
    binary_dir.mkdir(parents=True)
    native = binary_dir / ("dml.exe" if os.name == "nt" else "dml")
    shutil.copyfile(BIN, native); native.chmod(0o755)
    monkeypatch.setattr(cli_main.importlib, "import_module", lambda _: types.SimpleNamespace(__file__=str(package / "__init__.py")))
    monkeypatch.setattr(sys, "argv", ["dml", "--version"])
    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))
    assert cli_main.main() == 0
    assert capfd.readouterr().out.strip() == "0.1.0"
    native.write_bytes(b"not an executable\n")
    assert cli_main.main() == 1
    assert "cannot run bundled" in capfd.readouterr().err
