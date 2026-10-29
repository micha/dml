"""PRIVATE fixture ENTRYPOINT: finite hold ONLY AFTER unchanged installed worker returns.

Not packaged/imported by normal DML. Never signals/cancels a computational process.
Normal worker and this outer lifetime substitution are separately attributed evidence.
"""

import json
import os
from pathlib import Path
import sys
import time

from daggerml import exchange as ex, floci as f, floci_http as h, floci_worker as worker


def main():
    args = sys.argv[1:]
    assert (
        args[:3] == ["/opt/dml/bin/python", "-m", "daggerml.floci_worker"]
        and len(args) == 6
    )
    remote = f._remote(h.document(args[3].encode()))
    token, commit = args[4:]
    code = worker.main(args[3:])
    # run owns/reaps throughout catchable errors. An uncertain wait never returns
    # from installed main; this barrier cannot sacrifice a live computational child.
    workspaces = [
        path.parent
        for path in Path("/tmp").glob("dml-floci-execution-*/job.json")
        if ex.read_exchange_spec(path.parent).token == token
    ]
    assert len(workspaces) == 1
    marker = h.encoded(
        dict(
            job_id=os.environ["AWS_BATCH_JOB_ID"],
            token=token,
            commit=commit,
            worker_exit=code,
            workspace=str(workspaces[0]),
            private_after_reap=True,
        )
    )
    h.put_object(remote, h.Budget(10000, 1), token, "fixture/after-reap.json", marker)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if (
            h.get_object(remote, h.Budget(5000, 1), token, "fixture/release", 8192)
            is not None
        ):
            return 75
        time.sleep(0.15)
    return 76  # Finite private outer hold expiry, not a computational outcome.


if __name__ == "__main__":
    raise SystemExit(main())
