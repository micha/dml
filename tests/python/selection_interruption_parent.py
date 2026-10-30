"""PRIVATE authoring-only actual pre/post-store-commit barrier. NO computation."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import daggerml as d

source, mode, path, basis, packet, expected, marker, boundary = sys.argv[1:]
sys.path.insert(0, str(Path(source).parent))
spec = importlib.util.spec_from_file_location("private_selection", source)
app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = app
spec.loader.exec_module(app)
assert not {"http.client", "daggerml.floci", "docker"} & set(sys.modules)
subprocess.Popen = lambda *a, **k: (_ for _ in ()).throw(
    AssertionError("authoring cannot spawn")
)
opening = d.Repository.__init__
created = []
allocating = tempfile.TemporaryDirectory


def temporary(*a, **k):
    got = allocating(*a, **k)
    if k.get("prefix", "").startswith("dml-selection-"):
        created.append(Path(got.name))
    return got


tempfile.TemporaryDirectory = temporary


def opened(self, selected, **k):
    opening(self, selected, **k)
    self.selected = Path(selected).resolve() == Path(path).resolve()


d.Repository.__init__ = opened
committing = d.Transaction.commit


def pause():
    assert created and all(
        not p.exists() for p in created
    ), "projection disposed before A publication"
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
(app.select if mode == "select" else app.adopt)(
    path,
    commit=d.ObjectId.from_hex(basis),
    slot="selected-new" if mode == "select" else "selected-double",
    binding_name="double-binding",
    inputs_name="double-inputs",
    intent_uri="urn:example:double",
    packet=packet,
    expected_file=expected,
    ref="authored",
)
raise AssertionError("private barrier must prevent response")
