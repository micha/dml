import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

import daggerml as dml
from hypothesis import example, given, settings, strategies as st
import pytest

from test_history import overwrite
from test_inspection_cli import cli, success
from test_objects_hypothesis import encode, envelope, ids, names, object_id, tree_payload
from test_public_acceptance import BOOTSTRAP
from test_records_hypothesis import run_driver

EXAMPLE = Path(__file__).resolve().parents[2] / "examples/composable_dags.py"


@given(root=ids, entries=st.lists(st.tuples(names, ids), unique_by=lambda pair: pair[0], max_size=8))
def test_dag_independent_encoding_permutation_and_identity(root, entries):
    payload = root + tree_payload(entries)
    packed = encode(4, payload)
    assert packed == envelope(4, root + tree_payload(sorted(entries)))
    assert packed == encode(4, root + tree_payload(list(reversed(entries))))
    changed_root = bytes([root[0] ^ 1]) + root[1:]
    assert object_id(packed) != object_id(encode(4, changed_root + tree_payload(entries)))
    if entries:
        name, node = entries[0]
        for target in [node, b"\x55" * 16]:
            result = run_driver("encode-object", "4", data=root + tree_payload(entries + [(name, target)]), check=False)
            assert result.returncode == 1 and b"record_type=dag" in result.stderr
        renamed = [(name + "-renamed", node)] + entries[1:]
        assert object_id(packed) != object_id(encode(4, root + tree_payload(renamed)))
        retargeted = [(name, bytes([node[0] ^ 1]) + node[1:])] + entries[1:]
        assert object_id(packed) != object_id(encode(4, root + tree_payload(retargeted)))


@given(ids)
def test_subdag_encoding_kind_domain(reference):
    literal = encode(3, (1).to_bytes(4, "little") + reference)
    subdag = encode(3, (2).to_bytes(4, "little") + reference)
    assert subdag == envelope(3, (2).to_bytes(4, "little") + reference)
    assert object_id(subdag) != object_id(literal)


@pytest.mark.parametrize("payload", [
    b"\0" * 16,  # old 36-byte root-only encoding is explicitly rejected
    b"\0" * 16 + tree_payload([]) + b"extra",
    b"\0" * 16 + (0xffffffff).to_bytes(4, "little"),
    b"\0" * 16 + tree_payload([("z", b"\0" * 16), ("a", b"\0" * 16)]),
    b"\0" * 16 + tree_payload([("a", b"\0" * 16), ("a", b"\0" * 16)]),
    b"\0" * 16 + (1).to_bytes(4, "little") + (0xffffffff).to_bytes(4, "little") + b"a" + b"\0" * 16,
    b"\0" * 16 + tree_payload([("a", b"\0" * 16)])[:-1],
])
def test_dag_malformed_payload_diagnostics(payload):
    result = run_driver("validate", data=envelope(4, payload), check=False)
    assert result.returncode == 1 and b"record_type=dag" in result.stderr


@pytest.mark.parametrize("name", ["", ".a", "a/b", "a b", "a\0b", "é", "a" * 129])
def test_binding_names_and_rollback(tmp_path, name):
    with dml.Repository(tmp_path / "repo", create=True) as repo:
        with repo.write() as tx:
            node = tx.put_literal(tx.put_datum(1))
        tx = repo.write()
        before = tx.put_datum(999)
        with pytest.raises(dml.DmlError) as error:
            tx.put_dag(root=node, bindings=[(name, node)])
        assert "record_type=dag" in error.value.detail
        with pytest.raises(dml.InvalidStateError):
            tx.commit()
        with repo.read() as tx:
            with pytest.raises(dml.NotFoundError):
                tx.get_datum(before)


