"""Synchronous caller-Q SSH transport; Docker is not a runtime dependency.

Fetch supplies transport candidates only. Existing exchange.receive_exchange owns
exact-history validation and atomic publication. See docs/spec-next/ssh-execution.md.
"""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import struct
import subprocess
import tempfile
import unicodedata

from . import exchange, transfer

__all__ = [
    "SSHRemote",
    "SSHExchange",
    "SSHError",
    "stage_ssh_exchange",
    "execute_ssh_exchange",
    "fetch_ssh_exchange",
]

SHUTDOWN_SECONDS = 5
FRAME_FORMAT = "daggerml-ssh-{}-v1"


class SSHError(ValueError):
    """Transport failure is not a computational outcome or permission to retry.

    Only a failed local-client shutdown retains ``process`` for explicit caller
    ownership/reaping. It is never a remote process or execution authority.
    """

    def __init__(self, message, *, process=None):
        self.process = process
        super().__init__(message)


def _text(value):
    if type(value) is not str:
        raise TypeError("SSH configuration requires str")
    value.encode("utf-8")
    if (
        not value
        or any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value)
        or unicodedata.normalize("NFC", value) != value
    ):
        raise SSHError("SSH spelling must be nonempty NFC without controls")
    return value


def _posix_path(value):
    value = _text(value)
    path = PurePosixPath(value)
    if not value.startswith("/") or value.startswith("//") or ".." in path.parts:
        raise SSHError("remote path requires an absolute POSIX spelling without ..")
    if str(path) != value:
        raise SSHError("remote path must already be normalized")
    return value


def _path(value):
    value = _text(os.fsdecode(os.fspath(value)))
    return Path(os.path.abspath(value))


def _credential(value):
    path = _path(value)
    # OpenSSH performs token/environment expansion, even with shell=False.
    if any(c in path.as_posix() for c in '%$"\\'):
        raise SSHError("credential path contains SSH expansion/config characters")
    return path


def _timeout(value):
    if type(value) is not int:
        raise TypeError("timeout_ms requires int")
    if not 1 <= value <= 3600000:
        raise SSHError("timeout_ms must be in 1..3600000")
    return value


def _expected(value):
    if not isinstance(value, exchange.ExchangeSpec):
        raise TypeError("expected requires ExchangeSpec")
    if value.request is None:
        raise SSHError("SSH exchange requires a caller-recorded request")
    return value


@dataclass(frozen=True)
class SSHRemote:
    host: str
    port: int
    user: str
    identity_file: Path
    known_hosts_file: Path
    python: str
    workspace_root: str

    def __post_init__(self):
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.:-]*", _text(self.host)) is None:
            raise SSHError("invalid SSH host")
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", _text(self.user)) is None:
            raise SSHError("invalid SSH user")
        if type(self.port) is not int:
            raise TypeError("port requires int")
        if not 1 <= self.port <= 65535:
            raise SSHError("port must be in 1..65535")
        for field in ("identity_file", "known_hosts_file"):
            object.__setattr__(self, field, _credential(getattr(self, field)))
        _posix_path(self.python)
        _posix_path(self.workspace_root)


@dataclass(frozen=True)
class SSHExchange:
    remote: SSHRemote
    expected: exchange.ExchangeSpec
    control: Path

    def __post_init__(self):
        if not isinstance(self.remote, SSHRemote):
            raise TypeError("remote requires SSHRemote")
        _expected(self.expected)
        object.__setattr__(self, "control", _path(self.control))

    @property
    def workspace(self) -> str:
        return str(PurePosixPath(self.remote.workspace_root) / self.expected.token)


