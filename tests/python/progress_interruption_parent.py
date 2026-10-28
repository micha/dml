"""Private finite process barriers. Never installed. No kill with live child."""

import json
from pathlib import Path
import subprocess
import sys
import time

import daggerml as d
from daggerml import exchange as ex, local, transfer

saved, marker, stage, caller, packet = sys.argv[1:]
h = ex.load_exchange_handle(saved)


def barrier():
    Path(marker).write_text("ready")
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        time.sleep(0.01)
    raise TimeoutError("private barrier watchdog")


if stage == "launch-marker":
    subprocess.Popen = lambda *a, **k: barrier()  # marker obtained, no spawn
    ex.start_exchange(h)
elif stage == "initial":
    local._execute = lambda *a, **k: barrier()  # P committed BEFORE spawn
    ex.execute_exchange(h.workspace)
elif stage == "publication":
    # Real _execute wait reaped actual direct child; _cleanup completed. U durable,
    # final storage has not begun. No live child is sacrificed at this barrier.
    local._finalize = lambda *a, **k: barrier()
    ex.execute_exchange(h.workspace)
elif stage == "completion":
    original = local.run_step if h.expected.request is None else local.run_request

    def done(*a, **k):
        original(*a, **k)  # real reaping, cleanup, final storage commit
        barrier()

    if h.expected.request is None:
        local.run_step = done
    else:
        local.run_request = done
    ex.execute_exchange(h.workspace)
else:
    original_import, original_put, original_commit = (
        transfer.import_commit,
        d.Transaction.put_record,
        d.Transaction.commit,
    )
    active, new, puts = False, set(), 0

    def importing(path, *a, **k):
        global active, new
        active = Path(path) == Path(caller)
        if active:
            with d.Repository(caller) as r, r.read() as t:
                for row in json.loads(a[0])["objects"]:
                    key = row["kind"], d.ObjectId.from_hex(row["id"])
                    try:
                        t.get_record(*key)
                    except d.NotFoundError:
                        new.add(key)
        try:
            return original_import(path, *a, **k)
        finally:
            active = False

    def putting(self, kind, record):
        global puts
        oid = original_put(self, kind, record)
        if active and (kind, oid) in new:
            assert self.get_record(kind, oid) == record
            puts += 1
            if stage == "receive-pre" and puts == 3:
                barrier()
        return oid

    def committing(self):
        original_commit(self)
        if active and stage == "receive-post":
            assert puts >= 3
            barrier()

    transfer.import_commit, d.Transaction.put_record, d.Transaction.commit = (
        importing,
        putting,
        committing,
    )
    ex.receive_observation(caller, packet=packet, expected=h.expected, ref="received")
raise AssertionError("barrier should prevent response")
