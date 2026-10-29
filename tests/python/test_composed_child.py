"""Direct trusted standalone-consumer statements/failures, NOT installed coverage."""

import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

import daggerml as d
from daggerml import local
import pytest

from test_exchange import ROOT, literal


def module():
    spec = importlib.util.spec_from_file_location(
        "double_child", ROOT / "examples/floci_double.py"
    )
    child = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(child)
    return child


def context(tmp_path, *, shape=None, **changes):
    path = tmp_path / "child"
    with d.Repository(path, create=True) as repo, repo.write() as tx:
        root = literal(tx, changes.pop("number", 42))
        if shape == "root":
            root = tx.put_subdag(tx.put_dag(root=root))
        value = tx.put_dag(root=root)
        fields = {
            "value": tx.put_subdag(value),
            "producer": tx.put_subdag(tx.put_dag(root=literal(tx, "opaque witness"))),
        }
        fields.update(
            {
                name: literal(tx, item)
                for name, item in {
                    "factor": 2,
                    "exit-code": 0,
                    "endpoint": "http://floci:4566",
                    "bucket": "dml-local",
                    "gate": "gates/double",
                    "artifacts": b"",
                    **changes,
                }.items()
            }
        )
        if shape == "value":
            fields["value"] = literal(tx, 42)
        if shape == "scalar":
            fields["factor"] = tx.put_subdag(value)
        inputs = tx.put_dag(root=fields["value"], bindings=fields)
    return SimpleNamespace(repository_path=path, inputs=inputs)


def wire(monkeypatch, child, statuses=(200, 200, 200), body=b"", error=None):
    states = iter(statuses)
    connections = []
    responses = []
    requests = []

    class Response:
        def __init__(self):
            self.status = next(states)
            self.closed = False
            responses.append(self)

        def read(self, n):
            assert n == 8193
            if error:
                raise error
            return body

        def close(self):
            self.closed = True

    class Connection:
        def __init__(self, *a, **k):
            self.closed = False
            connections.append(self)

        def request(self, method, path, data, headers):
            requests.append((method, path, data))

        def getresponse(self):
            return Response()

        def close(self):
            self.closed = True

    monkeypatch.setattr(child.http.client, "HTTPConnection", Connection)
    return connections, responses, requests


@pytest.mark.parametrize("batch", [False, True])
def test_construct_84_declared_provenance_and_separate_exit(
    tmp_path, monkeypatch, batch
):
    child = module()
    site = Path(d.__file__).resolve().parent.parent
    inventory = [
        dict(
            file="daggerml/__init__.py",
            sha256=hashlib.sha256(
                (site / "daggerml/__init__.py").read_bytes()
            ).hexdigest(),
        )
    ]
    c = context(tmp_path, artifacts=json.dumps(inventory).encode(), **{"exit-code": 23})
    monkeypatch.setattr(child, "child_context", lambda: c)
    if batch:
        monkeypatch.setenv("AWS_BATCH_JOB_ID", "declared-job")
        monkeypatch.setenv("AWS_BATCH_JOB_ATTEMPT", "1")
        reading = Path.read_text
        monkeypatch.setattr(
            Path,
            "read_text",
            lambda self, *a, **k: (
                "Uid:\t1000\nGid:\t1000\nOther:\tignored\n"
                if str(self) == "/proc/self/status"
                else reading(self, *a, **k)
            ),
        )
    else:
        monkeypatch.delenv("AWS_BATCH_JOB_ID", raising=False)
    published = []
    monkeypatch.setattr(
        child, "publish_result", lambda tx, c, result: published.append(result)
    )
    connections, responses, requests = wire(
        monkeypatch, child, statuses=(200, 404, 200, 200)
    )
    monkeypatch.setattr(child.time, "sleep", lambda _: None)
    assert child.main() == 23
    assert all(c.closed for c in connections) and all(r.closed for r in responses)
    assert [r[0] for r in requests] == ["PUT", "GET", "GET", "GET"]
    identity = json.loads(requests[0][2])
    assert identity["factor"] == 2 and identity["artifacts"] == inventory
    with d.Repository(c.repository_path) as repo, repo.read() as tx:
        assert tx.get_datum(
            tx.get_node(tx.get_dag(published[0]).root).datum
        ) == d.Datum.i64(84)


@pytest.mark.parametrize(
    "changes,shape",
    [
        ({}, "value"),
        ({}, "root"),
        ({}, "scalar"),
        ({"number": True}, None),
        ({"factor": True}, None),
        ({"endpoint": "https://floci:4566"}, None),
        ({"bucket": "a..b"}, None),
        ({"gate": "a/../b"}, None),
        ({"artifacts": b'[{"file":"daggerml/__init__.py","sha256":"wrong"}]'}, None),
    ],
    ids=[
        "value-link",
        "root-link",
        "scalar-link",
        "root-type",
        "factor-type",
        "endpoint",
        "bucket",
        "gate",
        "artifact",
    ],
)
def test_bad_input_rejects_before_http(tmp_path, monkeypatch, changes, shape):
    child = module()
    c = context(tmp_path, shape=shape, **changes)
    monkeypatch.setattr(child, "child_context", lambda: c)
    monkeypatch.setattr(
        child.http.client,
        "HTTPConnection",
        lambda *a, **k: pytest.fail("no HTTP before contract validation"),
    )
    with pytest.raises(ValueError):
        child.main()


@pytest.mark.parametrize("fault", ["started", "status", "oversize", "read", "deadline"])
def test_gate_error_disposes_all_owned_resources(tmp_path, monkeypatch, fault):
    child = module()
    c = context(tmp_path)
    monkeypatch.setattr(child, "child_context", lambda: c)
    connections, responses, _ = wire(
        monkeypatch,
        child,
        statuses=(
            (500,)
            if fault == "started"
            else (200, 500) if fault == "status" else (200, 404)
        ),
        body=b"x" * 8193 if fault == "oversize" else b"",
        error=OSError("private read") if fault == "read" else None,
    )
    clock = [0]
    monkeypatch.setattr(child.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(child.time, "sleep", lambda _: clock.__setitem__(0, 121))
    with pytest.raises((ValueError, OSError, TimeoutError)):
        child.main()
    assert all(c.closed for c in connections) and all(r.closed for r in responses)


def test_standalone_entry_has_no_uninstalled_helper_import(tmp_path, monkeypatch):
    child = module()
    c = context(tmp_path)
    monkeypatch.setattr(local, "child_context", lambda: c)
    monkeypatch.setattr(local, "publish_result", lambda *a: None)
    wire(monkeypatch, child)
    monkeypatch.delenv("AWS_BATCH_JOB_ID", raising=False)
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(ROOT / "examples/floci_double.py"), run_name="__main__")
    assert error.value.code == 0
