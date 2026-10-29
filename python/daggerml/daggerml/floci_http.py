"""Fixed unsigned local Floci HTTP/object framing, not a generic AWS transport.

Internal to the floci transport family. Exchange owns all job/role/history codecs.
"""

from __future__ import annotations

import hashlib
import http.client
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
import time
import unicodedata
from urllib.parse import quote, urlsplit

from . import exchange, transfer

DESCRIPTOR_BYTES = exchange.MAX_DESCRIPTOR_BYTES
INPUT_FILES = ("job.json", "input.bundle")
PACKET_FILES = ("job.json", "observation.json", "snapshot.bundle")
PHASES = ("completion", "publication", "initial")
REMOTE_FIELDS = (
    "endpoint",
    "bucket",
    "prefix",
    "queue",
    "job_definition",
    "image",
    "python",
)


class FlociError(ValueError):
    """Transport failure is not a DML outcome or permission to resubmit.

    job_id retains a known acknowledgement on later local receipt failure only.
    None does not assert that the service rejected or did not execute the request.
    """

    def __init__(self, message, *, job_id=None):
        self.job_id = job_id
        super().__init__(message)


def text(value):
    if type(value) is not str:
        raise TypeError("Floci configuration requires str")
    value.encode("utf-8")
    if (
        not value
        or unicodedata.normalize("NFC", value) != value
        or any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value)
    ):
        raise FlociError("Floci spelling requires nonempty NFC without controls")
    return value


def match(value, pattern):
    if re.fullmatch(pattern, text(value)) is None:
        raise FlociError("invalid Floci operational spelling")
    return value


def hex_id(value):
    return match(value, r"[0-9a-f]{32}")


