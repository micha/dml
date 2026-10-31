"""Scoped post-report cleanup regressions; no Docker, map/profile weakening."""

from pathlib import Path
import os
import subprocess
import sys
from types import SimpleNamespace

import daggerml as d
import pytest

from test_exchange import ROOT
import reuse_test_cleanup as cleanup


def item(path, owned=None):
    result = SimpleNamespace(path=path, stash=pytest.Stash())
    if owned is not None:
        result.stash[cleanup.OWNED] = owned
    return result


def report(when, passed=True):
    return SimpleNamespace(
        when=when,
        passed=passed,
        outcome="passed" if passed else "failed",
        longrepr=None,
    )


@pytest.mark.parametrize(
    "name",
    [
        "test_reuse_selection.py",
        "test_reuse_selection_records.py",
        "test_reuse_selection_atomicity.py",
        "test_reuse_selection_modes.py",
        "test_reuse_selection_fixture.py",
        "test_intent_defaults.py",
        "test_intent_defaults_records.py",
        "test_intent_defaults_atomicity.py",
        "test_intent_defaults_modes.py",
        "test_intent_defaults_edges.py",
        "test_intent_defaults_fixture.py",
        "test_implementation_selection.py",
        "test_implementation_selection_edges.py",
        "test_implementation_selection_atomicity.py",
        "test_implementation_selection_fixture.py",
        "test_implementation_supersession.py",
        "test_implementation_supersession_atomicity.py",
        "test_implementation_supersession_fixture.py",
        "test_multi_input_reuse.py",
        "test_multi_input_atomicity.py",
        "test_multi_input_story.py",
    ],
)
def test_exact_new_selection_module_scope_post_report_and_unknown_retention(
    tmp_path, name
):
    assert name in cleanup.OWN_TESTS
    owned = tmp_path / "owned"
    owned.mkdir()
    with d.Repository(owned / "closed.dml", create=True):
        pass
    current = item(Path(name), owned)
    cleanup.finish_report(current, report("setup"))
    cleanup.finish_report(current, report("teardown"))  # no call => unknown disposition
    assert owned.exists()
    cleanup.finish_report(current, report("call"))
    assert owned.exists()  # never dispose before a fresh passing teardown report
    cleanup.finish_report(current, report("teardown"))
    assert not owned.exists()


def test_passed_closed_native_windows_extent_model_deletes_only_owned_root(tmp_path):
    owned, neighbor = tmp_path / "owned", tmp_path / "unrelated"
    owned.mkdir()
    neighbor.mkdir()
    (neighbor / "keep").write_bytes(b"unrelated evidence")
    with d.Repository(owned / "A.dml", create=True):
        pass
    # Closed native Windows file-extent model, not an original disk-full census.
    with (owned / "A.dml/data.mdb").open("r+b") as stream:
        stream.truncate(64 * 1024 * 1024)
    current = item(Path("test_explicit_reuse.py"), owned)
    for phase in ("setup", "call"):
        cleanup.finish_report(current, report(phase))
        assert owned.exists()
    cleanup.finish_report(current, report("teardown"))
    assert (
        not owned.exists() and (neighbor / "keep").read_bytes() == b"unrelated evidence"
    )


@pytest.mark.parametrize(
    "mode", ["setup", "call", "teardown", "no-call", "unknown", "unrelated"]
)
def test_ineligible_reports_retain_owned_artifacts(tmp_path, mode):
    owned = tmp_path / "owned"
    owned.mkdir()
    (owned / "keep").write_bytes(b"original evidence")
    current = item(
        Path("test_unrelated.py" if mode == "unrelated" else "test_explicit_reuse.py"),
        None if mode == "unknown" else owned,
    )
    cleanup.finish_report(current, report("setup", mode != "setup"))
    if mode != "no-call":
        cleanup.finish_report(current, report("call", mode != "call"))
    cleanup.finish_report(current, report("teardown", mode != "teardown"))
    assert (owned / "keep").read_bytes() == b"original evidence"


@pytest.mark.parametrize(
    "mode",
    ["success", "setup", "call", "teardown", "skip", "cleanup-error", "unrelated"],
)
def test_real_pytest_phase_order_failure_retention_and_visible_cleanup_error(
    tmp_path, mode
):
    case = tmp_path / "case"
    case.mkdir()
    base = case / "tmp"
    conftest = (
        "import sys\nfrom pathlib import Path\nsys.path.insert(0,"
        + repr(str(ROOT / "tests/python"))
        + ")\npytest_plugins=('reuse_test_cleanup',)\n"
    )
    if mode == "cleanup-error":
        conftest += """import reuse_test_cleanup as cleanup
original=cleanup.shutil.rmtree
def denied(path,*a,**k):
 if (Path(path)/'closed-data').exists():raise PermissionError('private cleanup denial')
 return original(path,*a,**k)
cleanup.shutil.rmtree=denied
"""
    (case / "conftest.py").write_text(conftest)
    source = """import pytest
from pathlib import Path
MODE=MODE_VALUE
@pytest.fixture
def specimen(tmp_path):
 (Path.cwd()/'owned.txt').write_text(str(tmp_path))
 (tmp_path/'closed-data').write_bytes(b'closed original evidence')
 if MODE=='setup':raise AssertionError('original setup failure')
 yield
 assert (tmp_path/'closed-data').exists(), 'no deletion before fixture teardown'
 (Path.cwd()/'teardown.txt').write_text('owning fixtures finished')
 if MODE=='teardown':raise AssertionError('original teardown failure')
def test_success(specimen):
 if MODE=='call':raise AssertionError('original call failure')
 if MODE=='skip':pytest.skip('original skipped test')
""".replace(
        "MODE_VALUE", repr(mode)
    )
    name = "test_unrelated.py" if mode == "unrelated" else "test_explicit_reuse.py"
    (case / name).write_text(source)
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--basetemp", str(base), name],
        cwd=case,
        env=environment,
        capture_output=True,
        timeout=30,
    )
    output = (result.stdout + result.stderr).decode()
    assert "INTERNALERROR" not in output
    assert result.returncode == (
        0 if mode in ("success", "skip", "unrelated") else 1
    ), output
    owned = Path((case / "owned.txt").read_text())
    assert owned.exists() == (mode != "success")
    if mode != "setup":
        assert (case / "teardown.txt").read_text() == "owning fixtures finished"
    if mode == "cleanup-error":
        assert "owned reuse tmp cleanup failed" in output and "1 error" in output
        assert (owned / "closed-data").read_bytes() == b"closed original evidence"
