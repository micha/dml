"""Informative finite model; not a DML schema or real resource-manager adapter."""
from dataclasses import dataclass, field
from pathlib import Path
import json


class Unsafe(RuntimeError):
    pass


@dataclass
class Resource:
    kind: str  # external, provisioned, adopted
    deps: set[str] = field(default_factory=set)
    container: str | None = None
    cleaner: str | None = None


@dataclass(frozen=True)
class Commit:
    parents: tuple[str, ...]
    datums: tuple[str, ...]


@dataclass
class Repo:
    commits: dict[str, Commit] = field(default_factory=dict)
    heads: dict[str, str] = field(default_factory=dict)
    available: bool = True


@dataclass
class Obligation:
    target: str
    cleaner: str
    phase: str = "pending-adoption"
    failures: int = 0


@dataclass(frozen=True)
class Plan:
    revision: int
    victims: frozenset[str]


class Manager:
    def __init__(self, sandbox: Path):
        self.sandbox = sandbox
        sandbox.mkdir(parents=True, exist_ok=True)
        self.resources: dict[str, Resource] = {}
        self.aliases: dict[str, str] = {}
        self.repos = {"A": Repo(), "B": Repo()}
        self.membership_complete = True
        self.exports: dict[str, set[str]] = {}
        self.obligations: dict[str, Obligation] = {}
        self.state: dict[str, str] = {}  # operational address -> actual object identity
        self.config: dict[str, str] = {}  # disposable materialization
        self.audit: list[dict] = []  # never traversed by ordinary retention
        self.withdrawn: set[str] = set()
        self.tombstones: dict[str, dict] = {}
        self.deleted: set[str] = set()
        self.copies: dict[str, dict[str, bytes]] = {}  # simulated content copies
        self.uncontrolled_copies: dict[str, bytes] = {}
        self.revision = 0
        self.reserved: frozenset[str] | None = None

    def add(self, rid, kind, deps=(), container=None, cleaner=None, registered=True):
        if self.reserved is not None:
            raise Unsafe("resource namespace mutation during reservation")
        if kind not in {"external", "provisioned", "adopted"}:
            raise ValueError(kind)
        self.resources[rid] = Resource(kind, set(deps), container, cleaner)
        self.aliases[rid] = rid
        self.copies[rid] = {}
        (self.sandbox / f"{rid}.object").write_bytes(b"SYNTHETIC RESOURCE")
        if kind != "external" and registered:
            self.state[f"managed.{rid}"] = rid
        self.revision += 1

    def alias(self, datum, actual):
        if self.reserved is not None:
            raise Unsafe("alias mutation during reservation")
        if datum in self.aliases:
            raise Unsafe("stable alias cannot be rebound")
        self.aliases[datum] = actual
        self.revision += 1

    def closure(self, roots):
        seen = set()
        todo = list(roots)
        while todo:
            rid = todo.pop()
            if rid in seen:
                continue
            if rid not in self.resources:
                raise Unsafe(f"unknown resource: {rid}")
            seen.add(rid)
            todo.extend(self.resources[rid].deps)
            if self.resources[rid].cleaner is not None:
                todo.append(self.resources[rid].cleaner)
        return seen

    def history(self, repo, heads=None):
        r = self.repos[repo]
        seen, todo = set(), list((heads or r.heads).values())
        # Explicit empty candidate heads must mean empty, not existing heads.
        if heads is not None:
            todo = list(heads.values())
        roots = set()
        while todo:
            cid = todo.pop()
            if cid in seen:
                continue
            seen.add(cid)
            c = r.commits[cid]
            roots.update(self.aliases[d] for d in c.datums)
            todo.extend(c.parents)
        return roots

    def publish(self, repo, cid, parents=(), datums=(), head="main"):
        r = self.repos[repo]
        if cid in r.commits:
            raise Unsafe("immutable commit cannot be overwritten")
        if any(p not in r.commits for p in parents):
            raise Unsafe("unknown parent")
        r.commits[cid] = Commit(tuple(parents), tuple(datums))
        try:
            self.move_head(repo, head, cid)
        except Exception:
            del r.commits[cid]
            raise

    def move_head(self, repo, head, cid):
        r = self.repos[repo]
        proposed = dict(r.heads)
        if cid is None:
            proposed.pop(head, None)
        else:
            proposed[head] = cid
        required = self.closure(self.history(repo, proposed) - self.withdrawn)
        if required & self.deleted:
            raise Unsafe("publication references already deleted resource")
        if self.reserved is not None and required & self.reserved:
            raise Unsafe("publication conflicts with deletion fence")
        r.heads = proposed
        self.revision += 1

    def add_export(self, name, roots):
        needed = self.closure(roots)
        if needed & self.deleted or (self.reserved is not None and needed & self.reserved):
            raise Unsafe("export conflicts with resource availability/fence")
        self.exports[name] = set(roots)
        self.revision += 1

    def direct_roots(self):
        if not self.membership_complete or any(not r.available for r in self.repos.values()):
            raise Unsafe("incomplete repository census")
        return set().union(*(self.history(n) for n in self.repos), *self.exports.values())

    def retained(self):
        return self.closure(self.direct_roots() - self.withdrawn)

    def recovery_roots(self):
        # Small recovery records retain actual identity and cleanup prerequisites,
        # not the old commit DAG. Targets are excluded from ordinary GC and are
        # disposed by reconciliation, so this is not a permanent research root.
        return self.closure({x for o in self.obligations.values() for x in (o.target, o.cleaner)})

    def plan(self):
        protected = self.retained() | self.recovery_roots()
        victims = {rid for rid, r in self.resources.items()
                   if r.kind != "external" and rid not in protected and rid not in self.deleted}
        return Plan(self.revision, frozenset(victims))

    def reserve(self, plan):
        if self.reserved is not None:
            raise Unsafe("another reservation active")
        if plan != self.plan():
            raise Unsafe("stale approval")
        self.reserved = plan.victims
        return plan.victims

    def _unlink(self, rid):
        if self.resources[rid].kind == "external":
            raise Unsafe("outside deletion authority")
        cleaner = self.resources[rid].cleaner
        if cleaner is not None and cleaner in self.deleted:
            raise Unsafe("sole cleanup identity is gone")
        (self.sandbox / f"{rid}.object").unlink(missing_ok=True)
        self.deleted.add(rid)
        self.state = {a: r for a, r in self.state.items() if r != rid}
        self.audit.append({"deleted": rid})

    def destroy_reserved(self):
        if self.reserved is None:
            raise Unsafe("missing fence")
        remaining = set(self.reserved)
        try:
            if remaining & (self.retained() | self.recovery_roots()):
                raise Unsafe("reservation no longer safe")
            while remaining:
                # Delete dependent before prerequisite. Reject dependency cycles.
                choices = sorted(rid for rid in remaining if not any(
                    rid in self.resources[other].deps or rid == self.resources[other].cleaner
                    for other in remaining))
                if not choices:
                    raise Unsafe("dependency cycle needs backend-specific handling")
                rid = choices[0]
                self._unlink(rid)
                remaining.remove(rid)
            self.revision += 1
        finally:
            self.reserved = None

    def naive_destroy(self, plan):
        # Intentionally faulty comparator: approval is not a retention transaction.
        for rid in sorted(plan.victims):
            self._unlink(rid)

    def start_adoption(self, rid, cleaner):
        needed = self.closure({rid, cleaner})
        if needed & self.deleted or (self.reserved is not None and needed & self.reserved):
            raise Unsafe("adoption conflicts with deletion")
        self.obligations[rid] = Obligation(rid, cleaner)
        self.revision += 1

    def reconcile(self, rid, fail=False):
        o = self.obligations[rid]
        if o.cleaner in self.deleted:
            raise Unsafe("sole cleanup identity is gone")
        if o.phase == "pending-adoption":
            self.state[f"managed.{rid}"] = rid
            o.phase = "cleanup-ready"
        if rid in self.retained():
            del self.obligations[rid]  # adoption transferred to rooted ownership
        elif fail:
            o.failures += 1
            o.phase = "cleanup-failed"
        else:
            # A dependent outside the journal target prevents disposal.
            if any(rid in r.deps and other not in self.deleted and other not in self.withdrawn
                   for other, r in self.resources.items() if other != rid):
                raise Unsafe("live dependent prevents cleanup")
            self._unlink(rid)
            del self.obligations[rid]  # only discharge after confirmed absence
        self.revision += 1

    def consumers(self, victims):
        owners = {n for n in self.repos if self.closure(self.history(n)) & victims}
        owners |= {f"export:{n}" for n, roots in self.exports.items()
                   if self.closure(roots) & victims}
        return owners

    def excise(self, victims, approvals, erase=False):
        if self.reserved is not None:
            raise Unsafe("excision during reservation")
        victims = set(victims)
        self.direct_roots()  # unavailable owners cannot silently consent
        if any(self.resources[r].kind == "external" for r in victims):
            raise Unsafe("external ownership")
        if not self.consumers(victims) <= set(approvals):
            raise Unsafe("missing shared-consumer authorization")
        # A key cannot disappear while an unwithdrawn artifact needs it.
        still_needed = self.closure(self.direct_roots() - self.withdrawn - victims)
        if victims & still_needed:
            raise Unsafe("retained consumer needs excised prerequisite")
        if victims & self.recovery_roots():
            raise Unsafe("pending cleanup obligation needs excised resource")
        self.withdrawn.update(victims)
        for rid in victims:
            self.tombstones[rid] = {"id": rid, "status": "erasure-pending" if erase else "retired"}
        self.revision += 1

    def erase_controlled(self, rid):
        if self.tombstones[rid]["status"] != "erasure-pending":
            raise Unsafe("content erasure not authorized")
        self.copies[rid].clear()
        self.tombstones[rid]["status"] = "erased-controlled-copies"
        self.revision += 1

    def available(self, rid):
        return not bool(self.closure({rid}) & (self.withdrawn | self.deleted))

    def regenerate(self):
        wanted = self.retained() | self.recovery_roots()
        self.config = {a: rid for a, rid in self.state.items() if rid in wanted}
        return self.config

    def save_state(self):
        (self.sandbox / "state.json").write_text(json.dumps(self.state, sort_keys=True))

    def load_state(self):
        self.state = json.loads((self.sandbox / "state.json").read_text())

    def assert_safety(self):
        assert not (self.retained() & self.deleted), "deleted retained resource/prerequisite"
        assert not (self.recovery_roots() & self.deleted), "lost cleanup identity or target"
        assert all(self.resources[r].kind != "external" for r in self.deleted)
        assert all(self.tombstones[r].keys() == {"id", "status"} for r in self.tombstones)
        assert all(not self.copies[r] for r, t in self.tombstones.items()
                   if t["status"] == "erased-controlled-copies")
