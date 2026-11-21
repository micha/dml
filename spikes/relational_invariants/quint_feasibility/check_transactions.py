"""Differential, offline, boundary and shrink checks for transaction rules."""

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

import daggerml as dml
import generated_transactions as generated
from hypothesis import strategies as st

from transaction_binding import validate_observation


RULES = Path(__file__).with_name("transaction_rules.qnt")


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
    quint: Path, attempts: tuple[dict, ...], *, rules: Path = RULES,
    rule_ids: tuple[str, ...] = generated.RULE_IDS,
) -> list[str]:
    literals = ",\n".join(quint_literal(attempt) for attempt in attempts)
    rule_list = ", ".join(json.dumps(rule) for rule in rule_ids)
    with TemporaryDirectory(prefix="quint-txn-eval-") as tmp:
        directory = Path(tmp)
        copyfile(rules, directory / "transaction_rules.qnt")
        module = directory / "observations.qnt"
        report = directory / "verdicts.json"
        module.write_text(
            'module observations {\n'
            '  import transaction_rules.* from "./transaction_rules"\n'
            f'  pure val attempts: List[Attempt] = List({literals})\n'
            f'  pure val orderedRules = List({rule_list})\n'
            '  var verdicts: List[str]\n'
            '  action init = all {\n'
            f'    ruleIds == Set({rule_list}),\n'
            '    verdicts\' = attempts.foldl(List(), (items, a) =>\n'
            '      orderedRules.foldl(items, (results, rule) => results.append(verdict(rule, a)))),\n'
            '  }\n'
            '  action step = verdicts\' = verdicts\n'
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


def compare_with_quint(quint: Path) -> None:
    alphabet = tuple(product(generated.OPERATIONS, generated.TARGETS))
    histories = [trace for size in range(generated.MAX_STEPS + 1) for trace in product(alphabet, repeat=size)]
    actual = tuple(generated.execute(initial, requests, finish).evidence
                   for initial, requests, finish in product((None, *generated.TARGETS), histories,
                                                            generated.FINISHES))
    commits = tuple(generated.execute(None, [("create_ref", target)], "commit").evidence["staged"]
                    for target in generated.TARGETS)
    assert len(set(commits)) == len(commits), "abstract targets did not map to distinct commits"
    absent, unreadable = ("Absent", ()), ("Unreadable", "invalid_state")
    refs = (absent, *commits)
    outcomes = (("Succeeded", ()), ("Failed", "invalid_state"), ("Failed", "not_found"))
    empty = generated.execute(None, [], "commit").evidence
    outer_matrix = tuple(
        {**empty, "before": before, "staged": staged, "after": after, "finish": finish,
         "outcome": outcome, "markerAfter": marker_after}
        for before, staged, after, finish, outcome, marker_after in
        product(refs, (*refs, unreadable), refs, generated.FINISHES, outcomes, (False, True))
    )
    step_matrix = tuple(
        {**empty, "steps": ({"operation": operation, "before": before, "after": after,
                             "requested": requested[1], "outcome": outcome, "poisoned": poisoned},)}
        for operation, before, after, requested, outcome, poisoned in
        product(generated.OPERATIONS, (*refs, unreadable), (*refs, unreadable), commits,
                outcomes, (False, True))
    )
    marker_matrix = tuple({**empty, "markerBefore": before, "markerStaged": staged, "markerAfter": after}
                          for before, staged, after in product((False, True), repeat=3))
    # Explicit poisoned envelopes cross completion outcomes, published refs and markers.
    poisoned = generated.execute(None, [("create_ref", "a"), ("create_ref", "b")], "commit").evidence
    poisoned_matrix = tuple({**poisoned, "finish": finish, "outcome": outcome,
                             "after": after, "markerAfter": marker_after}
                            for finish, outcome, after, marker_after in
                            product(generated.FINISHES, outcomes, refs, (False, True)))
    discontinuous = tuple(batch.evidence for _, batch in continuity_controls())
    synthetic = outer_matrix + step_matrix + marker_matrix + poisoned_matrix + discontinuous

    def compare(cases: tuple[dict, ...]) -> dict[str, Counter[str]]:
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
    print(f"agreement: {len(actual)} real batches, {len(synthetic)} synthetic batches, "
          f"{(len(actual) + len(synthetic)) * len(generated.RULE_IDS)} identical verdicts")
    for rule in generated.RULE_IDS:
        print(f"  {rule}: actual={dict(actual_counts[rule])}, synthetic={dict(synthetic_counts[rule])}")


def expect_invalid(call, message: str) -> None:
    try:
        call()
    except ValueError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"Invalid evidence accepted: {message}")


