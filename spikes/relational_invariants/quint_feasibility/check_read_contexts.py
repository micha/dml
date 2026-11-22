"""Validate the generated read-context property and capture a real binding-path failure."""

import argparse
from itertools import product
import json
from pathlib import Path
from shutil import copyfile, which
import subprocess
from tempfile import TemporaryDirectory
from unittest.mock import patch

import daggerml as dml

import generated_read_contexts as generated


RULE = "readStillUsable"
SEED = 4120
MAX_EXAMPLES = 120


def clean_cases() -> list[dict]:
    cases = []
    for size in range(1, generated.MAX_STEPS + 1):
        for requests, mode in product(product(generated.OPERATIONS, repeat=size), generated.EXIT_MODES):
            actual = generated.execute(requests, mode)
            generated.check(requests, mode, actual)
            cases.append(actual)
    assert {step["operation"] for case in cases for step in case["steps"]} == set(generated.OPERATIONS)
    assert {case["exitMode"] for case in cases} == set(generated.EXIT_MODES)
    return cases


def clean() -> dict:
    cases = clean_cases()
    histories, counts = generated.run_property(sample_seed=SEED, max_examples=MAX_EXAMPLES)
    return {"enumerated": len(cases), "sampled": histories,
            "witnesses": {rule: counts[rule, "pass"] for rule in generated.RULE_IDS}}


def capture(path: Path) -> dict:
    # Isolate the design counterexample. Other operations on the ended handle
    # could distinguish the mutant via their own outcomes instead.
    histories = generated.HISTORIES.filter(lambda trace: all(op == "commit" for op in trace[0]))
    violations: list[generated.RuleViolation] = []
    check_live = generated.check
    checks = 0

    def observe_check(requests, mode, attempt):
        nonlocal checks
        checks += 1
        assert not path.exists(), "Unexpected failure receipt during shrinking"
        try:
            return check_live(requests, mode, attempt)
        except generated.RuleViolation as error:
            assert error.attempt is attempt and error.rule == RULE, error
            violations.append(error)
            raise

    try:
        with patch.object(generated, "check", observe_check):
            generated.run_property(sample_seed=SEED, max_examples=MAX_EXAMPLES, history_strategy=histories)
    except generated.RuleViolation as error:
        assert any(error is observed for observed in violations), "Failure was not the reported live observation"
        verdicts = generated.verdicts(error.attempt)
        assert {rule for rule, verdict in verdicts.items() if verdict == "violation"} == {RULE}, verdicts
        assert error.requests == ("commit",), error.requests
        receipt = {"checks": checks, "violations": len(violations), "firstRequests": violations[0].requests,
                   "requests": error.requests, "exitMode": error.exit_mode, "observed": error.attempt,
                   "rule": error.rule, "verdicts": verdicts}
        with path.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2, sort_keys=True)
        return receipt
    raise AssertionError("Premature read-context ending did not produce a failure")


def replay(path: Path) -> tuple[dict, dict]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    requests, mode = receipt["requests"], receipt["exitMode"]
    attempt = {**receipt["observed"], "steps": tuple(receipt["observed"]["steps"])}
    with (patch.object(generated, "execute", side_effect=AssertionError("Replay executed DML")),
          patch.object(dml, "Repository", side_effect=AssertionError("Replay opened a repository"))):
        try:
            generated.check(requests, mode, attempt)
        except generated.RuleViolation as error:
            assert error.rule == receipt["rule"] == RULE, error
        else:
            raise AssertionError("Saved observations no longer report a violation")
        verdicts = generated.verdicts(attempt)
        assert verdicts == receipt["verdicts"], verdicts
    # Rerun separately, once, to distinguish the same recipe on the pristine binding.
    pristine = generated.execute(requests, mode)
    generated.check(requests, mode, pristine)
    observed_step, = attempt["steps"]
    pristine_step, = pristine["steps"]
    assert observed_step["readAfter"] == "invalid_state"
    assert {**attempt, "steps": ({**observed_step, "readAfter": pristine_step["readAfter"]},)} == pristine
    return {"rule": RULE, "verdicts": verdicts, "pristine": pristine}, attempt


