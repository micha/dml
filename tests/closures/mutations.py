"""Finite measured private capture mutations; HOST tests, never installed computation."""

import hashlib
import json
import os
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
        raise ValueError("explicit NEW owned output directory required")
    out = Path(args[0]).resolve()
    out.mkdir()
    cases = [
        ("ignore-scale", "closure_calls.py", "(selected.closure.key, selected.inputs.datum) == (closure.key, full.datum)", "selected.inputs.datum == full.datum",
         "tests/python/test_closure_calls.py::test_changed_scale_miss_full_MAP_same_poison_not_fallback", "reuse ref required ONLY"),
        ("include-source", "closure_calls.py", "(selected.closure.key, selected.inputs.datum) == (closure.key, full.datum)",
         "(selected.closure.key, selected.closure.environment.scale.dag, selected.inputs.datum) == (closure.key, closure.environment.scale.dag, full.datum)",
         "tests/python/test_closure_calls.py::test_own_Q_reuse_new_capture_OLD_execution_and_fresh_control", "required selection has no capture/value match"),
        ("moving-scale", "closure_runtime.py", "scale = rec.load(closure.environment.scale.dag)", "scale = rec.load(tree(tx, context.pre_dispatch)['default-scale'])",
         "tests/python/test_closure_calls.py::test_own_Q_reuse_new_capture_OLD_execution_and_fresh_control", "AssertionError"),
        ("control-flags", "closure_runtime.py", '        }[values["control"]]):',
         '        }.get("fresh" if values["action"] == "execute-fresh" else "require-selected")):',
         "tests/python/test_closure_edges.py::test_child_native_spines_and_coherent_control_before_write[control]", "child rejected BEFORE publication write"),
    ]
    results = []
    for label, filename, old, new, nodeid, expected in cases:
        directory = out / label
        directory.mkdir()
        for n in ("closure_calls.py", "closure_runtime.py", "closure_funcs.py"):
            shutil.copyfile(ROOT / "examples" / n, directory / n)
        source = (directory / filename).read_text()
        if source.count(old) != 1:
            raise ValueError("mutation source match not unique: " + label)
        (directory / filename).write_text(source.replace(old, new))
        plugin = directory / "private_closure_mutant.py"
        plugin.write_text("import sys\nfrom pathlib import Path\ndef pytest_configure(config):\n"
            "    sys.path.insert(0, %r)\n    sys.path.insert(1, %r)\n"
            "    import closure_calls,closure_runtime,closure_funcs\n"
            "    assert Path(closure_calls.__file__).resolve() == Path(%r)\n"
            % (str(directory), str(ROOT / "examples"), str(directory / "closure_calls.py")))
        tests = [ROOT / "tests/python" / n for n in ("test_closure_calls.py", "test_closure_edges.py")]
        measured = dict(controller=dict(path=__file__, sha256=digest(__file__)),
            files={str(p): digest(p) for p in (*directory.glob("*.py"), *tests)}, test=nodeid, expected=expected)
        (directory / "prelaunch.json").write_text(json.dumps(measured, indent=2) + "\n")
        with (directory / "log").open("wb") as log:
            run = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "private_closure_mutant", nodeid,
                "--junitxml=" + str(directory / "results.xml")], cwd=ROOT,
                env={**os.environ, "PYTHONPATH": str(directory)}, stdout=log, stderr=subprocess.STDOUT)
        (directory / "exit").write_text(str(run.returncode) + "\n")
        if run.returncode != 1 or expected not in (directory / "log").read_text():
            raise RuntimeError("mutation did NOT fail at predicted invariant: " + label)
        results.append(dict(label=label, exit=run.returncode, predicted_invariant=expected, measured=True))
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
