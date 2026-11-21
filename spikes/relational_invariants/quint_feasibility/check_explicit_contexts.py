"""Independent differential and offline controls for explicit endings inside with tx."""

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
import explicit_context_binding as binding
import generated_explicit_contexts as generated
from hypothesis import strategies as st


SPIKE = Path(__file__).resolve().parent


def quint_literal(value) -> str:
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is str:
        return json.dumps(value)
    if type(value) is int:
        return str(value)
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
    quint: Path, attempts: tuple[dict, ...], *, rules: Path = SPIKE / "explicit_context_rules.qnt",
    rule_ids: tuple[str, ...] = generated.RULE_IDS,
) -> list[str]:
    literals = ",\n".join(quint_literal(attempt) for attempt in attempts)
    rule_list = ", ".join(json.dumps(rule) for rule in rule_ids)
    with TemporaryDirectory(prefix="quint-explicit-context-eval-") as tmp:
        directory = Path(tmp)
        copyfile(rules.with_name("transaction_rules.qnt"), directory / "transaction_rules.qnt")
        copyfile(rules, directory / "explicit_context_rules.qnt")
        module = directory / "observations.qnt"
        report = directory / "verdicts.json"
        module.write_text(
            'module observations {\n'
            '  import transaction_rules.* from "./transaction_rules"\n'
            '  import explicit_context_rules.* from "./explicit_context_rules"\n'
            f'  pure val attempts: List[ExplicitContext] = List({literals})\n'
            f'  pure val orderedRules = List({rule_list})\n'
            '  var verdicts: List[str]\n'
            '  action init = all {\n'
            f'    explicitContextRuleIds == Set({rule_list}),\n'
            "    verdicts' = attempts.foldl(List(), (items, a) =>\n"
            '      orderedRules.foldl(items, (results, rule) => results.append(explicitContextVerdict(rule, a)))),\n'
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


def outer_changed(observation, **fields):
    return replace(observation, evidence={**observation.evidence, **fields})


def continuity_controls() -> tuple:
    updated = generated.execute("a", [("update_ref", "b")], "commit_normal")
    evidence = updated.evidence["batch"]
    assert evidence["before"] != evidence["staged"]
    lost_update = outer_changed(changed(updated, staged=evidence["before"], after=evidence["before"]),
                                endedRef=evidence["before"])
    disconnected_start = changed(updated, steps=({**evidence["steps"][0], "before": evidence["staged"]},))
    two = generated.execute("a", [("update_ref", "b"), ("update_ref", "a")], "commit_normal")
    second = {**two.evidence["batch"]["steps"][1], "before": two.evidence["batch"]["before"]}
    disconnected_middle = changed(two, steps=(two.evidence["batch"]["steps"][0], second))
    empty = generated.execute("a", [], "commit_normal")
    disconnected_empty = outer_changed(changed(empty, staged=evidence["staged"], after=evidence["staged"]),
                                       endedRef=evidence["staged"])
    poisoned = generated.execute("a", [("update_ref", "b"), ("create_ref", "a"),
                                       ("create_ref", "b")], "commit_normal")
    steps = poisoned.evidence["batch"]["steps"]
    wrong_poison = changed(poisoned, steps=(*steps[:2], {**steps[2], "poisoned": False}))
    cases = (lost_update, disconnected_start, disconnected_middle, disconnected_empty, wrong_poison)
    for batch in cases:
        binding.validate_observation(batch.initial, batch.requests, batch.finish, batch)
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
    commits = tuple(generated.execute(None, [("create_ref", target)], "commit_normal")
                    .evidence["batch"]["staged"] for target in generated.TARGETS)
    assert len(set(commits)) == len(commits), "abstract targets did not map to distinct commits"
    absent, unreadable = ("Absent", ()), ("Unreadable", "invalid_state")
    refs = (absent, *commits)
    outcomes = (("Succeeded", ()), ("Failed", "invalid_state"), ("Failed", "not_found"),
                ("Failed", "body_exception"), ("Failed", "replaced_exception"))
    empty = generated.execute(None, [], "commit_normal").evidence
    # Synthetic observations exercise rule branches, not claims about native execution.
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
    completion_matrix = tuple(
        {**batch.evidence, "explicit": explicit, "exception": exception, "exitCalls": exit_calls,
         "batch": {**batch.evidence["batch"], "outcome": outcome}}
        for batch, explicit, outcome, exception, exit_calls in
        product(representatives, outcomes[:3], outcomes,
                ("none", "original", "replaced", "suppressed"), (0, 1))
    )
    snapshot_matrix = tuple(
        {**batch.evidence, "endedRef": ended_ref, "endedMarker": ended_marker,
         "batch": {**batch.evidence["batch"], "after": after, "markerAfter": marker_after}}
        for batch, ended_ref, after, ended_marker, marker_after in
        product(representatives, refs, refs, (False, True), (False, True))
    )
    probe_matrix = tuple(
        {**empty, field: outcome}
        for field, outcome in product(("endRead", "endWrite", "endCommit", "endAbort"), outcomes)
    )
    marker_matrix = tuple(
        {**empty, "batch": {**empty["batch"], "markerBefore": before,
                            "markerStaged": staged, "markerAfter": after}}
        for before, staged, after in product((False, True), repeat=3)
    )
    synthetic = (step_matrix + completion_matrix + snapshot_matrix + probe_matrix + marker_matrix
                 + tuple(batch.evidence for batch in continuity_controls()))

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

    actual_counts, synthetic_counts = compare(actual), compare(synthetic)
    assert len(histories) == 85 and len(actual) == 1020
    assert all(counts["pass"] > 0 and counts["violation"] == 0 for counts in actual_counts.values())
    assert all(counts["violation"] > 0 for counts in synthetic_counts.values())
    print(f"agreement: {len(actual)} real explicit contexts, {len(synthetic)} synthetic contexts, "
          f"{(len(actual) + len(synthetic)) * len(generated.RULE_IDS)} identical verdicts", flush=True)
    for rule in generated.RULE_IDS:
        print(f"  {rule}: actual={dict(actual_counts[rule])}, synthetic={dict(synthetic_counts[rule])}")


def check_boundaries() -> None:
    clean = generated.execute("a", [("update_ref", "b")], "commit_normal")
    for key in clean.evidence:
        expect_invalid(lambda key=key: generated.check(clean.initial, clean.requests, clean.finish, replace(
            clean, evidence={field: value for field, value in clean.evidence.items() if field != key})), "evidence")
    for key in clean.evidence["batch"]:
        missing = {field: value for field, value in clean.evidence["batch"].items() if field != key}
        expect_invalid(lambda missing=missing: generated.check(clean.initial, clean.requests, clean.finish,
            outer_changed(clean, batch=missing)), "evidence")
    expect_invalid(lambda: generated.check(clean.initial, clean.requests, "unsupported", clean), "ending")
    for initial, requests, finish in ((None, clean.requests, clean.finish),
                                      (clean.initial, [], clean.finish),
                                      (clean.initial, clean.requests, "commit_exception")):
        expect_invalid(lambda initial=initial, requests=requests, finish=finish:
            generated.check(initial, requests, finish, clean), "another exercise")
    expect_invalid(lambda: generated.check(clean.initial, clean.requests, clean.finish,
        changed(clean, steps=())), "action count")
    for key in clean.evidence["batch"]["steps"][0]:
        step = {field: value for field, value in clean.evidence["batch"]["steps"][0].items() if field != key}
        expect_invalid(lambda step=step: generated.check(clean.initial, clean.requests, clean.finish,
            changed(clean, steps=(step,))), "step evidence")
    for field, value in (("operation", "create_ref"), ("requested", "wrong-target")):
        step = {**clean.evidence["batch"]["steps"][0], field: value}
        expect_invalid(lambda step=step: generated.check(clean.initial, clean.requests, clean.finish,
            changed(clean, steps=(step,))), "step evidence")
    for field, value in (("explicit", ("Failed", None)), ("endedRef", ("Absent", ("extra",))),
                         ("endedMarker", None), ("endRead", ("Unknown", ())),
                         ("exitCalls", True), ("exitCalls", -1), ("exception", None)):
        expect_invalid(lambda field=field, value=value:
            generated.check(clean.initial, clean.requests, clean.finish, outer_changed(clean, **{field: value})), "")
    print("offline boundaries: missing/misassociated/malformed outer, batch and step evidence rejected")


def check_fabricated_controls() -> None:
    controls = 0
    for finish, requests, rule in (
        ("commit_normal", [("update_ref", "b")], "explicitCleanCommit"),
        ("commit_exception", [("update_ref", "b")], "explicitCleanCommit"),
        ("commit_normal", [("update_ref", "b"), ("create_ref", "a")], "explicitPoisonedCommit"),
        ("commit_exception", [("update_ref", "b"), ("create_ref", "a")], "explicitPoisonedCommit"),
        ("abort_normal", [("update_ref", "b")], "explicitAbort"),
        ("abort_exception", [("update_ref", "b"), ("create_ref", "a")], "explicitAbort"),
    ):
        batch = generated.execute("a", requests, finish)
        generated.check(batch.initial, batch.requests, batch.finish, batch)
        for fields in ({"explicit": ("Failed", "not_found")},
                       {"endedMarker": not batch.evidence["endedMarker"]},
                       {"endedRef": ("Absent", ())}):
            corrupted = outer_changed(batch, **fields)
            if "endedMarker" in fields:
                corrupted = changed(corrupted, markerAfter=fields["endedMarker"])
            if "endedRef" in fields:
                corrupted = changed(corrupted, after=fields["endedRef"])
            expect_violation(corrupted, rule)
            controls += 1
        for fields in ({"exitCalls": 1}, {"exception": "replaced"}, {"exception": "suppressed"}):
            expect_violation(outer_changed(batch, **fields), "contextExit")
            controls += 1
        expect_violation(changed(batch, markerAfter=not batch.evidence["batch"]["markerAfter"]), "contextExit")
        controls += 1
        for field in ("endRead", "endWrite", "endCommit", "endAbort"):
            expect_violation(outer_changed(batch, **{field: ("Failed", "not_found")}), "endedHandle")
            controls += 1
    empty = generated.execute(None, [], "commit_normal")
    try:
        generated.require_witnesses(generated.check(None, [], "commit_normal", empty))
    except AssertionError as error:
        assert all(rule in str(error) for rule in ("explicitPoisonedCommit", "explicitAbort", "stepEffects")), error
        print(f"offline non-vacuity: {error}")
    else:
        raise AssertionError("A clean empty explicit commit concealed unexercised rules")
    print(f"offline fabricated controls: {controls} explicit-call, ended-handle and exit failures rejected")


def check_adapter_controls() -> None:
    marker_present = binding.marker_present
    commit, abort, exit_context = dml.Transaction.commit, dml.Transaction.abort, dml.Transaction.__exit__
    tested = None

    def arm(tx, marker):
        nonlocal tested
        if tx._write:
            tested = tx
        return marker_present(tx, marker)

    # Change real completion behavior, not just an assembled observation.
    def rollback_commit(tx):
        if tx is tested and not tx._ended:
            return abort(tx)
        return commit(tx)

    with patch.object(binding, "marker_present", arm), patch.object(dml.Transaction, "commit", rollback_commit):
        rolled_back = generated.execute("a", [("update_ref", "b")], "commit_normal")
    assert not rolled_back.evidence["endedMarker"], rolled_back.evidence
    expect_violation(rolled_back, "explicitCleanCommit")

    def publish_abort(tx):
        if tx is tested and not tx._ended:
            return commit(tx)
        return abort(tx)

    with patch.object(binding, "marker_present", arm), patch.object(dml.Transaction, "abort", publish_abort):
        published = generated.execute("a", [("update_ref", "b")], "abort_normal")
    assert published.evidence["endedMarker"], published.evidence
    expect_violation(published, "explicitAbort")

    for method, finish in (("commit", "commit_normal"), ("abort", "abort_normal"),
                           ("abort", "commit_exception")):
        def repeat_at_exit(tx, exc_type, exc, traceback):
            if tx is tested:
                getattr(tx, method)()
            return exit_context(tx, exc_type, exc, traceback)

        with patch.object(binding, "marker_present", arm), patch.object(dml.Transaction, "__exit__", repeat_at_exit):
            repeated = generated.execute("a", [("update_ref", "b")], finish)
        assert repeated.evidence["exitCalls"] >= 1, repeated.evidence
        expect_violation(repeated, "contextExit")

    for replacement in (False, True):
        def faulty_exception(tx, exc_type, exc, traceback):
            if tx is tested and exc_type is not None:
                if replacement:
                    raise type(exc)(*exc.args)
                return True
            return exit_context(tx, exc_type, exc, traceback)

        with patch.object(binding, "marker_present", arm), patch.object(dml.Transaction, "__exit__", faulty_exception):
            wrong_exception = generated.execute("a", [("update_ref", "b")], "commit_exception")
        assert wrong_exception.evidence["exception"] == ("replaced" if replacement else "suppressed")
        assert wrong_exception.evidence["endedMarker"] and wrong_exception.evidence["batch"]["markerAfter"]
        expect_violation(wrong_exception, "contextExit")

    for name in ("get_ref", "put_datum", "commit", "abort"):
        original = getattr(dml.Transaction, name)
        corrupted = False

        def wrong_ended_operation(tx, *args):
            nonlocal corrupted
            if tx is tested and tx._ended and not corrupted:
                corrupted = True
                if name == "abort":
                    raise dml.NotFoundError("not_found", detail="fault-injected ended abort rejection")
                return None
            return original(tx, *args)

        with patch.object(binding, "marker_present", arm), patch.object(dml.Transaction, name, wrong_ended_operation):
            wrong_handle = generated.execute("a", [("update_ref", "b")], "commit_normal")
        assert corrupted
        expect_violation(wrong_handle, "endedHandle")

    # A fresh reader must detect a still-active writer inside the body. Neither
    # __exit__ nor fallback cleanup is allowed to supply evidence of consumption.
    read = dml.Repository.read
    for method, requests in (("commit", [("update_ref", "b")]),
                             ("commit", [("update_ref", "b"), ("create_ref", "a")]),
                             ("abort", [("update_ref", "b")])):
        attempted = False
        events = []
        original = commit if method == "commit" else abort

        def leave_active(tx):
            nonlocal attempted
            if tx is tested and not attempted:
                attempted = True
                events.append("non-consuming ending")
                if method == "commit" and tx._failed:
                    raise dml.InvalidStateError("invalid_state", detail="fault-injected non-consuming rejection")
                return None
            return original(tx)

        def observe(repo):
            if attempted:
                events.append("fresh read")
            return read(repo)

        def cleanup_exit(tx, exc_type, exc, traceback):
            if tx is tested:
                events.append("context exit")
            return exit_context(tx, exc_type, exc, traceback)

        with patch.object(binding, "marker_present", arm), patch.object(dml.Transaction, method, leave_active), \
                patch.object(dml.Repository, "read", observe), \
                patch.object(dml.Transaction, "__exit__", cleanup_exit):
            try:
                generated.execute("a", requests, f"{method}_normal")
            except dml.InvalidStateError as error:
                assert error.detail == "repository already has an active transaction", error
            else:
                raise AssertionError("A non-consuming explicit ending borrowed rollback from context exit")
        assert events[:3] == ["non-consuming ending", "fresh read", "context exit"], events
        assert tested is not None and tested._ended, "The injected leaked writer was not cleaned up"
    print("offline real-adapter controls: wrong publication, repeated completion, swallowed/replaced sentinel, "
          "four wrong ended operations and three non-consuming endings rejected before repair")


def check_unexpected_errors() -> None:
    marker_present, exit_context = binding.marker_present, dml.Transaction.__exit__
    errors = (RuntimeError("unexpected body failure"), binding.ContextBodyError("unrelated sentinel"),
              dml.InvalidStateError("invalid_state", detail="failure before completion"))
    for error in errors:
        def fail_body(tx, marker):
            if tx._write:
                raise error
            return marker_present(tx, marker)

        with patch.object(binding, "marker_present", fail_body):
            try:
                generated.execute("a", [("update_ref", "b")], "commit_normal")
            except type(error) as caught:
                assert caught is error, caught
            else:
                raise AssertionError("An unrelated body error became ending evidence")

    error = RuntimeError("unexpected exit failure")

    def fail_exit(tx, exc_type, exc, traceback):
        if exc_type is not None:
            raise error
        return exit_context(tx, exc_type, exc, traceback)

    with patch.object(dml.Transaction, "__exit__", fail_exit):
        try:
            generated.execute("a", [("update_ref", "b")], "commit_exception")
        except RuntimeError as caught:
            assert caught is error, caught
        else:
            raise AssertionError("An unrelated exit failure became completion evidence")
    print("offline propagation: unrelated runtime/sentinel/InvalidStateError body failures and exit failure retained")


def check_shrinking() -> None:
    first_failure = None
    strategy = st.tuples(st.sampled_from(generated.TARGETS),
                         st.lists(generated.REQUESTS, max_size=generated.MAX_STEPS), st.just("commit_exception"))

    def corrupt(trace, actual):
        nonlocal first_failure
        evidence = actual.evidence["batch"]
        if (actual.evidence["explicit"] != ("Succeeded", ())
                or evidence["staged"] == evidence["before"]):
            return actual
        if first_failure is None:
            first_failure = (trace[0], tuple(trace[1]), trace[2])
        # Emulate a later exception rolling back a successful explicit commit.
        return changed(actual, after=evidence["before"], markerAfter=False)

    try:
        generated.run_property(sample_seed=8150, max_examples=120, corrupt=corrupt, history_strategy=strategy)
    except generated.RuleViolation as error:
        assert error.rule == "contextExit" and error.finish == "commit_exception", error
        assert len(error.requests) == 1 and error.requests[0][0] == "update_ref", error
        assert error.requests[0][1] != error.initial, error
        final = (error.initial, error.requests, error.finish)
        assert first_failure is not None and first_failure != final, (first_failure, final)
        print(f"offline explicit-context shrink: {first_failure} -> {final}\n  {error}", flush=True)
    else:
        raise AssertionError("Hypothesis did not detect post-commit rollback after body exception")


def check_without_quint() -> None:
    if any(which(tool) is not None for tool in ("quint", "node", "npm")):
        raise RuntimeError("Use the offline staging directory with an empty tool PATH")
    for finish, requests in product(generated.FINISHES, ([], [("update_ref", "b")],
                                   [("update_ref", "b"), ("create_ref", "a")])):
        batch = generated.execute("a", requests, finish)
        generated.check(batch.initial, batch.requests, batch.finish, batch)
        assert batch.evidence["exitCalls"] == 0
        assert batch.evidence["batch"]["after"] == batch.evidence["endedRef"]
        assert batch.evidence["batch"]["markerAfter"] == batch.evidence["endedMarker"]
        if finish.endswith("exception"):
            assert batch.evidence["exception"] == "original"
            assert batch.evidence["batch"]["outcome"] == ("Failed", "body_exception")
        else:
            assert batch.evidence["exception"] == "none"
            assert batch.evidence["batch"]["outcome"] == ("Succeeded", ())
    check_boundaries()
    check_fabricated_controls()
    print(f"offline continuity: {len(continuity_controls())} disconnected histories rejected")
    check_adapter_controls()
    check_unexpected_errors()
    histories, counts = generated.run_property(sample_seed=8150, max_examples=120)
    print(f"offline: {histories} generated explicit contexts; matches="
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
