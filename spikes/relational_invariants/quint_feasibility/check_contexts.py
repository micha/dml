"""Differential, boundary and shrinking controls for context-manager completion."""

import argparse
from collections import Counter
from dataclasses import replace
from itertools import batched, product
import json
from pathlib import Path
import re
from shutil import copyfile, which
import subprocess
from tempfile import TemporaryDirectory
from unittest.mock import patch

import context_binding as binding
import daggerml as dml
import generated_contexts as generated
from hypothesis import strategies as st

from context_binding import validate_observation


SPIKE = Path(__file__).resolve().parent


def quint_literal(value) -> str:
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is str:
        return json.dumps(value)
    if type(value) is dict:
        if any(re.fullmatch(r"[a-zA-Z_][a-zA-Z_0-9]*", key) is None for key in value):
            raise ValueError("Invalid Quint record field")
        return "{ " + ", ".join(f"{key}: {quint_literal(item)}" for key, item in value.items()) + " }"
    if type(value) is tuple:
        if len(value) == 2 and type(value[0]) is str:
            tag, payload = value
            if tag in ("Absent", "Succeeded") and payload == ():
                return tag
            if tag in ("Target", "Unreadable", "Failed") and type(payload) is str:
                return f"{tag}({json.dumps(payload)})"
            raise ValueError(f"Invalid sum value: {value!r}")
        return "List(" + ", ".join(quint_literal(item) for item in value) + ")"
    raise ValueError(f"Unsupported evidence value: {value!r}")


def evaluate(
    quint: Path, attempts: tuple[dict, ...], *, rules: Path = SPIKE / "context_rules.qnt",
    rule_ids: tuple[str, ...] = generated.RULE_IDS,
) -> list[str]:
    literals = ",\n".join(quint_literal(attempt) for attempt in attempts)
    rule_list = ", ".join(json.dumps(rule) for rule in rule_ids)
    with TemporaryDirectory(prefix="quint-context-eval-") as tmp:
        directory = Path(tmp)
        copyfile(rules.with_name("transaction_rules.qnt"), directory / "transaction_rules.qnt")
        copyfile(rules, directory / "context_rules.qnt")
        module = directory / "observations.qnt"
        report = directory / "verdicts.json"
        module.write_text(
            'module observations {\n'
            '  import transaction_rules.* from "./transaction_rules"\n'
            '  import context_rules.* from "./context_rules"\n'
            f'  pure val attempts: List[Context] = List({literals})\n'
            f'  pure val orderedRules = List({rule_list})\n'
            '  var verdicts: List[str]\n'
            '  action init = all {\n'
            f'    contextRuleIds == Set({rule_list}),\n'
            "    verdicts' = attempts.foldl(List(), (items, a) =>\n"
            '      orderedRules.foldl(items, (results, rule) => results.append(contextVerdict(rule, a)))),\n'
            '  }\n'
            "  action step = verdicts' = verdicts\n"
            '}\n', encoding="utf-8",
        )
        completed = subprocess.run(
            [quint, "run", module, "--backend=typescript", "--max-samples=1", "--max-steps=0",
             "--seed=1", "--verbosity=0", f"--out-itf={report}"],
            capture_output=True, text=True, timeout=10,
        )
        if completed.returncode != 0 or not report.is_file():
            raise RuntimeError(f"Quint evaluation failed ({completed.returncode}):\n"
                               f"{completed.stdout}{completed.stderr}")
        trace = json.loads(report.read_text(encoding="utf-8"))
    if trace["#meta"]["status"] != "ok" or trace["vars"] != ["verdicts"] or len(trace["states"]) != 1:
        raise ValueError("Expected one successful Quint ITF state")
    results = trace["states"][0]["verdicts"]
    if (type(results) is not list or len(results) != len(attempts) * len(rule_ids)
            or any(item not in ("pass", "unexercised", "violation") for item in results)):
        raise ValueError(f"Invalid Quint verdicts: {results!r}")
    return results


def changed(batch, **fields):
    return replace(batch, evidence={**batch.evidence, "batch": {**batch.evidence["batch"], **fields}})


def expect_invalid(call, message: str) -> None:
    try:
        call()
    except ValueError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"Invalid evidence accepted: {message}")


