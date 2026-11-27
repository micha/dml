"""Focused storage and input boundaries for recorded argument maps."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from daggerml import core

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
import recorded_argument_maps as maps

from test_recorded_calls import put, view


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

    def test_inspect_accepts_a_64_deep_returned_source_walk(self):
        source = number(b"x", 0)[1]
        for i in range(64):
            source = self.execute(str(i).encode(), DOUBLE, (b"x", source))
        self.assertEqual(maps.inspect(self.repo, source.ref)["value"], 0)


if __name__ == "__main__":
    unittest.main()