@settings(max_examples=15)
@example(["root", "absent"])
@given(st.lists(names, unique=True, min_size=1, max_size=6))
def test_public_bindings_copy_order_alias_and_scope(binding_names):
    with tempfile.TemporaryDirectory() as scratch:
        with dml.Repository(Path(scratch) / "repo", create=True) as repo:
            with repo.write() as tx:
                node = tx.put_literal(tx.put_datum(2))
                pairs = [(name, node) for name in binding_names]
                dag = tx.put_dag(root=node, bindings=pairs)
                assert dag == tx.put_dag(root=node, bindings=list(reversed(pairs)))
                description = tx.get_dag(dag)
                assert list(description.bindings) == sorted(binding_names)
                pairs.clear()
                for name in binding_names:
                    assert tx.lookup_node(dag, name) == node
                with pytest.raises(dml.NotFoundError):
                    tx.lookup_node(dag, "missing-name-guaranteed")
                with pytest.raises(dml.DmlError):
                    tx.lookup_node(dag, "bad/name")
                second = tx.put_dag(root=node, bindings={"root": node, "A": node, "a": node})
                assert tx.lookup_node(second, "root") == node
                if "root" not in binding_names:
                    with pytest.raises(dml.NotFoundError):
                        tx.lookup_node(dag, "root")
                else:
                    assert tx.lookup_node(dag, "root") == node
                assert tx.get_node(node) == dml.LiteralNode(tx.get_node(node).datum)
            with pytest.raises(TypeError):
                description.bindings["new"] = node
            assert description.root == node and len(description.bindings) == len(binding_names)
            with repo.read() as tx:
                assert tx.get_dag(second).bindings["root"] == node


def test_descriptions_and_argument_failure_boundaries(tmp_path):
    node = dml.ObjectId(b"\0" * 16)
    pairs = [("a", node)]
    description = dml.DAG(node, pairs)
    pairs.clear()
    assert description.bindings == {"a": node}
    assert dml.SubDAGNode(node).dag == node
    for constructor in [lambda: dml.SubDAGNode(1), lambda: dml.DAG(node, [(1, node)]),
                        lambda: dml.DAG(node, [("a", 1)]), lambda: dml.DAG(node, [("a", node), ("a", node)])]:
        with pytest.raises((TypeError, ValueError)):
            constructor()
    with dml.Repository(tmp_path / "repo", create=True) as repo:
        with repo.write() as tx:
            real = tx.put_literal(tx.put_datum(1))
            dag = tx.put_dag(root=real)
            for name in [1, None]:
                with pytest.raises(TypeError):
                    tx.lookup_node(dag, name)
            tx.put_datum(2)  # failed reads have not poisoned this batch
        operations = [lambda tx: tx.put_subdag(1), lambda tx: tx.put_dag(root=real, bindings=[(1, real)]),
                      lambda tx: tx.put_dag(root=real, bindings=[("ok", real), ("bad", 1)]),
                      lambda tx: tx.put_dag(root=real, bindings=[("a", real), ("a", real)])]
        for operation in operations:
            tx = repo.write()
            before = tx.put_datum(77)
            with pytest.raises((TypeError, dml.DmlError)):
                operation(tx)
            with pytest.raises(dml.InvalidStateError):
                tx.commit()
            with repo.read() as tx:
                with pytest.raises(dml.NotFoundError):
                    tx.get_datum(before)


