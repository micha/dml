"""Default-safe controller entrypoints/document navigation, no installed computation."""

import importlib.util
from pathlib import Path
import re
import sys

from daggerml import exchange as ex, local
import pytest

from test_exchange import ROOT


def load(filename):
    spec = importlib.util.spec_from_file_location("closure_test_" + filename, ROOT / "tests/closures" / (filename + ".py"))
    module = importlib.util.module_from_spec(spec)
    saved = list(sys.path)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = saved
    return module


def test_import_and_nonrun_modes_never_dispatch(monkeypatch, capsys):
    def forbidden(*a, **k):
        pytest.fail("tooling import/metadata entrypoints cannot dispatch")
    monkeypatch.setattr(ex, "execute_exchange", forbidden)
    monkeypatch.setattr(local, "run_request", forbidden)
    story = load("installed_story")
    monkeypatch.setattr(story, "run", forbidden)
    monkeypatch.setattr(story, "metadata_controls", lambda: ([True], {"metadata": True}))
    assert story.main(["metadata-controls"]) == 0
    assert '"metadata": true' in capsys.readouterr().out
    with pytest.raises(ValueError, match="explicit fresh"):
        story.main(["run"])
    with pytest.raises(SystemExit) as error:
        story.main([])
    assert error.value.code == 2


@pytest.mark.parametrize("name,expected", [("urllib", False), ("urllib.parse", False), ("urllib.request", True), ("http.client", True), ("daggerml.ssh", True), ("daggerml.builtin", False)])
def test_exact_parser_not_transport(name, expected):
    reader = load("offline_read")
    assert reader.blocked(name) == expected
    if expected:
        with pytest.raises(RuntimeError):
            reader.NoTransport().find_spec(name)


def test_new_docs_relative_targets_exist():
    for path in (ROOT / "docs/closure-bound-dependencies.md", ROOT / "tests/closures/README.md"):
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if "://" not in link:
                assert (path.parent / link.split("#")[0]).resolve().exists(), (path, link)


def test_controller_four_dispatch_count_is_explicit_not_default_fixture():
    source = (ROOT / "tests/closures/installed_story.py").read_text()
    assert '(1, "A", "fresh", False)' in source
    assert '(3, "A", "fresh", False)' in source
    assert '(5, "B", "fresh", False)' in source
    assert '(6, "C", "try-selected", False)' in source
    assert 'process.wait_receipts' in source and 'all_four_known_wait_reaped_absent' in source
    assert not (ROOT / "tests/closures/installed_story.py").name.startswith("test_")
    assert 'if __name__ == "__main__":' in source