def expect_violation(initial, requests, finish, batch, rule) -> None:
    try:
        generated.check(initial, requests, finish, batch)
    except generated.RuleViolation as error:
        assert error.rule == rule, error
    else:
        raise AssertionError(f"Fabricated evidence escaped {rule}")


def continuity_controls() -> tuple:
    """Locally plausible but disconnected evidence, with unchanged input receipts."""
    updated = generated.execute("a", [("update_ref", "b")], "commit")
    generated.check(updated.initial, updated.requests, updated.finish, updated)
    assert updated.evidence["before"] != updated.evidence["staged"]
    lost_update = replace(updated, evidence={**updated.evidence, "staged": updated.evidence["before"],
                                             "after": updated.evidence["before"]})
    first_step = {**updated.evidence["steps"][0], "before": updated.evidence["staged"]}
    disconnected_start = replace(updated, evidence={**updated.evidence, "steps": (first_step,)})

    two = generated.execute("a", [("update_ref", "b"), ("update_ref", "a")], "commit")
    second_step = {**two.evidence["steps"][1], "before": two.evidence["before"]}
    disconnected_middle = replace(two, evidence={**two.evidence,
                                                 "steps": (two.evidence["steps"][0], second_step)})
    empty = generated.execute("a", [], "commit")
    disconnected_empty = replace(empty, evidence={**empty.evidence, "staged": updated.evidence["staged"],
                                                 "after": updated.evidence["staged"]})
    poisoned = generated.execute("a", [("update_ref", "b"), ("create_ref", "a"),
                                        ("create_ref", "b")], "commit")
    third_step = {**poisoned.evidence["steps"][2], "poisoned": False}
    wrong_poison = replace(poisoned, evidence={**poisoned.evidence,
                                             "steps": (*poisoned.evidence["steps"][:2], third_step)})
    cases = (("lost-update endpoint", lost_update), ("disconnected first read", disconnected_start),
             ("disconnected interior read", disconnected_middle), ("empty staged drift", disconnected_empty),
             ("incorrect prior-poison flag", wrong_poison))
    for label, batch in cases:
        validate_observation(batch.initial, batch.requests, batch.finish, batch)
        results = generated.verdicts(batch.evidence)
        assert all(result != "violation" for rule, result in results.items() if rule != "continuity"), label
        expect_violation(batch.initial, batch.requests, batch.finish, batch, "continuity")
    return cases


def check_nonconsuming_commit() -> None:
    """A fake failed commit cannot borrow rollback from the adapter's cleanup."""
    commit, abort, read = dml.Transaction.commit, dml.Transaction.abort, dml.Repository.read
    target = None
    events = []

    def leave_active(tx):
        nonlocal target
        if not tx._failed:  # Only the tested poisoned batch; setup commits stay real.
            return commit(tx)
        target = tx
        events.append("commit rejected without consuming")
        raise dml.InvalidStateError("invalid_state", detail="non-consuming ending control")

    def observe(repo):
        if target is not None:
            events.append("fresh read attempted")
        return read(repo)

    def cleanup(tx):
        if tx is target:
            events.append("fallback cleanup")
        return abort(tx)

    with patch.object(dml.Transaction, "commit", leave_active), patch.object(
        dml.Transaction, "abort", cleanup
    ), patch.object(dml.Repository, "read", observe):
        try:
            generated.execute("a", [("update_ref", "b"), ("create_ref", "a")], "commit")
        except dml.InvalidStateError as error:
            assert error.detail == "repository already has an active transaction", error
        else:
            raise AssertionError("Non-consuming rejected commit was accepted after fallback cleanup")
    assert events[:3] == ["commit rejected without consuming", "fresh read attempted", "fallback cleanup"], events
    assert target is not None and target._ended, "The deliberately leaked transaction was not cleaned up"
    print("offline ending control: non-consuming rejected commit failed before fallback cleanup")


