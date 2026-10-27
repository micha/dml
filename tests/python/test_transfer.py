"""Public packed insertion, typed closure and atomic bounded exchange."""

import base64
import json
from pathlib import Path
import struct
import tempfile
import threading

import daggerml as dml
from daggerml import transfer as tr
from hypothesis import given, settings, strategies as st
import pytest

from test_history import overwrite
from test_records_hypothesis import run_driver


def rich(path):
    records = []
    with dml.Repository(path, create=True) as repo, repo.write() as tx:

        def save(kind, oid):
            records.append(((kind, oid), tx.get_record(kind, oid)))
            return oid

        values = [
            None,
            True,
            -(2**63),
            2**63 - 1,
            -0.0,
            float("nan"),
            float("inf"),
            float("-inf"),
            b"opaque",
            "e\u0301",
            dml.Datum.uri("urn:test:resource"),
        ]
        datums = [save("datum", tx.put_datum(value)) for value in values]
        for value in [
            dml.Datum.list([datums[0], datums[0], datums[1]]),
            dml.Datum.set(reversed(datums[:3])),
            dml.Datum.map([(datums[1], datums[2]), (datums[0], datums[3])]),
        ]:
            datums.append(save("datum", tx.put_datum(value)))
        nodes = [save("node", tx.put_literal(datum)) for datum in datums]
        small = save("dag", tx.put_dag(root=nodes[0]))
        nested = save("node", tx.put_subdag(small))
        dag = save(
            "dag",
            tx.put_dag(root=nested, bindings=[(f"n{i}", node) for i, node in enumerate(nodes)]),
        )
        tree = save("tree", tx.put_tree({"all": dag, "shared": small}))
        first = save("commit", tx.put_commit(tree))
        empty = save("tree", tx.put_tree({}))
        second = save("commit", tx.put_commit(empty, parents=[first]))
        root = save("commit", tx.put_commit(tree, parents=[second, first]))
        unrelated = tx.put_datum("unrelated branch-only sentinel")
        other = tx.put_commit(tx.put_tree({"other": tx.put_dag(root=tx.put_literal(unrelated))}))
        tx.create_ref("main", root)
        tx.create_ref("other", other)
    return root, records, unrelated, other


def initialize(path):
    with dml.Repository(path, create=True) as repo, repo.write() as tx:
        sentinel = tx.put_datum("destination keep")
        root = tx.put_commit(tx.put_tree({"keep": tx.put_dag(root=tx.put_literal(sentinel))}))
        tx.create_ref("keep", root)
    return sentinel, root


def doc(bundle):
    return json.loads(bundle)


def pack(document):
    return json.dumps(document, separators=(",", ":")).encode()


def assert_absent(path, key, keep):
    with dml.Repository(path) as repo, repo.read() as tx:
        with pytest.raises(dml.NotFoundError):
            tx.get_record(*key)
        assert tx.get_ref("keep") == keep
        with pytest.raises(dml.NotFoundError):
            tx.get_ref("received")


def test_public_packed_all_kinds_and_owned_bytes(tmp_path):
    root, records, _, _ = rich(tmp_path / "a")
    with dml.Repository(tmp_path / "b", create=True) as repo, repo.write() as tx:
        for (kind, oid), record in records:
            assert tx.put_record(kind, record) == oid
            assert tx.put_record(kind, record) == oid
            assert tx.get_record(kind, oid) == record
    with dml.Repository(tmp_path / "b") as repo, repo.read() as tx:
        assert tx.get_commit(root).parents == (records[-2][0][1], records[-4][0][1])
        with pytest.raises(dml.InvalidStateError):
            tx.put_record("datum", records[0][1])
        assert tx.get_record(*records[0][0]) == records[0][1]
    with pytest.raises(dml.InvalidStateError):
        tx.put_record("datum", records[0][1])


