import gc
import math
from pathlib import Path
import struct
import threading
import weakref

import daggerml as dml
from hypothesis import given, settings, strategies as st
import pytest

from test_records_hypothesis import record


@pytest.fixture
def repo(tmp_path):
    with dml.Repository(tmp_path / "repo", create=True) as owner:
        yield owner


def snapshot(tx, value, parents=()):
    datum = tx.put_datum(value)
    node = tx.put_literal(datum)
    dag = tx.put_dag(root=node)
    tree = tx.put_tree({"example": dag})
    commit = tx.put_commit(tree, parents=parents)
    return {"datum": datum, "node": node, "dag": dag, "tree": tree, "commit": commit}


def test_real_native_values_and_ownership(repo):
    assert dml.version() == "0.1.0" and repo.schema == 1
    values = [None, True, False, -(2**63), 2**63 - 1, 4.5, -0.0, float("nan"),
              float("inf"), -float("inf"), b"\0\xff", "e\u0301", dml.Datum.uri("https://example.org/")]
    with repo.write() as tx:
        ids = [tx.put_datum(value) for value in values]
        descriptions = [tx.get_datum(value) for value in ids]
        composites = [tx.put_datum(dml.Datum.list(ids)), tx.put_datum(dml.Datum.set(ids)),
                      tx.put_datum(dml.Datum.map([(ids[0], ids[1]), (ids[2], ids[3])]))]
        assert tx.get_datum(composites[0]).value == tuple(ids)
        assert tx.get_datum(composites[1]).value == tuple(sorted(ids, key=lambda item: item.bytes))
        assert len(tx.get_datum(composites[2]).value) == 2
        assert tx.get_record("datum", ids[6]) == record(4, struct.pack("<d", 0.0))
        assert tx.get_record("datum", ids[7]) == record(4, struct.pack("<Q", 0x7ff8000000000000))
        assert tx.get_record("datum", ids[11]) == record(6, "é".encode())
        assert tx.get_record("datum", ids[1]) == record(2, b"\1")
    assert descriptions[0] == dml.Datum.null()
    assert descriptions[1] == dml.Datum.bool(True)
    assert descriptions[3] == dml.Datum.i64(-(2**63))
    assert descriptions[5] == dml.Datum.f64(4.5)
    assert math.isnan(descriptions[7].value)
    assert descriptions[11] == dml.Datum.string("é")
    assert descriptions[12].kind == "uri"
    assert str(dml.ObjectId.from_hex(str(ids[0]))) == str(ids[0])
    assert hash(dml.ObjectId(ids[0].bytes)) == hash(ids[0])


@given(value=st.one_of(st.none(), st.booleans(), st.integers(-(2**63), 2**63 - 1),
                 st.floats(width=64), st.binary(max_size=200),
                 st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=100)))
@settings(max_examples=60)
def test_scalar_canonical_roundtrip(value, tmp_path_factory):
    import unicodedata
    path = tmp_path_factory.mktemp("scalar") / "repo"
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            identity = tx.put_datum(value)
            decoded = tx.get_datum(identity)
            assert tx.put_datum(decoded) == identity
            if type(value) is float and math.isnan(value):
                assert math.isnan(decoded.value)
            elif type(value) is str:
                assert decoded.value == unicodedata.normalize("NFC", value)
            else:
                assert decoded.value == value


def test_history_atomicity_and_descriptions(repo):
    with repo.write() as tx:
        first = snapshot(tx, 42)
        tx.create_ref("main", first["commit"])
        saved = {kind: tx.get_record(kind, identity) for kind, identity in first.items()}
    with repo.write() as tx:
        second = snapshot(tx, 43, [first["commit"]])
        tx.update_ref("main", second["commit"])
        third = snapshot(tx, 44, [first["commit"]])
        tx.create_ref("branch", third["commit"])
        tree = tx.get_tree(first["tree"])
        assert list(tree) == ["example"] and len(tree) == 1
        assert tx.get_node(first["node"]).datum == first["datum"]
        assert tx.get_dag(first["dag"]).root == first["node"]
        commit = tx.get_commit(second["commit"])
        assert commit.parents == (first["commit"],)
    with repo.read() as tx:
        assert tx.get_ref("main") == second["commit"]
        for kind, identity in first.items():
            assert tx.get_record(kind, identity) == saved[kind]
    assert tree["example"] == first["dag"]
    with pytest.raises(KeyError):
        tree["missing"]
    with pytest.raises(RuntimeError, match="stop"):
        with repo.write() as tx:
            aborted = snapshot(tx, 99, [second["commit"]])
            tx.update_ref("main", aborted["commit"])
            raise RuntimeError("stop")
    with repo.read() as tx:
        assert tx.get_ref("main") == second["commit"]
        with pytest.raises(dml.NotFoundError):
            tx.get_commit(aborted["commit"])


