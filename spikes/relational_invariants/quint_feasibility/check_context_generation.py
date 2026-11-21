"""Check context generation, imported predicates and independent model controls."""

import argparse
import os
from pathlib import Path
import runpy
import subprocess
import sys

from check_contexts import evaluate


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
    context = (SPIKE / "context_rules.qnt").read_text(encoding="utf-8")
    transaction = (SPIKE / "transaction_rules.qnt").read_text(encoding="utf-8")
    generator = SPIKE / "generate_contexts.py"

    def generate(label, source=context, dependency=transaction, *, expected=0, hash_seed="1"):
        directory = out / label
        directory.mkdir(exist_ok=True)
        rules = directory / "context_rules.qnt"
        rules.write_text(source, encoding="utf-8")
        (directory / "transaction_rules.qnt").write_text(dependency, encoding="utf-8")
        output = directory / "generated_contexts.py"
        if output.exists():
            output.unlink()
        invoke([sys.executable, "-B", generator, "--quint", quint, "--source", rules, "--out", output],
               directory / "generate.log", expected=expected, env={**os.environ, "PYTHONHASHSEED": hash_seed})
        assert output.exists() == (expected == 0), output
        return rules, output

    _, first = generate("seed-1")
    _, second = generate("seed-2", hash_seed="2")
    reordered = (context.replace('Set("a", "b")', 'Set("b", "a")')
                 .replace('Set("create_ref", "update_ref")', 'Set("update_ref", "create_ref")')
                 .replace('Set("normal", "exception")', 'Set("exception", "normal")')
                 .replace('Set("stepEffects", "continuity", "freshMarker",\n'
                          '    "normalClean", "normalPoisoned", "exceptionalExit")',
                          'Set("exceptionalExit", "normalPoisoned", "normalClean",\n'
                          '    "freshMarker", "continuity", "stepEffects")'))
    _, third = generate("reordered", reordered)
    assert first.read_bytes() == second.read_bytes() == third.read_bytes()
    print("determinism: identical across hash seeds and reordering all four context sets", flush=True)

    _, changed = generate("changed-scenario", context.replace('Set("a", "b")', 'Set("z", "x")')
                          .replace("maxSteps: 3", "maxSteps: 2"))
    code = runpy.run_path(str(changed))
    assert code["TARGETS"] == ("x", "z") and code["MAX_STEPS"] == 2
    batch = code["execute"](None, [("create_ref", "z"), ("update_ref", "x")], "exception")
    code["check"](batch.initial, batch.requests, batch.finish, batch)
    print("scenario control: changed alphabet/bound exercised real exceptional rollback", flush=True)

    # Deliberately artificial rule: prove new context predicates flow to the backend.
    extra = context.replace('"normalClean", "normalPoisoned", "exceptionalExit")',
                            '"normalClean", "normalPoisoned", "exceptionalExit", "identityControl")', 1)
    extra = extra.replace('    else "unknown rule"',
                          '    else if (rule == "identityControl") '
                          'classify(whenExceptional(c), c.exception == "original")\n'
                          '    else "unknown rule"')
    extra_rules, extra_output = generate("extra-rule", extra)
    code = runpy.run_path(str(extra_output))
    normal = code["execute"](None, [], "normal").evidence
    exceptional = code["execute"](None, [], "exception").evidence
    cases = (normal, exceptional, {**exceptional, "exception": "replaced"})
    results = [result for case in cases for result in code["verdicts"](case).values()]
    assert evaluate(quint, cases, rules=extra_rules, rule_ids=code["RULE_IDS"]) == results
    assert {code["verdicts"](case)["identityControl"] for case in cases} == {"unexercised", "pass", "violation"}

    # A type-correct change to the *imported* expected status must not be ignored.
    dependency = transaction.replace('s.outcome == Failed("not_found")', 's.outcome == Failed("invalid_state")')
    assert dependency != transaction
    inherited_rules, inherited_output = generate("changed-imported-predicate", dependency=dependency)
    code = runpy.run_path(str(inherited_output))
    cases = tuple(code["execute"](initial, requests, finish).evidence for initial, requests, finish in (
        (None, [], "normal"), (None, [("update_ref", "a")], "normal"),
        ("a", [("update_ref", "b")], "exception"),
    ))
    results = [result for case in cases for result in code["verdicts"](case).values()]
    assert evaluate(quint, cases, rules=inherited_rules, rule_ids=code["RULE_IDS"]) == results
    assert code["verdicts"](cases[1])["stepEffects"] == "violation"
    print("spec controls: added context rule and changed imported predicate agreed with Quint", flush=True)

    controls = {
        "extra-import": (context.replace('  type Context',
            '  import transaction_rules as unused from "./transaction_rules"\n\n  type Context'), transaction),
        "context-schema": (context.replace("batch: Attempt, exception: str",
                                           "batch: Attempt, exception: str, extra: bool"), transaction),
        "imported-schema": (context, transaction.replace("Unreadable(str)", "Unreadable(str) | Extra(str)", 1)),
        "imported-unsupported": (context, transaction.replace("a.steps.foldl(false",
                                                            "a.steps.select(step => true).foldl(false", 1)),
    }
    for label, (source, dependency) in controls.items():
        rules, _ = generate(label, source, dependency, expected=1)
        invoke([quint, "typecheck", rules], rules.parent / "typecheck.log")
    print("fail-closed: extra import, changed context/imported layouts and unsupported imported IR emitted no file",
          flush=True)

    model = (SPIKE / "context_model.qnt").read_text(encoding="utf-8")
    models = {
        "exceptional-publication": model.replace('finish == "normal" and not(history.poisoned)',
                                                 'not(history.poisoned)'),
        "marker-leak": model.replace("markerAfter: publish", "markerAfter: true"),
        "replaced-exception": model.replace('if (finish == "exception") "original"',
                                             'if (finish == "exception") "replaced"'),
        "poison-masks-exception": model.replace('if (finish == "exception") Failed("body_exception")',
            'if (finish == "exception" and history.poisoned) Failed("invalid_state")\n'
            '          else if (finish == "exception") Failed("body_exception")'),
    }
    for label, source in models.items():
        assert source != model, label
        directory = out / label
        directory.mkdir(exist_ok=True)
        (directory / "transaction_rules.qnt").write_text(transaction, encoding="utf-8")
        (directory / "context_rules.qnt").write_text(context, encoding="utf-8")
        (directory / "transaction_model.qnt").write_bytes((SPIKE / "transaction_model.qnt").read_bytes())
        path = directory / "context_model.qnt"
        path.write_text(source, encoding="utf-8")
        invoke([quint, "typecheck", path], directory / "typecheck.log")
        output = invoke([quint, "test", path, "--backend=typescript", "--max-samples=1"],
                        directory / "model.log", expected=1)
        assert "boundedContextSafetyTest failed" in output, output
    print("negative models: exceptional publication, marker leak, replaced/masked exception failed bounded safety",
          flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quint", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    check(args.quint.absolute(), args.out.absolute())


if __name__ == "__main__":
    main()
