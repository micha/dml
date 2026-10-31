"""Default-safe controller arithmetic/oracles/offline blockers; no service or jobs."""

import ast
from dataclasses import replace
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_exchange import ROOT, exchange_runtime
from test_implementation_supersession import app, state, author, request

spec = importlib.util.spec_from_file_location(
    "supersession_story", ROOT / "tests/supersession/story.py"
)
story = importlib.util.module_from_spec(spec)
spec.loader.exec_module(story)


@pytest.mark.parametrize(
    "n,expected_a,expected_b", [(-3, 0, -6), (0, 0, 0), (7, 14, 14)]
)
def test_actual_captured_arithmetic_not_canned(n, expected_a, expected_b):
    from types import SimpleNamespace

    for source, expected in ((story.BUGGY, expected_a), (story.SOURCE, expected_b)):
        node = next(
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "answer" for t in node.targets)
        )
        scope = {"n": SimpleNamespace(value=n)}
        # Owning real test filename, never an invented source path under ROOT.
        exec(
            compile(
                ast.Module(body=[node], type_ignores=[]),
                str(Path(__file__).resolve()),
                "exec",
            ),
            scope,
        )
        assert scope["answer"] == expected
    assert story.SOURCE != story.BUGGY


@pytest.mark.parametrize(
    "module",
    [
        "http.client",
        "urllib.request",
        "urllib.error",
        "boto3",
        "docker",
        "daggerml.floci",
        "requests",
        "httpx",
        "aiohttp",
        "botocore",
    ],
)
def test_offline_copied_client_import_blockers(tmp_path, exchange_runtime, module):
    script = tmp_path / "client.py"
    script.write_text(
        "import importlib\nimportlib.import_module(" + repr(module) + ")\n"
    )
    run = subprocess.run(
        [sys.executable, "-c", story.OFFLINE, str(script)],
        capture_output=True,
        timeout=20,
    )
    assert (
        run.returncode != 0 and b"offline client cannot import transport" in run.stderr
    )


@pytest.mark.parametrize(
    "code",
    ["import subprocess;subprocess.Popen(['true'])", "import os;os.system('true')"],
)
def test_offline_client_spawn_blockers(tmp_path, code):
    script = tmp_path / "client.py"
    script.write_text(code)
    run = subprocess.run(
        [sys.executable, "-c", story.OFFLINE, str(script)],
        capture_output=True,
        timeout=20,
    )
    assert run.returncode != 0 and b"offline client cannot spawn" in run.stderr


def test_pure_parser_permitted_without_transport(tmp_path):
    script = tmp_path / "client.py"
    script.write_text(
        "import urllib.parse\nassert urllib.parse.urlsplit('https://example.test').hostname=='example.test'\n"
    )
    subprocess.run(
        [sys.executable, "-c", story.OFFLINE, str(script)], check=True, timeout=20
    )


@pytest.mark.parametrize("fault", ["override", "implementation-reason", "reuse-reason"])
def test_controller_request_oracles_known_call_not_response_flags(
    state, monkeypatch, fault
):
    path, definition = state
    owning = app.policy.record_policy_request

    def forged(*a, **k):
        got = owning(*a, **k)
        change = (
            {"implementation_override": "a"}
            if fault == "override"
            else (
                {"implementation_reason": "explicit-implementation"}
                if fault == "implementation-reason"
                else {"reason": "override-fresh"}
            )
        )
        return replace(got, decision=replace(got.decision, **change))

    monkeypatch.setattr(app.policy, "record_policy_request", forged)
    with pytest.raises(AssertionError):
        story.request(path, app, {"requests": {}}, "a", str(definition.commit))


@pytest.mark.parametrize("fault", ["relation", "same-relation-wrong-commit"])
def test_controller_reader_wrong_actual_basis_or_ignored_knowledge_rejects(
    state, monkeypatch, fault
):
    path, definition = state
    old = request(state, definition.commit)
    declared = author(state)
    item = dict(
        commit=str(old.recorded.commit),
        request=str(old.recorded.request),
        decision=old.decision.name,
        base=str(old.decision.base),
        satisfaction=None,
        binding=str(old.decision.binding),
        inputs=str(old.decision.inputs),
        implementation_override="default",
        reason="default-no-selection",
    )
    saved = dict(requests={"a": item}, operational="unused")
    owning = app.inspect_request_context

    def forged(*a, **k):
        got = owning(*a, **k)
        historical = (
            replace(got.explicit_knowledge, relation="predecessor")
            if fault == "relation"
            else replace(got.as_known_then, commit=got.decision.commit)
        )
        return replace(got, as_known_then=historical)

    monkeypatch.setattr(app, "inspect_request_context", forged)
    with pytest.raises(AssertionError):
        story.read(path, app, saved, "a", str(declared.commit))
