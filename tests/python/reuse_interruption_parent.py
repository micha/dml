"""PRIVATE actual authoring-only W pre/post-store-commit barrier; NO child/job."""

import importlib.util
from pathlib import Path
import sys
import time
import uuid

import daggerml as d
from daggerml import exchange as ex

source, path, basis, packet, expected_file, payload, marker, boundary = sys.argv[1:]
spec = importlib.util.spec_from_file_location("reuse_private", source)
app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = app
spec.loader.exec_module(app)
assert not {"http.client", "daggerml.floci", "docker"} & set(sys.modules)
ex.uuid.uuid4 = lambda: uuid.UUID(hex=payload)
opening = d.Repository.__init__


def opened(self, p, **k):
    opening(self, p, **k)
    self.selected = Path(p).resolve() == Path(path).resolve()


d.Repository.__init__ = opened
recording = ex.record_exchange_request


def recorded(*a, **k):
    got = recording(*a, **k)
    Path(marker + ".q-bytes").write_bytes((Path(path) / "data.mdb").read_bytes())
    Path(marker + ".q").write_text(str(got.commit))
    return got


ex.record_exchange_request = recorded
committing = d.Transaction.commit
writes = 0


def pause():
    Path(marker).touch()
    while True:
        time.sleep(0.1)


def commit(self):
    global writes
    selected = self._owner.selected and self._write
    if selected:
        writes += 1
    if selected and writes == 2 and boundary == "pre":
        pause()
    committing(self)
    if selected and writes == 2 and boundary == "post":
        pause()


d.Transaction.commit = commit
app.reuse_attempt(
    path,
    commit=d.ObjectId.from_hex(basis),
    binding_name="double-binding",
    inputs_name="double-inputs",
    intent_uri="urn:example:double",
    historical_packet=packet,
    historical_expected=ex.load_exchange_handle(expected_file).expected,
    submission_ref="reuse-submission",
    ref="reused-double",
)
raise AssertionError("private barrier must prevent response")