@pytest.mark.parametrize(
    "kind,record,error",
    [
        ("meta", b"x", ValueError),
        (None, b"x", TypeError),
        ("datum", bytearray(b"x"), TypeError),
        ("datum", b"x", dml.DmlError),
        ("datum", memoryview(b"x"), TypeError),
        ([], b"x", TypeError),
        ("datum", None, TypeError),
    ],
    ids=["kind", "kind-type", "mutable", "native", "view", "unhashable-kind", "bytes-type"],
)
def test_put_record_poison(tmp_path, kind, record, error):
    with dml.Repository(tmp_path / "repo", create=True) as repo:
        with pytest.raises(dml.InvalidStateError):
            with repo.write() as tx:
                earlier = tx.put_datum(997)
                with pytest.raises(error):
                    tx.put_record(kind, record)
        with repo.read() as tx:
            with pytest.raises(dml.NotFoundError):
                tx.get_datum(earlier)


def test_packed_insertion_owner_thread_and_missing_dependency(tmp_path):
    root, records, _, _ = rich(tmp_path / "a")
    with dml.Repository(tmp_path / "b", create=True) as repo:
        tx = repo.write()
        errors = []

        def foreign():
            try:
                tx.put_record("datum", records[0][1])
            except dml.InvalidStateError as error:
                errors.append(error)

        worker = threading.Thread(target=foreign)
        worker.start()
        worker.join(timeout=5)
        assert not worker.is_alive() and len(errors) == 1
        assert tx.put_record("datum", records[0][1]) == records[0][0][1]
        tx.abort()
        tx = repo.write()
        earlier = tx.put_datum("dependency abort sentinel")
        node_record = next(record for (kind, _), record in records if kind == "node")
        with pytest.raises(dml.NotFoundError):
            tx.put_record("node", node_record)
        with pytest.raises(dml.InvalidStateError):
            tx.commit()
        with repo.read() as tx:
            with pytest.raises(dml.NotFoundError):
                tx.get_datum(earlier)


def test_pin_population_reexport_and_refs(tmp_path):
    source, dest = tmp_path / "a", tmp_path / "b"
    root, records, unrelated, other = rich(source)
    keep_datum, keep = initialize(dest)
    bundle = tr.export_commit(source, commit=root)
    rows = doc(bundle)["objects"]
    assert {(r["kind"], r["id"]) for r in rows} == {(k, str(o)) for (k, o), _ in records}
    assert len(rows) == len(records)
    with dml.Repository(source) as repo, repo.write() as tx:
        tx.update_ref("main", other)
    assert tr.export_commit(source, commit=root) == bundle
    for ref in ("received", "received", None):
        assert tr.import_commit(dest, bundle, ref=ref) == tr.ImportResult(root, len(records), ref)
    assert tr.export_commit(dest, commit=root) == bundle
    with dml.Repository(dest) as repo, repo.read() as tx:
        for key, record in records:
            assert tx.get_record(*key) == record
        assert tx.get_ref("keep") == keep
        assert tx.get_datum(keep_datum).value == "destination keep"
        for name in ("main", "other"):
            with pytest.raises(dml.NotFoundError):
                tx.get_ref(name)
        with pytest.raises(dml.NotFoundError):
            tx.get_datum(unrelated)


@settings(max_examples=16, deadline=None)
@given(st.lists(st.integers(min_value=-(2**63), max_value=2**63 - 1), min_size=1, max_size=12))
def test_generated_sharing_roundtrip(tmp_path_factory, values):
    with tempfile.TemporaryDirectory(dir=tmp_path_factory.getbasetemp()) as scratch:
        source, dest = Path(scratch) / "a", Path(scratch) / "b"
        with dml.Repository(source, create=True) as repo, repo.write() as tx:
            ids = [tx.put_datum(v) for v in values]
            sequence = tx.put_datum(dml.Datum.list(ids + ids))
            set_ids = [tx.put_datum(str(v)) for v in values]
            unique = tuple(dict.fromkeys(set_ids))
            unordered = tx.put_datum(dml.Datum.set(reversed(unique)))
            # Disjoint I64 LIST children and STRING SET children are reached only
            # via the MAP key and value respectively, never through bindings.
            collection = tx.put_datum(dml.Datum.map([(sequence, unordered)]))
            node = tx.put_literal(collection)
            dag = tx.put_dag(root=node, bindings={"a": node, "b": node})
            tree = tx.put_tree({"a": dag, "b": dag})
            first = tx.put_commit(tree)
            root = tx.put_commit(tree, parents=[first])
        initialize(dest)
        bundle = tr.export_commit(source, commit=root)
        tr.import_commit(dest, bundle)
        assert tr.export_commit(dest, commit=root) == bundle


