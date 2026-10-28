"""Owning read-only inspection, saved SSH identity and fixed progress retrieval.

Transport is private in-process emulation here; installed SSH evidence is separate.
"""

from dataclasses import replace
import builtins
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import daggerml as d
from daggerml import exchange as ex, local, ssh, ssh_worker as worker, transfer
import pytest

from test_caller_requests import caller_job, caller_completed
from test_exchange import exchange_runtime, typed_oracle, bundle_oracle
from test_exchange_progress import observation, observed_form
from test_ssh import (
    remote,
    frame,
    header,
    transport,
    stage,
    local_workspace,
    worker_host_path,
)


@pytest.mark.parametrize("phase", ["initial", "publication", "completion"])
def test_public_inspector_owned_equivalent_no_a_or_executor(
    caller_completed, phase, monkeypatch
):
    path, workspace, spec, state, run = caller_completed
    selected = observation(caller_completed, phase)
    before = (path / "data.mdb").read_bytes()
    importing = transfer.import_commit
    allocated = []

    def only_validation(repository, *args, **kwargs):
        assert Path(repository) != path
        allocated.append(Path(repository).parent)
        return importing(repository, *args, **kwargs)

    with monkeypatch.context() as guard:
        guard.setattr(transfer, "import_commit", only_validation)
        guard.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("no executor"))
        got = ex.read_observation(selected.packet, expected=spec)
    assert got == selected.snapshot and got.ref is None
    assert got.completion is None or got.completion.ref is None
    assert allocated and all(not p.exists() for p in allocated)
    assert (path / "data.mdb").read_bytes() == before
    assert (
        observed_form(
            ex.receive_observation(
                path, packet=selected.packet, expected=spec, ref="received"
            )
        )
        == got
    )
    shutil.rmtree(selected.packet)
    assert got.commit == selected.snapshot.commit  # description remains owned
    with pytest.raises(TypeError):
        ex.read_observation(path, expected=None)


@pytest.mark.parametrize("phase", ["initial", "publication", "completion"])
def test_inspector_cleanup_prevents_success(caller_completed, phase, monkeypatch):
    selected = observation(caller_completed, phase)
    allocated, removing = [], shutil.rmtree

    def deny(path):
        allocated.append(path)
        raise PermissionError("owned scratch cleanup")

    before = (caller_completed[0] / "data.mdb").read_bytes()
    with monkeypatch.context() as guard:
        guard.setattr(ex.shutil, "rmtree", deny)
        with pytest.raises(PermissionError):
            ex.read_observation(selected.packet, expected=caller_completed[2])
    for path in allocated:
        removing(path)
    assert len(allocated) == 1
    assert (caller_completed[0] / "data.mdb").read_bytes() == before


def test_saved_identity_with_every_endpoint_input_control_offline(
    caller_job, tmp_path, monkeypatch
):
    handle = ssh.SSHExchange(
        remote(tmp_path), caller_job[2], tmp_path / "absent-control"
    )
    saved = tmp_path / "saved"
    monkeypatch.setattr(
        subprocess, "Popen", lambda *a, **k: pytest.fail("save/load never connects")
    )
    ssh.save_ssh_exchange(saved, handle)
    caller_job[0].rename(tmp_path / "offline-a")
    caller_job[1].rename(tmp_path / "offline-input")
    got = ssh.load_ssh_exchange(saved)
    assert got == handle and got.workspace == handle.workspace
    assert set(p.name for p in saved.iterdir()) == {"expected.json", "ssh.json"}
    document = json.loads((saved / "ssh.json").read_bytes())
    assert set(document) == {"format", *ssh._REMOTE_FIELDS}
    assert not handle.control.exists()
    with pytest.raises(FileExistsError):
        ssh.save_ssh_exchange(saved, handle)
    with pytest.raises(TypeError):
        ssh.save_ssh_exchange(tmp_path / "wrong", None)


@pytest.mark.parametrize(
    "data",
    [
        b"{}",
        b"[]",
        b'{"format":"a","format":"b"}',
        b'{"x":NaN}',
        b"\xff",
        b"\xef\xbb\xbf{}",
        b"{}{}",
        b"[" * 1500 + b"]" * 1500,
        b"x" * 8193,
    ],
    ids=[
        "missing",
        "array",
        "duplicate",
        "constant",
        "utf8",
        "bom",
        "trailing",
        "deep",
        "oversize",
    ],
)
def test_saved_metadata_malformed(caller_job, tmp_path, data):
    saved = tmp_path / "saved"
    ssh.save_ssh_exchange(
        saved, ssh.SSHExchange(remote(tmp_path), caller_job[2], tmp_path / "control")
    )
    (saved / "ssh.json").write_bytes(data)
    with pytest.raises(ssh.SSHError):
        ssh.load_ssh_exchange(saved)


