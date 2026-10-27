import errno
import gc
import importlib.util
import math
import os
from pathlib import Path
import threading

import daggerml as dml
import pytest

from native_extension import native_extension_path

ROOT = Path(__file__).resolve().parents[2]
BUILD = Path(os.environ.get("DML_BIN", ROOT / "build/check/dml")).resolve().parent
spec = importlib.util.spec_from_file_location("_core_fault", native_extension_path(BUILD, "_core_fault"))
FAULT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(FAULT)


@pytest.fixture
def core(monkeypatch):
    monkeypatch.setattr(dml, "_core", FAULT)
    FAULT.set_fault(0, 0)
    FAULT.native_fault(0, 0, 0)
    yield FAULT
    FAULT.set_fault(0, 0)
    FAULT.native_fault(0, 0, 0)


def test_handle_allocation_cleanup(tmp_path, core):
    for kind in [1, 2]:
        for nth in [1]:
            core.set_fault(kind, nth)
            with pytest.raises(MemoryError):
                dml.Repository(tmp_path / f"fail-{kind}", create=True)
    with dml.Repository(tmp_path / "repo", create=True) as repo:
        for kind in [1, 2]:
            core.set_fault(kind, 1)
            with pytest.raises(MemoryError):
                repo.write()
            with repo.write() as tx:
                tx.put_datum(42)
        core.set_fault(2, 1)
        with pytest.raises(MemoryError):
            repo.schema
    gc.collect()


@pytest.mark.parametrize("operation", ["bytes", "string", "uri", "list", "set", "map", "tree", "commit"])
def test_encode_binding_allocation_failures_rollback(tmp_path, core, operation):
    # Sweep every binding allocation until the operation succeeds. Includes
    # copied UTF-8/record bytes, ID-return objects and tuple/reference arrays.
    for kind in [1, 2]:
        successes = 0
        for nth in range(1, 12):
            with dml.Repository(tmp_path / f"{operation}-{kind}-{nth}", create=True) as repo:
                with repo.write() as tx:
                    child = tx.put_datum(42)
                    node = tx.put_literal(child); dag = tx.put_dag(root=node)
                    tree = tx.put_tree({"a": dag}); parent = tx.put_commit(tree)
                failed = False
                tx = repo.write()
                before = tx.put_datum(43)
                core.set_fault(kind, nth)
                try:
                    if operation == "tree":
                        result = tx.put_tree({"b": dag})
                    elif operation == "commit":
                        result = tx.put_commit(tree, parents=[parent])
                    else:
                        value = {"bytes": dml.Datum.bytes(b"data"), "string": dml.Datum.string("text"),
                                 "uri": dml.Datum.uri("https://example.org/"), "list": dml.Datum.list([child]),
                                 "set": dml.Datum.set([child]), "map": dml.Datum.map([(child, child)])}[operation]
                        result = tx.put_datum(value)
                except MemoryError:
                    failed = True
                finally:
                    core.set_fault(0, 0)
                if failed:
                    with pytest.raises(dml.InvalidStateError):
                        tx.commit()
                else:
                    tx.commit(); successes += 1
                with repo.read() as tx:
                    if failed:
                        with pytest.raises(dml.NotFoundError):
                            tx.get_datum(before)
                    else:
                        assert result is not None
            if successes:
                break
        assert successes


class BadBool:
    def __bool__(self):
        raise TypeError("bad bool")


@pytest.mark.parametrize("value", [None, True, False, -(2**63), -42, 2**63 - 1, -3.25,
                                   1.0 / 3.0, -0.0, float("nan"), float("inf"), -float("inf"),
                                   b"bytes", "text", dml.Datum.uri("https://example.org/")])
def test_decode_scalar_python_allocation_failure(tmp_path, core, value):
    with dml.Repository(tmp_path / "repo", create=True) as repo:
        with repo.write() as tx:
            identity = tx.put_datum(value)
        with repo.read() as tx:
            for nth in [1, 2, 3]:
                core.set_fault(2, nth)
                try:
                    tx.get_datum(identity)
                except MemoryError:
                    pass
                finally:
                    core.set_fault(0, 0)
            decoded = tx.get_datum(identity)
            expected = value.value if isinstance(value, dml.Datum) else value
            if type(expected) is float and math.isnan(expected):
                assert decoded.kind == "f64" and math.isnan(decoded.value)
            else:
                assert decoded.value == expected and type(decoded.value) is type(expected)
            if type(expected) is float and expected == 0:
                assert math.copysign(1, decoded.value) == 1


def test_faults_disabled_public_small_boundaries(tmp_path, core):
    from test_python_api import assert_small_boundaries
    core.set_fault(0, 0)
    core.native_fault(0, 0, 0)
    with dml.Repository(tmp_path / "repo", create=True) as repo:
        assert_small_boundaries(repo)


