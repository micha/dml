"""Durable cooperative candidate; SQLite is a test substrate, not a DML proposal."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import uuid
from contextlib import contextmanager

CONTRACT_VERSION = "journal-v1"


class Rejected(RuntimeError):
    pass


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class Journal:
    def __init__(self, db_path, sandbox_path, runtime_root=None):
        feasibility = Path(__file__).resolve().parent.parent
        runtime = (Path(__file__).parent / "runtime" if runtime_root is None else Path(runtime_root)).resolve()
        if runtime.name != "runtime" or runtime.parent.parent != feasibility:
            raise Rejected("runtime root must be a feasibility workstream's runtime directory")
        self.sandbox = Path(sandbox_path).resolve(strict=True)
        self.db_path = Path(db_path).resolve()
        if not self.sandbox.is_relative_to(runtime) or not self.db_path.is_relative_to(runtime):
            raise Rejected("journal and sandbox must be inside the selected runtime root")
        if not self.db_path.exists() and any(self.sandbox.iterdir()):
            raise Rejected("a new journal requires a fresh empty sandbox")
        self.db = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS resources (
          id TEXT PRIMARY KEY, physical TEXT UNIQUE NOT NULL,
          owner TEXT NOT NULL CHECK(owner IN ('external','managed')),
          path TEXT UNIQUE, dev INTEGER, ino INTEGER, digest TEXT,
          withdrawn INTEGER NOT NULL DEFAULT 0, disposed INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS aliases (
          name TEXT PRIMARY KEY, resource TEXT NOT NULL REFERENCES resources(id));
        CREATE TABLE IF NOT EXISTS members (repo TEXT PRIMARY KEY, available INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS commits (
          repo TEXT NOT NULL REFERENCES members(repo), key TEXT NOT NULL,
          parents TEXT NOT NULL, provenance TEXT NOT NULL, operational TEXT NOT NULL,
          PRIMARY KEY(repo,key));
        CREATE TABLE IF NOT EXISTS heads (
          repo TEXT NOT NULL REFERENCES members(repo), name TEXT NOT NULL, tip TEXT NOT NULL,
          PRIMARY KEY(repo,name), FOREIGN KEY(repo,tip) REFERENCES commits(repo,key));
        CREATE TABLE IF NOT EXISTS dependencies (
          source TEXT NOT NULL REFERENCES resources(id), target TEXT NOT NULL REFERENCES resources(id),
          PRIMARY KEY(source,target));
        CREATE TABLE IF NOT EXISTS obligations (
          target TEXT PRIMARY KEY REFERENCES resources(id), kind TEXT NOT NULL,
          cleanup TEXT REFERENCES resources(id), resolved INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS tickets (
          id TEXT PRIMARY KEY, revision INTEGER NOT NULL, victims TEXT NOT NULL,
          plan_digest TEXT NOT NULL, status TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS immutable_resource
          BEFORE UPDATE OF id,physical,owner,path,dev,ino,digest ON resources
          BEGIN SELECT RAISE(ABORT,'immutable identity/ownership'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_commit BEFORE UPDATE ON commits
          BEGIN SELECT RAISE(ABORT,'immutable commit'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_alias BEFORE UPDATE ON aliases
          BEGIN SELECT RAISE(ABORT,'immutable alias'); END;
        """)
        with self.tx():
            for key, value in (("version", CONTRACT_VERSION), ("revision", "0"),
                               ("sandbox", str(self.sandbox))):
                self.db.execute("INSERT OR IGNORE INTO meta VALUES (?,?)", (key, value))
            if self.meta("version") != CONTRACT_VERSION or self.meta("sandbox") != str(self.sandbox):
                raise Rejected("version/sandbox mismatch")

    def close(self):
        self.db.close()

    @contextmanager
    def tx(self, write=True):
        self.db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def meta(self, key):
        return self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()[0]

    def revision(self):
        return int(self.meta("revision"))

    def bump(self):
        rev = self.revision() + 1
        self.db.execute("UPDATE meta SET value=? WHERE key='revision'", (str(rev),))
        return rev

    def unfenced(self):
        if self.db.execute("SELECT 1 FROM tickets WHERE status != 'acknowledged'").fetchone():
            raise Rejected("global destruction fence active")

    def resource(self, identity):
        row = self.db.execute("SELECT * FROM resources WHERE id=?", (identity,)).fetchone()
        if row is None:
            raise Rejected("unknown resource")
        return row

    def operational(self, identity):
        r = self.resource(identity)
        if r["withdrawn"] or r["disposed"]:
            raise Rejected("operational acquisition of withdrawn/disposed identity")

    def unused(self, identity, physical, alias):
        if self.db.execute("SELECT 1 FROM resources WHERE id=? OR physical=?", (identity, physical)).fetchone():
            raise Rejected("duplicate physical identity or lifecycle identity")
        if self.db.execute("SELECT 1 FROM aliases WHERE name=?", (alias,)).fetchone():
            raise Rejected("conflicting alias binding")

    def register_external(self, identity, physical, alias):
        with self.tx():
            self.unfenced()
            self.unused(identity, physical, alias)
            self.db.execute("INSERT INTO resources(id,physical,owner) VALUES (?,?,'external')", (identity, physical))
            self.db.execute("INSERT INTO aliases VALUES (?,?)", (alias, identity))
            self.bump()

    def alias(self, name, identity):
        with self.tx():
            self.unfenced()
            self.resource(identity)
            if self.db.execute("SELECT 1 FROM aliases WHERE name=?", (name,)).fetchone():
                raise Rejected("alias already bound")
            self.db.execute("INSERT INTO aliases VALUES (?,?)", (name, identity))
            self.bump()

    def fsync_directory(self):
        fd = os.open(self.sandbox, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def create_file(self, alias, content=b"synthetic", cleanup=None):
        identity = "file:" + uuid.uuid4().hex
        path = self.sandbox / identity[5:]
        physical = "sandbox:" + str(path)
        with self.tx():
            self.unfenced()
            self.unused(identity, physical, alias)
            if cleanup is not None:
                self.operational(cleanup)
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                    st = os.fstat(stream.fileno())
                self.fsync_directory()
                self.db.execute("""INSERT INTO resources
                  (id,physical,owner,path,dev,ino,digest) VALUES (?,?,'managed',?,?,?,?)""",
                  (identity, physical, str(path), st.st_dev, st.st_ino, hashlib.sha256(content).hexdigest()))
                self.db.execute("INSERT INTO aliases VALUES (?,?)", (alias, identity))
                self.db.execute("INSERT INTO obligations VALUES (?,'adoption',?,0)", (identity, cleanup))
                self.bump()
            except BaseException:
                # Never unlink on registration failure; retain any orphan for inspection.
                raise
        return identity

    def member(self, repo, available=True):
        with self.tx():
            self.unfenced()
            self.db.execute("INSERT INTO members VALUES (?,?) ON CONFLICT(repo) DO UPDATE SET available=excluded.available",
                            (repo, int(available)))
            self.bump()

    def require_member(self, repo):
        r = self.db.execute("SELECT available FROM members WHERE repo=?", (repo,)).fetchone()
        if r is None or not r[0]:
            raise Rejected("repository unknown/unavailable")

    def commit_row(self, repo, key):
        r = self.db.execute("SELECT * FROM commits WHERE repo=? AND key=?", (repo, key)).fetchone()
        if r is None:
            raise Rejected("unknown commit")
        return r

    def commit(self, repo, key, parents=(), provenance=(), operational=()):
        with self.tx():
            self.unfenced()
            self.require_member(repo)
            if self.db.execute("SELECT 1 FROM commits WHERE repo=? AND key=?", (repo, key)).fetchone():
                raise Rejected("immutable commit key already registered")
            for parent in parents:
                self.commit_row(repo, parent)
            for identity in provenance:
                self.resource(identity)
            for identity in operational:
                self.operational(identity)
            self.db.execute("INSERT INTO commits VALUES (?,?,?,?,?)",
                            (repo, key, encode(sorted(set(parents))), encode(sorted(set(provenance))),
                             encode(sorted(set(operational)))))
            self.bump()

    def ancestry(self, repo, tip):
        seen, todo = set(), [] if tip is None else [tip]
        while todo:
            key = todo.pop()
            if key not in seen:
                row = self.commit_row(repo, key)
                seen.add(key)
                todo.extend(json.loads(row["parents"]))
        return seen

    def head(self, repo, name, expected, new):
        with self.tx():
            self.unfenced()
            self.require_member(repo)
            row = self.db.execute("SELECT tip FROM heads WHERE repo=? AND name=?", (repo, name)).fetchone()
            old = None if row is None else row[0]
            if old != expected:
                raise Rejected("head CAS conflict")
            for key in self.ancestry(repo, new) - self.ancestry(repo, old):
                for identity in json.loads(self.commit_row(repo, key)["operational"]):
                    self.operational(identity)
            if new is None:
                self.db.execute("DELETE FROM heads WHERE repo=? AND name=?", (repo, name))
            else:
                self.db.execute("INSERT INTO heads VALUES (?,?,?) ON CONFLICT(repo,name) DO UPDATE SET tip=excluded.tip",
                                (repo, name, new))
            self.bump()

    def _export(self):
        associations, commits, heads = set(), {}, {}
        for row in self.db.execute("SELECT * FROM heads ORDER BY repo,name"):
            repo, name, tip = row
            heads.setdefault(repo, {})[name] = tip
            for key in self.ancestry(repo, tip):
                commits.setdefault(repo, set()).add(key)
                c = self.commit_row(repo, key)
                associations.update(json.loads(c["provenance"]))
                associations.update(json.loads(c["operational"]))
        retained = set(associations)
        retained.update(r[0] for r in self.db.execute("SELECT cleanup FROM obligations WHERE resolved=0 AND cleanup IS NOT NULL"))
        todo = list(retained)
        while todo:
            for row in self.db.execute("SELECT target FROM dependencies WHERE source=?", (todo.pop(),)):
                if row[0] not in retained:
                    retained.add(row[0])
                    todo.append(row[0])
        return {"version": CONTRACT_VERSION, "revision": self.revision(), "heads": heads,
                "commits": {r: sorted(c) for r, c in commits.items()},
                "associations": sorted(associations), "retained": sorted(retained),
                "members": {r[0]: bool(r[1]) for r in self.db.execute("SELECT * FROM members ORDER BY repo")}}

    def export(self):
        with self.tx(write=False):
            return self._export()

    def snapshot(self):
        roots = self.export()
        return {"version": CONTRACT_VERSION, "revision": roots["revision"], "roots": roots}

    def dependency(self, source, target):
        with self.tx():
            self.unfenced()
            self.operational(source)
            self.operational(target)
            if source == target:
                raise Rejected("self dependency")
            self.db.execute("INSERT OR IGNORE INTO dependencies VALUES (?,?)", (source, target))
            self.bump()

    def excise(self, identity):
        with self.tx():
            self.unfenced()
            r = self.resource(identity)
            if r["owner"] != "managed" or r["disposed"]:
                raise Rejected("no excision authority / already disposed")
            if self.db.execute("""SELECT 1 FROM dependencies d JOIN resources r ON r.id=d.source
                                 WHERE d.target=? AND r.disposed=0""", (identity,)).fetchone():
                raise Rejected("live operational dependents")
            if self.db.execute("SELECT 1 FROM obligations WHERE cleanup=? AND resolved=0", (identity,)).fetchone():
                raise Rejected("pending cleanup prerequisite")
            self.db.execute("UPDATE resources SET withdrawn=1 WHERE id=?", (identity,))
            self.bump()

    def obligations(self):
        with self.tx(write=False):
            return [dict(r) for r in self.db.execute("SELECT * FROM obligations ORDER BY target")]

    def adopted(self, identity):
        with self.tx():
            self.unfenced()
            self.operational(identity)
            # Adoption completes import, not the lifecycle disposal responsibility.
            # Keep cleanup prerequisites pinned until target absence is acknowledged.
            self.db.execute("UPDATE obligations SET kind='managed' WHERE target=? AND kind='adoption'", (identity,))
            self.bump()

    def census(self):
        if not self.db.execute("SELECT 1 FROM members").fetchone():
            raise Rejected("empty registered census")
        if self.db.execute("SELECT 1 FROM members WHERE available=0").fetchone():
            raise Rejected("unavailable repository member")

    def reserve(self, victims, expected_revision, plan_digest):
        victims = sorted(set(victims))
        with self.tx():
            self.unfenced()
            self.census()
            if expected_revision != self.revision() or not victims or not plan_digest:
                raise Rejected("stale revision / empty plan")
            retained = set(self._export()["retained"])
            for identity in victims:
                r = self.resource(identity)
                if r["owner"] != "managed" or r["disposed"]:
                    raise Rejected("not an owned live victim")
                if identity in retained and not r["withdrawn"]:
                    raise Rejected("full-history retained")
                if self.db.execute("SELECT 1 FROM obligations WHERE cleanup=? AND resolved=0", (identity,)).fetchone():
                    raise Rejected("cleanup prerequisite still required")
                if self.db.execute("""SELECT 1 FROM dependencies d JOIN resources r ON r.id=d.source
                                     WHERE d.target=? AND r.disposed=0""", (identity,)).fetchone():
                    raise Rejected("live dependent; dispose it first")
            rev = self.bump()
            ticket_id = uuid.uuid4().hex
            self.db.execute("INSERT INTO tickets VALUES (?,?,?,?,'reserved')", (ticket_id, rev, encode(victims), plan_digest))
            for identity in victims:
                self.db.execute("""INSERT INTO obligations VALUES (?,'disposal',NULL,0)
                  ON CONFLICT(target) DO UPDATE SET kind='disposal',resolved=0""", (identity,))
            return self._ticket(ticket_id)

    def _ticket(self, ticket_id):
        row = self.db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        if row is None:
            raise Rejected("unknown ticket")
        return {"version": CONTRACT_VERSION, "id": row["id"], "revision": row["revision"],
                "victims": json.loads(row["victims"]), "plan_digest": row["plan_digest"], "status": row["status"]}

    def _verify(self, ticket, allow_ack=False):
        t = self._ticket(ticket["id"])
        for field in ("version", "id", "revision", "victims", "plan_digest"):
            if ticket.get(field) != t[field]:
                raise Rejected("ticket binding mismatch")
        if t["status"] == "acknowledged":
            if allow_ack:
                return t
            raise Rejected("ticket finished")
        self.census()
        if self.revision() != t["revision"]:
            raise Rejected("stale ticket revision")
        return t

    def verify(self, ticket):
        with self.tx(write=False):
            return self._verify(ticket)

    def begin_effect(self, ticket):
        with self.tx():
            t = self._verify(ticket, allow_ack=True)
            if t["status"] != "acknowledged":
                self.db.execute("UPDATE tickets SET status='intent' WHERE id=?", (t["id"],))
            return self._ticket(t["id"])

    def recorded_path(self, identity):
        r = self.resource(identity)
        if r["owner"] != "managed" or not r["path"]:
            raise Rejected("no disposable sandbox identity")
        path = Path(r["path"])
        if path.parent != self.sandbox or path.name != identity[5:] or not identity.startswith("file:"):
            raise Rejected("invalid sandbox path")
        return r, path

    def check_file(self, identity):
        r, path = self.recorded_path(identity)
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return path, False
        with os.fdopen(fd, "rb") as stream:
            st = os.fstat(stream.fileno())
            if not stat.S_ISREG(st.st_mode) or (st.st_dev, st.st_ino) != (r["dev"], r["ino"]):
                raise Rejected("physical file identity mismatch")
            if hashlib.sha256(stream.read()).hexdigest() != r["digest"]:
                raise Rejected("recorded content identity mismatch")
        return path, True

    def effect(self, ticket):
        # Keep DB write lock during this synthetic effect; ticket also survives exit.
        with self.tx():
            t = self._verify(ticket, allow_ack=True)
            if t["status"] == "acknowledged":
                return
            if t["status"] != "intent":
                raise Rejected("persist intent before effect")
            for identity in t["victims"]:
                path, present = self.check_file(identity)
                if present:
                    path.unlink()
                    self.fsync_directory()

    def ack(self, ticket):
        with self.tx():
            t = self._verify(ticket, allow_ack=True)
            if t["status"] == "acknowledged":
                return t
            if t["status"] != "intent":
                raise Rejected("no in-flight intent")
            for identity in t["victims"]:
                _, path = self.recorded_path(identity)
                if os.path.lexists(path):
                    raise Rejected("absence not observed")
            for identity in t["victims"]:
                self.db.execute("UPDATE resources SET disposed=1 WHERE id=?", (identity,))
                self.db.execute("UPDATE obligations SET resolved=1 WHERE target=?", (identity,))
            self.db.execute("UPDATE tickets SET status='acknowledged' WHERE id=?", (t["id"],))
            self.bump()
            return self._ticket(t["id"])

    def recover(self, ticket):
        self.begin_effect(ticket)
        self.effect(ticket)
        return self.ack(ticket)