@pytest.mark.parametrize(
    "field,value",
    [
        ("format", "other"),
        ("extra", 1),
        ("port", True),
        ("identity_file", 1),
        ("known_hosts_file", None),
        ("python", "C:/python"),
        ("host", "-option"),
    ],
)
def test_saved_metadata_strict_fields(caller_job, tmp_path, field, value):
    saved = tmp_path / "saved"
    ssh.save_ssh_exchange(
        saved, ssh.SSHExchange(remote(tmp_path), caller_job[2], tmp_path / "control")
    )
    document = json.loads((saved / "ssh.json").read_bytes())
    document[field] = value
    (saved / "ssh.json").write_text(json.dumps(document))
    with pytest.raises((ssh.SSHError, TypeError)):
        ssh.load_ssh_exchange(saved)


@pytest.mark.parametrize("missing", ["expected.json", "ssh.json"])
def test_partial_saved_directory_never_repairs(caller_job, tmp_path, missing):
    saved = tmp_path / "saved"
    ssh.save_ssh_exchange(
        saved, ssh.SSHExchange(remote(tmp_path), caller_job[2], tmp_path / "control")
    )
    (saved / missing).unlink()
    with pytest.raises(FileNotFoundError):
        ssh.load_ssh_exchange(saved)
    with pytest.raises(FileExistsError):
        ssh.save_ssh_exchange(
            saved,
            ssh.SSHExchange(remote(tmp_path), caller_job[2], tmp_path / "control"),
        )


@pytest.mark.parametrize("phase", ["initial", "publication", "completion"])
def test_fixed_observe_validates_packet_readonly_fresh_saved_client(
    caller_job, transport, phase, monkeypatch
):
    path, _, spec, state, _ = caller_job
    handle = stage(caller_job, transport)
    ssh.execute_ssh_exchange(handle, timeout_ms=10000)
    workspace = local_workspace(handle)
    with d.Repository(workspace / "worker.dml") as repo, repo.write() as tx:
        final = tx.get_ref("work")
        pre, publication = tx.get_commit(final).parents
        aid = next(
            n for n in tx.get_tree(tx.get_commit(pre).tree) if n.startswith("attempt-")
        )
        if phase != "completion":
            tx.update_ref("work", pre)
            if phase == "initial":
                tx.update_ref(aid, pre)
    before_a = (path / "data.mdb").read_bytes()
    before_b = (workspace / "worker.dml/data.mdb").read_bytes()
    saved = path.parent / "saved"
    ssh.save_ssh_exchange(saved, handle)
    for name in ("output.bundle", "completion.json", "input.bundle"):
        (workspace / name).unlink()
    for name in ("run_request", "run_step", "retry_step"):
        monkeypatch.setattr(
            local, name, lambda *a, **k: pytest.fail("observe never executes")
        )
    got = ssh.observe_ssh_exchange(
        ssh.load_ssh_exchange(saved), packet=path.parent / "progress", timeout_ms=10000
    )
    assert got.phase == phase and got.lifecycle == (
        "done" if phase == "completion" else "working"
    )
    assert got.snapshot == ex.read_observation(got.packet, expected=spec)
    assert got.snapshot.request == spec.request
    assert bundle_oracle(got.packet / "snapshot.bundle") == typed_oracle(
        workspace / "worker.dml", (got.snapshot.commit,)
    )
    assert (path / "data.mdb").read_bytes() == before_a
    assert (workspace / "worker.dml/data.mdb").read_bytes() == before_b
    with pytest.raises(FileExistsError):
        ssh.observe_ssh_exchange(handle, packet=got.packet, timeout_ms=10000)
    received = ex.receive_observation(
        path, packet=got.packet, expected=spec, ref="progress"
    )
    assert observed_form(received) == got.snapshot


def test_fixed_bootstrap_does_not_allocate_packet(caller_job, transport):
    handle = stage(caller_job, transport)
    packet = handle.control.with_name("packet")
    got = ssh.observe_ssh_exchange(handle, packet=packet, timeout_ms=10000)
    assert got == ex.ExchangeObservation("working", "bootstrap", None, None)
    assert not packet.exists()
    assert not (local_workspace(handle) / "started").exists()
    with pytest.raises(TypeError):
        ssh.observe_ssh_exchange(None, packet=packet, timeout_ms=1)


