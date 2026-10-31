"""PRIVATE authoring-only actual-A store barrier, no computational child."""

import sys
from pathlib import Path
import subprocess
import time

import daggerml as d

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "examples"))
import implementation_supersession as app

path, basis, marker, boundary = sys.argv[1:]
assert not {"http.client", "daggerml.floci", "docker"} & set(sys.modules)
subprocess.Popen = lambda *a, **k: (_ for _ in ()).throw(
    AssertionError("authoring cannot spawn")
)
opening = d.Repository.__init__


def opened(self, selected, **k):
    opening(self, selected, **k)
    self.selected = Path(selected).resolve() == Path(path).resolve()


d.Repository.__init__ = opened
committing = d.Transaction.commit


def pause():
    Path(marker).touch()
    while True:
        time.sleep(0.1)


def commit(self):
    selected = self._owner.selected and self._write
    if selected and boundary == "pre":
        pause()
    committing(self)
    if selected and boundary == "post":
        pause()


d.Transaction.commit = commit
app.record_supersession(
    path,
    commit=d.ObjectId.from_hex(basis),
    intent_name="intent",
    slot="supersession",
    predecessor_label="a",
    successor_label="b",
    reason="correctness-fix",
    evidence_name="evidence",
    ref="declared",
)
raise AssertionError("barrier must prevent response")