def test_comparison_example_fresh_processes_and_cli(tmp_path):
    path = tmp_path / "repo"
    producer = BOOTSTRAP + f"import sys; sys.argv = [{str(EXAMPLE)!r}, {str(path)!r}]; runpy.run_path({str(EXAMPLE)!r}, run_name='__main__')"
    result = subprocess.run([sys.executable, "-c", producer], check=True, capture_output=True, text=True, encoding="utf-8")
    saved = json.loads(result.stdout)
    for commit, value in [(saved["c1"], "A=5; B=6"), (saved["c2"], "A=5; B=7")]:
        snapshot = success(path, "snapshot", "--commit", commit)
        assert snapshot["entries"][0]["preview"]["value"] == value
        nested = snapshot["entries"][1]
        assert nested["root_node"] == {"kind": "subdag", "dag": saved["a"]}
        assert "datum" not in nested and "preview" not in nested
    assert success(path, "snapshot", "--ref", "main")["commit"] == saved["c2"]
    assert success(path, "show", "node", saved["a_node"])["dag"] == saved["a"]
    assert success(path, "show", "node", saved["a_node"])["kind"] == "subdag"
    for compare in [saved["comparison1"], saved["comparison2"]]:
        assert success(path, "lookup", compare, "trial-a")["node"] == saved["a_node"]
        missing = cli(path, "lookup", compare, "result")
        assert missing.returncode == 1 and missing.stdout == ""
    for key, value in [("a", "5"), ("b", "6"), ("b2", "7")]:
        node = success(path, "lookup", saved[key], "result")["node"]
        datum = success(path, "show", "node", node)["datum"]
        assert success(path, "show", "datum", datum)["datum"]["value"] == value
    reader = BOOTSTRAP + f"""
import daggerml as dml, json
saved = json.loads({json.dumps(saved)!r})
with dml.Repository({str(path)!r}) as repo:
    with repo.read() as tx:
        for key, record in saved['saved'].items():
            kind, identity = key.split(':')
            assert tx.get_record(kind, dml.ObjectId.from_hex(identity)).hex() == record
"""
    subprocess.run([sys.executable, "-c", reader], check=True)
    for key, record in saved["saved"].items():
        assert run_driver("object-id", data=bytes.fromhex(record)).stdout.decode().strip() == key.split(":")[1]
    full = success(path, "walk", saved["comparison1"])
    records = full["records"]
    assert records[0]["type"] == "dag" and records[0]["id"] == saved["comparison1"]
    assert [item["name"] for item in records[0]["bindings"]] == ["summary", "trial-a", "trial-b"]
    assert len({(item["type"], item["id"]) for item in records}) == len(records)
    for limit in range(1, len(records) + 2):
        prefix = success(path, "walk", saved["comparison1"], "--limit", str(limit))
        assert prefix["records"] == records[:limit]
        assert prefix["truncated"] == (limit < len(records))
    assert "DAG structure\n" in cli(path, "walk", saved["comparison1"], json_mode=False).stdout
    assert "Lookup\n" in cli(path, "lookup", saved["a"], "result", json_mode=False).stdout


def test_example_in_process_and_iterative_deep_chain(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [str(EXAMPLE), str(tmp_path / "example")])
    runpy.run_path(str(EXAMPLE), run_name="__main__")
    assert json.loads(capsys.readouterr().out)["c1"]
    path = tmp_path / "deep"
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            node = tx.put_literal(tx.put_datum(dml.Datum.list([])))
            start = tx.put_dag(root=node, bindings={"alias": node})
            for _ in range(1100):
                start = tx.put_dag(root=tx.put_subdag(start))
    full = success(path, "walk", str(start), "--limit", "2202")
    assert len(full["records"]) == 2202 and not full["truncated"]
    assert full["records"][-1]["preview"]["value"] == []
    assert success(path, "walk", str(start))["truncated"]


def test_walk_late_corruption_has_no_success_document(tmp_path):
    path = tmp_path / "repo"
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            datum = tx.put_datum(5)
            leaf = tx.put_dag(root=tx.put_literal(datum))
            root = tx.put_dag(root=tx.put_subdag(leaf))
    overwrite(path, f"objects/datums/{datum}", b"bad")
    prefix = success(path, "walk", str(root), "--limit", "1")
    assert prefix["truncated"]
    failure = cli(path, "walk", str(root))
    assert failure.returncode == 1 and failure.stdout == ""
    assert json.loads(failure.stderr)["error"]["code"] == "invalid_header"


