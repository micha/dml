import json
from pathlib import Path
import runpy
import subprocess
import sys

import daggerml as dml

from test_inspection_cli import success
from test_records_hypothesis import run_driver

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/repository_history.py"
BOOTSTRAP = f"import runpy; runpy.run_path({str(ROOT / 'tests/conftest.py')!r})\n"


def test_runnable_example_in_process_coverage(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [str(EXAMPLE), str(tmp_path / "repo")])
    runpy.run_path(str(EXAMPLE), run_name="__main__")
    document = json.loads(capsys.readouterr().out)
    assert document["first"]["commit"] != document["second"]["commit"]
    namespace = runpy.run_path(str(EXAMPLE))
    assert callable(namespace["main"])


def test_acceptance_fresh_producer_native_cli_and_fresh_reader(tmp_path):
    path = tmp_path / "repo"
    producer = BOOTSTRAP + f"import sys; sys.argv = [{str(EXAMPLE)!r}, {str(path)!r}]; runpy.run_path({str(EXAMPLE)!r}, run_name='__main__')"
    result = subprocess.run([sys.executable, "-c", producer], check=True, capture_output=True, text=True)
    document = json.loads(result.stdout)
    assert success(path, "snapshot", "--ref", "main")["entries"][0]["preview"]["value"] == "43"
    assert success(path, "snapshot", "--commit", document["first"]["commit"])["entries"][0]["preview"]["value"] == "42"
    for branch in ["main", "branch"]:
        result = success(path, "log", "--ref", branch)
        assert result["commits"][1]["id"] == document["first"]["commit"]
    reader = BOOTSTRAP + f"""
import daggerml as dml, json
saved = json.loads({json.dumps(document)!r})
with dml.Repository({str(path)!r}) as repo:
    with repo.read() as tx:
        for kind, identity in saved['first'].items():
            assert tx.get_record(kind, dml.ObjectId.from_hex(identity)).hex() == saved['first_records'][kind]
print('immutable records verified')
"""
    result = subprocess.run([sys.executable, "-c", reader], check=True, capture_output=True, text=True)
    assert result.stdout.strip() == "immutable records verified"
    # Independent existing C test helper hashes the bytes returned by Python.
    for kind, identity in document["first"].items():
        assert run_driver("object-id", data=bytes.fromhex(document["first_records"][kind])).stdout.strip().decode() == identity