def expect_violation(batch, rule: str) -> None:
    try:
        generated.check(batch.initial, batch.requests, batch.finish, batch)
    except generated.RuleViolation as error:
        assert error.rule == rule, error
    else:
        raise AssertionError(f"Fabricated evidence escaped {rule}")


def continuity_controls() -> tuple:
    updated = generated.execute("a", [("update_ref", "b")], "normal")
    generated.check(updated.initial, updated.requests, updated.finish, updated)
    evidence = updated.evidence["batch"]
    assert evidence["before"] != evidence["staged"]
    lost_update = changed(updated, staged=evidence["before"], after=evidence["before"])
    start = {**evidence["steps"][0], "before": evidence["staged"]}
    disconnected_start = changed(updated, steps=(start,))
    two = generated.execute("a", [("update_ref", "b"), ("update_ref", "a")], "normal")
    second = {**two.evidence["batch"]["steps"][1], "before": two.evidence["batch"]["before"]}
    disconnected_middle = changed(two, steps=(two.evidence["batch"]["steps"][0], second))
    empty = generated.execute("a", [], "normal")
    disconnected_empty = changed(empty, staged=evidence["staged"], after=evidence["staged"])
    poisoned = generated.execute("a", [("update_ref", "b"), ("create_ref", "a"),
                                       ("create_ref", "b")], "normal")
    steps = poisoned.evidence["batch"]["steps"]
    wrong_poison = changed(poisoned, steps=(*steps[:2], {**steps[2], "poisoned": False}))
    cases = (lost_update, disconnected_start, disconnected_middle, disconnected_empty, wrong_poison)
    for batch in cases:
        validate_observation(batch.initial, batch.requests, batch.finish, batch)
        results = generated.verdicts(batch.evidence)
        assert all(result != "violation" for rule, result in results.items() if rule != "continuity"), results
        expect_violation(batch, "continuity")
    return cases


def compare_with_quint(quint: Path) -> None:
    alphabet = tuple(product(generated.OPERATIONS, generated.TARGETS))
    histories = [trace for size in range(generated.MAX_STEPS + 1) for trace in product(alphabet, repeat=size)]
    batches = tuple(generated.execute(initial, requests, finish)
                    for initial, requests, finish in product((None, *generated.TARGETS), histories,
                                                             generated.FINISHES))
    actual = tuple(batch.evidence for batch in batches)
    commits = tuple(generated.execute(None, [("create_ref", target)], "normal").evidence["batch"]["staged"]
                    for target in generated.TARGETS)
    assert len(set(commits)) == len(commits), "abstract targets did not map to distinct commits"
    absent, unreadable = ("Absent", ()), ("Unreadable", "invalid_state")
    refs = (absent, *commits)
    outcomes = (("Succeeded", ()), ("Failed", "invalid_state"), ("Failed", "not_found"),
                ("Failed", "body_exception"), ("Failed", "replaced_exception"))
    empty = generated.execute(None, [], "normal").evidence
    # These are type-correct observations, not claims that native DML produced them.
    step_matrix = tuple(
        {**empty, "batch": {**empty["batch"], "steps": ({
            "operation": operation, "before": before, "after": after,
            "requested": requested[1], "outcome": outcome, "poisoned": poisoned,
        },)}}
        for operation, before, after, requested, outcome, poisoned in
        product(generated.OPERATIONS, (*refs, unreadable), (*refs, unreadable), commits,
                outcomes, (False, True))
    )
    representatives = tuple(generated.execute("a", requests, finish)
                            for requests, finish in product(([], [("create_ref", "b")]), generated.FINISHES))
    ending_matrix = tuple(
        {**batch.evidence, "exception": exception,
         "batch": {**batch.evidence["batch"], "finish": finish, "outcome": outcome,
                   "after": after, "markerAfter": marker_after}}
        for batch, finish, outcome, exception, after, marker_after in
        product(representatives, generated.FINISHES, outcomes,
                ("none", "original", "replaced", "suppressed"), refs, (False, True))
    )
    marker_matrix = tuple(
        {**empty, "batch": {**empty["batch"], "markerBefore": before,
                            "markerStaged": staged, "markerAfter": after}}
        for before, staged, after in product((False, True), repeat=3)
    )
    disconnected = tuple(batch.evidence for batch in continuity_controls())
    synthetic = step_matrix + ending_matrix + marker_matrix + disconnected

    def compare(cases):
        counts = {rule: Counter() for rule in generated.RULE_IDS}
        for batch in batched(cases, 32):
            direct = evaluate(quint, batch)
            translated = ((attempt, rule, result) for attempt in batch
                          for rule, result in generated.verdicts(attempt).items())
            for expected, (attempt, rule, result) in zip(direct, translated, strict=True):
                if expected != result:
                    raise AssertionError(f"{rule}: Quint={expected}, Python={result}, evidence={attempt!r}")
                counts[rule][result] += 1
        return counts

    actual_counts = compare(actual)
    synthetic_counts = compare(synthetic)
    assert len(histories) == 85 and len(actual) == 510
    assert all(counts["pass"] > 0 and counts["violation"] == 0 for counts in actual_counts.values())
    assert all(counts["violation"] > 0 for counts in synthetic_counts.values())
    print(f"agreement: {len(actual)} real contexts, {len(synthetic)} synthetic contexts, "
          f"{(len(actual) + len(synthetic)) * len(generated.RULE_IDS)} identical verdicts")
    for rule in generated.RULE_IDS:
        print(f"  {rule}: actual={dict(actual_counts[rule])}, synthetic={dict(synthetic_counts[rule])}")