@pytest.mark.parametrize("reply", ["bootstrap", "observation"])
def test_observe_framing_original_limits(reply):
    bodies = (
        (b"j" * 8192,)
        if reply == "bootstrap"
        else (b"j" * 8192, b"o" * 8192, b"b" * transfer.MAX_BUNDLE_BYTES)
    )
    assert ssh._read_frame(io.BytesIO(frame(reply, bodies)), "observe") == (
        reply,
        bodies,
    )
    for position in range(len(bodies)):
        values = list(bodies)
        values[position] += b"x"
        with pytest.raises(ssh.SSHError):
            frame(reply, tuple(values))
    for suffix in (b"extra",):
        with pytest.raises(ssh.SSHError):
            ssh._read_frame(io.BytesIO(frame(reply, bodies) + suffix), "observe")
    with pytest.raises(ssh.SSHError):
        ssh._read_frame(io.BytesIO(frame(reply, bodies)[:-1]), "observe")


@pytest.mark.parametrize(
    "document",
    [
        None,
        {},
        {"format": "daggerml-ssh-fetch-v1", "sizes": [0, 0, 0]},
        {"format": "daggerml-ssh-bootstrap-v1", "sizes": [True]},
        {"format": "daggerml-ssh-observation-v1", "sizes": [0, 0]},
        {"format": "daggerml-ssh-observation-v1", "sizes": [0, 8193, 0]},
        {"format": "daggerml-ssh-bootstrap-v1", "sizes": [0], "done": True},
    ],
)
def test_observe_framing_wrong_claims_never_done(document):
    with pytest.raises(ssh.SSHError):
        ssh._read_frame(io.BytesIO(header(document)), "observe")


@pytest.mark.parametrize("name", ["snapshot.bundle", "job.json", "observation.json"])
def test_observe_packet_write_failure_retains_partial_no_success(
    caller_job, transport, monkeypatch, name
):
    handle = stage(caller_job, transport)
    ssh.execute_ssh_exchange(handle, timeout_ms=10000)
    packet = handle.control.with_name("partial")
    opening = builtins.open

    def deny(file, mode="r", *args, **kwargs):
        if Path(file) == packet / name and mode == "xb":
            raise OSError("packet IO")
        return opening(file, mode, *args, **kwargs)

    before = (caller_job[0] / "data.mdb").read_bytes()
    monkeypatch.setattr(builtins, "open", deny)
    with pytest.raises(OSError):
        ssh.observe_ssh_exchange(handle, packet=packet, timeout_ms=10000)
    assert packet.exists() and not (packet / "observation.json").exists()
    assert (caller_job[0] / "data.mdb").read_bytes() == before


@pytest.mark.parametrize("boundary", [8192, 8193])
def test_saved_metadata_original_budget_before_directory(
    caller_job, tmp_path, boundary
):
    # Fixed metadata encoding overhead plus a long valid POSIX root. Original
    # descriptor budget, not a substituted small limit; no filesystem root opened.
    handle = ssh.SSHExchange(remote(tmp_path), caller_job[2], tmp_path / "control")
    document = {"format": ssh.SAVED_FORMAT}
    document.update(
        (
            name,
            (
                str(getattr(handle.remote, name))
                if name.endswith("_file")
                else getattr(handle.remote, name)
            ),
        )
        for name in ssh._REMOTE_FIELDS
    )
    size = len(json.dumps(document, ensure_ascii=True, separators=(",", ":")).encode())
    selected = replace(
        handle,
        remote=replace(
            handle.remote,
            workspace_root=handle.remote.workspace_root + "x" * (boundary - size),
        ),
    )
    target = tmp_path / "saved"
    if boundary == 8193:
        with pytest.raises(ssh.SSHError, match="exceeds"):
            ssh.save_ssh_exchange(target, selected)
        assert not target.exists()
    else:
        ssh.save_ssh_exchange(target, selected)
        assert (target / "ssh.json").stat().st_size == 8192
        assert ssh.load_ssh_exchange(target) == selected


@pytest.mark.parametrize("reply", ["bootstrap", "observation"])
def test_wrong_transport_job_rejects_before_host_packet(
    caller_job, transport, monkeypatch, reply
):
    handle = stage(caller_job, transport)
    document = json.loads((caller_job[1] / "job.json").read_bytes())
    document["token"] = "e" * 32
    descriptor = json.dumps(document).encode()
    bodies = (descriptor,) if reply == "bootstrap" else (descriptor, b"{}", b"{}")
    monkeypatch.setattr(ssh, "_invoke", lambda *a: (reply, bodies))
    packet = handle.control.with_name("packet")
    with pytest.raises(ssh.SSHError, match="observed job differs"):
        ssh.observe_ssh_exchange(handle, packet=packet, timeout_ms=1)
    assert not packet.exists()


