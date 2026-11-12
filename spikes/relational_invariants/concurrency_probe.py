"""Finite event-synchronized normalizer/checker overlap on retained facts."""

import json
from pathlib import Path
from queue import Queue
import sys
from threading import Event, Thread

import duckdb

from embedded import check_snapshot, collected_batches, connect, initialize, publish, snapshot


def await_event(event):
    if not event.wait(10):
        raise TimeoutError("concurrency probe barrier did not complete")


def probe(evidence, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    database = output / "facts.duckdb"
    first, second = collected_batches(evidence)
    initialize(database)
    with connect(database) as conn:
        assert publish(conn, first)
        original = check_snapshot(conn)
    assert original["contexts"] == 1 and not original["violations"]
    staged, proceed, marker, commit, done = (Event() for _ in range(5))
    errors = Queue()
    observations = {"initial": original}

    def writer():
        try:
            with connect(database) as conn:
                def hook(table, connection):
                    if table == "objects":
                        staged.set()
                        await_event(proceed)
                    if table == "marker":
                        marker.set()
                        await_event(commit)
                assert publish(conn, second, hook)
        except BaseException as error:
            errors.put(error)
            # Wake the controller on failure too; it checks errors BEFORE treating
            # either barrier as successful readiness, preserving the root exception.
            staged.set()
            marker.set()
        finally:
            done.set()

    thread = Thread(target=writer, name="spike-normalizer")
    try:
        with connect(database) as reader, connect(database) as observer:
            reader.execute("BEGIN;")
            assert snapshot(reader) == original
            thread.start()
            await_event(staged)
            if not errors.empty():
                raise errors.get()
            observations["partial_facts_uncommitted"] = check_snapshot(observer)
            assert observations["partial_facts_uncommitted"] == original
            proceed.set()
            await_event(marker)
            if not errors.empty():
                raise errors.get()
            observations["complete_batch_and_marker_uncommitted"] = check_snapshot(observer)
            assert observations["complete_batch_and_marker_uncommitted"] == original
            commit.set()
            await_event(done)
            if not errors.empty():
                raise errors.get()
            observations["reader_snapshot_after_writer_commit"] = snapshot(reader)
            assert observations["reader_snapshot_after_writer_commit"] == original
            reader.execute("COMMIT;")
            observations["fresh_reader_after_commit"] = check_snapshot(reader)
            fresh = observations["fresh_reader_after_commit"]
            assert fresh["batches"] == [first.name, second.name]
            assert fresh["objects"] == 473 and fresh["contexts"] == 2 and fresh["roots"] == 4
            assert fresh["violations"] == []
    except BaseException as error:
        (output / "failure.txt").write_text(repr(error) + "\n")
        raise
    finally:
        proceed.set()
        commit.set()
        if thread.ident is not None:
            thread.join(20)
            if thread.is_alive():
                raise RuntimeError("spike writer did not join; stop and investigate")
    # All prior connections are closed before reopening the owned database.
    with connect(database) as reopened:
        observations["reopened_after_clean_close"] = check_snapshot(reopened)
    assert observations["reopened_after_clean_close"] == fresh
    assert "daggerml" not in sys.modules
    result = {"duckdb_version": duckdb.__version__, "writer_joined": not thread.is_alive(),
              "dml_imported": False, "observations": observations,
              "qualification": "same-process connections; graceful reopen, not crash/power-loss proof"}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: concurrency_probe.py COLLECTED_EVIDENCE NEW_OUTPUT_DIRECTORY")
    print(json.dumps(probe(sys.argv[1], sys.argv[2]), indent=2))