def check_context_adapter_controls() -> None:
    exit_context, abort, read = dml.Transaction.__exit__, dml.Transaction.abort, dml.Repository.read

    for replacement in (False, True):
        def faulty_exit(tx, exc_type, exc, traceback):
            if exc_type is None:
                return exit_context(tx, exc_type, exc, traceback)
            abort(tx)
            if replacement:
                raise type(exc)(*exc.args)
            return True

        with patch.object(dml.Transaction, "__exit__", faulty_exit):
            batch = generated.execute("a", [("update_ref", "b")], "exception")
        assert batch.evidence["exception"] == ("replaced" if replacement else "suppressed"), batch.evidence
        expect_violation(batch, "exceptionalExit")

    def publish_on_exception(tx, exc_type, exc, traceback):
        if exc_type is None:
            return exit_context(tx, exc_type, exc, traceback)
        tx.commit()
        return None

    with patch.object(dml.Transaction, "__exit__", publish_on_exception):
        published = generated.execute("a", [("update_ref", "b")], "exception")
    assert published.evidence["exception"] == "original", published.evidence
    assert published.evidence["batch"]["markerAfter"], published.evidence
    expect_violation(published, "exceptionalExit")

    def swallow_poisoned_exit(tx, exc_type, exc, traceback):
        if exc_type is None and tx._failed:
            abort(tx)
            return None
        return exit_context(tx, exc_type, exc, traceback)

    with patch.object(dml.Transaction, "__exit__", swallow_poisoned_exit):
        swallowed = generated.execute("a", [("update_ref", "b"), ("create_ref", "a")], "normal")
    assert swallowed.evidence["batch"]["outcome"] == ("Succeeded", ()), swallowed.evidence
    expect_violation(swallowed, "normalPoisoned")

    # If exceptional exit does not consume the writer, publication must be observed
    # before fallback abort can make the transaction look correctly rolled back.
    target = None
    events = []

    def leave_active(tx, exc_type, exc, traceback):
        nonlocal target
        if exc_type is None:
            return exit_context(tx, exc_type, exc, traceback)
        target = tx
        events.append("exceptional exit left writer active")
        return None

    def observe(repo):
        if target is not None:
            events.append("fresh read attempted")
        return read(repo)

    def cleanup(tx):
        if tx is target:
            events.append("fallback cleanup")
        return abort(tx)

    with patch.object(dml.Transaction, "__exit__", leave_active), patch.object(
        dml.Transaction, "abort", cleanup
    ), patch.object(dml.Repository, "read", observe):
        try:
            generated.execute("a", [("update_ref", "b")], "exception")
        except dml.InvalidStateError as error:
            assert error.detail == "repository already has an active transaction", error
        else:
            raise AssertionError("A non-consuming exceptional exit borrowed rollback from fallback cleanup")
    assert events[:3] == ["exceptional exit left writer active", "fresh read attempted", "fallback cleanup"], events
    assert target is not None and target._ended, "The deliberately leaked transaction was not cleaned up"
    print("offline adapter controls: swallowed/replaced sentinel, exceptional publication and silent poisoned exit "
          "rejected; non-consuming exit rejected before cleanup")


