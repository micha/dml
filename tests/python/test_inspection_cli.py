import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import daggerml as dml
from hypothesis import given, settings, strategies as st
import pytest

from test_history import overwrite
from test_python_api import snapshot

ROOT = Path(__file__).resolve().parents[2]
BIN = Path(os.environ.get("DML_BIN", ROOT / "build/check/dml")).resolve()


def cli(path, *args, json_mode=True):
    return subprocess.run([str(BIN), *(["--json"] if json_mode else []), "--repo", str(path), *args],
                          capture_output=True, text=True, encoding="utf-8")


def success(path, *args):
    result = cli(path, *args)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    return json.loads(result.stdout)


def test_snapshot_history_shows_all_types_and_immutable_data(tmp_path):
    path = tmp_path / "repository with spaces"
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            first = snapshot(tx, 42)
            tx.create_ref("main", first["commit"])
            frozen = {kind: tx.get_record(kind, identity) for kind, identity in first.items()}
        with repo.write() as tx:
            second = snapshot(tx, 43, [first["commit"]])
            tx.update_ref("main", second["commit"])
            third = snapshot(tx, 44, [first["commit"]])
            tx.create_ref("branch", third["commit"])
            joined = tx.put_commit(second["tree"], parents=[second["commit"], third["commit"]])
            tx.create_ref("joined", joined)
    assert success(path, "ref", "get", "main")["target"] == str(second["commit"])
    assert success(path, "snapshot", "--ref", "main")["entries"][0]["preview"]["value"] == "43"
    assert success(path, "snapshot", "--commit", str(first["commit"]))["entries"][0]["preview"]["value"] == "42"
    for kind, identity in second.items():
        result = success(path, "show", kind, str(identity))
        assert result["type"] == kind and result["id"] == str(identity)
    assert success(path, "show", "node", str(second["node"]))["kind"] == "literal"
    assert success(path, "show", "dag", str(second["dag"]))["root"] == str(second["node"])
    assert success(path, "show", "commit", str(second["commit"]))["parents"] == [str(first["commit"])]
    assert success(path, "show", "tree", str(second["tree"]))["entries"] == [{"name": "example", "dag": str(second["dag"])}]
    expected = [joined, second["commit"], first["commit"], third["commit"]]
    result = success(path, "log", "--ref", "joined")
    assert [item["id"] for item in result["commits"]] == [str(item) for item in expected]
    assert not result["truncated"]
    for limit in range(1, 6):
        result = success(path, "log", "--limit", str(limit), "--commit", str(joined))
        assert [item["id"] for item in result["commits"]] == [str(item) for item in expected[:limit]]
        assert result["truncated"] == (limit < 4)
    human = cli(path, "snapshot", "--ref", "main", json_mode=False)
    assert human.returncode == 0 and human.stderr == ""
    assert human.stdout.startswith("Snapshot\n{\n")
    assert '\n  "commit": ' in human.stdout and '"value": "43"' in human.stdout
    with dml.Repository(path) as repo:
        with repo.read() as tx:
            for kind, identity in first.items():
                assert tx.get_record(kind, identity) == frozen[kind]
            assert tx.get_ref("main") == second["commit"]


@pytest.mark.parametrize("value,kind,expected", [
    (None, "null", None), (True, "bool", True), (False, "bool", False),
    (-(2**63), "i64", str(-(2**63))), (2**63-1, "i64", str(2**63-1)),
    (0.0, "f64", "0"), (-0.0, "f64", "0"), (0.25, "f64", "0.25"),
    (float("nan"), "f64", "nan"), (float("inf"), "f64", "inf"),
    (-float("inf"), "f64", "-inf"), (b"\0\xff", "bytes", "00ff"),
    ('a"\\\n\x1b\x7f\u0085\u009b', "string", 'a"\\\n\x1b\x7f\u0085\u009b'),
    ("\u00a0", "string", "\u00a0"),
    (dml.Datum.uri("https://example.org/"), "uri", "https://example.org/"),
])
def test_json_datum_values_and_human_escaping(tmp_path, value, kind, expected):
    path = tmp_path / "repo"
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            identity = tx.put_datum(value)
    result = success(path, "show", "datum", str(identity))["datum"]
    assert result["kind"] == kind and result["value"] == expected
    if kind == "bytes":
        assert result["encoding"] == "hex"
    human = cli(path, "show", "datum", str(identity), json_mode=False)
    assert human.returncode == 0
    assert "\x1b" not in human.stdout and "\u0085" not in human.stdout and "\u009b" not in human.stdout
    if kind == "string" and "\u0085" in expected:
        assert "\\u0085" in human.stdout and "\\u009b" in human.stdout


