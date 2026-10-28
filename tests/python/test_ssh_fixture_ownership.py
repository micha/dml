"""Private fixture error ownership regression; imports never start Docker/SSH."""

import importlib.util
from pathlib import Path
import subprocess
import sys

from daggerml import ssh
import pytest

from test_exchange import ROOT


@pytest.fixture
def fixture_driver(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tests/ssh"))
    spec = importlib.util.spec_from_file_location(
        "progress_fixture", ROOT / "tests/ssh/progress_integration.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("fault", [None, "wait", "status", "release", "writers"])
def test_finally_waits_exited_owner_restores_a_and_checks_writers(
    fixture_driver, tmp_path, monkeypatch, fault
):
    events = []
    offline, caller = tmp_path / "offline", tmp_path / "caller"
    offline.mkdir()
    original = ValueError("original phase assertion")

    class Owner:
        process = None

        def __init__(self):
            self.process = self

        def poll(self):
            return None if fault == "wait" else 0

        def wait(self, timeout):
            events.append("wait")
            if fault == "wait":
                raise subprocess.TimeoutExpired("owned", timeout)
            if fault == "status":
                raise ssh.SSHError("known reaped status")
            return 0

    def release(gate, phase):
        events.append(phase)
        if fault == "release" and phase == "initial":
            raise OSError("gate release")

    def writers():
        events.append("writers")
        if fault == "writers":
            raise AssertionError("remote writer remains")

    monkeypatch.setattr(fixture_driver, "release", release)
    monkeypatch.setattr(fixture_driver, "stopped_writers", writers)
    owner = Owner()
    if fault in ("wait", "release", "writers"):
        with pytest.raises(RuntimeError, match="blocker") as error:
            fixture_driver.finish_execution(
                owner, "/remote/gates", offline, caller, original
            )
        assert error.value.launch is owner and error.value.original_error is original
        assert error.value.cleanup_errors
    else:
        fixture_driver.finish_execution(
            owner, "/remote/gates", offline, caller, original
        )
        if fault == "status":
            assert isinstance(original.transport_cleanup_error, ssh.SSHError)
    assert events == ["initial", "publication", "wait", "writers"]
    assert caller.exists() and not offline.exists()


@pytest.mark.parametrize("fault", ["spawn", "communicate", "check", "cleanup"])
def test_parallel_clients_all_acquired_owners_reaped_on_failure(
    fixture_driver, tmp_path, monkeypatch, fault
):
    acquired = []

    class Reader:
        returncode = 0

        def __init__(self):
            self.number = len(acquired)
            self.calls = 0
            acquired.append(self)

        def communicate(self, timeout):
            self.calls += 1
            if self.number == 0 and (
                (fault == "communicate" and self.calls == 1) or fault == "cleanup"
            ):
                raise subprocess.TimeoutExpired("reader", timeout)
            return (b'{"commit":"right"}' if fault != "check" else b"{}", b"")

    def spawn(*args, **kwargs):
        if acquired and fault == "spawn":
            raise OSError("second spawn")
        return Reader()

    monkeypatch.setattr(fixture_driver.subprocess, "Popen", spawn)
    with pytest.raises(
        (OSError, subprocess.TimeoutExpired, KeyError, RuntimeError)
    ) as error:
        fixture_driver.parallel_readers("script", "saved", tmp_path, "right")
    assert all(reader.calls >= 1 for reader in acquired)
    if fault in ("communicate", "check", "cleanup"):
        assert len(acquired) == 2 and acquired[0].calls >= 2
    if fault == "cleanup":
        assert error.value.processes == tuple(acquired)


@pytest.mark.parametrize(
    "mode", ["matching", "mismatch", "parser-error", "windows-text"]
)
def test_changed_known_hosts_newline_parser_and_fingerprint(
    fixture_driver, tmp_path, monkeypatch, mode
):
    public, hosts = tmp_path / "public.pub", tmp_path / "changed-hosts"
    public.write_text("ssh-ed25519 AAAAFIXTURE comment\n")
    parsed = []
    writing = Path.write_text

    def windows_text(path, text, *args, **kwargs):
        if path == hosts:
            text = text.replace("\n", "\r\n")
        return writing(path, text, *args, **kwargs)

    if mode == "windows-text":
        monkeypatch.setattr(Path, "write_text", windows_text)

    def parse(command, *, timeout):
        assert command[:5] == ["ssh-keygen", "-l", "-E", "sha256", "-f"]
        assert timeout == 10
        path = Path(command[-1])
        parsed.append(path)
        if path == hosts:
            data = path.read_bytes()
            assert data == b"[127.0.0.1]:32769 ssh-ed25519 AAAAFIXTURE\n"
            assert not data.endswith(b"\\n")
            if mode == "parser-error":
                raise subprocess.CalledProcessError(255, command)
            if mode == "mismatch":
                return b"256 SHA256:different (ED25519)\n"
        return b"256 SHA256:fixture (ED25519)\n"

    monkeypatch.setattr(fixture_driver.subprocess, "check_output", parse)
    if mode in ("matching", "windows-text"):
        assert (
            fixture_driver.write_changed_hosts(hosts, 32769, public) == "SHA256:fixture"
        )
    elif mode == "mismatch":
        with pytest.raises(AssertionError, match="fingerprint mismatch"):
            fixture_driver.write_changed_hosts(hosts, 32769, public)
    else:
        with pytest.raises(subprocess.CalledProcessError):
            fixture_driver.write_changed_hosts(hosts, 32769, public)
    assert parsed == [public, hosts]