def check_unexpected_errors() -> None:
    marker_present, exit_context = binding.marker_present, dml.Transaction.__exit__
    body_errors = (RuntimeError("unexpected body failure"),
                   binding.ContextBodyError("unrelated body sentinel"),
                   dml.InvalidStateError("invalid_state", detail="body failure before completion"))
    for error in body_errors:
        def fail_in_body(tx, marker):
            if tx._write:
                raise error
            return marker_present(tx, marker)

        with patch.object(binding, "marker_present", fail_in_body):
            try:
                generated.execute("a", [("update_ref", "b")], "normal")
            except type(error) as caught:
                assert caught is error, caught
            else:
                raise AssertionError("An unrelated body error was converted into completion evidence")

    error = RuntimeError("unexpected exit failure")

    def fail_at_exit(tx, exc_type, exc, traceback):
        if exc_type is not None:
            raise error
        return exit_context(tx, exc_type, exc, traceback)

    with patch.object(dml.Transaction, "__exit__", fail_at_exit):
        try:
            generated.execute("a", [("update_ref", "b")], "exception")
        except RuntimeError as caught:
            assert caught is error, caught
        else:
            raise AssertionError("An unrelated exit error was converted into completion evidence")
    print("offline propagation: unrelated body/sentinel/InvalidStateError and exit errors propagated unchanged")


def check_shrinking() -> None:
    first_failure = None
    strategy = st.tuples(st.sampled_from(generated.TARGETS),
                         st.lists(generated.REQUESTS, max_size=generated.MAX_STEPS), st.just("exception"))

    def corrupt(trace, actual):
        nonlocal first_failure
        evidence = actual.evidence["batch"]
        moved = [step for step in evidence["steps"]
                 if step["outcome"] == ("Succeeded", ()) and step["after"] != evidence["before"]]
        if not moved:
            return actual
        assert actual.evidence["exception"] == "original"
        if first_failure is None:
            first_failure = (trace[0], tuple(trace[1]), trace[2])
        return changed(actual, after=moved[-1]["after"])

    try:
        generated.run_property(sample_seed=4120, max_examples=100, corrupt=corrupt, history_strategy=strategy)
    except generated.RuleViolation as error:
        assert error.rule == "exceptionalExit" and error.finish == "exception" and error.initial is not None, error
        assert len(error.requests) == 1 and error.requests[0][0] == "update_ref", error
        assert error.requests[0][1] != error.initial, error
        final = (error.initial, error.requests, error.finish)
        assert first_failure is not None and first_failure != final, (first_failure, final)
        print(f"offline context shrink: {first_failure} -> {final}\n  {error}", flush=True)
    else:
        raise AssertionError("Hypothesis did not detect exceptional-exit partial publication")