def synthetic_cases() -> list[dict]:
    base = generated.execute(("commit", "missing_read"), "exception")
    first, last = base["steps"]
    before = base["before"]
    wrong_id = ("1" if before[0] == "0" else "0") + before[1:]
    controls = (
        ("readStillUsable", {"steps": ({**first, "readAfter": wrong_id}, last)}),
        ("rejectionStatus", {"steps": (first, {**last, "outcome": "invalid_state"})}),
        ("contextExit", {"exitOutcome": "ok"}),
        ("contextExit", {"endedRead": before}),
        ("noPublication", {"after": wrong_id}),
        ("noPublication", {"probeRef": "ok"}),
    )
    cases = []
    for expected, changes in controls:
        attempt = {**base, **changes}
        verdicts = generated.verdicts(attempt)
        assert {rule for rule, verdict in verdicts.items() if verdict == "violation"} == {expected}, verdicts
        cases.append(attempt)

    missing = {**base, "steps": ({key: value for key, value in first.items() if key != "readAfter"}, last)}
    try:
        generated.check(("commit", "missing_read"), "exception", missing)
    except ValueError as error:
        assert "Incomplete or mismatched" in str(error), error
    else:
        raise AssertionError("Missing read evidence was not rejected")
    empty = {**base, "steps": ()}
    assert generated.verdicts(empty)[RULE] == "unexercised"
    return [*cases, empty]


def quint_literal(value) -> str:
    if type(value) is str:
        return json.dumps(value)
    if type(value) is tuple:
        return "List(" + ", ".join(quint_literal(item) for item in value) + ")"
    if type(value) is dict and all(key.isascii() and key.isidentifier() for key in value):
        return "{ " + ", ".join(f"{key}: {quint_literal(item)}" for key, item in value.items()) + " }"
    raise ValueError(f"Cannot represent read-context evidence in Quint: {value!r}")


def compare_direct(quint: Path, rules: Path, cases: list[dict]) -> int:
    ids = tuple(generated.RULE_IDS)
    with TemporaryDirectory(prefix="quint-read-context-eval-") as tmp:
        stage = Path(tmp)
        copyfile(rules, stage / "read_context_rules.qnt")
        model = stage / "observations.qnt"
        model.write_text(
            'module observations {\n'
            '  import read_context_rules.* from "./read_context_rules"\n'
            f'  pure val cases: List[Attempt] = {quint_literal(tuple(cases))}\n'
            f'  pure val ids = {quint_literal(ids)}\n'
            '  var verdicts: List[str]\n'
            '  action init = all {\n'
            '    ruleIds == ids.foldl(Set(), (seen, rule) => seen.union(Set(rule))),\n'
            "    verdicts' = cases.foldl(List(), (out, a) =>\n"
            '      ids.foldl(out, (results, rule) => results.append(verdict(rule, a)))),\n'
            '  }\n'
            "  action step = verdicts' = verdicts\n"
            '}\n', encoding="utf-8",
        )
        report = stage / "verdicts.json"
        subprocess.run([quint, "run", model, "--backend=typescript", "--seed=1", "--max-samples=1",
                        "--max-steps=0", "--verbosity=0", f"--out-itf={report}"], check=True, timeout=30)
        trace = json.loads(report.read_text(encoding="utf-8"))
    assert trace["#meta"]["status"] == "ok" and trace["vars"] == ["verdicts"], trace["#meta"]
    observed, = trace["states"]
    expected = [value for case in cases for value in generated.verdicts(case).values()]
    assert observed["verdicts"] == expected, "Direct Quint and generated verdicts disagree"
    return len(expected)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--clean", action="store_true")
    group.add_argument("--fault", type=Path, help="New JSON path for the reported failure")
    group.add_argument("--replay", type=Path, help="Saved JSON receipt to recheck using the pristine binding")
    parser.add_argument("--quint", type=Path)
    parser.add_argument("--rules", type=Path)
    args = parser.parse_args()
    if not __debug__:
        parser.error("Run without optimizations to keep the checks enabled")
    if args.replay and args.quint and args.rules:
        rechecked, attempt = replay(args.replay)
        cases = [*clean_cases(), *synthetic_cases(), attempt]
        result = {**rechecked, "agreeingVerdicts": compare_direct(args.quint.resolve(), args.rules, cases)}
    elif args.quint or args.rules:
        parser.error("Direct comparison needs --replay, --quint and --rules together")
    elif any(which(tool) for tool in ("quint", "node", "npm")):
        parser.error("Run offline with no Quint, Node or npm on PATH")
    elif args.clean:
        result = clean()
    elif args.fault:
        if args.fault.exists() or args.fault.is_symlink() or not args.fault.parent.is_dir():
            parser.error("Expected a new receipt path with an existing parent directory")
        result = capture(args.fault)
    else:
        result, _ = replay(args.replay)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