def check_existing_ref_shrink() -> None:
    first_failure = None
    strategy = st.tuples(st.sampled_from(generated.TARGETS),
                         st.lists(generated.REQUESTS, max_size=generated.MAX_STEPS), st.just("commit"))

    def corrupt(trace, actual):
        nonlocal first_failure
        evidence = actual.evidence
        # The control keeps an existing initial ref, a real successful update to a
        # different commit, and a later actual duplicate-create rejection. It does
        # not pre-filter DML validity or manufacture a failed operation outcome.
        for index, step in enumerate(evidence["steps"]):
            if (step["operation"] != "update_ref" or step["outcome"] != ("Succeeded", ())
                    or step["after"] == evidence["before"]):
                continue
            if not any(later["operation"] == "create_ref" and not later["poisoned"]
                       and later["outcome"] == ("Failed", "invalid_state")
                       for later in evidence["steps"][index + 1:]):
                continue
            assert actual.initial is not None and evidence["before"][0] == "Target"
            assert actual.finish == "commit" and evidence["outcome"] == ("Failed", "invalid_state")
            if first_failure is None:
                first_failure = (trace[0], tuple(trace[1]), trace[2])
            return replace(actual, evidence={**evidence, "after": step["after"]})
        return actual

    try:
        generated.run_property(sample_seed=4120, max_examples=80, corrupt=corrupt, history_strategy=strategy)
    except generated.RuleViolation as error:
        assert error.rule == "commitPoisoned" and error.initial is not None and error.finish == "commit", error
        assert len(error.requests) == 2, error
        assert tuple(operation for operation, _ in error.requests) == ("update_ref", "create_ref"), error
        assert error.requests[0][1] != error.initial, error
        final = (error.initial, error.requests, error.finish)
        assert first_failure is not None and first_failure != final, (first_failure, final)
        print(f"offline existing-ref shrink: {first_failure} -> {final}\n  {error}", flush=True)
    else:
        raise AssertionError("Hypothesis did not detect partial publication for the existing-ref update story")


