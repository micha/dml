"""Informative feasibility model, not DML schemas or bindings.

All records are ordinary JSON DAG nodes; their labels are application conventions.
Only repository heads and the deliberately simulated external service are mutable.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


class Conflict(Exception):
    pass


class Store:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else None
        if self.directory:
            self.directory.mkdir(parents=True, exist_ok=True)
        self.objects = {}

    def put(self, kind, value=None, refs=None):
        refs = dict(refs or {})
        for target in refs.values():
            self.get(target)  # existing-only edges make construction acyclic
        raw = canonical({"kind": kind, "value": value, "refs": refs})
        cid = hashlib.sha256(raw).hexdigest()
        if self.directory:
            path = self.directory / (cid + ".json")
            if not path.exists():
                with path.open("xb") as stream:
                    stream.write(raw)
            elif path.read_bytes() != raw:
                raise ValueError("content collision/corruption")
        self.objects[cid] = raw
        return cid

    def get(self, cid):
        raw = self.objects.get(cid)
        if raw is None and self.directory:
            raw = (self.directory / (cid + ".json")).read_bytes()
        if raw is None:
            raise KeyError(cid)
        if hashlib.sha256(raw).hexdigest() != cid:
            raise ValueError("content corruption")
        return json.loads(raw)  # callers cannot mutate stored bytes

    def walk(self, root):
        seen, pending = set(), [root]
        while pending:
            cid = pending.pop()
            if cid not in seen:
                seen.add(cid)
                pending.extend(self.get(cid)["refs"].values())
        return seen


class IDs:
    """Deterministic test allocator; issuer uniqueness/durable counter are assumptions."""
    def __init__(self, issuer):
        self.issuer, self.counter = issuer, 0

    def next(self):
        self.counter += 1
        return f"{self.issuer}:{self.counter}"


class Repo:
    def __init__(self, store, head_file=None):
        self.store = store
        self.head_file = Path(head_file) if head_file else None
        if self.head_file and self.head_file.exists():
            self.heads = json.loads(self.head_file.read_text())
        else:
            empty = store.put("snapshot", {"selection_keys": []})
            genesis = store.put("commit", {"git": None}, {"snapshot": empty})
            self.heads = {"main": genesis}
            self._save()

    def _save(self):
        if self.head_file:
            tmp = self.head_file.with_suffix(".tmp")
            tmp.write_bytes(canonical(self.heads))
            tmp.replace(self.head_file)

    def state(self, commit):
        snap = self.store.get(self.store.get(commit)["refs"]["snapshot"])
        events = {v for k, v in snap["refs"].items() if k.startswith("event:")}
        selections = {k.removeprefix("selected:"): v for k, v in
                      snap["refs"].items() if k.startswith("selected:")}
        return events, selections

    def commit(self, parents, events, selections, git=None):
        refs = {"event:" + e: e for e in events}
        refs.update({"selected:" + k: v for k, v in selections.items()})
        snap = self.store.put("snapshot", {"selection_keys": sorted(selections)}, refs)
        return self.store.put("commit", {"git": git},
                              {"snapshot": snap, **{f"parent:{i}": p
                               for i, p in enumerate(parents)}})

    def propose(self, base, events=(), selections=None, git=None):
        old_events, old_selections = self.state(base)
        old_selections.update(selections or {})
        return self.commit([base], old_events | set(events), old_selections, git)

    def publish(self, branch, expected, proposed):
        if self.heads[branch] != expected:
            raise Conflict("head advanced; observation is durable but not published")
        self.heads[branch] = proposed
        self._save()

    def append(self, branch, events=(), selections=None, git=None):
        base = self.heads[branch]
        proposed = self.propose(base, events, selections, git)
        self.publish(branch, base, proposed)
        return proposed

    def fork(self, name, source="main"):
        self.heads[name] = self.heads[source]
        self._save()

    def ancestors(self, commit):
        seen, todo = set(), [commit]
        while todo:
            current = todo.pop()
            if current not in seen:
                seen.add(current)
                todo.extend(v for k, v in self.store.get(current)["refs"].items()
                            if k.startswith("parent:"))
        return seen

    def merge(self, base, left, right, resolution=None, git=None):
        if base not in self.ancestors(left) or base not in self.ancestors(right):
            raise ValueError("not a common ancestor")
        be, bs = self.state(base)
        le, ls = self.state(left)
        re, rs = self.state(right)
        selected, conflicts = {}, []
        for key in sorted(set(bs) | set(ls) | set(rs)):
            b, l, r = bs.get(key), ls.get(key), rs.get(key)
            if l == r:
                chosen = l
            elif l == b:
                chosen = r
            elif r == b:
                chosen = l
            elif resolution is not None and key in resolution:
                chosen = resolution[key]
            else:
                conflicts.append(key)
                continue
            if chosen is not None:
                selected[key] = chosen
        if conflicts:
            raise Conflict("selection conflict: " + ", ".join(conflicts))
        # No last-writer-wins for observations, including contradictory ones.
        return self.commit([left, right], be | le | re, selected, git)


def binding(store, intent, closure, inputs):
    return store.put("binding", {"intent": intent},
                     {"closure": closure, "inputs": inputs})


def request(store, ids, bound, policy=None, override=None):
    refs = {"binding": bound}
    if policy is not None:
        refs["intent-policy"] = policy
    return store.put("request", {"occurrence": ids.next(), "override": override}, refs)


def attempt(store, ids, req):
    return store.put("attempt", {"occurrence": ids.next()}, {"request": req})


def event(store, ids, subject, name, value=None, refs=None):
    return store.put("observation", {"occurrence": ids.next(), "name": name,
                     "data": value}, {"subject": subject, **(refs or {})})


def observations(repo, commit, subject):
    events, _ = repo.state(commit)
    return {cid: repo.store.get(cid) for cid in events
            if repo.store.get(cid)["refs"].get("subject") == subject}


def outcome(repo, commit, att):
    """No recorded terminal => unknown, never inferred failure. Conflicts stay visible."""
    finals = {cid: n for cid, n in observations(repo, commit, att).items()
              if n["value"]["name"] == "done"}
    if not finals:
        return "unknown"
    signatures = {canonical({"data": n["value"]["data"],
                             "result": n["refs"].get("result")}) for n in finals.values()}
    if len(signatures) > 1:
        return "conflicting"
    return next(iter(finals.values()))["value"]["data"]["computation"]


def choose(repo, commit, bound, default_reuse, explicit=None, fresh=False):
    """Reuse eligibility: matching binding, unambiguous success, recorded result.

    Does NOT require live compute resources. Actual result availability is an
    unmodeled project-level check, not implied by content IDs.
    """
    if fresh and explicit is not None:
        raise ValueError("fresh and explicit reuse conflict")
    candidate = explicit
    if candidate is None and default_reuse and not fresh:
        candidate = repo.state(commit)[1].get(bound)
    if candidate is None:
        return None
    req = repo.store.get(candidate)["refs"]["request"]
    if repo.store.get(req)["refs"]["binding"] != bound:
        raise ValueError("reuse binding mismatch")
    if outcome(repo, commit, candidate) != "success":
        raise ValueError("reuse requires unambiguous recorded success")
    finals = [n for n in observations(repo, commit, candidate).values()
              if n["value"]["name"] == "done"]
    if any("result" not in n["refs"] for n in finals):
        raise ValueError("successful reuse requires a recorded result DAG")
    return candidate


def install(store, ids, description, resource_binding, incidental):
    resolved = store.put("resolved-resource", {"binding": resource_binding,
                         "operational": incidental})
    desc = store.get(description)
    # Deliberate modeling choice: incidental outputs/HCL text do not key closure.
    artifact = store.put("resource-binding", resource_binding)
    closure = store.put("bound-closure", desc["value"]["execution_config"],
                        {"implementation": desc["refs"]["implementation"],
                         "adapter": desc["refs"]["adapter"], "resource": artifact})
    installation = store.put("installation", {"occurrence": ids.next()},
                             {"description": description, "resolved": resolved,
                              "closure": closure})
    return installation, closure


class FakeService:
    """No actual external execution; idempotency is a service assumption."""
    def __init__(self, path):
        self.path = Path(path)
        self.jobs = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.calls = 0

    def submit(self, token):
        self.calls += 1
        self.jobs.setdefault(token, {"job": "job:" + token, "executions": 1})
        self.path.write_bytes(canonical(self.jobs))
        return self.jobs[token]["job"]

    def cleanup(self, job, succeeds):
        self.calls += 1
        return "success" if succeeds else "failed"


class Adapter:
    """One finite simulated interaction per tick; progress is immutable events."""
    def __init__(self, repo, ids, service):
        self.repo, self.ids, self.service = repo, ids, service

    def tick(self, branch, att, fail=False, cleanup_succeeds=True,
             crash_after_submit=False):
        repo, store = self.repo, self.repo.store
        records = {cid: node for cid, node in
                   observations(repo, repo.heads[branch], att).items()
                   if node["value"]["name"] in ("working", "done")}
        tips = set(records)
        for node in records.values():
            tips.difference_update(v for k, v in node["refs"].items()
                                   if k.startswith("previous:"))
        if len(tips) > 1:
            raise Conflict("concurrent adapter observations require reconciliation")
        previous = next(iter(tips), None)
        prior = records[previous] if previous else None
        if prior and prior["value"]["name"] == "done":
            return "done"
        phase = prior["value"]["data"].get("phase") if prior else None
        links = {"previous:0": previous} if previous else {}
        if phase is None:
            # Dispatch may succeed without its acknowledgement being recorded.
            token = store.get(att)["value"]["occurrence"]
            job = self.service.submit(token)
            if crash_after_submit:
                raise RuntimeError("simulated crash after external effect")
            value = {"status": "working", "phase": "submitted", "job": job}
            name = "working"
        elif phase == "submitted":
            partial = store.put("datum", {"partial": 4})
            links["partial"] = partial
            value = {"status": "working", "phase": "retrieved", "job":
                     prior["value"]["data"]["job"]}
            name = "working"
        else:
            cleanup = self.service.cleanup(prior["value"]["data"]["job"],
                                           cleanup_succeeds)
            if not fail:
                links["result"] = store.put("datum", 11)
            value = {"status": "done", "computation": "failure" if fail else "success",
                     "failure": "executor error" if fail else None,
                     "cleanup": cleanup, "job": prior["value"]["data"]["job"]}
            name = "done"
        recorded = event(store, self.ids, att, name, value, links)
        repo.append(branch, [recorded])
        return value["status"]