def check_without_quint() -> None:
    if any(which(tool) is not None for tool in ("quint", "node", "npm")):
        raise RuntimeError("Use the offline staging directory with an empty tool PATH")
    clean = generated.execute("a", [("update_ref", "b")], "normal")
    poisoned = generated.execute("a", [("update_ref", "b"), ("create_ref", "a")], "normal")
    exceptional = generated.execute("a", [("update_ref", "b")], "exception")
    exceptional_poisoned = generated.execute("a", [("update_ref", "b"), ("create_ref", "a")], "exception")
    for batch in (clean, poisoned, exceptional, exceptional_poisoned):
        generated.check(batch.initial, batch.requests, batch.finish, batch)
    assert clean.evidence["batch"]["outcome"] == ("Succeeded", ())
    assert poisoned.evidence["batch"]["outcome"] == ("Failed", "invalid_state")
    for batch in (exceptional, exceptional_poisoned):
        assert batch.evidence["exception"] == "original"
        assert batch.evidence["batch"]["outcome"] == ("Failed", "body_exception")
        assert batch.evidence["batch"]["before"] == batch.evidence["batch"]["after"]
        assert not batch.evidence["batch"]["markerAfter"]

    for key in clean.evidence:
        expect_invalid(lambda key=key: generated.check(clean.initial, clean.requests, clean.finish, replace(
            clean, evidence={field: value for field, value in clean.evidence.items() if field != key})),
            "context evidence")
    for key in clean.evidence["batch"]:
        missing = {field: value for field, value in clean.evidence["batch"].items() if field != key}
        expect_invalid(lambda missing=missing: generated.check(clean.initial, clean.requests, clean.finish,
            replace(clean, evidence={**clean.evidence, "batch": missing})), "transaction evidence")
    for initial, requests, finish in ((None, clean.requests, clean.finish),
                                      (clean.initial, [], clean.finish),
                                      (clean.initial, clean.requests, "exception")):
        expect_invalid(lambda initial=initial, requests=requests, finish=finish:
            generated.check(initial, requests, finish, clean), "another exercise")
    expect_invalid(lambda: generated.check(clean.initial, clean.requests, clean.finish,
        changed(clean, steps=())), "action count")
    for field in clean.evidence["batch"]["steps"][0]:
        step = {key: value for key, value in clean.evidence["batch"]["steps"][0].items() if key != field}
        expect_invalid(lambda step=step: generated.check(clean.initial, clean.requests, clean.finish,
            changed(clean, steps=(step,))), "step evidence")
    for field, value in (("operation", "create_ref"), ("requested", "wrong-target")):
        step = {**clean.evidence["batch"]["steps"][0], field: value}
        expect_invalid(lambda step=step: generated.check(clean.initial, clean.requests, clean.finish,
            changed(clean, steps=(step,))), "step evidence")
    for field, value, message in (("markerAfter", None, "boolean"),
                                  ("outcome", ("Failed", None), "tagged-sum"),
                                  ("before", ("Absent", ("extra",)), "tagged-sum")):
        expect_invalid(lambda field=field, value=value: generated.check(clean.initial, clean.requests, clean.finish,
            changed(clean, **{field: value})), message)
    expect_invalid(lambda: generated.check(clean.initial, clean.requests, clean.finish,
        replace(clean, evidence={**clean.evidence, "exception": None})), "exception")

    controls = 0
    for batch, rule, changes in (
        (clean, "normalClean", ({"markerAfter": False}, {"after": clean.evidence["batch"]["before"]},
                                 {"outcome": ("Failed", "invalid_state")})),
        (poisoned, "normalPoisoned", ({"markerAfter": True}, {"after": clean.evidence["batch"]["staged"]},
                                       {"outcome": ("Succeeded", ())})),
        (exceptional, "exceptionalExit", ({"markerAfter": True}, {"after": clean.evidence["batch"]["staged"]},
                                          {"outcome": ("Succeeded", ())})),
        (exceptional_poisoned, "exceptionalExit", ({"markerAfter": True},
                                                   {"outcome": ("Failed", "invalid_state")})),
    ):
        for fields in changes:
            expect_violation(changed(batch, **fields), rule)
            controls += 1
    for exception in ("none", "replaced", "suppressed"):
        expect_violation(replace(exceptional, evidence={**exceptional.evidence, "exception": exception}),
                         "exceptionalExit")
        controls += 1
    expect_violation(replace(clean, evidence={**clean.evidence, "exception": "original"}), "normalClean")
    controls += 1
    try:
        empty = generated.execute(None, [], "normal")
        generated.require_witnesses(generated.check(None, [], "normal", empty))
    except AssertionError as error:
        assert all(rule in str(error) for rule in ("normalPoisoned", "exceptionalExit", "stepEffects")), error
        print(f"offline non-vacuity control: {error}")
    else:
        raise AssertionError("A clean empty normal exit concealed unexercised rules")
    print(f"offline boundaries: incomplete/mismatched/malformed evidence and {controls} completion failures rejected")
    print(f"offline continuity: {len(continuity_controls())} disconnected histories rejected")
    check_context_adapter_controls()
    check_unexpected_errors()
    histories, counts = generated.run_property(sample_seed=4120, max_examples=100)
    print(f"offline: {histories} generated contexts; matches="
          f"{ {rule: counts[rule, 'pass'] for rule in generated.RULE_IDS} }", flush=True)
    check_shrinking()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_subparsers(dest="mode", required=True)
    mode.add_parser("offline")
    differential = mode.add_parser("differential")
    differential.add_argument("--quint", required=True, type=Path)
    args = parser.parse_args()
    if args.mode == "offline":
        check_without_quint()
    else:
        compare_with_quint(args.quint.absolute())


if __name__ == "__main__":
    main()
