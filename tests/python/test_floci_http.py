"""Finite loopback wire probes; not actual Floci/DML-in-Batch evidence."""

from contextlib import contextmanager
import json
from types import SimpleNamespace
import socket
import threading
import time

from daggerml import floci_http as h
import pytest


@contextmanager
def wire(chunks):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(2)
    captured, errors = [], []

    def serve():
        try:
            with listener.accept()[0] as connection:
                connection.settimeout(2)
                raw = bytearray()
                while b"\r\n\r\n" not in raw:
                    raw.extend(connection.recv(1))
                head = bytes(raw).decode("ascii")
                length = next(
                    int(row.split(":", 1)[1])
                    for row in head.split("\r\n")
                    if row.lower().startswith("content-length:")
                )
                body = bytearray()
                while len(body) < length:
                    body.extend(connection.recv(length - len(body)))
                captured.append((head, bytes(body)))
                for pause, data in chunks:
                    time.sleep(pause)
                    connection.sendall(data)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Client intentionally closes on bounded protocol rejection.
        except BaseException as error:
            errors.append(error)
        finally:
            listener.close()

    thread = threading.Thread(target=serve)
    thread.start()
    try:
        yield SimpleNamespace(
            endpoint="http://127.0.0.1:" + str(listener.getsockname()[1])
        ), captured
    finally:
        thread.join(timeout=4)
        assert not thread.is_alive(), "owned fake-service thread must be stopped"
        assert not errors, errors


def raw(body=b"abc", *, declared=3, headers=b""):
    return (
        b"HTTP/1.1 200 OK\r\nConnection: close\r\nContent-Length: "
        + str(declared).encode()
        + b"\r\n"
        + headers
        + b"\r\n"
        + body
    )


def call(remote, bound=8192, timeout=1000):
    return h.request(
        remote, h.Budget(timeout, 1), "POST", "/v1/describejobs", b"{}", "batch", bound
    )


def test_direct_fixed_wire_exact_body_and_synthetic_headers(monkeypatch):
    monkeypatch.setenv("http_proxy", "http://invalid:1")
    monkeypatch.setenv("HTTP_PROXY", "http://invalid:1")
    with wire([(0, raw())]) as (remote, captured):
        assert call(remote) == (200, b"abc")
    head, body = captured[0]
    assert body == b"{}" and head.startswith("POST /v1/describejobs HTTP/1.1\r\n")
    assert "Connection: close\r\n" in head
    assert "Credential=test/19700101/us-east-1/batch/aws4_request" in head


@pytest.mark.parametrize(
    "payload",
    [
        raw(b"ab"),
        raw(b"abcd"),
        raw(headers=b"Content-Length: 3\r\n"),
        raw(headers=b"Transfer-Encoding: chunked\r\n"),
        raw(headers=b"Content-Encoding: gzip\r\n"),
        raw(headers=b"Content-Encoding: identity\r\nContent-Encoding: gzip\r\n"),
        raw(headers=b"Content-Encoding: identity\r\nContent-Encoding: identity\r\n"),
        raw(declared=-1),
        raw(declared="03"),
        b"HTTP/1.1 200 OK\r\n\r\nabc",
        b"noise\r\n",
        raw(headers=b"X-Large: " + b"x" * 8192 + b"\r\n"),
    ],
    ids=[
        "truncated",
        "extra-wire",
        "duplicate-length",
        "chunked",
        "encoded",
        "duplicate-mixed-encoding",
        "duplicate-identity",
        "negative-count",
        "noncanonical-count",
        "missing-length",
        "noise",
        "header-overflow",
    ],
)
def test_strict_raw_framing_eof_not_hidden_by_content_length(payload):
    with wire([(0, payload)]) as (remote, _):
        with pytest.raises(h.FlociError):
            call(remote)


@pytest.mark.parametrize(
    "body", [b"x" * 8192, b"x" * 8193], ids=["original-limit", "limit-plus-one"]
)
def test_original_response_descriptor_bound(body):
    with wire([(0, raw(body, declared=len(body)))]) as (remote, _):
        if len(body) == 8192:
            assert call(remote) == (200, body)
        else:
            with pytest.raises(h.FlociError, match="profile"):
                call(remote)


