"""Actual captured entry bootstrap in HOST; native driver/framing real, ZERO OS children.

Only known generated compile filenames are TEST-PRIVATELY mapped to byte-identical
maintained files for truthful coverage accounting, not phantom reporting sources.
"""

import builtins
import sys

import daggerml as d
from daggerml import local
import pytest

from test_implementation_calls import initial, p, adapter, leaf, ROOT


def test_exact_captured_entry_BOOTSTRAP_and_common_facade_native_publication_HOST(initial, tmp_path, monkeypatch):
    path, commit = initial
    publications = []
    compile_code = builtins.compile
    child_context = local.child_context
    def host(context, source, interpreter, timeout):
        filenames = {"implementation_call_leaf.py": ROOT / "examples/implementation_call_leaf.py",
                     "implementation_leaf_funcs.py": ROOT / "examples/implementation_leaf_funcs.py"}
        def precise_filename(code, filename, mode, *args, **kwargs):
            if filename in filenames:
                owning = filenames[filename]
                assert code == owning.read_bytes()  # Actual canonical source/line correspondence.
                filename = str(owning)
            return compile_code(code, filename, mode, *args, **kwargs)
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(builtins, "compile", precise_filename)
            patch.setattr(local, "child_context", lambda *a, **k: context)
            exec(compile_code(source, __file__, "exec"), {})  # Generated ENTRY scaffolding is test code.
        publications.append(context)
        return local._Observation(0, None, "", (b"", 0), (b"", 0))
    def forbidden(*a, **k):
        pytest.fail("HOST bootstrap must not spawn")
    monkeypatch.setattr(local, "_execute", host)
    monkeypatch.setattr(local.subprocess, "Popen", forbidden)
    result = adapter.invoke(path, commit=commit, ref="outer", workspace=tmp_path / "HOST-bootstrap")
    assert result.node.value == d.Datum.i64(84) and len(publications) == 2
    assert local.child_context is child_context
    assert p.inspect_completion(path, commit=result.commit)["request"] == result.request.request
