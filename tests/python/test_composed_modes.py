"""Finite maintained host modes over public APIs; transport substitutions labelled."""

from dataclasses import asdict
import json
import runpy
import sys

import daggerml as d
from daggerml import floci as f, local
import pytest

from test_composed_execution import producer, execute, example, REMOTE
from test_exchange import ROOT, exchange_runtime
from test_floci import service


def save_job(path, selected):
    job = f.FlociJob(
        REMOTE,
        selected[1],
        path.parent / "inert-control",
        "12345678-1234-1234-1234-123456789abc",
    )
    f.save_floci_job(path, job)


def test_basis_summary_modes_validate_saved_independent_selection(producer, capsys):
    path, base, first = producer
    saved = path.parent / "saved-first"
    save_job(saved, first)
    config = path.parent / "remote.json"
    config.write_text(json.dumps(asdict(REMOTE)))
    assert (
        example.main(
            ["basis", str(path), str(saved), str(first[0]), str(config), "gates/double"]
        )
        == 0
    )
    authored = json.loads(capsys.readouterr().out)
    second = execute(
        path,
        d.ObjectId.from_hex(authored["commit"]),
        "double",
        "double-binding",
        "double-inputs",
    )
    second_saved = path.parent / "saved-second"
    save_job(second_saved, second)
    assert (
        example.main(
            [
                "summary",
                str(path),
                str(saved),
                str(first[0]),
                str(second_saved),
                str(second[0]),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["ref"] == "experiment-result"


def test_init_request_submit_observe_modes_no_implicit_sequence(
    tmp_path, service, exchange_runtime, monkeypatch, capsys
):
    # Private native-host binding adaptation only. Config stays POSIX/unchanged.
    original = local.put_local_binding

    def host(tx, **kwargs):
        if kwargs["interpreter"] == "/opt/dml/bin/python":
            kwargs["interpreter"] = sys.executable
        return original(tx, **kwargs)

    monkeypatch.setattr(local, "put_local_binding", host)
    config = tmp_path / "remote.json"
    config.write_text(json.dumps(asdict(service.remote)))
    path = tmp_path / "A"
    source = tmp_path / "source.py"
    source.write_bytes(b"pass\n")
    assert (
        example.main(
            ["init", str(path), str(config), str(source), str(source), "gates/add"]
        )
        == 0
    )
    base = json.loads(capsys.readouterr().out)["commit"]
    step = tmp_path / "step"
    assert (
        example.main(
            [
                "request",
                str(path),
                str(step),
                str(config),
                base,
                "add-binding",
                "add-inputs",
                "urn:example:add",
                "submission",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["request"]
    assert service.body is None
    assert example.main(["submit", str(step)]) == 0
    assert json.loads(capsys.readouterr().out)["job_id"]
    assert (
        example.main(["observe", str(step / "saved"), str(tmp_path / "bootstrap")]) == 0
    )
    assert json.loads(capsys.readouterr().out)["phase"] == "bootstrap"
    assert not (tmp_path / "bootstrap").exists()
    config.write_bytes(b"x" * 8193)
    with pytest.raises(ValueError, match="configuration exceeds"):
        example.main(
            [
                "init",
                str(tmp_path / "bad"),
                str(config),
                str(source),
                str(source),
                "gates/add",
            ]
        )


def test_mode_entry_is_finite_parser_only_without_arguments(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["composed_execution.py"])
    with pytest.raises(SystemExit) as error:
        runpy.run_path(
            str(ROOT / "examples/composed_execution.py"), run_name="__main__"
        )
    assert error.value.code == 2
