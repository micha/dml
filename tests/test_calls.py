"""Focused Python ownership and structural profile checks for daggerml.calls."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from daggerml import builtin, calls, core

from test_recorded_calls import transaction


EMPTY = builtin.Datum(core.DATUM_MAP, core.datum_decode(core.datum_encode(core.DATUM_MAP, ()))[0])
INTENT = b"urn:dml:test:double"
IMPLEMENTATION = b"urn:dml:test:double:v2"
GETTER = b"dml://source/builtin/map/get/v2"


class CallScopeTest(unittest.TestCase):
    def test_copied_value_outlives_scope_and_nested_calls_preserve_node_identity(self):
        with calls.Scope() as scope:
            arguments = scope.copy(EMPTY)
            with scope.bind(lambda node: node) as leaf:
                with scope.bind(lambda node: scope.invoke(leaf, node)) as outer:
                    result = scope.invoke(outer, arguments)
            self.assertIs(result, arguments)
        self.assertEqual(result.value, EMPTY)
        with self.assertRaisesRegex(calls.CallError, "inactive"):
            scope.invoke(outer, arguments)

    def test_rejects_fabricated_inputs_and_foreign_results(self):
        for mode in ("input", "result"):
            with self.subTest(mode=mode), self.assertRaisesRegex(calls.CallError, "caught error poisoned"):
                with calls.Scope() as first, calls.Scope() as second:
                    local, foreign = first.copy(EMPTY), second.copy(EMPTY)
                    with first.bind(lambda _: foreign) as target:
                        if mode == "input":
                            with self.assertRaisesRegex(calls.CallError, "owned argument MAP"):
                                first.invoke(target, calls.Node(local.value))
                        else:
                            with self.assertRaisesRegex(calls.CallError, "returned a foreign node"):
                                first.invoke(target, local)

    def test_caught_nested_error_cannot_return_a_successful_node(self):
        with self.assertRaisesRegex(calls.CallError, "poisoned"):
            with calls.Scope() as scope:
                arguments = scope.copy(EMPTY)
                with scope.bind(lambda node: node) as expired:
                    pass

                def swallow(node):
                    with self.assertRaisesRegex(calls.CallError, "unbound call target"):
                        scope.invoke(expired, node)
                    return node

                with scope.bind(swallow) as target:
                    scope.invoke(target, arguments)
                    self.fail("a caught nested failure escaped as a successful result")

    def test_foreign_thread_cannot_enter_a_live_adapter(self):
        with calls.Scope() as scope, ThreadPoolExecutor(max_workers=1) as pool:
            arguments = scope.copy(EMPTY)
            entered = []

            def adapter(node):
                entered.append(node)
                return node

            with scope.bind(adapter) as target:
                with self.assertRaisesRegex(calls.CallError, "foreign"):
                    pool.submit(scope.invoke, target, arguments).result()
                self.assertEqual(entered, [])
                self.assertIs(scope.invoke(target, arguments), arguments)
                self.assertEqual(entered, [arguments])


class ClosureTest(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name) / "repo"
        core.repo_close(core.repo_open(self.repo, True))

    def test_closure_keeps_exact_named_binding_without_authorizing_dispatch(self):
        with transaction(self.repo, core.TXN_WRITE) as txn:
            getter = builtin.put_binding(txn, b"dml://source/builtin/map/get/unsupported")
            closure = calls.put_closure(txn, intent=INTENT, implementation=IMPLEMENTATION, captures={b"get": getter})
            description = calls.inspect_closure(txn, closure, names=(b"get",))
            self.assertEqual(description, calls.Closure(closure, INTENT, IMPLEMENTATION, ((b"get", getter),)))
            with self.assertRaisesRegex(ValueError, "binding count"):
                calls.inspect_closure(txn, closure, names=())
            with self.assertRaisesRegex(ValueError, "missing builtin profile field"):
                calls.inspect_closure(txn, closure, names=(b"wrong",))
            with self.assertRaisesRegex(calls.CallError, "may not shadow metadata"):
                calls.put_closure(txn, intent=INTENT, implementation=IMPLEMENTATION, captures={b"intent": getter})

    def test_builtin_target_uses_the_prepared_native_argument_node(self):
        with transaction(self.repo, core.TXN_WRITE) as txn:
            getter = builtin.put_binding(txn, GETTER)
            with builtin.Recorder(txn) as recorder, calls.Scope() as scope:
                original = recorder.arguments({b"x": recorder.literal(core.DATUM_I64, 42)})
                prepared = recorder.arguments({b"map": original, b"key": recorder.literal(core.DATUM_STRING, b"x")})
                prepared_id = recorder.dag(prepared)
                with scope.bind_builtin(recorder, builtin.MAP_GET, getter, prepared) as (target, arguments):
                    self.assertEqual(scope.invoke(target, arguments).value.as_i64(), 42)
                trace = builtin.Inspector(txn).trace(recorder.trace())
                self.assertEqual(len(trace), 1)
                self.assertEqual(trace[0].arguments.dag, prepared_id)
                self.assertEqual(trace[0].binding.dag, getter)

    def test_equal_copied_map_cannot_replace_a_bound_builtin_argument(self):
        with transaction(self.repo, core.TXN_WRITE) as txn:
            getter = builtin.put_binding(txn, GETTER)
            with builtin.Recorder(txn) as recorder:
                prepared = recorder.arguments()
                with self.assertRaisesRegex(calls.CallError, "caught error poisoned"):
                    with calls.Scope() as scope:
                        with scope.bind_builtin(recorder, builtin.MAP_GET, getter, prepared) as (target, arguments):
                            with self.assertRaisesRegex(calls.CallError, "exact prepared argument"):
                                scope.invoke(target, scope.copy(arguments.value))
                self.assertEqual(builtin.Inspector(txn).trace(recorder.trace()), ())


if __name__ == "__main__":
    unittest.main()
