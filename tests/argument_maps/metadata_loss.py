"""PRIVATE authoring-only pre/post commit loss actor; no computational child."""

from pathlib import Path
import subprocess
import sys
import time

import daggerml as d

source, path, basis, marker, boundary = sys.argv[1:]
sys.path.insert(0, source)
import recorded_maps as maps

subprocess.Popen = lambda *a, **k: (_ for _ in ()).throw(AssertionError("metadata actor cannot spawn"))
opening = d.Repository.__init__
committing = d.Transaction.commit


def opened(self, selected, **kwargs):
    opening(self, selected, **kwargs)
    self.selected_target = Path(selected).resolve() == Path(path).resolve()


def pause():
    Path(marker).touch()
    while True:
        time.sleep(0.1)


def commit(self):
    target = self._owner.selected_target and self._write
    if target and boundary == "pre":
        pause()
    committing(self)
    if target and boundary == "post":
        pause()


d.Repository.__init__ = opened
d.Transaction.commit = commit
selected_basis = d.ObjectId.from_hex(basis)
with d.Repository(path) as repo, repo.read() as tx:
    entries = maps.tree(tx, selected_basis)
inputs = maps.inspect_input(path, commit=selected_basis, dag=entries["first-inputs"])
maps.map_insert(path, commit=selected_basis, prior=inputs.construction, key=entries["source-left"], value=entries["source-n13"], output_name="authored", ref="authored")
raise AssertionError("private barrier must prevent acknowledgement")