def test_remote_packet_selection_change_rejects_before_reply(
    caller_job, transport, monkeypatch
):
    handle = stage(caller_job, transport)
    ssh.execute_ssh_exchange(handle, timeout_ms=10000)
    observing = ex.observe_exchange

    def changed(*args, **kwargs):
        result = observing(*args, **kwargs)
        document = json.loads((result.packet / "job.json").read_bytes())
        document["token"] = "e" * 32
        (result.packet / "job.json").write_text(json.dumps(document))
        return result

    monkeypatch.setattr(ex, "observe_exchange", changed)
    output = io.BytesIO()
    with pytest.raises(ssh.SSHError, match="owned selection"):
        worker.serve("observe", local_workspace(handle), io.BytesIO(), output)
    assert output.getvalue() == b""


@pytest.mark.parametrize("endpoint", ["host", "remote"])
def test_observe_temporary_packet_cleanup_error_no_success(
    caller_job, transport, monkeypatch, endpoint
):
    handle = stage(caller_job, transport)
    ssh.execute_ssh_exchange(handle, timeout_ms=10000)
    allocated, removing = [], shutil.rmtree
    prefix = "dml-ssh-observation-" if endpoint == "host" else "dml-ssh-observe-"

    def deny(directory, *args, **kwargs):
        if Path(directory).name.startswith(prefix):
            allocated.append(directory)
            raise PermissionError("packet scratch cleanup")
        return removing(directory, *args, **kwargs)

    packet = handle.control.with_name("packet")
    before = (caller_job[0] / "data.mdb").read_bytes()
    with monkeypatch.context() as guard:
        guard.setattr(shutil, "rmtree", deny)
        if endpoint == "host":
            with pytest.raises(PermissionError):
                ssh.observe_ssh_exchange(handle, packet=packet, timeout_ms=10000)
        else:
            output = io.BytesIO()
            with pytest.raises(PermissionError):
                worker.serve("observe", local_workspace(handle), io.BytesIO(), output)
            assert output.getvalue() == b""
    for directory in allocated:
        removing(directory)
    assert len(allocated) == 1 and not packet.exists()
    assert (caller_job[0] / "data.mdb").read_bytes() == before


def test_ssh_helper_selected_immutable_pin_survives_ref_advance(
    caller_job, transport, monkeypatch
):
    handle = stage(caller_job, transport)
    ssh.execute_ssh_exchange(handle, timeout_ms=10000)
    source = local_workspace(handle) / "worker.dml"
    with d.Repository(source) as repo, repo.write() as tx:
        final = tx.get_ref("work")
        pre, publication = tx.get_commit(final).parents
        aid = next(
            name
            for name in tx.get_tree(tx.get_commit(pre).tree)
            if name.startswith("attempt-")
        )
        tx.update_ref("work", pre)
        tx.update_ref(aid, pre)
    exporting = transfer.export_commit
    moved = []

    def advance(repository, *, commit):
        if Path(repository) == source:
            assert commit == pre
            with d.Repository(source) as repo, repo.write() as tx:
                tx.update_ref("work", final)
                tx.update_ref(aid, publication)
            moved.append(True)
        return exporting(repository, commit=commit)

    with monkeypatch.context() as guard:
        guard.setattr(transfer, "export_commit", advance)
        selected = ssh.observe_ssh_exchange(
            handle, packet=handle.control.with_name("pinned"), timeout_ms=10000
        )
    assert moved == [True] and selected.snapshot.commit == pre
    assert bundle_oracle(selected.packet / "snapshot.bundle") == typed_oracle(
        source, (pre,)
    )
    newer = ssh.observe_ssh_exchange(
        handle, packet=handle.control.with_name("newer"), timeout_ms=10000
    )
    assert newer.snapshot.commit == final and newer.lifecycle == "done"


def test_observe_shutdown_uncertainty_retains_its_client_not_execution_owner(
    caller_job, tmp_path, monkeypatch
):
    control = tmp_path / "control"
    control.mkdir()
    handle = ssh.SSHExchange(remote(tmp_path), caller_job[2], control)
    streams = []
    events = []

    class ObservationClient:
        def __init__(self, command, **kwargs):
            streams.extend(kwargs[name] for name in ("stdin", "stdout", "stderr"))

        def wait(self, timeout):
            events.append("wait")
            raise subprocess.TimeoutExpired("observation", timeout)

        def poll(self):
            return None

        def terminate(self):
            events.append("terminate")

        def kill(self):
            events.append("kill")

    monkeypatch.setattr(subprocess, "Popen", ObservationClient)
    with pytest.raises(ssh.SSHError, match="caller must reap") as error:
        ssh.observe_ssh_exchange(handle, packet=tmp_path / "packet", timeout_ms=1)
    assert isinstance(error.value.process, ObservationClient)
    assert events == ["wait", "terminate", "wait", "kill", "wait"]
    assert all(stream.closed for stream in streams)
    assert not (control / "dispatched").exists()
    assert not (tmp_path / "packet").exists()