def job_id(value):
    return match(value, r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def endpoint(value):
    value = text(value)
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        raise FlociError("invalid explicit Floci endpoint") from None
    if (
        parts.scheme != "http"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.path
        or parts.query
        or parts.fragment
        or port is None
        or not 1 <= port <= 65535
    ):
        raise FlociError("Floci endpoint requires explicit http host:port only")
    host = match(parts.hostname, r"[a-z0-9][a-z0-9.:-]*")
    spelling = "[" + host + "]" if ":" in host else host
    if value != "http://" + spelling + ":" + str(port):
        raise FlociError("Floci endpoint must already be canonical")
    return host, port


def posix_path(value):
    value = text(value)
    path = PurePosixPath(value)
    if (
        not value.startswith("/")
        or value.startswith("//")
        or ".." in path.parts
        or str(path) != value
    ):
        raise FlociError("job interpreter requires normalized absolute POSIX spelling")
    return value


def expected(value):
    if not isinstance(value, exchange.ExchangeSpec):
        raise TypeError("expected requires ExchangeSpec")
    if value.request is None:
        raise FlociError("Floci execution requires caller-recorded exact Q")
    return value


def read_file(path, limit):
    with open(path, "rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise FlociError("Floci file exceeds owning profile")
    return data


def pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise FlociError("duplicate Floci descriptor field")
        result[key] = value
    return result


def constant(_):
    raise FlociError("nonstandard Floci descriptor constant")


def document(data):
    if type(data) is not bytes:
        raise TypeError("Floci descriptor requires bytes")
    if len(data) > DESCRIPTOR_BYTES:
        raise FlociError("Floci descriptor exceeds profile")
    try:
        return json.loads(
            data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant
        )
    except (ValueError, RecursionError):
        raise FlociError("invalid bounded Floci UTF-8/JSON descriptor") from None


def encoded(value):
    data = json.dumps(
        value, ensure_ascii=True, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")
    if len(data) > DESCRIPTOR_BYTES:
        raise FlociError("Floci descriptor exceeds profile")
    return data


def fields(value, keys, label):
    if (
        type(value) is not dict
        or set(value) != set(keys) | {"format"}
        or value["format"] != label
    ):
        raise FlociError("unexpected Floci descriptor fields/format")
    return value


def owned_spec(data):
    with tempfile.TemporaryDirectory(prefix="dml-floci-job-") as temporary:
        path = Path(temporary)
        (path / "job.json").write_bytes(data)
        return expected(exchange.read_exchange_spec(path))


def limit(name):
    return transfer.MAX_BUNDLE_BYTES if name.endswith(".bundle") else DESCRIPTOR_BYTES


def file_rows(files):
    return [
        dict(name=name, size=len(data), sha256=hashlib.sha256(data).hexdigest())
        for name, data in files
    ]


def validate_rows(rows, names):
    if type(rows) is not list or len(rows) != len(names):
        raise FlociError("unexpected immutable file set")
    for row, name in zip(rows, names):
        if (
            type(row) is not dict
            or set(row) != {"name", "size", "sha256"}
            or row["name"] != name
        ):
            raise FlociError("unexpected immutable file fields/order")
        if type(row["size"]) is not int or not 0 <= row["size"] <= limit(name):
            raise FlociError("immutable file size exceeds owning profile")
        match(row["sha256"], r"[0-9a-f]{64}")
    return rows


class Budget:
    """One invocation's remaining HTTP time/call accounting; no polling/retries.

    DNS/filesystem/native work has no portable hard deadline. Header/body reads
    account remaining time before each bounded read; socket calls use that remainder.
    """

    def __init__(self, timeout_ms, calls):
        if type(timeout_ms) is not int:
            raise TypeError("timeout_ms requires int")
        if not 1 <= timeout_ms <= 3600000:
            raise FlociError("timeout_ms requires 1..3600000")
        self.deadline = time.monotonic() + timeout_ms / 1000
        self.calls = calls

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise FlociError("Floci invocation HTTP budget exhausted")
        return remaining


class HeaderReader:
    """Bound total HTTP status/header bytes, including informational replies."""

    def __init__(self, stream, sock, budget):
        self.stream, self.sock, self.budget = stream, sock, budget
        self.remaining = DESCRIPTOR_BYTES

    def readline(self, size=-1):
        line = bytearray()
        while size < 0 or len(line) < size:
            if self.remaining == 0:
                raise FlociError("HTTP headers exceed profile")
            self.sock.settimeout(self.budget.remaining())
            byte = self.stream.read1(1)
            if not byte:
                break
            self.remaining -= 1
            line.extend(byte)
            if byte == b"\n":
                break
        return bytes(line)

    def flush(self):
        self.stream.flush()

    def close(self):
        self.stream.close()


def request(remote, budget, method, path, data, service, body_limit, *, create=False):
    """Fixed internal calls only; no proxies, redirects, SDK or credential discovery."""
    if budget.calls <= 0:
        raise FlociError("Floci invocation call budget exhausted")
    budget.calls -= 1
    host, port = endpoint(remote.endpoint)
    connection = http.client.HTTPConnection(host, port, timeout=budget.remaining())
    response = None
    try:
        connection.connect()
        sock = connection.sock
        sock.settimeout(budget.remaining())

        # Install a bounded header reader without duplicating HTTP syntax parsing.
        def response_class(socket, **kwargs):
            value = http.client.HTTPResponse(socket, **kwargs)
            value.fp = HeaderReader(value.fp, socket, budget)
            return value

        connection.response_class = response_class
        headers = {
            "Connection": "close",
            "Accept-Encoding": "identity",
            "Content-Type": (
                "application/json" if service == "batch" else "application/octet-stream"
            ),
            "Authorization": "AWS4-HMAC-SHA256 Credential=test/19700101/us-east-1/"
            + service
            + "/aws4_request, SignedHeaders=host, Signature=00",
            "X-Amz-Date": "19700101T000000Z",
        }
        if create:
            headers["If-None-Match"] = "*"
        connection.request(method, path, body=data, headers=headers)
        sock.settimeout(budget.remaining())
        response = connection.getresponse()
        response.fp = response.fp.stream
        lengths = response.headers.get_all("Content-Length", [])
        if (
            len(lengths) != 1
            or re.fullmatch(r"0|[1-9][0-9]*", lengths[0]) is None
            or response.headers.get("Transfer-Encoding") is not None
            or response.headers.get_all("Content-Encoding", [])
            not in ([], ["identity"])
        ):
            raise FlociError("unsupported HTTP response framing")
        size = int(lengths[0])
        if size > body_limit:
            raise FlociError("HTTP response exceeds owning profile")
        # Public read1 normally hides bytes after Content-Length. For this explicit
        # Connection:close profile, read to EOF and compare the exact declared count.
        response.length = None
        body = bytearray()
        while True:
            sock.settimeout(budget.remaining())
            chunk = response.read1(min(65536, body_limit + 1 - len(body)))
            if not chunk:
                break
            body.extend(chunk)
            if len(body) > body_limit:
                raise FlociError("HTTP response exceeds owning profile")
        if len(body) != size:
            raise FlociError("HTTP response count mismatch")
        return response.status, bytes(body)
    except (OSError, http.client.HTTPException):
        raise FlociError("Floci HTTP IO failed; remote disposition unknown") from None
    finally:
        try:
            if response is not None:
                response.close()
        finally:
            connection.close()


def batch(remote, budget, action, value):
    status, data = request(
        remote,
        budget,
        "POST",
        "/v1/" + action.lower(),
        encoded(value),
        "batch",
        DESCRIPTOR_BYTES,
    )
    if status != 200:
        raise FlociError("Floci Batch status error")
    return document(data)


def object_path(remote, token, key):
    return "/" + "/".join(
        quote(part, safe="")
        for part in (
            remote.bucket,
            *remote.prefix.split("/"),
            hex_id(token),
            *key.split("/"),
        )
    )


def get_object(remote, budget, token, key, bound):
    status, data = request(
        remote, budget, "GET", object_path(remote, token, key), b"", "s3", bound
    )
    if status == 404:
        return None
    if status != 200:
        raise FlociError("Floci S3 read status error")
    return data


def put_object(remote, budget, token, key, data, *, same=False):
    status, _ = request(
        remote,
        budget,
        "PUT",
        object_path(remote, token, key),
        data,
        "s3",
        DESCRIPTOR_BYTES,
        create=True,
    )
    if status == 412 and same:
        current = get_object(remote, budget, token, key, len(data))
        if current == data:
            return
    elif status == 200:
        return
    raise FlociError("Floci immutable object publication rejected")


def fetch_files(remote, budget, token, prefix, rows):
    files = []
    for row in rows:
        data = get_object(
            remote, budget, token, prefix + "/" + row["name"], limit(row["name"])
        )
        if (
            data is None
            or len(data) != row["size"]
            or hashlib.sha256(data).hexdigest() != row["sha256"]
        ):
            raise FlociError("immutable object missing or bytes differ")
        files.append((row["name"], data))
    return tuple(files)