@pytest.mark.parametrize("failure", ["native", "conversion", "encoding", "duplicate"])
def test_caught_mutation_rolls_back_prior_objects_and_ref(repo, failure):
    with repo.write() as tx:
        first = snapshot(tx, 42)
        tx.create_ref("main", first["commit"])
    with pytest.raises(dml.InvalidStateError, match="entire transaction aborted"):
        with repo.write() as tx:
            second = snapshot(tx, 43, [first["commit"]])
            tx.update_ref("main", second["commit"])
            try:
                if failure == "native":
                    tx.put_literal(dml.ObjectId(b"\0" * 16))
                elif failure == "conversion":
                    tx.put_datum([1])
                elif failure == "encoding":
                    tx.put_datum(dml.Datum.uri("HTTP://Example.org"))
                else:
                    tx.put_datum(dml.Datum.set([second["datum"], second["datum"]]))
            except (dml.DmlError, TypeError):
                pass
            with pytest.raises(dml.InvalidStateError):
                tx.get_ref("main")
    with repo.read() as tx:
        assert tx.get_ref("main") == first["commit"]
        with pytest.raises(dml.NotFoundError):
            tx.get_commit(second["commit"])


def test_missing_read_does_not_poison(repo):
    with repo.write() as tx:
        with pytest.raises(dml.NotFoundError) as failure:
            tx.get_datum(dml.ObjectId(b"\0" * 16))
        assert failure.value.code == "not_found" and isinstance(failure.value.native_code, int)
        identity = tx.put_datum(8)
        with pytest.raises(ValueError):
            tx.get_record("ref", identity)
        with pytest.raises(TypeError):
            tx.get_record("datum", str(identity))
        with pytest.raises(TypeError):
            tx.get_ref(1)
    with repo.read() as tx:
        assert tx.get_datum(identity).value == 8
        with pytest.raises(dml.NotFoundError):
            tx.get_node(identity)
        with pytest.raises(dml.InvalidStateError):
            tx.put_datum(1)
        with pytest.raises(dml.InvalidStateError):
            tx.commit()
        assert tx.get_datum(identity).value == 8


def test_contexts_explicit_endings_and_active_close(tmp_path):
    with dml.Repository(tmp_path / "repo", create=True) as repo:
        with pytest.raises(dml.InvalidStateError):
            repo.__enter__()
        with pytest.raises(TypeError, match="Repository.read"):
            dml.Transaction(repo, True)
        with repo.write() as tx:
            with pytest.raises(dml.InvalidStateError):
                repo.close()
            with pytest.raises(dml.InvalidStateError):
                repo.read()
            with pytest.raises(dml.InvalidStateError):
                tx.__enter__()
            identity = tx.put_datum(42)
            tx.commit()
        tx.abort()
        with pytest.raises(dml.InvalidStateError):
            tx.get_datum(identity)
        with repo.write() as tx:
            tx.abort()
        tx.abort()
        with repo.read() as tx:
            assert tx.get_datum(identity).value == 42
        repo.close()
        tx.abort()
    repo.close()
    with pytest.raises(dml.InvalidStateError):
        repo.schema
    with pytest.raises(dml.InvalidStateError):
        repo.__enter__()
    # Cleanup does not replace an unrelated original exception.
    with pytest.raises(ValueError, match="original"):
        with dml.Repository(tmp_path / "repo") as repo:
            repo.close()
            raise ValueError("original")
    with dml.Repository(tmp_path / "repo") as repo:
        dangling = repo.write()
        identity = dangling.put_datum(100)
    assert dangling._ended
    dangling.abort()
    with dml.Repository(tmp_path / "repo") as repo:
        with repo.read() as tx:
            with pytest.raises(dml.NotFoundError):
                tx.get_datum(identity)


def test_finalizers_owner_retention_and_foreign_drop(tmp_path):
    repo = dml.Repository(tmp_path / "repo", create=True)
    owner_ref = weakref.ref(repo)
    tx = repo.write()
    value = tx.put_datum(42)
    del repo
    gc.collect()
    assert owner_ref() is not None
    repo = owner_ref()
    tx.abort()
    del tx
    gc.collect()
    tx = repo.write()
    tx.put_datum(43)
    box = [tx]
    del tx
    thread = threading.Thread(target=lambda: box.pop())
    thread.start(); thread.join()
    gc.collect()
    # Foreign capsule destruction queues the live transaction. Owner-thread
    # operation must reclaim it before attempting a new write or closing.
    with repo.read() as tx:
        with pytest.raises(dml.NotFoundError):
            tx.get_datum(value)
    with repo.write() as tx:
        tx.put_datum(44)
    repo.close()
    repo = dml.Repository(tmp_path / "repo")
    tx = repo.write()
    tx.put_datum(45)
    del tx
    gc.collect()
    repo.close()
    del repo
    gc.collect()
    assert owner_ref() is None


def test_thread_affinity(repo):
    tx = repo.read()
    failures = []
    def foreign():
        for op in [lambda: repo.schema, repo.read, repo.close, tx.abort, tx.commit,
                   lambda: tx.get_ref("main"), lambda: repo.__exit__(None, None, None)]:
            try:
                op()
            except dml.InvalidStateError:
                failures.append(True)
    thread = threading.Thread(target=foreign)
    thread.start(); thread.join()
    assert len(failures) == 7
    tx.abort()


