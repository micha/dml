"""Private authoring-only pre/post-store-commit barrier. NO computational child."""

import importlib.util
import json
from pathlib import Path
import sys
import time

import daggerml as d
from daggerml import exchange as ex, floci as f

(
    source,
    path,
    first_packet,
    first_saved,
    second_packet,
    second_saved,
    marker,
    boundary,
    operation,
) = sys.argv[1:]
spec = importlib.util.spec_from_file_location("composed_private", source)
app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = app
spec.loader.exec_module(app)
opening = d.Repository.__init__


def opened(self, p, **k):
    opening(self, p, **k)
    self.selected = Path(p).resolve() == Path(path).resolve()


d.Repository.__init__ = opened
committing = d.Transaction.commit


def pause():
    Path(marker).touch()
    while True:
        time.sleep(0.1)


def commit(self):
    if self._owner.selected and self._write:
        if boundary == "pre":
            pause()
        committing(self)
        if boundary == "post":
            pause()
    else:
        committing(self)


d.Transaction.commit = commit
first = ex.load_exchange_handle(first_saved).expected
if operation == "basis":
    remote = f.FlociRemote(
        "http://floci:4566",
        "dml-local",
        "example/scope",
        "local",
        "installed:1",
        "sha256:" + "1" * 64,
        "/opt/dml/bin/python",
    )
    app.consumer_basis(
        path,
        producer_packet=first_packet,
        producer_expected=first,
        remote=remote,
        gate="gates/double",
    )
else:
    app.experiment_summary(
        path,
        producer_packet=first_packet,
        producer_expected=first,
        consumer_packet=second_packet,
        consumer_expected=ex.load_exchange_handle(second_saved).expected,
    )