def test_previews_collections_order_and_limits(tmp_path):
    path = tmp_path / "repo"
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            children = [tx.put_datum(i) for i in range(12)]
            values = {"text": "é" * 90, "bytes": bytes(range(40)),
                      "list": dml.Datum.list(children), "set": dml.Datum.set(children),
                      "map": dml.Datum.map(list(zip(children, children)))}
            entries = {}
            ids = {}
            for name, value in values.items():
                datum_id = tx.put_datum(value); ids[name] = datum_id
                entries[name] = tx.put_dag(root=tx.put_literal(datum_id))
            tree = tx.put_tree(list(reversed(list(entries.items()))))
            commit = tx.put_commit(tree); tx.create_ref("main", commit)
    result = success(path, "snapshot", "--ref", "main")
    assert [entry["name"] for entry in result["entries"]] == sorted(entries)
    for entry in result["entries"]:
        preview = entry["preview"]
        assert preview["truncated"]
        assert len(preview["value"]) == {"bytes": 64, "list": 8, "map": 8, "set": 8, "text": 80}[entry["name"]]
    assert result["entry_count"] == 5 and not result["truncated"]
    assert len(success(path, "show", "tree", str(tree))["entries"]) == 5
    assert success(path, "snapshot", "--ref", "main", "--limit", "2")["truncated"]
    for name in ["list", "set", "map"]:
        full = success(path, "show", "datum", str(ids[name]))["datum"]
        assert len(full["value"]) == 12
        human = cli(path, "show", "datum", str(ids[name]), json_mode=False)
        assert human.returncode == 0 and '"truncated": true' in human.stdout
    with dml.Repository(path) as repo:
        with repo.write() as tx:
            empty = tx.put_commit(tx.put_tree({})); tx.create_ref("empty", empty)
            short = tx.put_datum(dml.Datum.list([]))
    assert '"truncated": false' in cli(path, "show", "datum", str(short), json_mode=False).stdout
    assert success(path, "snapshot", "--ref", "empty")["entries"] == []


@pytest.mark.parametrize("args", [
    [], ["init"], ["ref"], ["ref", "create", "main"], ["show", "unknown", "0"*32],
    ["show", "datum"], ["show", "datum", "A"*32], ["snapshot"],
    ["snapshot", "--ref", "main", "--commit", "0"*32], ["log", "--ref"],
    ["log", "--commit", "bad"], ["snapshot", "--ref", "main", "--limit", "0"],
    ["log", "--ref", "main", "--limit", "-1"], ["log", "--ref", "main", "--limit", "1.5"],
    ["log", "--ref", "main", "--limit", ""], ["log", "--ref", "main", "--limit", "9"*100],
    ["log", "--ref", "main", "--ref", "other"],
    ["log", "--ref", "main", "--limit", "1a"],
    ["log", "--ref", "main", "--limit", "2", "--limit", "3"], ["snapshot", "--foo", "main"],
])
def test_parser_errors_have_no_success_stdout(tmp_path, args):
    result = cli(tmp_path / "absent", *args)
    assert result.returncode == 2 and result.stdout == ""
    error = json.loads(result.stderr)["error"]
    assert error["native_code"] is None
    human = cli(tmp_path / "absent", *args, json_mode=False)
    assert human.returncode == 2 and human.stderr and human.stdout == ""


def test_global_parser_runtime_errors_and_no_implicit_initialization(tmp_path):
    for args in [[], ["--repo"], ["--json"], ["--repo", str(tmp_path), "--repo", "other", "ref", "get", "main"]]:
        result = subprocess.run([str(BIN), *args], capture_output=True, text=True, encoding="utf-8")
        assert result.returncode == 2 and result.stdout == ""
    for flag in ["--version", "-V", "--help"]:
        result = subprocess.run([str(BIN), flag], capture_output=True, text=True, encoding="utf-8")
        assert result.returncode == 0 and result.stderr == ""
    path = tmp_path / "missing"
    result = cli(path, "ref", "get", "main")
    assert result.returncode == 1 and result.stdout == "" and not path.exists()
    assert json.loads(result.stderr)["error"]["code"]
    with dml.Repository(path, create=True):
        pass
    for args in [("ref", "get", "unknown"), ("show", "commit", "0"*32), ("log", "--commit", "0"*32)]:
        result = cli(path, *args)
        assert result.returncode == 1 and result.stdout == ""
        assert json.loads(result.stderr)["error"]["code"] == "not_found"
    human = cli(path, "ref", "get", "unknown", json_mode=False)
    assert human.returncode == 1 and "not_found" in human.stderr


