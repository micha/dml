"""Generation, imported-predicate and independent model controls for explicit contexts."""

import argparse
import os
from pathlib import Path
import runpy
import subprocess
import sys

from check_explicit_contexts import evaluate


SPIKE = Path(__file__).resolve().parent


def invoke(command, log: Path, *, expected: int = 0, env=None) -> str:
    completed = subprocess.run(command, capture_output=True, text=True, env=env, timeout=30)
    output = completed.stdout + completed.stderr
    log.write_text(output, encoding="utf-8")
    log.with_suffix(".exit").write_text(f"{completed.returncode}\n", encoding="utf-8")
    if completed.returncode != expected:
        raise AssertionError(f"Expected exit {expected}, got {completed.returncode}: {command!r}\n{output}")
    return output


def changed(source: str, old: str, new: str) -> str:
    assert old in source and old != new, old
    return source.replace(old, new)


def check(quint: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    explicit = (SPIKE / "explicit_context_rules.qnt").read_text(encoding="utf-8")
    transaction = (SPIKE / "transaction_rules.qnt").read_text(encoding="utf-8")
    generator = SPIKE / "generate_explicit_contexts.py"

    def generate(label, source=explicit, dependency=transaction, *, expected=0, hash_seed="1"):
        directory = out / label
        directory.mkdir(exist_ok=True)
        rules = directory / "explicit_context_rules.qnt"
        rules.write_text(source, encoding="utf-8")
        (directory / "transaction_rules.qnt").write_text(dependency, encoding="utf-8")
        output = directory / "generated_explicit_contexts.py"
        if output.exists():
            output.unlink()
        invoke([sys.executable, "-B", generator, "--quint", quint, "--source", rules, "--out", output],
               directory / "generate.log", expected=expected, env={**os.environ, "PYTHONHASHSEED": hash_seed})
        assert output.exists() == (expected == 0), output
        return rules, output

    _, first = generate("seed-1")
    _, second = generate("seed-2", hash_seed="2")
    reordered = changed(explicit, 'Set("a", "b")', 'Set("b", "a")')
    reordered = changed(reordered, 'Set("create_ref", "update_ref")', 'Set("update_ref", "create_ref")')
    reordered = changed(reordered, 'Set("commit_normal", "commit_exception", "abort_normal", "abort_exception")',
                        'Set("abort_exception", "abort_normal", "commit_exception", "commit_normal")')
    reordered = changed(reordered,
        'Set("stepEffects", "continuity", "freshMarker",\n'
        '    "explicitCleanCommit", "explicitPoisonedCommit", "explicitAbort", "endedHandle", "contextExit")',
        'Set("contextExit", "endedHandle", "explicitAbort", "explicitPoisonedCommit",\n'
        '    "explicitCleanCommit", "freshMarker", "continuity", "stepEffects")')
    _, third = generate("reordered", reordered)
    assert first.read_bytes() == second.read_bytes() == third.read_bytes()
    print("determinism: identical across hash seeds and reordering all four explicit-context sets", flush=True)

    altered = changed(changed(explicit, 'Set("a", "b")', 'Set("z", "x")'), "maxSteps: 3", "maxSteps: 2")
    _, scenario_output = generate("changed-scenario", altered)
    code = runpy.run_path(str(scenario_output))
    assert code["TARGETS"] == ("x", "z") and code["MAX_STEPS"] == 2
    for finish in code["FINISHES"]:
        batch = code["execute"](None, [("create_ref", "z"), ("update_ref", "x")], finish)
        code["check"](batch.initial, batch.requests, batch.finish, batch)
        assert batch.evidence["endedMarker"] == finish.startswith("commit")
    print("scenario control: changed alphabet/bound exercised all four real explicit endings", flush=True)

    # The ninth predicate is deliberately artificial: it tests backend propagation.
    extra = changed(explicit, '"explicitAbort", "endedHandle", "contextExit")',
                    '"explicitAbort", "endedHandle", "contextExit", "identityControl")')
    extra = changed(extra, '    else "unknown rule"',
                    '    else if (rule == "identityControl") '
                    'classify(isExceptional(c), c.exception == "original")\n'
                    '    else "unknown rule"')
    extra_rules, extra_output = generate("new-rule", extra)
    code = runpy.run_path(str(extra_output))
    normal = code["execute"](None, [], "commit_normal").evidence
    exceptional = code["execute"](None, [], "commit_exception").evidence
    cases = (normal, exceptional, {**exceptional, "exception": "replaced"})
    results = [result for case in cases for result in code["verdicts"](case).values()]
    assert evaluate(quint, cases, rules=extra_rules, rule_ids=code["RULE_IDS"]) == results
    assert {code["verdicts"](case)["identityControl"] for case in cases} == {"unexercised", "pass", "violation"}

    dependency = changed(transaction, 's.outcome == Failed("not_found")', 's.outcome == Failed("invalid_state")')
    inherited_rules, inherited_output = generate("changed-imported-predicate", dependency=dependency)
    code = runpy.run_path(str(inherited_output))
    cases = tuple(code["execute"](initial, requests, finish).evidence for initial, requests, finish in (
        (None, [], "commit_normal"), (None, [("update_ref", "a")], "commit_exception"),
        ("a", [("update_ref", "b")], "abort_exception"),
    ))
    results = [result for case in cases for result in code["verdicts"](case).values()]
    assert evaluate(quint, cases, rules=inherited_rules, rule_ids=code["RULE_IDS"]) == results
    assert code["verdicts"](cases[1])["stepEffects"] == "violation"
    print("spec controls: new explicit-context rule and altered imported predicate agreed with Quint", flush=True)

    controls = {
        "extra-import": (changed(explicit, "  type ExplicitContext",
            '  import transaction_rules as unused from "./transaction_rules"\n\n  type ExplicitContext'), transaction),
        "explicit-schema": (changed(explicit, "exitCalls: int,", "exitCalls: int, extra: bool,"), transaction),
        "imported-schema": (explicit, changed(transaction, "Unreadable(str)", "Unreadable(str) | Extra(str)")),
        "imported-unsupported": (explicit, changed(transaction, "a.steps.foldl(false",
                                                  "a.steps.select(step => true).foldl(false")),
    }
    for label, (source, dependency) in controls.items():
        rules, _ = generate(label, source, dependency, expected=1)
        invoke([quint, "typecheck", rules], rules.parent / "typecheck.log")
    print("fail-closed: extra import, changed explicit/imported layouts and unsupported imported IR emitted no file",
          flush=True)

    model = (SPIKE / "explicit_context_model.qnt").read_text(encoding="utf-8")
    models = {
        "abort-publication": changed(model, "val publish = commit and not(history.poisoned)",
                                     "val publish = not(history.poisoned)"),
        "poisoned-publication": changed(model, "val publish = commit and not(history.poisoned)",
                                         "val publish = commit"),
        "post-commit-rollback": changed(model, "after: published,", "after: if (exceptional) before else published,"),
        "replaced-exception": changed(model, 'if (exceptional) "original"', 'if (exceptional) "replaced"'),
        "ended-handle-readable": changed(model, 'endRead: Failed("invalid_state")', "endRead: Succeeded"),
        "repeated-abort": changed(model, "exitCalls: 0", "exitCalls: 1"),
    }
    for label, source in models.items():
        directory = out / label
        directory.mkdir(exist_ok=True)
        (directory / "transaction_rules.qnt").write_text(transaction, encoding="utf-8")
        (directory / "explicit_context_rules.qnt").write_text(explicit, encoding="utf-8")
        (directory / "transaction_model.qnt").write_bytes((SPIKE / "transaction_model.qnt").read_bytes())
        path = directory / "explicit_context_model.qnt"
        path.write_text(source, encoding="utf-8")
        invoke([quint, "typecheck", path], directory / "typecheck.log")
        output = invoke([quint, "test", path, "--backend=typescript", "--max-samples=1"],
                        directory / "model.log", expected=1)
        assert "boundedExplicitContextSafetyTest failed" in output, output
    print("negative models: abort/poisoned publication, post-commit rollback, replaced sentinel, readable ended "
          "handle and repeated abort failed bounded safety", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quint", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    check(args.quint.absolute(), args.out.absolute())


if __name__ == "__main__":
    main()
