"""PRIVATE finite remote barriers; copied by acceptance fixture, never installed.

Before computational spawn, after actual child reaping (before F), or after closed
files. A gate is released by the fixture after client loss; no live child is killed.
"""

import io
from pathlib import Path
import sys
import time

from daggerml import exchange, local, ssh_worker

phase, workspace = sys.argv[1:]
workspace = Path(workspace)


def barrier(*args, **kwargs):
    (workspace / "private-barrier").write_text(phase)
    deadline = time.monotonic() + 20
    while not (workspace / "private-release").exists():
        if time.monotonic() >= deadline:
            raise RuntimeError("private cooperative barrier watchdog expired")
        time.sleep(0.01)
    raise SystemExit(75)


if phase == "stage":
    ssh_worker.serve("stage", workspace, sys.stdin.buffer, io.BytesIO())
    barrier()
elif phase == "fetch":
    response = io.BytesIO()
    ssh_worker.serve("fetch", workspace, sys.stdin.buffer, response)
    sys.stdout.buffer.write(response.getvalue()[:10])
    sys.stdout.buffer.flush()
    barrier()
else:
    if phase == "pre-child":
        local._execute = barrier
    elif phase == "reaped-pre-f":
        local._finalize = barrier
    elif phase != "post-files":
        raise ValueError("unsupported private phase")
    exchange.execute_exchange(workspace)
    barrier()
