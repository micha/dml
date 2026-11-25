"""Check trusted call boundaries and late rollback in the captured ordinary example."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from daggerml import core

from trace_support import scan_inventory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
import recorded_ordinary_calls as example


class OrdinaryCallsTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Path(directory.name) / "repo"
        self.defaults = example.defaults(self.repo, b"defaults", 1)
        self.capture = example.capture(self.repo, b"defaults", self.defaults, b"closure")

    def invoke(self, ref=b"call", a=13, b=29, **controls):
        return example.invoke(self.repo, b"closure", self.capture, ref, a, b, **controls)

    def inspect(self, ref):
        return example.inspect(self.repo, ref)

    def inventory(self):
        return scan_inventory(SCANNER, self.repo)

    def test_logical_func_calls_captured_leaves_with_exact_owned_nodes(self):
        outer = example._double_sum
        called, leaves = [], []

        def trace_outer(arguments, get, make_arguments, invoke, add, double):
            add_results, downstream_maps = [], []

            def trace_map(entries):
                self.assertIs(entries[b"x"], add_results[0])
                downstream_maps.append(make_arguments(entries))
                return downstream_maps[0]

            def trace_call(target, node):
                called.append(target)
                if target is add:
                    self.assertIs(node, arguments)
                    add_results.append(invoke(target, node))
                    return add_results[0]
                self.assertIs(target, double)
                self.assertIs(node, downstream_maps[0])
                return invoke(target, node)

            result = outer(arguments, get, trace_map, trace_call, add, double)
            self.assertEqual(called, [add, double])
            return result

        leaf = example._leaf_call

        def trace_leaf(kind, arguments, ops):
            leaves.append(kind)
            return leaf(kind, arguments, ops)

        with patch.object(example, "_double_sum", trace_outer), patch.object(example, "_leaf_call", trace_leaf):
            self.invoke()
        self.assertEqual(leaves, [example.ADD, example.DOUBLE])
        result = self.inspect(b"call")
        self.assertEqual(result["value"], 84)
        self.assertEqual(result["add"]["requested"]["inputs"], result["requested"]["inputs"])
        self.assertEqual(result["double"]["requested"]["upstream_return"], result["add"]["return_dag"])

    def test_outer_hit_and_inspection_do_not_invoke_either_adapter(self):
        first = self.invoke()
        selected = example.Selection(example.REQUIRE, b"call", first)
        with patch.object(example, "_double_sum", side_effect=AssertionError("outer invocation")), \
                patch.object(example, "_leaf_call", side_effect=AssertionError("leaf invocation")):
            self.invoke(b"hit", outer=selected)
            before = self.inventory()
            report = self.inspect(b"hit")
            self.assertEqual(report["status"], "hit")
            self.assertNotEqual(report["requested"]["request"], report["producing"]["request"])
            self.assertEqual(self.inventory(), before)
        self.assertEqual(self.inspect(b"main")["commit"], first.hex())

    def test_caught_foreign_node_error_poisoned_the_outer_attempt(self):
        first = self.invoke()
        callbacks = []

        def swallow(arguments, get, make_arguments, invoke, add, _double):
            get(arguments, b"a")
            get(arguments, b"b")
            summed = invoke(add, arguments)
            callbacks.append((make_arguments, summed))
            foreign = example._Node(summed.value)
            with self.assertRaisesRegex(ValueError, "exact add return"):
                make_arguments({b"x": foreign})
            with self.assertRaisesRegex(ValueError, "poisoned"):
                make_arguments({b"x": summed})
            return summed

        with patch.object(example, "_double_sum", swallow):
            with self.assertRaisesRegex(ValueError, "did not return its second call"):
                self.invoke(b"bad", 29, 13)
        self.assertEqual(self.inspect(b"bad")["status"], "add")
        self.assertEqual(self.inspect(b"main")["commit"], first.hex())
        before = self.inventory()
        make_arguments, summed = callbacks[0]
        with self.assertRaisesRegex(ValueError, "inactive or poisoned"):
            make_arguments({b"x": summed})
        self.assertEqual(self.inventory(), before)

    def test_healthy_but_ended_session_cannot_author_a_double(self):
        callbacks = []

        def abandon(arguments, get, make_arguments, invoke, add, _double):
            get(arguments, b"a")
            get(arguments, b"b")
            summed = invoke(add, arguments)
            callbacks.append((make_arguments, summed))
            return summed

        with patch.object(example, "_double_sum", abandon):
            with self.assertRaisesRegex(ValueError, "did not return its second call"):
                self.invoke()
        before = self.inventory()
        make_arguments, summed = callbacks[0]
        with self.assertRaisesRegex(ValueError, "inactive"):
            make_arguments({b"x": summed})
        self.assertEqual(self.inventory(), before)

    def test_late_phase_and_main_updates_roll_back_only_the_current_batch(self):
        first = self.invoke()
        outer = example._double_sum
        update = core.txn_ref_update
        for phase in (example.DOUBLE_T, example.FINISHED):
            with self.subTest(phase=phase):
                expected_prefix = "add" if phase == example.DOUBLE_T else "double"
                before = []
                out = b"rollback-" + expected_prefix.encode("ascii")

                def trace_outer(arguments, get, make_arguments, invoke, add, double):
                    def trace_call(target, node):
                        result = invoke(target, node)
                        if target is (add if phase == example.DOUBLE_T else double):
                            before.append(self.inventory())
                        return result
                    return outer(arguments, get, make_arguments, trace_call, add, double)

                def fail_late(txn, ref, commit):
                    update(txn, ref, commit)
                    fail_ref = out if phase == example.DOUBLE_T else b"main"
                    if ref == fail_ref and example._snapshot(txn, commit)[0] == phase:
                        raise ValueError("late update fault")

                with patch.object(example, "_double_sum", trace_outer), patch.object(core, "txn_ref_update", fail_late):
                    with self.assertRaisesRegex(ValueError, "late update fault"):
                        self.invoke(out, 29, 13)
                self.assertEqual(len(before), 1)
                self.assertEqual(self.inventory(), before[0])
                self.assertEqual(self.inspect(out)["status"], expected_prefix)
                self.assertEqual(self.inspect(b"main")["commit"], first.hex())

    def test_add_overflow_keeps_start_without_invoking_double(self):
        first = self.invoke()
        with patch.object(example, "_leaf_call", wraps=example._leaf_call) as leaf:
            with self.assertRaisesRegex(ValueError, "add result is not a signed 64-bit integer"):
                self.invoke(b"partial", (1 << 63) - 1, 1)
        self.assertEqual([call.args[0] for call in leaf.call_args_list], [example.ADD])
        self.assertEqual(self.inspect(b"partial")["status"], "start")
        self.assertEqual(self.inspect(b"main")["commit"], first.hex())

    def test_required_absent_double_keeps_successful_add(self):
        first = self.invoke()
        with self.assertRaisesRegex(ValueError, "no selected double attempt"):
            self.invoke(b"partial", double=example.Selection(example.REQUIRE, b"absent"))
        self.assertEqual(self.inspect(b"partial")["add"]["value"], 42)
        self.assertEqual(self.inspect(b"main")["commit"], first.hex())

    def test_new_outer_request_cannot_repeat_producer_occurrence(self):
        invocation = b"90000000-0000-4000-8000-000000000001"
        first = self.invoke(invocation=invocation)
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "new request"):
            self.invoke(b"hit", outer=example.Selection(example.REQUIRE, b"call", first), invocation=invocation)
        self.assertEqual(self.inventory(), before)

    def test_exact_i64_and_ref_aliases_rejected_before_recording(self):
        before = self.inventory()
        for value in (True, 1.5, 1 << 63, -(1 << 63) - 1):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "signed 64-bit integer"):
                self.invoke(a=value)
        with self.assertRaises(ValueError):
            self.invoke(b"closure")
        with self.assertRaises(ValueError):
            self.invoke(b"main")
        self.assertEqual(self.inventory(), before)


if __name__ == "__main__":
    SCANNER = Path(sys.argv.pop(1)).resolve()
    unittest.main()