def test_late_corruption_fails_without_partial_snapshot(tmp_path):
    path = tmp_path / "repo"
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            first = snapshot(tx, 42)
            second = snapshot(tx, 43)
            tree = tx.put_tree({"a": first["dag"], "b": second["dag"]})
            commit = tx.put_commit(tree); tx.create_ref("main", commit)
    overwrite(path, "objects/datums/" + str(second["datum"]), b"bad")
    for mode in [True, False]:
        result = cli(path, "snapshot", "--ref", "main", json_mode=mode)
        assert result.returncode == 1 and result.stdout == ""
        assert "invalid_header" in result.stderr
    # The bounded prefix can deliberately avoid the corrupt deeper value.
    assert success(path, "snapshot", "--ref", "main", "--limit", "1")["truncated"]


@given(value=st.integers(-(2**63), 2**63-1))
@settings(max_examples=12, deadline=None)
def test_cli_public_python_property_roundtrip(tmp_path_factory, value):
    path = tmp_path_factory.mktemp("cli") / "repo"
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            identity = tx.put_datum(value)
    assert success(path, "show", "datum", str(identity))["datum"]["value"] == str(value)


@pytest.mark.skipif(not Path("/dev/full").exists(), reason="Unix output-write error device")
@pytest.mark.parametrize("command", [["--version"], ["--help"], ["--json", "--repo", "REPO", "ref", "get", "main"], ["--repo", "REPO", "snapshot", "--ref", "main"]])
def test_output_write_failure(tmp_path, command):
    path = tmp_path / "repo"
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            obj = snapshot(tx, 42); tx.create_ref("main", obj["commit"])
    args = [str(path) if arg == "REPO" else arg for arg in command]
    with open("/dev/full", "wb") as output:
        result = subprocess.run([str(BIN), *args], stdout=output, stderr=subprocess.PIPE)
    assert result.returncode == 1


@pytest.mark.skipif(os.name == "nt", reason="Unix pipe/SIGPIPE behavior")
def test_closed_output_pipe_reports_failure(tmp_path):
    path = tmp_path / "repo"
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            obj = snapshot(tx, 42); tx.create_ref("main", obj["commit"])
    reader, writer = os.pipe()
    os.close(reader)
    try:
        result = subprocess.run([str(BIN), "--json", "--repo", str(path), "snapshot", "--ref", "main"],
                                stdout=writer, stderr=subprocess.PIPE)
    finally:
        os.close(writer)
    assert result.returncode == 1
    assert json.loads(result.stderr)["error"]["detail"] == "cannot write inspection output"


def test_cli_utf8_protocol_is_independent_of_locale(tmp_path, monkeypatch):
    path = tmp_path / "repo"
    value = "é\u00a0\U0001f642"
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            identity = tx.put_datum(value)
    # Force the fallback used for unspecified subprocess text encoding to ASCII.
    # The CLI's UTF-8 protocol must still round-trip without a decoding error.
    monkeypatch.setattr(subprocess, "_text_encoding", lambda: "ascii")
    assert success(path, "show", "datum", str(identity))["datum"]["value"] == value


@pytest.mark.parametrize("value", ["payloadé\n" * 400, bytes(range(256)) * 16])
def test_large_full_json_datum_grows_beyond_initial_buffer(tmp_path, value):
    path = tmp_path / "repo"
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            identity = tx.put_datum(value)
    result = cli(path, "show", "datum", str(identity))
    assert result.returncode == 0 and result.stderr == "" and len(result.stdout) > 4096
    description = json.loads(result.stdout)["datum"]
    if type(value) is bytes:
        assert description == {"kind": "bytes", "value": value.hex(), "encoding": "hex"}
    else:
        assert description == {"kind": "string", "value": value}
    # Human output remains bounded while full JSON retains every byte/code point.
    human = cli(path, "show", "datum", str(identity), json_mode=False)
    assert human.returncode == 0 and '"truncated": true' in human.stdout
    assert len(human.stdout) < 1024
