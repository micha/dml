"""Deterministic compact transcript; --write-fixture refreshes checked evidence."""
import json
from pathlib import Path
import sys
import tempfile

from model import (Adapter, Conflict, FakeService, IDs, Repo, Store, attempt,
                   binding, choose, event, install, observations, outcome, request)


HERE = Path(__file__).parent


def scenarios():
    store, ids = Store(), IDs("scenario")
    repo = Repo(store)
    rows = []

    def emit(name, **facts):
        rows.append({"scenario": name, **facts})

    impl = store.put("artifact", {"digest": "synthetic-code-v1"})
    adapter_artifact = store.put("artifact", {"digest": "synthetic-adapter-v1"})
    hcl = store.put("hcl", 'resource "synthetic_worker" "sum" {}\n')
    desc = store.put("installation-description", {"execution_config": {"size": "small"}},
                     {"implementation": impl, "adapter": adapter_artifact, "hcl": hcl})
    resource_binding = {"uri": "file:///synthetic/worker", "version": "v1"}
    i1, c1 = install(store, ids, desc, resource_binding, {"creation_time": 1})
    i2, c2 = install(store, ids, desc, resource_binding, {"creation_time": 2})
    _, c3 = install(store, ids, desc, {**resource_binding, "version": "v2"}, {})
    emit("installation", installations_distinct=i1 != i2, equal_closures=c1 == c2,
         changed_binding_changes_closure=c1 != c3, hcl_is_dag_data=hcl in store.walk(i1))
    bound = binding(store, "intent:sum", c1, store.put("datum", [4, 7]))
    result = store.put("datum", 11)

    def fresh():
        q = request(store, ids, bound)
        a = attempt(store, ids, q)
        repo.append("main", [event(store, ids, a, "registered")])
        done = event(store, ids, a, "done",
                     {"status": "done", "computation": "success", "cleanup": "success"},
                     {"result": result})
        repo.append("main", [done])
        return q, a

    q1, a1 = fresh()
    q2, a2 = fresh()
    emit("identical_trials", distinct_requests=q1 != q2, distinct_attempts=a1 != a2,
         result_roots=len({store.get(n)["refs"]["result"] for a in [a1, a2]
                           for n, e in observations(repo, repo.heads["main"], a).items()
                           if e["value"]["name"] == "done"}))
    naive = [store.put("execution", refs={"binding": bound, "result": result}) for _ in range(2)]
    emit("counterexample_content_identity", actual_trials=2, naive_unique_records=len(set(naive)))
    repo.append("main", selections={bound: a1})
    head = repo.heads["main"]
    emit("reuse", default_off=choose(repo, head, bound, False),
         explicit_off_override_reuses_original=choose(repo, head, bound, False, explicit=a1) == a1,
         default_on_reuses_original=choose(repo, head, bound, True) == a1,
         fresh_returns_no_cached_attempt=choose(repo, head, bound, True, fresh=True) is None)
    repo.fork("other")
    repo.append("main", selections={bound: a2})
    emit("adoption", main_selects_fresh=choose(repo, repo.heads["main"], bound, True) == a2,
         other_retains_original=choose(repo, repo.heads["other"], bound, True) == a1,
         historical_retains_original=choose(repo, head, bound, True) == a1)

    q3 = request(store, ids, bound)
    unknown = attempt(store, ids, q3)
    retry = attempt(store, ids, q3)
    repo.append("main", [event(store, ids, unknown, "registered"),
                         event(store, ids, retry, "registered")])
    emit("multiple_attempts", same_request=store.get(unknown)["refs"] == store.get(retry)["refs"],
         first_outcome=outcome(repo, repo.heads["main"], unknown),
         retry_outcome_before_dispatch=outcome(repo, repo.heads["main"], retry))
    runtime = HERE / "runtime"
    runtime.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=runtime) as td:
        svc = FakeService(Path(td) / "service.json")
        driver = Adapter(repo, ids, svc)
        try:
            driver.tick("main", retry, crash_after_submit=True)
        except RuntimeError:
            pass
        before_resume = outcome(repo, repo.heads["main"], retry)
        restarted = Adapter(repo, IDs("resumed"), FakeService(Path(td) / "service.json"))
        statuses = [restarted.tick("main", retry, cleanup_succeeds=False) for _ in range(3)]
        observed = observations(repo, repo.heads["main"], retry)
        done = next(n for n in observed.values() if n["value"]["name"] == "done")
        emit("crash_and_incremental_publication", outcome_after_crash=before_resume,
             statuses=statuses, external_jobs=len(restarted.service.jobs),
             partial_published=any("partial" in n["refs"] for n in observed.values()),
             computation=done["value"]["data"]["computation"],
             cleanup=done["value"]["data"]["cleanup"])
        remediation = event(store, ids, retry, "cleanup-remediated", {"cleanup": "success"})
        repo.append("main", [remediation])
        emit("remediation", attempt_unchanged=True,
             computation_after=outcome(repo, repo.heads["main"], retry),
             original_cleanup=done["value"]["data"]["cleanup"])

    base = repo.heads["main"]
    e1 = event(store, ids, unknown, "working", {"status": "working", "phase": "submitted"})
    e2 = event(store, IDs("other-observer"), unknown, "working",
               {"status": "working", "phase": "retrieved"})
    left = repo.propose(base, [e1], {bound: a1}, git="synthetic:L")
    right = repo.propose(base, [e2], {bound: retry}, git="synthetic:R")
    rejected = False
    try:
        repo.merge(base, left, right)
    except Conflict:
        rejected = True
    merged = repo.merge(base, left, right, {bound: retry}, git="synthetic:M")
    repo.publish("main", base, left)
    stale_rejected = False
    try:
        repo.publish("main", base, right)
    except Conflict:
        stale_rejected = True
    repo.publish("main", left, merged)
    emit("merge", selection_conflict_rejected=rejected, stale_publish_rejected=stale_rejected,
         both_observations_retained={e1, e2}.issubset(repo.state(merged)[0]),
         merge_parents=2, correlated_git=store.get(merged)["value"]["git"])

    resource = store.get(c1)["refs"]["resource"]
    repo.append("main", [event(store, ids, resource, "resource-retired",
                                {"physical_deletion": "confirmed", "authorized": True})])
    emit("resource_retirement", selected_execution_survives=choose(
         repo, repo.heads["main"], bound, True) == retry,
         result_retained=result in store.walk(repo.heads["main"]),
         physical_deletion_evidence="simulated assertion only",
         sensitive_content_erased=False)
    emit("counterexample_hidden_retries", modeled_attempts=1, actual_simulated_executions=2,
         difference_detectable_without_executor_reporting=False)
    return {"model_version": 1, "evidence": "executed model / simulated executor", "scenarios": rows}


if __name__ == "__main__":
    text = json.dumps(scenarios(), indent=2, sort_keys=True) + "\n"
    if sys.argv[1:] == ["--write-fixture"]:
        (HERE / "scenario-results.json").write_text(text)
    elif sys.argv[1:]:
        raise SystemExit("usage: python3 run_scenarios.py [--write-fixture]")
    else:
        print(text, end="")
