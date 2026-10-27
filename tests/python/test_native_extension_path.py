import importlib.machinery
import importlib.util

import pytest

from native_extension import native_extension_path


@pytest.mark.parametrize("suffixes", [
    [".cp314-mingw_x86_64_ucrt_gnu.pyd", ".pyd"],
    [".cpython-312-x86_64-linux-gnu.so", ".abi3.so", ".so"],
])
def test_extension_selection_ignores_linker_artifacts(tmp_path, monkeypatch, suffixes):
    # Create the decoy first, matching the Windows CI directory order that made
    # the previous glob-based selector return an unimportable linker library.
    (tmp_path / "_core_fault.dll.a").write_bytes(b"linker import library")
    (tmp_path / "_core_fault.lib").write_bytes(b"linker library")
    (tmp_path / "_core_fault.p").mkdir()
    extension = tmp_path / ("_core_fault" + suffixes[-1])
    extension.write_bytes(b"extension placeholder; selection only")
    monkeypatch.setattr(importlib.machinery, "EXTENSION_SUFFIXES", suffixes)
    assert native_extension_path(tmp_path, "_core_fault") == extension


def test_extension_selection_uses_interpreter_suffix_priority(tmp_path, monkeypatch):
    suffixes = [".abi3.so", ".so"]
    for suffix in suffixes:
        (tmp_path / ("_core_fault" + suffix)).write_bytes(b"selection only")
    monkeypatch.setattr(importlib.machinery, "EXTENSION_SUFFIXES", suffixes)
    assert native_extension_path(tmp_path, "_core_fault").name == "_core_fault.abi3.so"


def test_extension_selection_reports_missing_module(tmp_path, monkeypatch):
    (tmp_path / "_core_fault.dll.a").write_bytes(b"not an extension")
    monkeypatch.setattr(importlib.machinery, "EXTENSION_SUFFIXES", [".pyd"])
    with pytest.raises(FileNotFoundError, match="native test extension"):
        native_extension_path(tmp_path, "_core_fault")


def test_selected_fault_extension_has_native_loader():
    from test_binding_failures import BUILD
    spec = importlib.util.spec_from_file_location(
        "_core_fault", native_extension_path(BUILD, "_core_fault")
    )
    assert spec is not None
    assert isinstance(spec.loader, importlib.machinery.ExtensionFileLoader)
