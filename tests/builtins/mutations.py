"""Finite measured test-private copies; predicted invariant failures, no installed hooks."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "python/daggerml/daggerml/builtin.py"
PLUGIN = '''import importlib.util
import os
import sys

def pytest_sessionstart(session):
    import daggerml
    spec = importlib.util.spec_from_file_location("daggerml.builtin", os.environ["MUTANT_SOURCE"])
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    daggerml.builtin = module
'''


def run(destination, only=None):
    destination = Path(destination).resolve()
    destination.mkdir()
    original = SOURCE.read_text()
    specifications = (
        ("version-routing", "return (\"map\", \"key\"), _map_get_v1", "return (\"map\", \"key\"), _map_get_v2",
         "tests/python/test_builtin.py::test_real_v1_v2_exact_entrypoint_sentinels_and_NO_latest", 'assert "v1" in calls'),
        ("THIS-source", "        index_node = self.literal(Datum.i64(index))", "        container = next(n for n in self.handles if n.value == container.value)\n        index_node = self.literal(Datum.i64(index))",
         "tests/python/test_builtin.py::test_equal_nested_collections_THIS_source_not_global_origin", "sources[\"list\"]"),
        ("source-value", "or node_value(tx, selected)[0] != datum", "or False",
         "tests/python/test_builtin_profiles.py::test_strict_native_source_argument_operation_and_trace_recomputation[source-value]", "DID NOT RAISE"),
        ("common-preparation", "        key_node = self.literal(Datum.string(key))\n        return self.call(MAP_GET, binding, self.arguments({\"map\": container, \"key\": key_node}))",
         "        source = self._owned(container)\n        key_id = self.tx.put_datum(Datum.string(key))\n        selected = dict(source.value.value)[key_id]\n        return self.literal(self.tx.get_datum(selected))",
         "tests/python/test_builtin.py::test_actual_common_calls_nested_values_sources_URI_roundtrip_transfer_CLI", "assert 4 == 6"),
    )
    results = []
    for label, before, after, test, signature in specifications:
        if only is not None and label != only:
            continue
        if original.count(before) != 1:
            raise ValueError("mutant source anchor must be unique")
        path = destination / label
        path.mkdir()
        candidate = path / "builtin.py"
        candidate.write_text(original.replace(before, after))
        plugin = path / "mutant_hook.py"
        plugin.write_text(PLUGIN)
        manifest = dict(controller=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                        original=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                        candidate=hashlib.sha256(candidate.read_bytes()).hexdigest(),
                        plugin=hashlib.sha256(plugin.read_bytes()).hexdigest(), test=test, predicted=signature)
        (path / "prelaunch.json").write_text(json.dumps(manifest, indent=2) + "\n")
        env = {**os.environ, "PYTHONPATH": str(path), "MUTANT_SOURCE": str(candidate)}
        result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "mutant_hook", test], cwd=ROOT, env=env, capture_output=True, text=True)
        (path / "log").write_text(result.stdout + result.stderr)
        (path / "exit").write_text(str(result.returncode) + "\n")
        if result.returncode != 1 or signature not in result.stdout:
            raise AssertionError("mutation missed predicted invariant: " + label)
        results.append(dict(label=label, exit=result.returncode, predicted=signature, measured=manifest))
    (destination / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1], None if len(sys.argv) < 3 else sys.argv[2]), indent=2))
