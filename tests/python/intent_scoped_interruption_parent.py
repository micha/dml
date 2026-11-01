"""PRIVATE finite removal/W author-only commit barrier; no computational child."""

from pathlib import Path
import subprocess
import sys
import time

import daggerml as d
from daggerml import exchange as ex

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "examples"))
import intent_scoped_reuse as app

path, basis, slot, mode, marker, boundary = sys.argv[1:]
subprocess.Popen = lambda *a, **k: (_ for _ in ()).throw(
    AssertionError("author cannot spawn")
)
basis = d.ObjectId.from_hex(basis)
selected = app.selection.inspect(path, commit=basis, slot=slot)
if mode == "W":
    # Existing pending own-Q submission, PUBLIC exact preparation validates it.
    with d.Repository(path) as repo, repo.read() as tx:
        parent = tx.get_commit(basis).parents[0]
        entries = app._tree(tx, basis)
        qname = (set(entries) - set(app._tree(tx, parent))).pop()
        q = entries[qname]
    app._prepare(
        path, basis, "double-b-binding", "double-inputs", selected.intent_uri, request=q
    )
    recorded = ex.RecordedRequest(
        parent,
        basis,
        "submission",
        q,
        qname[len("request-") :],
        "double-b-binding",
        "double-inputs",
        app._prepare(
            path,
            basis,
            "double-b-binding",
            "double-inputs",
            selected.intent_uri,
            request=q,
        ).binding,
        selected.inputs,
        selected.intent_uri,
    )
opening = d.Repository.__init__


def opened(self, name, **k):
    opening(self, name, **k)
    self.selected = Path(name).resolve() == Path(path).resolve()


d.Repository.__init__ = opened
committing = d.Transaction.commit


def pause():
    Path(marker).touch()
    while True:
        time.sleep(0.1)


def commit(self):
    actual = self._owner.selected and self._write
    if actual and boundary == "pre":
        pause()
    committing(self)
    if actual and boundary == "post":
        pause()


d.Transaction.commit = commit
if mode == "remove":
    app.remove_entry(
        path, commit=basis, table_name="table", inputs=selected.inputs, ref="authored"
    )
else:
    app._publish_reuse(path, recorded, selected, "authored", 0)
raise AssertionError("barrier prevents response")
