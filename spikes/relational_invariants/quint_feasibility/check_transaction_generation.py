"""Executable determinism, fail-closed and negative-model controls for the spike."""

import argparse
import os
from pathlib import Path
import runpy
import subprocess
import sys

from check_transactions import evaluate


SPIKE = Path(__file__).resolve().parent


def invoke(command, log: Path, *, expected: int = 0, env=None) -> str:
    completed = subprocess.run(command, capture_output=True, text=True, env=env, timeout=30)
    output = completed.stdout + completed.stderr
    log.write_text(output, encoding="utf-8")
    log.with_suffix(".exit").write_text(f"{completed.returncode}\n", encoding="utf-8")
    if completed.returncode != expected:
        raise AssertionError(f"Expected exit {expected}, got {completed.returncode}: {command!r}\n{output}")
    return output


def check(quint: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    original = (SPIKE / "transaction_rules.qnt").read_text(encoding="utf-8")
    generator = SPIKE / "generate_transactions.py"

    def generate(label, source, *, expected=0, hash_seed="1"):
        directory = out / label
        directory.mkdir(exist_ok=True)
        rules = directory / "transaction_rules.qnt"
        rules.write_text(source, encoding="utf-8")
        output = directory / "generated_transactions.py"
        if output.exists():
            output.unlink()  # An old generated file cannot count as a new successful emission.
        invoke([sys.executable, "-B", generator, "--quint", quint, "--source", rules, "--out", output],
               directory / "generate.log", expected=expected, env={**os.environ, "PYTHONHASHSEED": hash_seed})
        assert output.exists() == (expected == 0), output
        return rules, output

    _, first = generate("seed-1", original)
    _, second = generate("seed-2", original, hash_seed="2")
    reordered = (original.replace('Set("a", "b")', 'Set("b", "a")')
                 .replace('Set("create_ref", "update_ref")', 'Set("update_ref", "create_ref")')
                 .replace('Set("commit", "abort")', 'Set("abort", "commit")')
                 .replace('Set("stepEffects", "continuity", "freshMarker", "commitClean", "commitPoisoned", "explicitAbort")',
                          'Set("explicitAbort", "commitPoisoned", "commitClean", "freshMarker", "continuity", "stepEffects")'))
    _, third = generate("reordered", reordered)
    assert first.read_bytes() == second.read_bytes() == third.read_bytes()
    print("determinism: identical across hash seeds and reordering all four sets", flush=True)

    changed = original.replace('Set("a", "b")', 'Set("z", "x")').replace("maxSteps: 3", "maxSteps: 2")
    _, changed_output = generate("changed-scenario", changed)
    changed_code = runpy.run_path(str(changed_output))
    assert changed_code["TARGETS"] == ("x", "z") and changed_code["MAX_STEPS"] == 2
    batch = changed_code["execute"](None, [("create_ref", "z"), ("create_ref", "x")], "commit")
    changed_code["check"](None, [("create_ref", "z"), ("create_ref", "x")], "commit", batch)
    print("scenario control: changed alphabet and history bound took effect", flush=True)

    # This artificial rule is solely a backend control: equality of every pair of
    # requested targets is deliberately not claimed to be a DML requirement.
    extra = '''
  pure def allPairsSame(a: Attempt): bool = {
    val steps = a.steps
    steps.foldl(true, (holds, step) => {
      val pair = { same: steps.foldl(true, (holds, other) => holds and step.requested == other.requested) }
      holds and pair.same
    })
  }
'''
    extra_source = original.replace('"explicitAbort")', '"explicitAbort", "pairControl")', 1)
    extra_source = extra_source.replace("  pure def verdict(", extra + "\n  pure def verdict(")
    extra_source = extra_source.replace('    else "unknown rule"',
        '    else if (rule == "pairControl") classify(whenSteps(a), allPairsSame(a))\n    else "unknown rule"')
    extra_rules, extra_output = generate("nested-fold-rule", extra_source)
    code = runpy.run_path(str(extra_output))
    cases = tuple(code["execute"](None, requests, "commit").evidence for requests in (
        [], [("create_ref", "a")], [("create_ref", "a"), ("update_ref", "a")],
        [("create_ref", "a"), ("update_ref", "b")],
    ))
    python_results = [result for case in cases for result in code["verdicts"](case).values()]
    assert evaluate(quint, cases, rules=extra_rules, rule_ids=code["RULE_IDS"]) == python_results
    assert {code["verdicts"](case)["pairControl"] for case in cases} == {"unexercised", "pass", "violation"}
    print("spec-only control: nested folds, local values and records agreed with Quint, including shadowing", flush=True)

    unsupported = original.replace("a.steps.foldl(false", "a.steps.select(step => true).foldl(false", 1)
    rules, _ = generate("unsupported-select", unsupported, expected=1)
    invoke([quint, "typecheck", rules], out / "unsupported-typecheck.log")
    schema = original.replace("markerAfter: bool", "markerAfter: str")
    # Keep the altered schema well-typed; rejection must be by the adapter boundary.
    schema = schema.replace("a.markerAfter == a.markerStaged", 'a.markerAfter == "yes"')
    schema = schema.replace("a.markerAfter == a.markerBefore", 'a.markerAfter == "no"')
    rules, _ = generate("unsupported-schema", schema, expected=1)
    invoke([quint, "typecheck", rules], out / "schema-typecheck.log")
    print("fail-closed controls: type-correct unsupported select and schema emitted no file", flush=True)

    model = (SPIKE / "transaction_model.qnt").read_text(encoding="utf-8")
    controls = {
        "poisoned-publication": model.replace('finish == "commit" and not(history.poisoned)', 'finish == "commit"'),
        "marker-leak": model.replace("markerAfter: publish", "markerAfter: true"),
        "disconnected-staged": model.replace('else history.current,\n      after:', 'else before,\n      after:')
                                   .replace('after: if (publish) history.current else before', 'after: before'),
    }
    for label, source in controls.items():
        directory = out / label
        directory.mkdir(exist_ok=True)
        (directory / "transaction_rules.qnt").write_text(original, encoding="utf-8")
        path = directory / "transaction_model.qnt"
        path.write_text(source, encoding="utf-8")
        invoke([quint, "typecheck", path], directory / "typecheck.log")
        output = invoke([quint, "test", path, "--backend=typescript", "--max-samples=1"],
                        directory / "model.log", expected=1)
        assert "boundedSafetyTest failed" in output, output
    print("negative models: poisoned publication, marker leakage and disconnected staging failed bounded safety",
          flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quint", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    check(args.quint.absolute(), args.out.absolute())


if __name__ == "__main__":
    main()
