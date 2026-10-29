"""Default-safe example source coverage; host model, not installed Batch evidence."""

import importlib.util
import json
import os
from pathlib import Path
import runpy
from types import SimpleNamespace
import sys

import daggerml as d
from daggerml import exchange as ex, floci as f, floci_worker as worker, local
import pytest

from test_exchange import exchange_runtime
from test_floci import service, remote

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(
        "example_" + name, ROOT / "examples" / (name + ".py")
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def host_binding(monkeypatch):
    original = local.put_local_binding

    def bind(tx, **kwargs):
        if kwargs["interpreter"] == "/opt/dml/bin/python":
            kwargs["interpreter"] = sys.executable
        return original(tx, **kwargs)

    monkeypatch.setattr(local, "put_local_binding", bind)
    return bind, original


def test_endpoint_modes_explicit_q_real_history_offline_receive(
    tmp_path, service, exchange_runtime, host_binding, capsys, monkeypatch
):
    application = module("floci_execution")
    config = tmp_path / "remote.json"
    from dataclasses import asdict

    config.write_text(json.dumps(asdict(service.remote)), encoding="utf-8")
    source = tmp_path / "entry.py"
    source.write_bytes(b"pass\n")
    story = tmp_path / "story"
    assert (
        application.main(
            ["prepare", str(story), str(config), str(source), "gates/local"]
        )
        == 0
    )
    expected = ex.read_exchange_spec(story / "input")
    with d.Repository(story / "caller.dml") as repo, repo.read() as tx:
        assert tx.get_ref("submission") == expected.commit
        assert tx.get_ref("main") == tx.get_commit(expected.commit).parents[0]
    assert application.main(["submit", str(story)]) == 0
    job = f.load_floci_job(story / "saved")
    assert (
        application.main(["observe", str(story / "saved"), str(story / "bootstrap")])
        == 0
    )
    ex.execute_exchange(story / "input")
    worker._publish(job, ex.ExchangeHandle(story / "input", expected))
    assert (
        application.main(["observe", str(story / "saved"), str(story / "packet")]) == 0
    )
    service.objects.clear()
    with monkeypatch.context() as guarded:
        guarded.setattr(
            f,
            "observe_floci_job",
            lambda *a, **k: pytest.fail("offline receive never connects"),
        )
        assert (
            application.main(
                [
                    "receive",
                    str(story / "caller.dml"),
                    str(story / "saved"),
                    str(story / "packet"),
                    "returned",
                ]
            )
            == 0
        )
    reports = [json.loads(row) for row in capsys.readouterr().out.splitlines()]
    assert (
        reports[0]["request"] == str(expected.request)
        and reports[-1]["lifecycle"] == "done"
    )
    assert reports[2]["phase"] == "bootstrap"
    config.write_bytes(b" " * 8193)
    with pytest.raises(ValueError, match="profile"):
        application.configuration(config)
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(ROOT / "examples/floci_execution.py"), run_name="__main__")
    assert error.value.code == 2


def test_binding_model_keeps_remote_posix_and_maps_only_selected_host_interpreter(
    tmp_path, monkeypatch
):
    native = r"C:\Python\python.exe"
    original = local.put_local_binding
    calls = []
    monkeypatch.setattr(
        local,
        "put_local_binding",
        lambda tx, **kwargs: calls.append(kwargs["interpreter"]),
    )

    # Semantic model of the private adapter, retaining public endpoint validation.
    def bind(tx, interpreter):
        return local.put_local_binding(
            tx,
            source=b"pass",
            interpreter=(
                sys.executable if interpreter == "/opt/dml/bin/python" else interpreter
            ),
            timeout_ms=1,
        )

    bind(None, "/opt/dml/bin/python")
    bind(None, native)
    assert calls == [sys.executable, native]
    assert remote().python == "/opt/dml/bin/python"
    with pytest.raises(f.FlociError):
        remote(python=native)


def child_context(tmp_path, **changes):
    values = dict(
        left=13,
        right=29,
        endpoint="http://floci:4566",
        bucket="dml-local",
        gate="gates/local",
        **{"exit-code": 0},
    )
    values.update(changes)
    path = tmp_path / "child.dml"
    with d.Repository(path, create=True) as repo, repo.write() as tx:
        fields = {
            name: tx.put_literal(tx.put_datum(value)) for name, value in values.items()
        }
        inputs = tx.put_dag(root=fields["left"], bindings=fields)
    return SimpleNamespace(repository_path=path, inputs=inputs)