def _argv(job, action, timeout_ms):
    remote = job.remote
    command = " ".join(
        shlex.quote(token)
        for token in (remote.python, "-m", "daggerml.ssh_worker", action, job.workspace)
    )
    return [
        "ssh",
        "-F",
        "none",
        "-T",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "IdentityAgent=none",
        "-o",
        'UserKnownHostsFile="' + remote.known_hosts_file.as_posix() + '"',
        "-o",
        "GlobalKnownHostsFile=none",
        "-o",
        "UpdateHostKeys=no",
        "-o",
        "PasswordAuthentication=no",
        "-o",
        "KbdInteractiveAuthentication=no",
        "-o",
        "PreferredAuthentications=publickey",
        "-o",
        "ClearAllForwardings=yes",
        "-o",
        "ForwardAgent=no",
        "-o",
        "ForwardX11=no",
        "-o",
        "ProxyCommand=none",
        "-o",
        "ProxyJump=none",
        "-o",
        "ConnectionAttempts=1",
        "-o",
        "ConnectTimeout=" + str((timeout_ms + 999) // 1000),
        "-i",
        remote.identity_file.as_posix(),
        "-p",
        str(remote.port),
        "-l",
        remote.user,
        remote.host,
        command,
    ]


def _limits(action):
    if action == "stage":
        return (exchange.MAX_DESCRIPTOR_BYTES, transfer.MAX_BUNDLE_BYTES)
    if action == "fetch":
        return (
            exchange.MAX_DESCRIPTOR_BYTES,
            exchange.MAX_DESCRIPTOR_BYTES,
            transfer.MAX_BUNDLE_BYTES,
        )
    if action == "ack":
        return ()
    raise SSHError("unsupported frame action")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SSHError("duplicate frame field")
        result[key] = value
    return result


def _constant(_):
    raise SSHError("nonstandard frame constant")


def _exact(stream, size):
    result = bytearray()
    while len(result) < size:
        chunk = stream.read(size - len(result))
        if not chunk:
            raise SSHError("truncated SSH frame")
        result.extend(chunk)
    return bytes(result)


def _eof(stream):
    if stream.read(1):
        raise SSHError("extra SSH frame bytes or startup noise")


def _read_frame(stream, action):
    size = struct.unpack(">I", _exact(stream, 4))[0]
    if not 1 <= size <= exchange.MAX_DESCRIPTOR_BYTES:
        raise SSHError("SSH frame header exceeds profile")
    try:
        header = json.loads(
            _exact(stream, size).decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_constant,
        )
    except (ValueError, RecursionError):
        raise SSHError("invalid SSH frame header") from None
    limits = _limits(action)
    if (
        type(header) is not dict
        or set(header) != {"format", "sizes"}
        or header["format"] != FRAME_FORMAT.format(action)
        or type(header["sizes"]) is not list
        or len(header["sizes"]) != len(limits)
    ):
        raise SSHError("unexpected SSH frame fields/format")
    sizes = header["sizes"]
    if any(
        type(n) is not int or not 0 <= n <= limit for n, limit in zip(sizes, limits)
    ):
        raise SSHError("SSH frame body exceeds profile")
    bodies = tuple(_exact(stream, n) for n in sizes)
    _eof(stream)
    return bodies


def _write_frame(stream, action, bodies):
    limits = _limits(action)
    if len(bodies) != len(limits) or any(
        type(b) is not bytes or len(b) > limit for b, limit in zip(bodies, limits)
    ):
        raise SSHError("SSH frame body exceeds profile")
    header = json.dumps(
        {"format": FRAME_FORMAT.format(action), "sizes": [len(b) for b in bodies]},
        separators=(",", ":"),
    ).encode("utf-8")
    stream.write(struct.pack(">I", len(header)))
    stream.write(header)
    for body in bodies:
        stream.write(body)


def _read_file(path, limit):
    with open(path, "rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise SSHError("SSH file exceeds profile")
    return data


def _owned_spec(data):
    # Exchange owns its job codec. Parse these exact owned bytes, not a second read
    # of a possibly different descriptor. Temporary scratch is never a B repository.
    with tempfile.TemporaryDirectory(prefix="dml-ssh-job-") as temporary:
        path = Path(temporary)
        (path / "job.json").write_bytes(data)
        return exchange.read_exchange_spec(path)


def _shutdown(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=SHUTDOWN_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=SHUTDOWN_SECONDS)


def _invoke(job, action, timeout_ms, bodies=()):
    timeout_ms = _timeout(timeout_ms)
    command = _argv(job, action, timeout_ms)
    # File streams avoid blocked parent pipe writes and unread stderr deadlocks.
    # Logs are retained; timeouts do not impose disk quotas or remote reaping.
    with ExitStack() as stack:
        streams = [
            stack.enter_context(
                tempfile.NamedTemporaryFile(
                    dir=job.control, prefix=action + "." + name + ".", delete=False
                )
            )
            for name in ("stdin", "stdout", "stderr")
        ]
        stdin, stdout, stderr = streams
        if action == "stage":
            _write_frame(stdin, action, bodies)
        stdin.flush()
        stdin.seek(0)
        # This guard survives spawn, authentication, timeout and response loss.
        if action == "execute":
            try:
                with open(job.control / "dispatched", "xb"):
                    pass
            except FileExistsError:
                raise SSHError(
                    "SSH exchange already dispatched; no automatic relaunch"
                ) from None
        process = subprocess.Popen(
            command, stdin=stdin, stdout=stdout, stderr=stderr, shell=False
        )
        try:
            status = process.wait(timeout=timeout_ms / 1000)
        except BaseException:
            try:
                _shutdown(process)
            except BaseException as cleanup:
                raise SSHError(
                    "local SSH client disposition unknown; caller must reap; remote outcome unknown",
                    process=process,
                ) from cleanup
            raise
        if status != 0:
            raise SSHError(
                "SSH invocation failed (status {}); remote outcome unknown".format(
                    status
                )
            )
        stdout.seek(0)
        if action == "execute":
            _eof(stdout)
            return ()
        return _read_frame(stdout, "ack" if action == "stage" else "fetch")


def stage_ssh_exchange(
    remote: SSHRemote,
    *,
    workspace,
    expected: exchange.ExchangeSpec,
    control,
    timeout_ms: int,
) -> SSHExchange:
    """Stage exact caller-Q bytes exclusively; no B initialization/dispatch."""
    _timeout(timeout_ms)
    job = SSHExchange(remote, expected, control)
    workspace = _path(workspace)
    descriptor = _read_file(workspace / "job.json", exchange.MAX_DESCRIPTOR_BYTES)
    if _owned_spec(descriptor) != job.expected:
        raise SSHError("job differs from caller expected selection")
    bundle = _read_file(workspace / "input.bundle", transfer.MAX_BUNDLE_BYTES)
    job.control.mkdir()
    _invoke(job, "stage", timeout_ms, (descriptor, bundle))
    return job


def execute_ssh_exchange(job: SSHExchange, *, timeout_ms: int) -> None:
    """One fixed synchronous invocation; status is not computational outcome."""
    if not isinstance(job, SSHExchange):
        raise TypeError("job requires SSHExchange")
    _invoke(job, "execute", timeout_ms)


def fetch_ssh_exchange(job: SSHExchange, *, packet, timeout_ms: int) -> Path:
    """Fetch closed fixed files only; authoritative receive remains separate."""
    if not isinstance(job, SSHExchange):
        raise TypeError("job requires SSHExchange")
    packet = _path(packet)
    descriptor, completion, bundle = _invoke(job, "fetch", timeout_ms)
    if _owned_spec(descriptor) != job.expected:
        raise SSHError("fetched job differs from caller expected selection")
    packet.mkdir()
    # Owned complete bytes before allocation; receipt last, partial files retained.
    for name, data in (
        ("output.bundle", bundle),
        ("job.json", descriptor),
        ("completion.json", completion),
    ):
        with open(packet / name, "xb") as stream:
            stream.write(data)
    return packet