@pytest.mark.parametrize("position", ["subdag", "binding", "root"])
@pytest.mark.parametrize("corruption", ["missing", "wrong_type", "wrong_id", "bad_record"])
def test_direct_target_integrity_and_poisoned_put(tmp_path, position, corruption):
    path = tmp_path / "repo"
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            datum = tx.put_datum(42)
            node = tx.put_literal(datum)
            dag = tx.put_dag(root=node)
            root_node = tx.put_literal(tx.put_datum(43)) if position == "binding" else node
            reference = dag if position == "subdag" else node
            valid_record = tx.get_record("dag" if position == "subdag" else "node", reference)
            wrong_record = tx.get_record("datum", datum)
            if position == "subdag":
                referring = tx.put_subdag(dag)
                kind = "node"
            else:
                referring = tx.put_dag(root=root_node, bindings={"a": node})
                kind = "dag"
        with repo.read() as tx:
            packed = tx.get_record(kind, referring)
    prefix = "dags" if position == "subdag" else "nodes"
    key = f"objects/{prefix}/{reference}"
    if corruption == "missing":
        # Replace referring bytes with an independently encoded missing reference;
        # test-only store insertion bypasses put validation.
        target = b"\xff" * 16
        if position == "subdag":
            packed = encode(3, (2).to_bytes(4, "little") + target)
        elif position == "root":
            packed = encode(4, target + tree_payload([]))
        else:
            packed = encode(4, root_node.bytes + tree_payload([("a", target)]))
        referring = dml.ObjectId.from_hex(object_id(packed).decode())
        overwrite(path, f"objects/{'nodes' if kind == 'node' else 'dags'}/{referring}", packed)
    else:
        if corruption == "wrong_type":
            replacement = wrong_record
        elif corruption == "wrong_id":
            replacement = bytearray(valid_record)
            replacement[24 if position == "subdag" else 25] ^= 1
            replacement = bytes(replacement)
        else:
            replacement = b"bad"
        overwrite(path, key, replacement)
    expected = {"missing": "not_found", "wrong_type": "invalid_kind", "wrong_id": "integrity_error",
                "bad_record": "invalid_header"}[corruption]
    with dml.Repository(path) as repo:
        with repo.read() as tx:
            with pytest.raises(dml.DmlError) as error:
                tx.get_record(kind, referring)
            assert error.value.code == expected
        tx = repo.write()
        before = tx.put_datum(10001)
        with pytest.raises(dml.DmlError) as error:
            dml._call(dml._core.put_record, tx._handle, 3 if kind == "node" else 4, packed)
        assert error.value.code == expected
        with pytest.raises(dml.InvalidStateError):
            tx.commit()
        with repo.read() as tx:
            with pytest.raises(dml.NotFoundError):
                tx.get_datum(before)


@pytest.mark.parametrize("target_type", ["missing", "datum", "node", "dag"])
def test_new_mutation_reference_types(tmp_path, target_type):
    with dml.Repository(tmp_path / "repo", create=True) as repo:
        with repo.write() as tx:
            datum = tx.put_datum(1)
            node = tx.put_literal(datum)
            dag = tx.put_dag(root=node)
        target = {"missing": dml.ObjectId(b"\xff" * 16), "datum": datum, "node": node, "dag": dag}[target_type]
        for expected_target, operation in [(dag, lambda tx: tx.put_subdag(target)),
                                            (node, lambda tx: tx.put_dag(root=node, bindings={"a": target}))]:
            tx = repo.write()
            before = tx.put_datum(998)
            if target != expected_target:
                with pytest.raises(dml.NotFoundError):
                    operation(tx)
                with pytest.raises(dml.InvalidStateError):
                    tx.commit()
                with repo.read() as reader:
                    with pytest.raises(dml.NotFoundError):
                        reader.get_datum(before)
            else:
                result = operation(tx)
                assert result is not None
                tx.abort()


@pytest.mark.parametrize("args", [("lookup",), ("lookup", "bad", "a"),
    ("lookup", "00" * 16, "a/b"), ("walk",), ("walk", "bad"),
    ("walk", "00" * 16, "--ref", "main"), ("walk", "00" * 16, "--limit", "0"),
    ("walk", "00" * 16, "--limit", "2", "--limit", "3")])
def test_new_cli_grammar(args, tmp_path):
    result = cli(tmp_path / "missing", *args)
    assert result.returncode == 2 and result.stdout == ""