@pytest.mark.parametrize("kind,value,error", [
    ("bad", None, ValueError), ("null", 0, TypeError), ("bool", 1, TypeError),
    ("i64", True, TypeError), ("i64", 2**63, OverflowError), ("i64", -(2**63)-1, OverflowError),
    ("bytes", bytearray(), TypeError), ("f64", 1, TypeError), ("list", [42], TypeError),
    ("map", [(dml.ObjectId(b"\0"*16),)], ValueError),
])
def test_datum_validation(kind, value, error):
    with pytest.raises(error):
        dml.Datum(kind, value)


def test_public_value_inputs(tmp_path, repo):
    with pytest.raises(TypeError):
        dml.ObjectId("00" * 16)
    with pytest.raises(ValueError):
        dml.ObjectId(b"\0")
    with pytest.raises(TypeError):
        dml.ObjectId.from_hex(1)
    with pytest.raises(dml.DmlError):
        dml.ObjectId.from_hex("A" * 32)
    with pytest.raises(TypeError):
        dml.canonicalize_uri(1)
    assert dml.canonicalize_uri("HTTP://Example.org/a/../b") == "http://example.org/b"
    with pytest.raises(dml.DmlError):
        dml.canonicalize_uri("relative")
    with pytest.raises(ValueError):
        dml.Repository("bad\0path")
    for kwargs in [{"create": 1}, {"map_size": True}]:
        with pytest.raises(TypeError):
            dml.Repository(tmp_path / "repo", **kwargs)
    with pytest.raises(ValueError):
        dml.Repository(tmp_path / "repo", map_size=-1)
    with pytest.raises(dml.DmlError):
        dml.Repository(tmp_path / "missing")
    with repo.write() as tx:
        identity = tx.put_datum(dml.Datum.bytes(b"x"))
        values = [identity]
        copied = dml.Datum.list(values)
        values.clear()
        assert copied.value == (identity,)
        assert dml.Datum.map([(identity, identity)]).value == ((identity, identity),)
        assert dml.Datum.set([identity]).value == (identity,)
    with pytest.raises(TypeError):
        dml.Tree([(1, identity)])


@pytest.mark.parametrize("op", ["literal", "dag", "tree", "commit", "parent", "create-name", "update-name", "create-target", "update-target"])
def test_mutation_conversion_errors(repo, op):
    with pytest.raises(dml.InvalidStateError):
        with repo.write() as tx:
            try:
                {"literal": lambda: tx.put_literal(1), "dag": lambda: tx.put_dag(root=1),
                 "tree": lambda: tx.put_tree([(1, 1)]), "commit": lambda: tx.put_commit(1),
                 "parent": lambda: tx.put_commit(dml.ObjectId(b"\0"*16), parents=[1]),
                 "create-name": lambda: tx.create_ref(1, 1), "update-name": lambda: tx.update_ref(1, 1),
                 "create-target": lambda: tx.create_ref("main", 1), "update-target": lambda: tx.update_ref("main", 1)}[op]()
            except TypeError:
                pass


def assert_small_boundaries(repo):
    """Use public methods against either the real or private-fault extension."""
    with repo.write() as tx:
        false_id = tx.put_datum(False)
        assert tx.get_datum(false_id) == dml.Datum.bool(False)
        for value in [-(2**63), -42, 2**63 - 1]:
            decoded = tx.get_datum(tx.put_datum(value))
            assert decoded.kind == "i64" and type(decoded.value) is int and decoded.value == value
        for value in [-3.25, 1.0 / 3.0, -0.0, float("inf"), -float("inf")]:
            decoded = tx.get_datum(tx.put_datum(value))
            assert decoded.kind == "f64" and type(decoded.value) is float and decoded.value == value
            if value == 0:
                assert math.copysign(1, decoded.value) == 1
        for kind in ["list", "set", "map"]:
            description = dml.Datum(kind, [])
            identity = tx.put_datum(description)
            decoded = tx.get_datum(identity)
            assert decoded.kind == kind and decoded.value == ()
            assert tx.put_datum(decoded) == identity
        tree = tx.put_tree({})
        assert len(tx.get_tree(tree)) == 0 and tx.get_tree(tree).entries == ()
        commit = tx.put_commit(tree)
        assert tx.get_commit(commit) == dml.Commit(tree, ())


def test_small_empty_boolean_and_numeric_boundaries(repo):
    assert_small_boundaries(repo)


def test_map_full_batch_retry(tmp_path):
    path = tmp_path / "repo"
    with dml.Repository(path, create=True, map_size=1024*1024) as repo:
        with pytest.raises(dml.MapFullError):
            with repo.write() as tx:
                first = tx.put_datum(42)
                tx.put_datum(b"x" * (2*1024*1024))
        with repo.read() as tx:
            with pytest.raises(dml.NotFoundError):
                tx.get_datum(first)
    with dml.Repository(path, map_size=8*1024*1024) as repo:
        with repo.write() as tx:
            assert tx.put_datum(42) == first
            tx.put_datum(b"x" * (2*1024*1024))
