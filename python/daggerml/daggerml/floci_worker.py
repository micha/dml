"""Fixed installed Floci job program; owns/reaps one public local WorkerLaunch.

The loop is job execution machinery, not a polling observer/supervisor service.
Catchable errors retain process ownership; hard loss has no cleanup/B-retention promise.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import time

from . import exchange
from . import floci
from . import floci_http as http


def _inputs(remote, token, commit):
    budget = http.Budget(30000, 3)
    raw = http.get_object(
        remote, budget, token, "input/manifest.json", http.DESCRIPTOR_BYTES
    )
    if raw is None:
        raise http.FlociError("staged input manifest unavailable")
    manifest = floci._read_input_manifest(raw, token, commit)
    files = http.fetch_files(remote, budget, token, "input", manifest["files"])
    expected = http.owned_spec(files[0][1])
    if (
        expected.token != token
        or str(expected.commit) != commit
        or str(expected.request) != manifest["request"]
    ):
        raise http.FlociError("downloaded public job differs from staged selection")
    # Retain job-local B/workspace on every catchable failure. Floci's outer
    # container retirement can nevertheless erase all unpublished local history.
    workspace = Path(tempfile.mkdtemp(prefix="dml-floci-execution-"))
    for name, data in reversed(files):
        with open(workspace / name, "xb") as stream:
            stream.write(data)
    return exchange.ExchangeHandle(workspace, expected)


def _closed_packet(handle):
    with tempfile.TemporaryDirectory(prefix="dml-floci-publish-") as temporary:
        packet = Path(temporary) / "packet"
        observation = exchange.observe_exchange(handle, packet=packet)
        if observation.packet is None:
            return None
        files = tuple(
            (name, http.read_file(packet / name, http.limit(name)))
            for name in http.PACKET_FILES
        )
        snapshot = exchange.read_observation(packet, expected=handle.expected)
    # No successful publication with live validation handles or owned packet scratch.
    return snapshot, files


def _publish(job, handle):
    selected = _closed_packet(handle)
    if selected is None:
        return False
    snapshot, files = selected
    manifest = floci._phase_manifest(job, snapshot.phase, snapshot, files)
    budget = http.Budget(30000, 8)
    for name, data in files:
        http.put_object(
            job.remote,
            budget,
            job.expected.token,
            "snapshots/" + str(snapshot.commit) + "/" + name,
            data,
            same=True,
        )
    http.put_object(
        job.remote,
        budget,
        job.expected.token,
        "phases/" + snapshot.phase + ".json",
        manifest,
        same=True,
    )
    return snapshot.lifecycle == "done"


class FlociWorkerError(http.FlociError):
    """Known direct-worker disposition with retained owner/error diagnostics."""

    def __init__(self, launch, primary, reap_error, final_error):
        self.launch = launch
        self.primary_error = primary
        self.reap_error = reap_error
        self.final_error = final_error
        super().__init__("Floci publisher failed after owned worker disposition")


def _reap(launch):
    # Uncertain wait retains owner indefinitely for investigation, without kill.
    # Emit at most one fixed diagnostic; do not grow an unbounded retry log.
    reported = False
    secondary = None
    while True:
        try:
            launch.wait(timeout=1)
            return secondary
        except BaseException as error:
            if launch.process.returncode is not None:
                # Known reap: do not retry permanent stream-close failure. Retain
                # the first secondary error (or this close error) with the owner.
                return secondary if secondary is not None else error
            if not reported:
                # Set BEFORE IO: even broken stderr cannot cause an unbounded
                # diagnostic retry, nor escape while the owner remains uncertain.
                reported = True
                try:
                    print(
                        "Floci worker wait disposition pending",
                        file=sys.stderr,
                        flush=True,
                    )
                except BaseException as diagnostic_error:
                    secondary = diagnostic_error
            try:
                time.sleep(0.2)
            except BaseException as sleep_error:
                if secondary is None:
                    secondary = sleep_error


def _finish(job, handle, launch):
    reap_error = _reap(launch)
    try:
        if not _publish(job, handle):
            raise http.FlociError("local worker exited without retrievable recorded F")
    except BaseException as final_error:
        return reap_error, final_error
    return reap_error, None


def run(
    remote: floci.FlociRemote, token: str, commit: str, *, job_id: str, attempt: str
) -> None:
    """Download once, start once; never repair/finalize/reexecute missing history."""
    http.hex_id(token)
    http.hex_id(commit)
    http.job_id(job_id)
    if type(attempt) is not str or attempt != "1":
        raise http.FlociError("Floci installed worker requires service attempt1")
    handle = _inputs(remote, token, commit)
    job = floci.FlociJob(remote, handle.expected, handle.workspace, job_id)
    launch = exchange.start_exchange(handle)
    primary = None
    try:
        while launch.process.poll() is None:
            _publish(job, handle)
            time.sleep(0.1)
    except BaseException as error:
        primary = error
    finally:
        # Unconditional reap AND final read-only publication even on earlier
        # poll/inspection/publication failure. No finalization/repair/reexecution.
        reap_error, final_error = _finish(job, handle, launch)
    if primary is not None or reap_error is not None or final_error is not None:
        raise FlociWorkerError(launch, primary, reap_error, final_error) from (
            primary or reap_error or final_error
        )


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != 3:
        print(
            "Floci worker requires fixed operational config/token/commit",
            file=sys.stderr,
        )
        return 2
    try:
        remote = floci._remote(http.document(args[0].encode("utf-8")))
        run(
            remote,
            args[1],
            args[2],
            job_id=os.environ.get("AWS_BATCH_JOB_ID"),
            attempt=os.environ.get("AWS_BATCH_JOB_ATTEMPT"),
        )
    except Exception as error:
        print("Floci worker failed: " + type(error).__name__, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