def check_without_quint() -> None:
    if any(which(tool) is not None for tool in ("quint", "node", "npm")):
        raise RuntimeError("Use the offline staging directory with an empty tool PATH")
    requests = [("create_ref", "a"), ("create_ref", "b"), ("update_ref", "b")]
    batch = generated.execute(None, requests, "commit")
    generated.check(None, requests, "commit", batch)
    assert batch.evidence["steps"][0]["outcome"] == ("Succeeded", ())
    assert batch.evidence["steps"][1]["outcome"] == ("Failed", "invalid_state")
    assert batch.evidence["steps"][2]["poisoned"] is True
    assert batch.evidence["outcome"] == ("Failed", "invalid_state")
    assert not batch.evidence["markerBefore"] and batch.evidence["markerStaged"]
    assert not batch.evidence["markerAfter"]

    for field in batch.evidence:
        expect_invalid(lambda field=field: generated.check(None, requests, "commit", replace(
            batch, evidence={key: value for key, value in batch.evidence.items() if key != field})),
            "complete transaction evidence")
    expect_invalid(lambda: generated.check(None, requests, "abort", batch), "another exercise")
    expect_invalid(lambda: generated.check("a", requests, "commit", batch), "another exercise")
    expect_invalid(lambda: generated.check(None, requests[:1], "commit", batch), "another exercise")
    expect_invalid(lambda: generated.check(None, requests, "commit", replace(
        batch, evidence={**batch.evidence, "steps": batch.evidence["steps"][:1]})), "action count")
    for field in batch.evidence["steps"][0]:
        steps = ({key: value for key, value in batch.evidence["steps"][0].items() if key != field},
                 *batch.evidence["steps"][1:])
        expect_invalid(lambda steps=steps: generated.check(None, requests, "commit", replace(
            batch, evidence={**batch.evidence, "steps": steps})), "step evidence")
    for field, value in (("operation", "update_ref"), ("requested", "wrong-target")):
        steps = ({**batch.evidence["steps"][0], field: value}, *batch.evidence["steps"][1:])
        expect_invalid(lambda steps=steps: generated.check(None, requests, "commit", replace(
            batch, evidence={**batch.evidence, "steps": steps})), "step evidence")
    for field, value, message in (("markerAfter", None, "must be boolean"),
                                  ("outcome", ("Failed", None), "tagged-sum"),
                                  ("before", ("Absent", ("extra",)), "tagged-sum")):
        expect_invalid(lambda field=field, value=value: generated.check(None, requests, "commit", replace(
            batch, evidence={**batch.evidence, field: value})), message)
    steps = ({**batch.evidence["steps"][0], "poisoned": None}, *batch.evidence["steps"][1:])
    expect_invalid(lambda: generated.check(None, requests, "commit", replace(
        batch, evidence={**batch.evidence, "steps": steps})), "must be boolean")
    try:
        generated.require_witnesses(generated.check(None, [], "commit", generated.execute(None, [], "commit")))
    except AssertionError as error:
        assert "commitPoisoned, explicitAbort" in str(error) and "stepEffects" in str(error), error
        print(f"offline non-vacuity control: {error}")
    else:
        raise AssertionError("A clean empty commit concealed unexercised rules")

    # Partial publication, false commit success, and both explicit-abort leaks.
    for changes in ({"markerAfter": True}, {"after": batch.evidence["steps"][0]["after"]},
                    {"outcome": ("Succeeded", ())}):
        expect_violation(None, requests, "commit", replace(batch, evidence={**batch.evidence, **changes}),
                         "commitPoisoned")
    aborted = generated.execute(None, [("create_ref", "a")], "abort")
    for changes in ({"markerAfter": True}, {"after": aborted.evidence["staged"]}):
        expect_violation(None, [("create_ref", "a")], "abort",
                         replace(aborted, evidence={**aborted.evidence, **changes}), "explicitAbort")
    clean = generated.execute(None, [("create_ref", "a")], "commit")
    for changes in ({"markerAfter": False}, {"after": ("Absent", ())},
                    {"outcome": ("Failed", "invalid_state")}):
        expect_violation(None, [("create_ref", "a")], "commit",
                         replace(clean, evidence={**clean.evidence, **changes}), "commitClean")
    print("offline boundaries: incomplete/mismatched evidence and eight fabricated publication failures rejected")
    cases = continuity_controls()
    print(f"offline continuity: {len(cases)} disconnected histories rejected; other rules accepted each")
    check_nonconsuming_commit()
    check_existing_ref_shrink()

    histories, counts = generated.run_property(sample_seed=4120, max_examples=80)
    print(f"offline: {histories} generated batches; matches="
          f"{ {rule: counts[rule, 'pass'] for rule in generated.RULE_IDS} }", flush=True)

    first_failure = None

    def corrupt(trace, actual):
        nonlocal first_failure
        evidence = actual.evidence
        succeeded = [step for step in evidence["steps"] if step["outcome"] == ("Succeeded", ())]
        # Require a successful ref movement before a later failure. This is a
        # fabricated partial publication, not an alteration of actual DML execution.
        if (trace[2] == "commit" and succeeded and succeeded[-1]["after"] != evidence["before"]
                and evidence["outcome"] == ("Failed", "invalid_state")):
            if first_failure is None:
                first_failure = (trace[0], tuple(trace[1]), trace[2])
            return replace(actual, evidence={**evidence, "after": succeeded[-1]["after"]})
        return actual

    try:
        generated.run_property(sample_seed=4120, max_examples=80, corrupt=corrupt)
    except generated.RuleViolation as error:
        assert error.rule == "commitPoisoned" and error.finish == "commit", error
        assert first_failure is not None and len(first_failure[1]) > 2, first_failure
        final = (error.initial, error.requests, error.finish)
        assert len(error.requests) == 2 and first_failure != final, (first_failure, final)
        print(f"offline shrink: {first_failure} -> {final}\n  {error}", flush=True)
    else:
        raise AssertionError("Hypothesis did not detect fabricated partial publication")


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