def test_deep_iterative_history(tmp_path):
    source, dest = tmp_path / "a", tmp_path / "b"
    with dml.Repository(source, create=True) as repo, repo.write() as tx:
        tree = tx.put_tree({})
        root = tx.put_commit(tree)
        for _ in range(1100):
            root = tx.put_commit(tree, parents=[root])
    initialize(dest)
    bundle = tr.export_commit(source, commit=root)
    assert tr.import_commit(dest, bundle).object_count == 1102
    assert tr.export_commit(dest, commit=root) == bundle


@pytest.mark.parametrize(
    "mode", ["id", "kind", "late-native", "extra", "omit", "forward", "parent", "ref"], ids=str
)
def test_late_failures_atomic_even_with_preexisting_dependencies(tmp_path, mode):
    source, dest = tmp_path / "a", tmp_path / "b"
    root, records, _, _ = rich(source)
    _, keep = initialize(dest)
    bundle = tr.export_commit(source, commit=root)
    document = doc(bundle)
    firstkey = document["objects"][0]["kind"], dml.ObjectId.from_hex(document["objects"][0]["id"])
    if mode in ("omit", "forward", "parent"):
        # Populate B fully, then choose a genuinely new extra prefix for the rollback oracle.
        tr.import_commit(dest, bundle)
        with dml.Repository(source) as repo, repo.write() as tx:
            oid = tx.put_datum("new rollback prefix")
            row = {
                "kind": "datum",
                "id": str(oid),
                "record": base64.b64encode(tx.get_record("datum", oid)).decode(),
            }
        firstkey = "datum", oid
        if mode == "parent":
            index = next(i for i, r in enumerate(document["objects"][:-1]) if r["kind"] == "commit")
        else:
            index = 0
        removed = document["objects"].pop(index)
        if mode == "forward":
            document["objects"].insert(-1, removed)
        document["objects"].insert(0, row)
    elif mode == "id":
        document["objects"][-2]["id"] = "0" * 32
    elif mode == "kind":
        document["objects"][-2]["kind"] = "datum"
    elif mode == "late-native":
        document["objects"][-1]["record"] = base64.b64encode(b"bad packed bytes").decode()
    elif mode == "extra":
        with dml.Repository(source) as repo, repo.read() as tx:
            oid = tx.get_ref("other")
            # Use a leaf unreachable from the selected root, placed after the valid first row.
            dag = tx.get_tree(tx.get_commit(oid).tree)["other"]
            datum = tx.get_node(tx.get_dag(dag).root).datum
            document["objects"].insert(
                1,
                {
                    "kind": "datum",
                    "id": str(datum),
                    "record": base64.b64encode(tx.get_record("datum", datum)).decode(),
                },
            )
    with pytest.raises((tr.TransferError, dml.DmlError)):
        tr.import_commit(dest, pack(document), ref="keep" if mode == "ref" else "received")
    assert_absent(dest, firstkey, keep)


