"""Default-safe new controller/oracles, no Docker or HTTP invocation."""

import ast
import importlib.util
import json
from pathlib import Path
import sys

import daggerml as d
import pytest

pytest_plugins = ("reuse_test_cleanup",)

from test_composed_execution import producer
from test_exchange import ROOT, exchange_runtime, tree
from test_explicit_reuse import double
from test_implementation_selection import app, menu, define, request
from test_intent_defaults_fixture import controller as old_controller


def controller():
    names = (
        "fixture",
        "integration",
        "retained_integration",
        "loss_integration",
        "composed_integration",
        "composed_app",
        "reuse_integration",
        "selection_integration",
        "intent_integration",
    )
    previous = {name: sys.modules.get(name) for name in names}
    paths = list(sys.path)
    for name in names:
        sys.modules.pop(name, None)
    try:
        sys.path.insert(0, str(ROOT / "tests/floci"))
        spec = importlib.util.spec_from_file_location(
            "implementation_controller",
            ROOT / "tests/floci/implementation_integration.py",
        )
        result = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(result)
        return result
    finally:
        sys.path[:] = paths
        for name, old in previous.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


def test_new_controller_scoped_aliases_existing_offline_blockers_no_start():
    old, paths = dict(sys.modules), list(sys.path)
    got = controller()
    assert got.OFFLINE == old_controller().OFFLINE
    for name in (
        "fixture",
        "integration",
        "composed_integration",
        "composed_app",
        "intent_integration",
    ):
        assert sys.modules.get(name) is old.get(name)
    assert sys.path == paths


def test_genuine_captured_B_addition_factor_two_contract_not_comment_or_canned84():
    got = controller()
    original = (ROOT / "examples/floci_double.py").read_bytes()
    candidate = got.double_b_source(original)
    assert candidate != original
    program = ast.parse(candidate)
    main = next(
        node
        for node in program.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    publication = next(
        node
        for node in main.body
        if isinstance(node, ast.With)
        and any(
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == "publish_result"
            for child in ast.walk(node)
        )
    )

    # Execute actual B captured arithmetic/contract statements with a tiny tx value
    # stub; real installed child+inputs/producer are separate acceptance evidence.
    class Tx:
        def put_datum(self, value):
            return value

        def put_literal(self, value):
            return value

    class Number:
        value = 42

    statements = publication.body[:2]
    code = compile(
        ast.fix_missing_locations(ast.Module(body=statements, type_ignores=[])),
        # This extracted AST runs with test-only value stubs, not an installed
        # source file. Attribute it to THIS test, never invent a ROOT source path.
        str(Path(__file__).resolve()),
        "exec",
    )
    for value in (42, -3, 17):
        number = Number()
        number.value = value
        values = dict(tx=Tx(), number=number, factor=2)
        exec(code, values)
        assert values["result"] == value + value
    with pytest.raises(ValueError, match="factor two"):
        exec(code, dict(tx=Tx(), number=Number(), factor=3))
    with pytest.raises(AssertionError):
        got.double_b_source(b"not a standalone arithmetic source")


def test_new_native_decision_Q_oracle_and_pending_separate_adapter(menu, monkeypatch):
    got = controller()
    path = menu[0][0][0]
    definition = define(menu)
    pending = request(path, definition.commit)
    report = app._decision_report(pending.decision)
    report.update(
        request_commit=str(pending.recorded.commit),
        request=str(pending.recorded.request),
        request_id=pending.recorded.request_id,
        commit=str(pending.recorded.commit),
        association=None,
    )
    assert (
        got.verify_policy(path, definition.commit, report, "double-a")
        == pending.recorded.commit
    )
    with pytest.raises(AssertionError):
        got.verify_policy(path, definition.commit, report, "double-b")
    expected = got.prepare_policy(path, path.parent, "separate", report)
    assert (
        expected.request == pending.recorded.request
        and expected.binding == pending.decision.binding
    )
    assert not (path.parent / "separate-input/worker.dml").exists()
    reader = dict(mode="inspect-request", **app._decision_report(pending.decision))
    monkeypatch.setattr(got, "invoke", lambda *a, **k: dict(reader))
    got.read_policy("copied-helper", [], path, report)
    for fault in ("missing-choice", "wrong-reason"):
        changed = dict(reader)
        if fault == "missing-choice":
            changed.pop("implementation_choice")
        else:
            changed["implementation_reason"] = "explicit-implementation"
        monkeypatch.setattr(got, "invoke", lambda *a, **k: dict(changed))
        with pytest.raises(AssertionError):
            got.read_policy("copied-helper", [], path, report)
    for changes in (
        dict(
            implementation_override="double-a",
            implementation_reason="explicit-implementation",
        ),
        dict(implementation_reason="explicit-implementation"),
    ):
        with pytest.raises(AssertionError):
            got.verify_policy(
                path, definition.commit, dict(report, **changes), "double-a"
            )
