"""Test-only disposal of successful reuse tests' explicitly owned tmp_path.

Windows LMDB opens extend data.mdb to the unchanged 64MiB default map. Retaining
all successful new repositories until session exit can exhaust runner disk.
ONLY these explicitly named synchronous/authoring-only modules qualify, AFTER all fixtures
finish and all three phase reports pass. Failure/skip/unknown artifacts remain.
No global purge, native profile change, historical-path action or process signal.
"""

from pathlib import Path
import shutil

import pytest

OWN_TESTS = frozenset(
    {
        "test_explicit_reuse.py",
        "test_explicit_reuse_atomicity.py",
        "test_explicit_reuse_fixture.py",
        "test_explicit_reuse_modes.py",
        "test_explicit_reuse_selection.py",
        "test_reuse_selection.py",
        "test_reuse_selection_records.py",
        "test_reuse_selection_atomicity.py",
        "test_reuse_selection_modes.py",
        "test_reuse_selection_fixture.py",
    }
)
OWNED = pytest.StashKey()
PHASES = pytest.StashKey()


@pytest.fixture(autouse=True)
def owned_reuse_tmp(request):
    if Path(request.node.path).name in OWN_TESTS:
        # Native/child handles belong to existing owning fixtures, not this plugin.
        # Their teardown must finish before makereport's teardown report exists.
        request.node.stash[OWNED] = request.getfixturevalue("tmp_path")


def finish_report(item, report):
    root = item.stash.get(OWNED, None)
    if Path(item.path).name not in OWN_TESTS or not isinstance(root, Path):
        return
    phases = item.stash.setdefault(PHASES, {})
    phases[report.when] = report
    if report.when != "teardown" or not all(
        phase in phases and phases[phase].passed
        for phase in ("setup", "call", "teardown")
    ):
        return  # Failed/skipped/no-call/unknown ownership never permits disposal.
    try:
        shutil.rmtree(root)
    except OSError as error:
        # Only a previously passing teardown reaches this point. Never replace an
        # original test/fixture failure, silently swallow cleanup or INTERNALERROR.
        report.outcome = "failed"
        report.longrepr = "owned reuse tmp cleanup failed: " + repr(error)


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    finish_report(item, outcome.get_result())
