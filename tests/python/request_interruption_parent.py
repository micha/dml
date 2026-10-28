"""Private actual Q/Cq storage barriers. No computation or installed runtime hook."""

import base64
import json
from pathlib import Path
import sys
import time

import daggerml as d
from daggerml import exchange as ex

path, base, marker, stage = sys.argv[1:]
base = d.ObjectId.from_hex(base)
new = {}
original_commit = d.Transaction.commit


def barrier():
    document = [
        [kind, str(oid), base64.b64encode(raw).decode()]
        for (kind, oid), raw in new.items()
    ]
    temporary = Path(marker + ".tmp")
    temporary.write_text(json.dumps(document), encoding="utf-8")
    temporary.replace(marker)
    end = time.monotonic() + 20
    while time.monotonic() < end:
        time.sleep(0.01)
    raise TimeoutError("private recording barrier watchdog")


for method, kind in (
    ("put_datum", "datum"),
    ("put_literal", "node"),
    ("put_subdag", "node"),
    ("put_dag", "dag"),
    ("put_tree", "tree"),
    ("put_commit", "commit"),
):
    original = getattr(d.Transaction, method)

    def putting(self, *a, _original=original, _kind=kind, **k):
        oid = _original(self, *a, **k)
        new[_kind, oid] = self.get_record(_kind, oid)
        return oid

    setattr(d.Transaction, method, putting)


def committing(self):
    assert any(
        kind == "commit" for kind, oid in new
    ), "barrier must follow actual new Cq put/readback"
    if stage == "pre":
        barrier()
    original_commit(self)
    if stage == "post":
        barrier()


d.Transaction.commit = committing
ex.record_exchange_request(
    path,
    commit=base,
    binding_name="binding",
    inputs_name="inputs",
    intent_uri="urn:example:add-i64",
    ref="recorded",
)
raise AssertionError("barrier should prevent response")
