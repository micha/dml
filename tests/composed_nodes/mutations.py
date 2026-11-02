"""Finite measured private helper mutations; HOST tests only, never installed story."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise ValueError("explicit NEW owned mutation output directory required")
    out = Path(args[0]).resolve()
    out.mkdir()
    source = (ROOT / "examples/composed_node_calls.py").read_text()
    cases = [
        ("wrong-producer", "if (selected, result, sources[\"x\"].datum) != (producer.selected.dag, producer.selected.result, producer.returned.datum):", "if False:",
         "tests/python/test_composed_node_calls.py::test_coherent_equal_value_alternate_C_parent_S_not_actual_selected_R", "DID NOT RAISE"),
        ("full-input-key", "selected.inputs.datum == full.datum", "selected.inputs.dag == full.dag",
         "tests/python/test_composed_node_calls.py::test_full_MAP_value_hit_NEW_requested_chain_OLD_executed_chain_no_job", "reuse ref required ONLY"),
        ("actual-parent", "if tx.get_commit(recorded.commit).parents != (authored,):", "if False:",
         "tests/python/test_composed_node_calls.py::test_actual_SAME_name_alternate_decision_parent_response_reject_BEFORE_W", "wrong actual parent must reject BEFORE W"),
        ("normalize-swapped", "for key, value in items:\n        d.Datum.i64(value)", "items = list(zip(('a', 'b'), sorted(value for key, value in items)))\n    for key, value in items:\n        d.Datum.i64(value)",
         "tests/python/test_composed_node_calls.py::test_map_insertion_order_equal_values_swapped_values_differ", "AssertionError"),
    ]
    start = source.index("    decision = inspect_request(path, commit=cq")
    end = source.index("    return Producer(selected, full, returned, cq, decision_name, decision)", start)
    cases.append(("original-chain", source[start:end], "    decision = None\n",
                  "tests/python/test_composed_node_profiles.py::test_selected_ORIGINAL_C_chain_poison_even_value_mismatch", "DID NOT RAISE"))
    results = []
    for label, old, new, nodeid, expected in cases:
        directory = out / label
        directory.mkdir()
        if source.count(old) != 1:
            raise ValueError("mutation source match not unique: " + label)
        candidate = directory / "composed_node_calls.py"
        candidate.write_text(source.replace(old, new))
        shutil.copyfile(ROOT / "examples/composed_node_funcs.py", directory / "composed_node_funcs.py")
        shutil.copyfile(ROOT / "examples/composed_node_calls.py", directory / "original.py")
        plugin = directory / "private_composed_mutant.py"
        plugin.write_text("import sys\nfrom pathlib import Path\ndef pytest_configure(config):\n"
                          "    sys.path.insert(0, %r)\n    sys.path.insert(1, %r)\n"
                          "    import composed_node_calls\n    assert Path(composed_node_calls.__file__).resolve() == Path(%r)\n"
                          % (str(directory), str(ROOT / "examples"), str(candidate)))
        tests = [ROOT / "tests/python/test_composed_node_calls.py", ROOT / "tests/python/test_composed_node_profiles.py"]
        measured = dict(controller=dict(path=__file__, sha256=digest(__file__)),
                        files={str(p): digest(p) for p in (candidate, directory / "original.py", directory / "composed_node_funcs.py", plugin, *tests)},
                        test=nodeid, expected=expected)
        (directory / "prelaunch.json").write_text(json.dumps(measured, indent=2) + "\n")
        with (directory / "log").open("wb") as log:
            run = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "private_composed_mutant", nodeid,
                                  "--junitxml=" + str(directory / "results.xml")], cwd=ROOT,
                                 env={**__import__("os").environ, "PYTHONPATH": str(directory)}, stdout=log, stderr=subprocess.STDOUT)
        (directory / "exit").write_text(str(run.returncode) + "\n")
        text = (directory / "log").read_text()
        if run.returncode != 1 or expected not in text:
            raise RuntimeError("mutation did NOT fail at predicted invariant: " + label)
        results.append(dict(label=label, exit=run.returncode, predicted_invariant=expected, measured=True))
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
