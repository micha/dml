"""Private actual-persistence barriers, not installed or runtime controls."""

import json
from pathlib import Path
import subprocess
import sys
import time

import daggerml as d
from daggerml import exchange as ex, local, transfer

path, workspace, expected_file, marker, stage = sys.argv[1:]
values = json.loads(Path(expected_file).read_text(encoding="utf-8"))
for key in ("commit", "binding", "inputs"):
    values[key] = d.ObjectId.from_hex(values[key])
expected = ex.ExchangeSpec(**values)


def barrier():
    Path(marker).write_text("ready", encoding="utf-8")
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        time.sleep(0.02)
    raise TimeoutError("private barrier expired")


if stage == "unknown":
    local._execute = (
        lambda *args: barrier()
    )  # Pre-dispatch committed, no child spawned.
    ex.execute_exchange(workspace)
elif stage == "worker-done":
    original = local.run_step

    def done(*args, **kwargs):
        result = original(
            *args, **kwargs
        )  # Real child reaped and final commit succeeded.
        barrier()
        return result

    local.run_step = done
    ex.execute_exchange(workspace)
elif stage == "caller":
    # Separate real worker process completed/reaped before caller pauses. The
    # cooperative fixture is bounded; no child is running at this barrier.
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from daggerml.exchange import execute_exchange; import sys; execute_exchange(sys.argv[1])",
            workspace,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        check=True,
        timeout=20,
    )
    barrier()  # Explicit receive not invoked.
else:
    original_import, original_put, original_commit = (
        transfer.import_commit,
        d.Transaction.put_record,
        d.Transaction.commit,
    )
    active, puts, new = False, 0, set()

    def importing(repository_path, *args, **kwargs):
        global active, new
        active = Path(repository_path) == Path(path)
        if active:
            rows = json.loads(args[0])["objects"]
            with d.Repository(path) as repo, repo.read() as tx:
                for row in rows:
                    oid = d.ObjectId.from_hex(row["id"])
                    try:
                        tx.get_record(row["kind"], oid)
                    except d.NotFoundError:
                        new.add((row["kind"], oid))
        try:
            return original_import(repository_path, *args, **kwargs)
        finally:
            active = False

    def putting(self, kind, record):
        global puts
        result = original_put(self, kind, record)
        if active and (kind, result) in new:
            puts += 1
            if stage == "receive-pre" and puts == 3:
                barrier()
        return result

    def committing(self):
        original_commit(self)
        if active and stage == "receive-post":
            barrier()

    transfer.import_commit = importing
    d.Transaction.put_record = putting
    d.Transaction.commit = committing
    ex.receive_exchange(path, workspace=workspace, expected=expected, ref="received")
raise AssertionError("barrier should prevent acknowledgement")
