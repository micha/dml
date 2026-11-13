"""Exactly THREE real native outer binding/version/source-interface refusals, ZERO HOST/OS."""

import daggerml as d
from daggerml import builtin as b, calls as c
import pytest

from test_implementation_calls import initial, p, leaf
from test_exchange_records import clone


def variant(path, commit, getter):
    with d.Repository(path) as repo, repo.write() as tx:
        entries = p.tree(tx, commit)
        map_binding = b.put_binding(tx, source_uri="dml://source/builtin/map/get/" + getter)
        env = c.put_environment(tx, {"add": c.Capture("ordinary", leaf.ADD, entries["add-A"]),
            "double": c.Capture("ordinary", leaf.DOUBLE, entries["double-A"]),
            "map-get": c.Capture("builtin", b.MAP_GET, map_binding)})
        binding = b.record(tx, c.INPROCESS_ROLE, values={"adapter": d.Datum.uri(p.ADAPTER),
            "source": p.binding_source(env), "interpreter": None, "timeout-ms": None}, links={"environment": env})
        closure = c.put_closure(tx, intent=p.INTENT, binding=binding, environment=env)
        entries["variant"] = closure
        current = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref("variant", current)
    return current, closure


def positives(tx, closure):
    generic = c.inspect_closure(tx, closure)
    shallow = leaf.shallow_closure(tx, closure, p.INTENT, {"add": ("ordinary", leaf.ADD),
        "double": ("ordinary", leaf.DOUBLE), "map-get": ("builtin", b.MAP_GET)})
    for name, intent in (("add", leaf.ADD), ("double", leaf.DOUBLE)):
        leaf.shallow_closure(tx, shallow[name], intent, {"map-get": ("builtin", b.MAP_GET),
            "list-get": ("builtin", b.LIST_GET)})
        leaf.inspect(tx, shallow[name], *leaf.sources())
    assert set(dict(generic.captures)) == set(shallow)
    return generic, shallow


def refuse_no_Q(path, commit, message, monkeypatch):
    baseline = (path / "data.mdb").read_bytes()
    def forbidden(*a, **k):
        pytest.fail("binding refusal MUST precede native Q authoring/ordinary dispatch")
    monkeypatch.setattr(p, "event", forbidden)
    monkeypatch.setattr(p.ex, "record_exchange_request", forbidden)
    monkeypatch.setattr(p.ex, "execute_exchange", forbidden)
    with pytest.raises(ValueError, match=message):
        p.record_request(path, commit=commit, closure_name="variant", ref="NEVER-Q")
    assert (path / "data.mdb").read_bytes() == baseline
    with d.Repository(path) as repo, repo.read() as tx:
        assert tx.get_ref("variant") == commit
        with pytest.raises(d.NotFoundError):
            tx.get_ref("NEVER-Q")
        assert not any(name.startswith(("outer-request-", "outer-attempt-", "request-q-", "attempt-a-")) for name in p.tree(tx, commit))


def test_actual_v99_generic_and_fixed_shallow_pass_then_exact_supported_version_refusal(initial, monkeypatch):
    path, commit = initial
    commit, closure = variant(path, commit, "v99")
    with d.Repository(path) as repo, repo.read() as tx:
        generic, shallow = positives(tx, closure)
        assert b.inspect_binding(tx, shallow["map-get"]).source_uri == "dml://source/builtin/map/get/v99"
        normal = tx.get_dag(generic.binding).bindings
        assert b.scalar(tx, normal["source"], "bytes") == p.binding_source(generic.environment)
    refuse_no_Q(path, commit, "fixed outer getter version differs", monkeypatch)


def test_actual_supported_v2_vs_v1leaves_pass_version_then_shared_binding_refusal(initial, monkeypatch):
    path, commit = initial
    commit, closure = variant(path, commit, "v2")
    with d.Repository(path) as repo, repo.read() as tx:
        generic, shallow = positives(tx, closure)
        actual = b.inspect_binding(tx, shallow["map-get"]).source_uri
        assert actual in ("dml://source/builtin/map/get/v1", "dml://source/builtin/map/get/v2")
        add = leaf.inspect(tx, shallow["add"], *leaf.sources())
        double = leaf.inspect(tx, shallow["double"], *leaf.sources())
        assert add["map_binding"] == double["map_binding"] != shallow["map-get"]
        assert b.scalar(tx, tx.get_dag(generic.binding).bindings["source"], "bytes") == p.binding_source(generic.environment)
    refuse_no_Q(path, commit, "outer/leaf getter captures must share actual binding", monkeypatch)


def test_retained_native_outer_B_source_ONEbyte_shapes_version_shared_pass_then_source_refusal(initial, monkeypatch):
    path, commit = initial
    with d.Repository(path) as repo, repo.write() as tx:
        entries = p.tree(tx, commit)
        original = c.inspect_closure(tx, entries["outer-A"])
        fields = tx.get_dag(original.binding).bindings
        source = b.scalar(tx, fields["source"], "bytes")
        changed = source[:-1] + (b"X" if source[-1:] != b"X" else b"Y")
        assert len(source) == len(changed) and sum(a != z for a, z in zip(source, changed)) == 1
        bad_binding = clone(tx, original.binding, fields={"source": b.literal(tx, changed)})
        entries["variant"] = c.put_closure(tx, intent=p.INTENT, binding=bad_binding, environment=original.environment)
        closure = entries["variant"]
        commit = tx.put_commit(tx.put_tree(entries), parents=(commit,))
        tx.create_ref("variant", commit)
    with d.Repository(path) as repo, repo.read() as tx:
        generic, shallow = positives(tx, closure)
        assert closure in b.Inspector(tx, commit=commit).retained
        assert b.inspect_binding(tx, shallow["map-get"]).source_uri == "dml://source/builtin/map/get/v1"
        assert shallow["map-get"] == leaf.inspect(tx, shallow["add"], *leaf.sources())["map_binding"]
        assert shallow["map-get"] == leaf.inspect(tx, shallow["double"], *leaf.sources())["map_binding"]
        assert b.scalar(tx, tx.get_dag(generic.binding).bindings["adapter"], "uri") == p.ADAPTER
        assert b.scalar(tx, tx.get_dag(generic.binding).bindings["source"], "bytes") != p.binding_source(generic.environment)
    refuse_no_Q(path, commit, "outer exact captured binding source differs", monkeypatch)
