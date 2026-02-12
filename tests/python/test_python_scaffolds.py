import importlib
import runpy
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _import_from_package_dir(package_root: Path, module_name: str):
  sys.path.insert(0, str(package_root))
  try:
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)
  finally:
    sys.path.pop(0)


def test_daggerml_version_uses_core_module(monkeypatch) -> None:
  package_dir = ROOT / "python" / "daggerml"
  daggerml = _import_from_package_dir(package_dir, "daggerml")

  core_module = types.SimpleNamespace(dml_version=lambda: "0.1.0")
  monkeypatch.setitem(sys.modules, "daggerml._core", core_module)

  assert daggerml.__all__ == ["version"]
  assert daggerml.version() == "0.1.0"


def test_cli_scaffold_entrypoints(monkeypatch, capsys) -> None:
  package_dir = ROOT / "python" / "daggerml-cli"
  cli_main = _import_from_package_dir(package_dir, "daggerml_cli.main")
  cli_pkg = importlib.import_module("daggerml_cli")

  assert cli_pkg.__all__ == ["main"]

  monkeypatch.setattr(sys, "argv", ["dml"])
  assert cli_main.main() == 0
  assert capsys.readouterr().out.strip() == "dml CLI scaffold is installed"

  fake_daggerml = types.SimpleNamespace(version=lambda: "0.1.0")
  monkeypatch.setattr(importlib, "import_module", lambda _: fake_daggerml)
  monkeypatch.setattr(sys, "argv", ["dml", "--version"])
  assert cli_main.main() == 0
  assert capsys.readouterr().out.strip() == "0.1.0"


def test_adapter_scaffold_entrypoints(capsys) -> None:
  package_dir = ROOT / "python" / "adapters" / "example"
  adapter_main = _import_from_package_dir(package_dir, "daggerml_adapter_example.main")
  adapter_pkg = importlib.import_module("daggerml_adapter_example")

  assert adapter_pkg.__all__ == ["adapter_entrypoint", "main"]
  assert adapter_main.adapter_entrypoint() == "example"
  assert adapter_main.main() == 0
  assert capsys.readouterr().out.strip() == "daggerml adapter scaffold: example"


def test_cli_module_main_invocation(monkeypatch, capsys) -> None:
  package_dir = ROOT / "python" / "daggerml-cli"
  sys.path.insert(0, str(package_dir))
  try:
    sys.modules.pop("daggerml_cli.main", None)
    monkeypatch.setattr(sys, "argv", ["dml"])
    with pytest.raises(SystemExit) as exc:
      runpy.run_module("daggerml_cli.main", run_name="__main__")
  finally:
    sys.path.pop(0)

  assert exc.value.code == 0
  assert capsys.readouterr().out.strip() == "dml CLI scaffold is installed"


def test_adapter_module_main_invocation(monkeypatch, capsys) -> None:
  package_dir = ROOT / "python" / "adapters" / "example"
  sys.path.insert(0, str(package_dir))
  try:
    sys.modules.pop("daggerml_adapter_example.main", None)
    monkeypatch.setattr(sys, "argv", ["daggerml-adapter-example"])
    with pytest.raises(SystemExit) as exc:
      runpy.run_module("daggerml_adapter_example.main", run_name="__main__")
  finally:
    sys.path.pop(0)

  assert exc.value.code == 0
  assert capsys.readouterr().out.strip() == "daggerml adapter scaffold: example"
