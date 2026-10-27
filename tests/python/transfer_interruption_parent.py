"""Private deterministic barriers around actual storage commit; never installed."""

from pathlib import Path
import sys
import time

from daggerml import Transaction
from daggerml.transfer import import_commit

path, bundle, marker, stage = sys.argv[1:]
original_put = Transaction.put_record
original_commit = Transaction.commit
puts = 0


def barrier():
    Path(marker).write_text("ready", encoding="utf-8")
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        time.sleep(0.02)
    raise TimeoutError("private barrier deadline expired")


def put(self, kind, record):
    global puts
    result = original_put(self, kind, record)
    puts += 1
    if stage == "pre" and puts == 3:
        barrier()
    return result


def commit(self):
    original_commit(self)
    if stage == "post":
        barrier()


Transaction.put_record = put
Transaction.commit = commit
import_commit(path, Path(bundle).read_bytes(), ref="received")
raise AssertionError("barrier should prevent acknowledgement")