@pytest.mark.parametrize(
    "chunks",
    [
        [(0.2, b"")],
        [(0, raw(b"", declared=3)), (0.2, b"abc")],
        [(0, raw(b"a", declared=3)), (0.06, b"b"), (0.06, b"c")],
        [
            (0, b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n"),
            (0.06, b"X"),
            (0.06, b": x\r\n\r\n"),
        ],
    ],
    ids=["silent-header", "silent-body", "trickled-body", "trickled-header"],
)
def test_whole_http_budget_stops_silent_and_slow_writers(chunks):
    with wire(chunks) as (remote, _):
        start = time.monotonic()
        with pytest.raises(h.FlociError):
            call(remote, timeout=90)
        assert time.monotonic() - start < 0.4


@pytest.mark.parametrize("value", [True, "1", 0, -1, 3600001])
def test_budget_exact_operational_types(value):
    with pytest.raises((TypeError, h.FlociError)):
        h.Budget(value, 1)


def test_budget_deadline_and_call_count(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(h.time, "monotonic", lambda: clock[0])
    budget = h.Budget(100, 1)
    clock[0] = 0.101
    with pytest.raises(h.FlociError, match="budget"):
        budget.remaining()
    with pytest.raises(h.FlociError, match="call budget"):
        h.request(None, h.Budget(100, 0), "GET", "/", b"", "s3", 1)


@pytest.mark.parametrize(
    "data",
    [
        b'{"x":1,"x":2}',
        b'{"x":NaN}',
        b"\xff",
        b"{}{}",
        b"\xef\xbb\xbf{}",
        b"[" * 2000,
        b" " * 8193,
    ],
    ids=["duplicate", "constant", "utf8", "extra-json", "bom", "deep", "over-budget"],
)
def test_strict_original_descriptor(data):
    with pytest.raises(h.FlociError):
        h.document(data)


def test_descriptor_encoding_file_budgets_and_owned_spec(caller_job, tmp_path):
    path, workspace, expected, _, _ = caller_job
    assert h.owned_spec((workspace / "job.json").read_bytes()) == expected
    assert h.document(b" " * 8190 + b"{}") == {}
    with pytest.raises(TypeError):
        h.document("{}")
    with pytest.raises(h.FlociError):
        h.encoded({"x": "x" * 8192})
    target = tmp_path / "file"
    target.write_bytes(b"x" * 8193)
    with pytest.raises(h.FlociError):
        h.read_file(target, 8192)


# Reuse public caller fixture only; fake wires never start a Docker fixture.
from test_caller_requests import caller_job
from test_exchange import exchange_runtime


def test_fixed_object_paths_and_conditional_create(monkeypatch):
    remote = SimpleNamespace(
        endpoint="http://127.0.0.1:1", bucket="dml-local", prefix="a/b"
    )
    token = "a" * 32
    calls = []
    monkeypatch.setattr(
        h, "request", lambda *args, **kwargs: calls.append((args, kwargs)) or (200, b"")
    )
    h.put_object(remote, h.Budget(100, 1), token, "input/job.json", b"{}")
    assert calls[0][0][3] == "/dml-local/a/b/" + token + "/input/job.json"
    assert calls[0][1] == {"create": True}
    assert h.get_object(remote, h.Budget(100, 1), token, "input/job.json", 8192) == b""


@pytest.mark.parametrize(
    "status,same,current,accepted",
    [
        (412, True, b"abc", True),
        (412, True, b"changed", False),
        (412, False, b"abc", False),
        (500, True, b"abc", False),
    ],
)
def test_create_only_no_silent_overwrite(monkeypatch, status, same, current, accepted):
    monkeypatch.setattr(h, "request", lambda *a, **k: (status, b"ignored-secret-error"))
    monkeypatch.setattr(h, "object_path", lambda *a: "/fixed")
    monkeypatch.setattr(h, "get_object", lambda *a: current)
    if accepted:
        h.put_object(None, None, None, None, b"abc", same=same)
    else:
        with pytest.raises(h.FlociError) as error:
            h.put_object(None, None, None, None, b"abc", same=same)
        assert "secret" not in str(error.value)


@pytest.mark.parametrize("status", [404, 301, 403, 500])
def test_status_absence_vs_error_no_redirect(monkeypatch, status):
    monkeypatch.setattr(h, "object_path", lambda *a: "/fixed")
    monkeypatch.setattr(h, "request", lambda *a, **k: (status, b"secret"))
    if status == 404:
        assert h.get_object(None, None, None, None, 8192) is None
    else:
        with pytest.raises(h.FlociError):
            h.get_object(None, None, None, None, 8192)
    with pytest.raises(h.FlociError):
        h.batch(None, None, "DescribeJobs", {})