def test_collection_and_object_decode_allocation_cleanup(tmp_path, core):
    with dml.Repository(tmp_path / "repo", create=True) as repo:
        with repo.write() as tx:
            child = tx.put_datum(42)
            ids = [tx.put_datum(dml.Datum.list([child, child])), tx.put_datum(dml.Datum.map([(child, child)]))]
            node = tx.put_literal(child); dag = tx.put_dag(root=node)
            tree = tx.put_tree({"a": dag}); first = tx.put_commit(tree); commit = tx.put_commit(tree, parents=[first])
        with repo.read() as tx:
            operations = [lambda: tx.get_datum(ids[0]), lambda: tx.get_datum(ids[1]), lambda: tx.get_tree(tree), lambda: tx.get_commit(commit), lambda: tx.get_node(node)]
            for operation in operations:
                for nth in range(1, 14):
                    core.set_fault(2, nth)
                    try:
                        operation()
                    except MemoryError:
                        pass
                    finally:
                        core.set_fault(0, 0)
                operation()


def test_version_uri_id_and_structured_error_allocation_cleanup(core):
    for operation in [dml.version, lambda: dml.canonicalize_uri("HTTP://Example.org/"),
                      lambda: dml.ObjectId.from_hex("00"*16), lambda: dml.ObjectId.from_hex("bad")]:
        for nth in [1, 2]:
            core.set_fault(2, nth)
            try:
                operation()
            except (MemoryError, dml.DmlError):
                pass
            finally:
                core.set_fault(0, 0)


def test_native_begin_commit_and_read_error_lifetime(tmp_path, core):
    with dml.Repository(tmp_path / "repo", create=True) as repo:
        core.native_fault(10, 1, errno.EIO)  # DML_TEST_TXN_BEGIN
        with pytest.raises(dml.DmlError):
            repo.write()
        with repo.write() as tx:
            child = tx.put_datum(42)
        with repo.read() as tx:
            core.native_fault(12, 1, errno.EIO)  # DML_TEST_GET
            with pytest.raises(dml.DmlError):
                tx.get_datum(child)
            assert tx.get_datum(child).value == 42
        tx = repo.write()
        new = tx.put_datum(43)
        core.native_fault(15, 1, errno.EIO)  # DML_TEST_COMMIT consumes LMDB handle
        with pytest.raises(dml.DmlError):
            tx.commit()
        tx.abort()
        with repo.read() as tx:
            with pytest.raises(dml.NotFoundError):
                tx.get_datum(new)


@pytest.mark.parametrize("name,args", [
    ("parse_id", (1,)), ("canonicalize_uri", (1,)), ("repo_open", (1,)),
    ("txn_begin", (1,)), ("txn_end", (1,)), ("get_record", (1,)),
    ("put_record", (1,)), ("ref_op", (1,)), ("encode_datum", (1,)),
    ("encode_object", (1,)), ("decode_datum", (1,)), ("decode_object", (1,)),
])
def test_private_native_argument_errors(name, args):
    with pytest.raises(TypeError):
        getattr(dml._core, name)(*args)


def test_private_native_state_thread_and_conversion_guards(tmp_path):
    core = dml._core
    for operation in [core.repo_schema, core.repo_close, lambda obj: core.txn_begin(obj, True),
                      lambda obj: core.txn_end(obj, False), lambda obj: core.get_record(obj, 2, b"\0"*16)]:
        with pytest.raises(ValueError):
            operation(None)
    with dml.Repository(tmp_path / "repo", create=True) as repo:
        tx = repo.read()
        with pytest.raises(dml.InvalidStateError):
            dml._call(core.txn_begin, repo._handle, False)
        errors = []
        def foreign():
            for operation in [lambda: core.repo_schema(repo._handle), lambda: core.txn_end(tx._handle, False),
                              lambda: core.get_record(tx._handle, 2, b"\0"*16), lambda: core.repo_close(repo._handle)]:
                try:
                    operation()
                except RuntimeError:
                    errors.append(True)
        thread = threading.Thread(target=foreign); thread.start(); thread.join()
        assert len(errors) == 4
        for value in [b"short", "not-bytes"]:
            with pytest.raises((TypeError, ValueError)):
                core.get_record(tx._handle, 2, value)
        tx.abort()
        with pytest.raises(RuntimeError):
            core.get_record(tx._handle, 2, b"\0"*16)
        core.txn_end(tx._handle, False)
        with pytest.raises(RuntimeError):
            core.txn_end(tx._handle, True)
        repo.close()
        with pytest.raises(RuntimeError):
            core.repo_schema(repo._handle)


@pytest.mark.parametrize("kind,value", [(2, BadBool()), (3, 2**70), (4, object()), (5, "not bytes"), (6, b"not str"),
    (8, []), (8, (b"short",)), (10, []), (10, ((),)), (10, ((b"short", b"\0"*16),)), (99, None)])
def test_private_datum_codec_conversion_errors(kind, value):
    with pytest.raises((TypeError, ValueError, OverflowError, RuntimeError)):
        dml._core.encode_datum(kind, value)


@pytest.mark.parametrize("type_code,value,parents", [(3, 1, None), (4, 1, None), (5, [], None), (5, ((),), None),
    (5, ((1, b"\0"*16),), None), (5, ((b"a", 1),), None), (6, 1, ()),
    (6, b"\0"*16, []), (6, b"\0"*16, (1,)), (99, None, None)])
def test_private_object_codec_conversion_errors(type_code, value, parents):
    with pytest.raises((TypeError, ValueError, RuntimeError)):
        dml._core.encode_object(type_code, value, parents)


def test_private_malformed_decoding():
    with pytest.raises(RuntimeError):
        dml._core.decode_datum(b"bad")
    with pytest.raises(RuntimeError):
        dml._core.decode_object(b"bad")
