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


def test_daggerml_version_uses_core_module() -> None:
  import daggerml
  assert daggerml.version() == "0.1.0"
  assert Path(daggerml._core.__file__).resolve().parent == ROOT / "build/check"


def test_cli_native_forwarding(monkeypatch) -> None:
  import daggerml_cli.main as cli_main
  import daggerml_cli as cli_pkg
  assert cli_pkg.__all__ == ["main"]
  calls = []
  monkeypatch.setattr(cli_main.subprocess, "run", lambda args, **kwargs:
                      calls.append(args) or types.SimpleNamespace(returncode=2))
  monkeypatch.setattr(sys, "argv", ["dml", "--version"])
  assert cli_main.main() == 2
  assert calls[0][1:] == ["--version"]
  assert Path(calls[0][0]).name in ("dml", "dml.exe")
  assert Path(calls[0][0]).parent.name == "_bin"


def test_cli_forwarding_failure_and_signal(monkeypatch, capsys) -> None:
  import daggerml_cli.main as cli_main
  def missing(*args, **kwargs):
    raise FileNotFoundError("missing native executable")
  monkeypatch.setattr(cli_main.subprocess, "run", missing)
  assert cli_main.main() == 1
  assert "cannot run bundled" in capsys.readouterr().err
  monkeypatch.setattr(cli_main.subprocess, "run", lambda *args, **kwargs:
                      types.SimpleNamespace(returncode=-15))
  assert cli_main.main() == 143



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
    import daggerml_cli.main as cli_main
    monkeypatch.setattr(cli_main.subprocess, "run", lambda *args, **kwargs:
                        types.SimpleNamespace(returncode=2))
    sys.modules.pop("daggerml_cli.main", None)
    monkeypatch.setattr(sys, "argv", ["dml"])
    with pytest.raises(SystemExit) as exc:
      runpy.run_module("daggerml_cli.main", run_name="__main__")
  finally:
    sys.path.pop(0)

  assert exc.value.code == 2
  assert capsys.readouterr().out == ""


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