@pytest.mark.parametrize("keykind", ["datum", "node", "commit", "ref", "dangling-ref"])
def test_real_stored_corruption_no_repair(tmp_path, keykind):
    source, dest = tmp_path / "a", tmp_path / "b"
    root, records, _, _ = rich(source)
    _, keep = initialize(dest)
    bundle = tr.export_commit(source, commit=root)
    document = doc(bundle)
    # Seed only the corrupted key; native insertion must not skip/rewrite it.
    if keykind in ("ref", "dangling-ref"):
        key, replacement = "refs/heads/received", b"bad" if keykind == "ref" else bytes(16)
    else:
        row = next(r for r in reversed(document["objects"]) if r["kind"] == keykind)
        prefix = {"datum": "datums", "node": "nodes", "commit": "commits"}[keykind]
        key, replacement = f"objects/{prefix}/{row['id']}", b"bad"
    overwrite(dest, key, replacement)
    firstrow = document["objects"][0]
    firstkey = firstrow["kind"], dml.ObjectId.from_hex(firstrow["id"])
    if keykind == "datum":
        # Ensure corruption is late enough to demonstrate earlier new insertion.
        assert key.rsplit("/", 1)[1] != str(firstkey[1])
    with pytest.raises(dml.DmlError):
        tr.import_commit(dest, bundle, ref="received")
    with dml.Repository(dest) as repo, repo.read() as tx:
        assert tx.get_ref("keep") == keep
        with pytest.raises(dml.NotFoundError):
            tx.get_record(*firstkey)
        if keykind in ("ref", "dangling-ref"):
            with pytest.raises(dml.DmlError):
                tx.get_ref("received")


@pytest.mark.parametrize("kind", ["datum", "node", "commit"])
def test_source_corrupt_reached_key(tmp_path, kind):
    root, records, _, _ = rich(tmp_path / "a")
    oid = next(o for (k, o), _ in records if k == kind)
    prefix = {"datum": "datums", "node": "nodes", "commit": "commits"}[kind]
    overwrite(tmp_path / "a", f"objects/{prefix}/{oid}", b"bad")
    with pytest.raises(dml.DmlError):
        tr.export_commit(tmp_path / "a", commit=root)


def test_wrong_content_key_parent_fails_integrity(tmp_path):
    root, records, _, _ = rich(tmp_path / "a")
    # Substitute a valid packed commit under its wrong content key; native reads detect it.
    parent = next((key, record) for key, record in records if key[0] == "commit")
    overwrite(tmp_path / "a", f"objects/commits/{parent[0][1]}", records[-1][1])
    with pytest.raises(dml.IntegrityError):
        tr.export_commit(tmp_path / "a", commit=root)


@pytest.mark.parametrize("missing", ["parent", "composite-child", "node"], ids=str)
def test_genuinely_missing_reached_source_key(tmp_path, missing):
    root, records, _, _ = rich(tmp_path / "a")
    source = tmp_path / "a"
    if missing == "parent":
        oid = next(o for (kind, o), _ in records if kind == "commit")
        prefix = "commits"
    elif missing == "node":
        oid = next(o for (kind, o), _ in records if kind == "node")
        prefix = "nodes"
    else:
        # This child is reached only via the composite datum, not a literal/binding.
        source = tmp_path / "composite-only"
        with dml.Repository(source, create=True) as repo, repo.write() as tx:
            oid = tx.put_datum("composite-only child")
            collection = tx.put_datum(dml.Datum.list([oid, oid]))
            dag = tx.put_dag(root=tx.put_literal(collection))
            root = tx.put_commit(tx.put_tree({"composite": dag}))
        prefix = "datums"
    run_driver("raw-delete", str(source), f"objects/{prefix}/{oid}")
    with pytest.raises(dml.DmlError) as error:
        tr.export_commit(source, commit=root)
    assert error.value.code in ("not_found", "invalid_kind")


def test_synthetic_traversal_cycle_not_hash_collision(tmp_path, monkeypatch):
    root, _, _, _ = rich(tmp_path / "a")
    monkeypatch.setattr(tr, "_edges", lambda tx, kind, oid: ((kind, oid),))
    with pytest.raises(tr.TransferError, match="cycle"):
        tr.export_commit(tmp_path / "a", commit=root)
