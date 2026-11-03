"""Opt-in SEVEN finite measured PRIVATE Python mutants; no shipped runtime hooks."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HELPERS = ("captured_calls.py", "captured_call_session.py", "captured_call_adapter.py", "captured_call_funcs.py",
           "captured_call_leaf.py", "composed_node_funcs.py", "reuse_selection.py", "explicit_reuse.py")
MUTANTS = (
    ("omit-poison", "captured_call_session.py", (("            self.poisoned = True", "            self.poisoned = False"),),
     "tests/python/test_captured_call_edges.py::test_session_scope_caught_poison_blocks_success[foreign]",
     "caught interface error fails permanent-poison assertion; not merely a successful later reply"),
    ("literal-launder", "captured_call_session.py", (("rec.arguments({\"x\": rec.load(source)})", "rec.arguments({\"x\": rec.literal(entries[\"x\"].value)})"),),
     "tests/python/test_captured_calls.py::test_actual_logical_calls_direct_sources_shared_content_but_distinct_positions",
     "exact double input/source guard rejects literal42 substituted for actual add R before double dispatch"),
    ("ignore-capture-key", "captured_calls.py", (("(selected[\"closure\"][\"key\"], selected[\"inputs_datum\"]) == (closure[\"key\"], full.datum)",
          "selected[\"inputs_datum\"] == full.datum"),),
     "tests/python/test_captured_call_profiles.py::test_changed_valid_capture_identity_cannot_reuse_even_equal_intent_full_MAP",
     "valid NEW captured B/E with same intent/MAP is wrongly reused; required mismatch assertion fails"),
    ("reread-default", "captured_call_session.py", (("        target = self.q.closure[\"add\" if slot == 0 else \"double\"]",
         "        with d.Repository(self.path) as repo, repo.read() as tx:\n            target = leaf.inspect(tx, p.tree(tx, self.current)[\"default-add\" if slot == 0 else \"default-double\"], *leaf.sources())"),),
     "tests/python/test_captured_call_profiles.py::test_moved_defaults_cannot_retarget_prepared_call_BEFORE_dispatch",
     "persisted pending preparation mismatches captured C; independent native guard rejects BEFORE fresh publication"),
    ("skip-original-control", "captured_calls.py", ((" or action != actual", ""),
         ("if (q.action != \"execute-fresh\" or initial_aid != aid", "if (initial_aid != aid")),
     "tests/python/test_captured_call_edges.py::test_selected_leaf_ORIGINAL_outer_poison_even_fresh_or_value_mismatch[fresh-inputs-outer-D-action]",
     "OLD public S with poisoned ORIGINAL D.action is incorrectly accepted standalone; expected rejection fails"),
    ("extra-inner-Q-on-hit", "captured_calls.py", (("            entries[\"outer-reuse-\" + qid] = b.record(tx, W_ROLE, links=fields, root=\"result\")",
         "            entries[\"outer-reuse-\" + qid] = b.record(tx, W_ROLE, links=fields, root=\"result\")\n            entries[\"request-q-\" + \"e\" * 32] = local.put_local_request(tx, request_id=\"q-\" + \"e\" * 32, intent_uri=leaf.ADD, binding=closure[\"add\"][\"binding\"], inputs=full.dag)"),),
     "tests/python/test_captured_calls.py::test_outer_hit_no_invocation_swapped_inner_ownQ_OLD_chain_and_fresh_default_pin",
     "outer hit publishes forbidden inner Q; native W-only delta guard rejects at hit, before later fresh rows"),
    ("omit-prospective-reserve", "captured_call_session.py", (("        self._reserve(6)", "        pass  # PRIVATE mutant omits aggregate reservation before semantic puts"),),
     "tests/python/test_captured_call_profiles.py::test_ACTUAL_native_union_and_prospective_64_boundary_BEFORE_child[7-57]",
     "real64 aggregate reaches authoring before rejection instead of deterministic pre-put SessionError; boundary oracle fails"),
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(directory):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    rows = []
    for label, filename, replacements, target, prediction in MUTANTS:
        case = directory / label
        private = case / "private"
        private.mkdir(parents=True)
        for n in HELPERS:
            shutil.copyfile(ROOT / "examples" / n, private / n)
        source = private / filename
        text = source.read_text()
        for old, new in replacements:
            if text.count(old) != 1:
                raise ValueError("mutation source is not unique: " + label)
            text = text.replace(old, new)
        source.write_text(text)
        hashes = {n: digest(private / n) for n in HELPERS}
        plugin = case / "candidate_plugin.py"
        plugin.write_text("import importlib,sys,json\nfrom pathlib import Path\n"
            "def pytest_configure(config):\n"
            "    root=Path(%r)\n    sys.path.insert(0,str(root))\n"
            "    modules={n:importlib.import_module(n) for n in %r}\n"
            "    assert all(Path(m.__file__).resolve()==root/(n+'.py') for n,m in modules.items())\n"
            "    Path(%r).write_text(json.dumps({n:str(m.__file__) for n,m in modules.items()}))\n"
            % (str(private), ("captured_calls", "captured_call_session", "captured_call_adapter", "captured_call_funcs", "captured_call_leaf"), str(case / "actual-imports.json")))
        before = dict(label=label, target=target, prediction=prediction, hashes=hashes, replacements=replacements)
        (case / "prelaunch.json").write_text(json.dumps(before, indent=2) + "\n")
        env = dict(os.environ, PYTHONPATH=str(case))
        command = [sys.executable, "-m", "pytest", "-q", "-p", "candidate_plugin", target,
                   "--junitxml=" + str(case / "pytest.xml")]
        with open(case / "stdout", "wb") as out, open(case / "stderr", "wb") as err:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=out, stderr=err)
        (case / "exit").write_text(str(result.returncode) + "\n")
        xml = ET.parse(case / "pytest.xml").getroot() if (case / "pytest.xml").exists() else None
        tests = [] if xml is None else xml.findall(".//testcase")
        failures = 0 if xml is None else len(xml.findall(".//failure"))
        errors = 0 if xml is None else len(xml.findall(".//error"))
        after = {n: digest(private / n) for n in HELPERS}
        row = dict(before, command=command, exit=result.returncode, tests=len(tests), failures=failures, errors=errors,
                   source_unchanged=hashes == after, actual_imports=(case / "actual-imports.json").exists(),
                   outcome="candidate-detected-review-primary" if result.returncode == 1 and failures else
                           "WEAK-SURVIVED" if result.returncode == 0 else "TOOLING-OR-SETUP-ERROR-not-a-kill")
        rows.append(row)
        (directory / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="explicit opt-in only")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if not args.run:
        raise ValueError("private mutations require explicit --run")
    print(json.dumps(run(args.output), indent=2))


if __name__ == "__main__":
    main()
