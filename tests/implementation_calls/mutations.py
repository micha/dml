"""Opt-in FOUR finite private-source causal mutants, not exhaustive scores/runtime hooks."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HELPERS = ("implementation_calls.py", "implementation_call_session.py", "implementation_call_adapter.py",
           "implementation_call_leaf.py", "implementation_call_funcs.py", "implementation_leaf_funcs.py",
           "reuse_selection.py", "explicit_reuse.py")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(output):
    output = Path(output).resolve()
    output.mkdir()
    cases = [
        dict(name="binding-in-key", file="implementation_calls.py",
             edits=[('hit = selected is not None and (selected["closure"]["intent"], selected["inputs_datum"]) == (closure["intent"], full.datum)',
                     'hit = selected is not None and (selected["closure"]["intent"], selected["closure"]["binding"], selected["inputs_datum"]) == (closure["intent"], closure["binding"], full.datum)')],
             test="tests/python/test_implementation_calls.py::test_targeted_cross_B_outer_and_inner_hits_PIN_OLD_A_no_automatic_adoption",
             prediction="positive cross-B reuse must fail required-hit oracle"),
        dict(name="moving-default-target", file="implementation_call_session.py",
             edits=[('        target = self.q.closure["add" if slot == 0 else "double"]\n        with d.Repository(self.path) as repo, repo.read() as tx:',
                     '        with d.Repository(self.path) as repo, repo.read() as tx:\n            target = leaf.inspect(tx, p.tree(tx, self.current)["default-add" if slot == 0 else "default-double"], *leaf.sources())\n        with d.Repository(self.path) as repo, repo.read() as tx:')],
             test="tests/python/test_implementation_calls.py::test_actual_pinned_A_leaf_dispatch_AFTER_defaults_B",
             prediction="pinned-A after defaultsB must refuse illegal target retargeting or fail source oracle"),
        dict(name="fresh-producer-association", file="implementation_calls.py",
             edits=[('if oid(tx, sf["completion"]) != joined:', 'if False:  # PRIVATE mutant: disable THIS joined F witness'),
                    ('if selected.request != own_q and (reused is None or selected.dag != inner_selected[prep[1]].dag):',
                     'if False:  # PRIVATE mutant: disable own fresh Q vs OLD producer guard'),
                    ('if selected.request != own_q:\n                        inspect_leaf_reuse(tx, current, own_q, selected, prep[0]["decision"])',
                     'if selected.request != own_q and reused is not None:\n                        inspect_leaf_reuse(tx, current, own_q, selected, prep[0]["decision"])')],
             test="tests/python/test_implementation_call_failures.py::test_native_coherent_wrong_inner_source_phase_producer_BEFORE_later_dispatch[valid-OLD-S-graft]",
             prediction="valid-but-wrong old S graft must escape refusal and kill no-later-dispatch oracle"),
        dict(name="caught-poison-exit", file="calls.py",
             edits=[('if kind is None and self.poisoned:', 'if False:  # PRIVATE mutant: accept caught poison on exit')],
             test="tests/python/test_calls.py::test_caught_scope_callback_verifier_and_state_errors_poison_whole_writer[fabricated-node]",
             prediction="caught fabricated-node error must no longer abort Context/native batch"),
    ]
    tests = [case["test"] for case in cases]
    rows = []
    baseline = output / "baseline"
    baseline.mkdir()
    command = [sys.executable, "-m", "pytest", "-q", *tests,
               "--basetemp=" + str(baseline / "native-cases"), "--junitxml=" + str(baseline / "pytest.xml")]
    with (baseline / "stdout.log").open("wb") as stdout, (baseline / "stderr.log").open("wb") as stderr:
        result = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr)
    (baseline / "exit").write_text(str(result.returncode) + "\n")
    if result.returncode != 0:
        raise RuntimeError("mutant baseline FAILED; STOP before all mutants")
    for case in cases:
        directory = output / case["name"]
        directory.mkdir()
        sources = directory / "source"
        sources.mkdir()
        for name in HELPERS:
            (sources / name).write_bytes((ROOT / "examples" / name).read_bytes())
        module = ROOT / "python/daggerml/daggerml/calls.py"
        (sources / "calls.py").write_bytes(module.read_bytes())
        path = sources / case["file"]
        original = path.read_text()
        changed = original
        for before, after in case["edits"]:
            if changed.count(before) != 1:
                raise RuntimeError("nonunique PRIVATE mutant anchor: " + case["name"])
            changed = changed.replace(before, after)
        path.write_text(changed)
        plugin = directory / "private_plugin.py"
        plugin.write_text('''import hashlib,importlib.util,json,sys
from pathlib import Path
SOURCES=Path(%r)
LOADED=False
def pytest_collect_file(file_path,parent):
    global LOADED
    if LOADED or "daggerml" not in sys.modules or not file_path.name.startswith("test_"):
        return
    LOADED=True
    import daggerml
    spec=importlib.util.spec_from_file_location("daggerml.calls",SOURCES/"calls.py")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    daggerml.calls=module
    sys.path.insert(0,str(SOURCES))
    import implementation_call_leaf,implementation_calls,implementation_call_session,implementation_call_adapter
    modules=(module,implementation_call_leaf,implementation_calls,implementation_call_session,implementation_call_adapter)
    actual={m.__name__:{"path":m.__file__,"sha256":hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()} for m in modules}
    (SOURCES.parent/"actual-imports.json").write_text(json.dumps(actual,indent=2)+"\\n")
''' % str(sources))
        environment = dict(os.environ, PYTHONPATH=str(directory))
        command = [sys.executable, "-m", "pytest", "-q", "-p", "private_plugin", case["test"],
                   "--basetemp=" + str(directory / "native-cases"), "--junitxml=" + str(directory / "pytest.xml")]
        with (directory / "stdout.log").open("wb") as stdout, (directory / "stderr.log").open("wb") as stderr:
            result = subprocess.run(command, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr)
        (directory / "exit").write_text(str(result.returncode) + "\n")
        row = dict(name=case["name"], expected=case["prediction"], command=command, exit=result.returncode,
            preliminary="oracle killed" if result.returncode == 1 else "survived" if result.returncode == 0 else "tooling failure NOT kill",
            original_sha256=hashlib.sha256(original.encode()).hexdigest(), mutant_sha256=digest(path),
            source={name: digest(sources / name) for name in (*HELPERS, "calls.py")},
            qualification="TEST-PRIVATE module loader/native-HOST cases; primary failure must be reviewed, exit1 alone is NOT a causal kill")
        rows.append(row)
        (output / "results.json").write_text(json.dumps(dict(baseline_exit=0, mutants=rows, planned=4, not_exhaustive=True), indent=2) + "\n")
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if not args.run:
        raise ValueError("explicit --run required; no default mutation/child execution")
    print(json.dumps(run(args.output), indent=2))


if __name__ == "__main__":
    main()
