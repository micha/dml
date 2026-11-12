"""Compare actual existing inspection work with unique extraction; never dispatch."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
import weakref

from run import ROOT, bootstrap


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def measure(repository, requests, scratch):
    import daggerml as dml
    from daggerml import builtin, transfer
    sys.path.insert(0, str(ROOT / "examples"))
    import composed_node_calls as calls

    repository = Path(repository).resolve()
    reads, refs, exports, scans = Counter(), Counter(), Counter(), Counter()
    owners = weakref.WeakKeyDictionary()
    original_init = dml.Repository.__init__
    original_write = dml.Repository.write
    original_get = dml.Transaction.get_record
    original_ref = dml.Transaction.get_ref
    original_export = transfer.export_commit
    original_scan = builtin._retained

    def repo_init(owner, path, **kwargs):
        path = Path(path).resolve()
        if path != repository and not path.is_relative_to(scratch):
            raise AssertionError("unexpected repository outside spike scratch")
        if path == repository and kwargs.get("create", False):
            raise AssertionError("cannot create original retained repository")
        original_init(owner, path, **kwargs)
        owners[owner] = path

    def write(owner):
        if owners[owner] == repository:
            raise AssertionError("cannot write original retained repository")
        return original_write(owner)

    def get(tx, kind, oid):
        reads[(kind, str(oid))] += 1
        return original_get(tx, kind, oid)

    def ref(tx, name):
        refs[name] += 1
        return original_ref(tx, name)

    def export(path, *, commit):
        exports[str(commit)] += 1
        return original_export(path, commit=commit)

    def scan(tx, commit):
        scans[str(commit)] += 1
        return original_scan(tx, commit)

    def forbidden(*args, **kwargs):
        raise AssertionError("inspection attempted process launch or network IO")

    started = time.perf_counter()
    answers = []
    with patch.object(dml.Repository, "__init__", repo_init), \
         patch.object(dml.Repository, "write", write), \
         patch.object(dml.Transaction, "get_record", get), \
         patch.object(dml.Transaction, "get_ref", ref), \
         patch.object(transfer, "export_commit", export), \
         patch.object(builtin, "_retained", scan), \
         patch.object(subprocess, "Popen", forbidden), \
         patch.object(socket.socket, "connect", forbidden), \
         patch.object(socket, "create_connection", forbidden), \
         patch.object(tempfile, "tempdir", str(scratch)):
        for request in requests:
            decision = calls.inspect_request(
                repository, commit=dml.ObjectId.from_hex(request["commit"]),
                request=dml.ObjectId.from_hex(request["request"]),
                decision_name=request["decision"],
                satisfaction_commit=dml.ObjectId.from_hex(request["satisfaction"]),
            )
            selected = decision.selected.selected
            answers.append({"number": request["number"], "action": decision.action,
                            "requested_inputs": str(decision.inputs.dag),
                            "requested_value": str(decision.inputs.datum),
                            "selected_request": str(selected.request), "selected_attempt": str(selected.attempt),
                            "selected_result": str(selected.result), "selected_inputs": str(selected.inputs)})
    return {"seconds_instrumented": time.perf_counter() - started,
            "record_reads": sum(reads.values()), "unique_typed_ids_read": len(reads),
            "ref_reads": sum(refs.values()), "exports": sum(exports.values()),
            "distinct_export_roots": len(exports), "retained_scans": sum(scans.values()),
            "distinct_scan_roots": len(scans), "answers": answers,
            "record_counts": [{"kind": k, "oid": oid, "reads": count}
                              for (k, oid), count in sorted(reads.items())],
            "exports_by_root": dict(exports), "scans_by_root": dict(scans)}


def compare(story, output):
    bootstrap()
    from normalizer import normalize
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    scratch = output / "scratch"
    scratch.mkdir()
    story = Path(story).resolve()
    receipt_path = story / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    repository = story / "replica.dml"
    datafile = repository / "data.mdb"
    before = digest(datafile)
    requests = [row for row in receipt["requests"] if row["number"] in (4, 6)]
    assert len(requests) == 2 and all(row["action"] == "reuse-selected" for row in requests)
    # Current inspection helpers must match the originally executed/retained helper bytes.
    helper_hashes = {name: digest(ROOT / "examples" / name) for name in
                     ("composed_node_calls.py", "composed_node_funcs.py", "reuse_selection.py", "explicit_reuse.py")}
    assert all(receipt["sources"][name] == value for name, value in helper_hashes.items())
    provenance = {"story": str(story), "repository": str(repository),
                  "receipt_sha256": digest(receipt_path), "data_sha256_before": before,
                  "helper_sha256": helper_hashes,
                  "scope": "two retained requests4/6; no fresh computation; scratch validation allowed"}
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    try:
        baseline = measure(repository, requests, scratch)
        (output / "baseline.json").write_text(json.dumps(baseline, indent=2) + "\n")
        roots = [identity for request in requests for identity in (request["commit"], request["satisfaction"])]
        manifest = {"repository": str(repository), "roots": roots,
                    "note": "retained real request/reuse prefix, not builtin synthetic checkpoints"}
        manifest_path = output / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        database, normalized = normalize(manifest_path, output / "normalized")
        (output / "request-contexts.json").write_text(json.dumps(requests, indent=2) + "\n")
        summary = {"baseline": {key: value for key, value in baseline.items()
                                if key not in ("record_counts", "exports_by_root", "scans_by_root")},
                   "normalizer": normalized, "database": str(database)}
        (output / "comparison.json").write_text(json.dumps(summary, indent=2) + "\n")
        return summary
    except Exception as error:
        (output / "failure.txt").write_text(repr(error) + "\n")
        raise
    finally:
        after = digest(datafile)
        (output / "data-after.json").write_text(json.dumps({"sha256": after, "unchanged": before == after}) + "\n")
        assert before == after, "original immutable repository changed"


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: compare_history.py RETAINED_STORY_DIRECTORY NEW_OUTPUT_DIRECTORY")
    print(json.dumps(compare(sys.argv[1], sys.argv[2]), indent=2))