def fake_http(monkeypatch, application, *, statuses=(200, 200), body=b"", error=None):
    acquired, responses, requests = [], [], []
    statuses = iter(statuses)

    class Response:
        def __init__(self):
            self.status = next(statuses)
            self.closed = False
            responses.append(self)

        def read(self, bound):
            assert bound == 8193
            if error:
                raise error
            return body

        def close(self):
            self.closed = True

    class Connection:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("floci", 4566, 5)
            self.closed = False
            acquired.append(self)

        def request(self, method, path, headers):
            requests.append((method, path, headers))

        def getresponse(self):
            return Response()

        def close(self):
            self.closed = True

    monkeypatch.setattr(application.http.client, "HTTPConnection", Connection)
    return acquired, responses, requests


def test_child_consumes_declared_endpoint_key_and_publishes_constructed_result(
    tmp_path, monkeypatch
):
    child = module("floci_add")
    context = child_context(tmp_path, **{"exit-code": 23})
    monkeypatch.setattr(child, "child_context", lambda: context)
    captured = []
    monkeypatch.setattr(
        child, "publish_result", lambda tx, c, result: captured.append((c, result))
    )
    connections, responses, requests = fake_http(monkeypatch, child)
    assert child.main() == 23
    assert all(c.closed for c in connections) and all(r.closed for r in responses)
    assert [row[1] for row in requests] == [
        "/dml-local/gates/local/gate1",
        "/dml-local/gates/local/gate2",
    ]
    with d.Repository(context.repository_path) as repo, repo.read() as tx:
        result = captured[0][1]
        assert tx.get_datum(tx.get_node(tx.get_dag(result).root).datum).value == 42


@pytest.mark.parametrize(
    "changes",
    [
        {"left": True},
        {"endpoint": 1},
        {"endpoint": "http://floci:0"},
        {"endpoint": "https://floci:4566"},
        {"endpoint": "http://floci:4566/path"},
        {"endpoint": "http://user@floci:4566"},
        {"endpoint": "http://FLOCI:4566"},
        {"bucket": "a..b"},
        {"gate": "gates/../x"},
        {"gate": "gates//x"},
    ],
)
def test_child_rejects_bad_declared_types_endpoint_and_key_before_http(
    tmp_path, monkeypatch, changes
):
    child = module("floci_add")
    context = child_context(tmp_path, **changes)
    monkeypatch.setattr(child, "child_context", lambda: context)
    monkeypatch.setattr(
        child.http.client,
        "HTTPConnection",
        lambda *a, **k: pytest.fail("bad inputs cannot acquire HTTP"),
    )
    with pytest.raises((TypeError, ValueError)):
        child.main()


@pytest.mark.parametrize("kind", ["oversize", "status", "read-io", "deadline"])
def test_child_disposes_all_owned_gate_responses_on_meaningful_errors(
    tmp_path, monkeypatch, kind
):
    child = module("floci_add")
    context = child_context(tmp_path)
    monkeypatch.setattr(child, "child_context", lambda: context)
    connections, responses, requests = fake_http(
        monkeypatch,
        child,
        statuses=(404, 500) if kind == "status" else (404, 404),
        body=b"x" * 8193 if kind == "oversize" else b"",
        error=OSError() if kind == "read-io" else None,
    )
    clock = [0]
    monkeypatch.setattr(child.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        child.time,
        "sleep",
        lambda seconds: clock.__setitem__(
            0, clock[0] + (121 if kind == "deadline" else 1)
        ),
    )
    monkeypatch.setattr(
        child,
        "publish_result",
        lambda *a: pytest.fail("no publication after gate failure"),
    )
    with pytest.raises((ValueError, OSError, TimeoutError)):
        child.main()
    assert all(c.closed for c in connections) and all(r.closed for r in responses)


def test_child_module_entry_preserves_recorded_exit_policy(tmp_path, monkeypatch):
    context = child_context(tmp_path)
    monkeypatch.setattr(local, "child_context", lambda: context)
    monkeypatch.setattr(local, "publish_result", lambda *a: None)
    child = module("floci_add")
    fake_http(monkeypatch, child)
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(ROOT / "examples/floci_add.py"), run_name="__main__")
    assert error.value.code == 0
