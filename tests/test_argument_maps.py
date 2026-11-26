"""Focused storage and input boundaries for recorded argument maps."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from daggerml import core

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
import recorded_argument_maps as maps

from test_recorded_calls import literal, put, view


DOUBLE = b"double@1"
ADD = b"add@1"


def identity(n):
    return f"00000000-0000-4000-8000-{n:012d}".encode()


def number(name, value):
    return name, maps.Literal(core.DATUM_I64, value)


def snapshot(txn, commit):
    commit_view, tree, count = view(txn, core.REC_COMMIT, commit)
    tree_view, _, entries = view(txn, core.REC_TREE, tree)
    if entries != 1:
        raise ValueError("fixture requires a single tree entry")
    dag, name = core.object_view_entry(tree_view, 0)
    return dag, name, tuple(core.object_view_parent(commit_view, i) for i in range(count))


def publish(txn, ref, name, dag, *parents):
    tree = put(txn, core.REC_TREE, name, dag)
    commit = put(txn, core.REC_COMMIT, tree, *parents)
    core.txn_ref_create(txn, ref, commit)
    return commit


class ArgumentMapsTest(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / "repo"
        self.serial = 0

    def request(self, tag, implementation, arguments, **kwargs):
        self.serial += 1
        return maps.request(self.repo, b"p" + tag, b"d" + tag, implementation, identity(self.serial),
                            arguments, **kwargs)

    def execute(self, tag, implementation, *arguments):
        self.request(tag, implementation, arguments)
        request = bytes.fromhex(maps.inspect(self.repo, b"p" + tag)["requested"]["request"])
        return maps.Returned(b"t" + tag, maps.work(self.repo, b"p" + tag, request, b"t" + tag, identity(self.serial)))

    def table(self, first):
        empty = maps.define_table(self.repo, b"empty", b"double")
        return maps.update_table(self.repo, b"empty", empty, b"selected", b"insert", selected=first)

    def data(self):
        return (self.repo / "data.mdb").read_bytes()

    def test_requested_map_cannot_substitute_another_well_formed_map(self):
        self.request(b"1", DOUBLE, [number(b"x", 42)])
        self.request(b"2", DOUBLE, [number(b"x", 43)])
        with maps.records._write_transaction(self.repo, create=False) as txn:
            dag, role, parents = snapshot(txn, core.txn_ref_get(txn, b"p1"))
            other, _, _ = snapshot(txn, core.txn_ref_get(txn, b"p2"))
            _, wrong_root, _ = view(txn, core.REC_DAG, other)
            fields = [field for name in (b"implementation", b"invocation", b"construction")
                      for field in (name, core.txn_lookup_node(txn, dag, name))]
            forged = put(txn, core.REC_DAG, wrong_root, *fields)
            publish(txn, b"forged", role, forged, *parents)
        with self.assertRaisesRegex(ValueError, "differs from its construction"):
            maps.inspect(self.repo, b"forged")

    def test_forged_returned_source_link_is_rejected_even_when_decoy_value_is_equal(self):
        exact = self.execute(b"first", ADD, number(b"a", 13), number(b"b", 29))
        decoy = self.execute(b"second", ADD, number(b"a", 12), number(b"b", 30))
        self.assertEqual(maps.inspect(self.repo, exact.ref)["value"], maps.inspect(self.repo, decoy.ref)["value"])
        self.request(b"correct", DOUBLE, [(b"x", exact)])
        with maps.records._write_transaction(self.repo, create=False) as txn:
            dag, role, parents = snapshot(txn, core.txn_ref_get(txn, b"pcorrect"))
            _, _, (_, decoy_result) = snapshot(txn, decoy.attempt)
            decoy_dag, _, _ = snapshot(txn, decoy_result)
            wrong_source = put(txn, core.REC_NODE, core.NODE_SUBDAG, decoy_dag)
            _, construction, _ = view(txn, core.REC_NODE, core.txn_lookup_node(txn, dag, b"construction"))
            _, map_root, _ = view(txn, core.REC_DAG, construction)
            fields = [field for name in (b"prior", b"key", b"origin")
                      for field in (name, core.txn_lookup_node(txn, construction, name))]
            wrong = put(txn, core.REC_DAG, map_root, b"source", wrong_source, *fields)
            fields = [field for name in (b"implementation", b"invocation")
                      for field in (name, core.txn_lookup_node(txn, dag, name))]
            forged = put(txn, core.REC_DAG, map_root, b"construction", put(txn, core.REC_NODE, core.NODE_SUBDAG, wrong),
                         *fields)
            publish(txn, b"forged", role, forged, *parents)
        with self.assertRaisesRegex(ValueError, "returned source does not match the selected attempt result"):
            maps.inspect(self.repo, b"forged")

    def test_equal_value_does_not_make_a_get_trace_portable_to_another_construction(self):
        literal_attempt = self.execute(b"literal", DOUBLE, number(b"x", 42))
        upstream = self.execute(b"upstream", ADD, number(b"a", 13), number(b"b", 29))
        self.request(b"new", DOUBLE, [(b"x", upstream)])
        with maps.records._write_transaction(self.repo, create=False) as txn:
            attempt_dag, role, (_, old_result) = snapshot(txn, literal_attempt.attempt)
            result_dag, result_role, _ = snapshot(txn, old_result)
            request = core.txn_ref_get(txn, b"pnew")
            graft = publish(txn, b"grafted-result", result_role, result_dag, request)
            publish(txn, b"grafted-attempt", role, attempt_dag, request, graft)
        with self.assertRaisesRegex(ValueError, "map_get trace does not match the producing construction"):
            maps.inspect(self.repo, b"grafted-attempt")

    def test_poisoned_unrelated_entry_cannot_be_hidden_by_removal(self):
        first = self.execute(b"one", DOUBLE, number(b"x", 42))
        other = self.execute(b"other", DOUBLE, number(b"x", 43))
        basis = self.table(first)
        other_input = maps.inspect(self.repo, other.ref)["producing"]["argument_map"]
        with maps.records._write_transaction(self.repo, create=False) as txn:
            # A native MAP for 43 exists, but this record claims the 42 attempt produced it.
            key = put(txn, core.REC_NODE, core.NODE_LITERAL, bytes.fromhex(other_input))

            def delta(op):
                return put(txn, core.REC_DAG, key, b"operation", literal(txn, core.DATUM_STRING, op))

            poison = publish(txn, b"forged", maps.DELTA, delta(b"insert"), basis, first.attempt)
            buried = publish(txn, b"buried", maps.DELTA, delta(b"remove"), poison)
        before = self.data()
        error = "does not match the table intent and argument MAP"
        for ref, commit in ((b"forged", poison), (b"buried", buried)):
            with self.subTest(ref=ref), self.assertRaisesRegex(ValueError, error):
                self.request(b"hit", DOUBLE, [number(b"x", 42)], mode=maps.TRY, table_ref=ref, table_commit=commit)
            self.assertEqual(self.data(), before)
        self.request(b"bypass", DOUBLE, [number(b"x", 42)], mode=maps.FRESH, table_ref=b"buried", table_commit=poison)
        self.assertEqual(maps.inspect(self.repo, b"dbypass")["table"], "")

    def test_inspect_accepts_a_64_deep_returned_source_walk(self):
        source = number(b"x", 0)[1]
        for i in range(64):
            source = self.execute(str(i).encode(), DOUBLE, (b"x", source))
        self.assertEqual(maps.inspect(self.repo, source.ref)["value"], 0)


if __name__ == "__main__":
    unittest.main()
