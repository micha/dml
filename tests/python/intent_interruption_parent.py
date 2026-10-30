"""PRIVATE first actual Idef/D authoring store-commit barrier; NO computation."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import daggerml as d

source, mode, path, basis, marker, boundary = sys.argv[1:]
sys.path.insert(0, str(Path(source).parent))
spec = importlib.util.spec_from_file_location("private_intent", source)
app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = app
spec.loader.exec_module(app)
assert not {"http.client", "daggerml.floci", "docker"} & set(sys.modules)
subprocess.Popen = lambda *a, **k: (_ for _ in ()).throw(
    AssertionError("authoring cannot spawn")
)
allocating = tempfile.TemporaryDirectory
created = []


def temporary(*a, **k):
    got = allocating(*a, **k)
    created.append(Path(got.name))
    return got


tempfile.TemporaryDirectory = temporary
opening = d.Repository.__init__


def opened(self, selected, **k):
    opening(self, selected, **k)
    self.selected = Path(selected).resolve() == Path(path).resolve()


d.Repository.__init__ = opened
committing = d.Transaction.commit


def pause():
    assert all(
        not p.exists() for p in created
    ), "ALL validation scratch disposed BEFORE publication"
    if mode == "decision":
        assert created, "real public preparation projection required"
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
if mode == "definition":
    app.define(
        path,
        commit=d.ObjectId.from_hex(basis),
        intent_name="double-intent",
        intent_uri="urn:example:double",
        default="execute-by-default",
        ref="authored",
    )
else:
    app.record_policy_request(
        path,
        commit=d.ObjectId.from_hex(basis),
        intent_name="double-intent",
        binding_name="double-binding",
        inputs_name="double-inputs",
        selection_slot="selected-double",
        decision_name="decision-one",
        decision_ref="authored",
        submission_ref="policy-submission",
    )
raise AssertionError("private barrier must prevent response")
