"""Informative local recorded execution story; run with an installed current runtime."""
import argparse
import json
from pathlib import Path
import sys

import daggerml as dml
from daggerml.local import put_local_binding, retry_step, run_step


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository")
    args = parser.parse_args()
    path = Path(args.repository).absolute()
    source = Path(__file__).with_name("local_add.py").read_bytes()
    with dml.Repository(path, create=True) as repo, repo.write() as tx:
        left = tx.put_literal(tx.put_datum(4))
        right = tx.put_literal(tx.put_datum(7))
        inputs = tx.put_dag(root=left, bindings={"left": left, "right": right})
        binding = put_local_binding(tx, source=source, interpreter=sys.executable, timeout_ms=10000)
        commit = tx.put_commit(tx.put_tree({"inputs": inputs, "binding": binding}))
        tx.create_ref("main", commit)
    runs = [run_step(path, head_ref="main", intent_uri="urn:example:add-i64", binding=binding,
                     inputs=inputs) for _ in range(2)]
    assert runs[0].attempt_id != runs[1].attempt_id
    assert runs[0].request_id != runs[1].request_id
    assert runs[0].result == runs[1].result
    with dml.Repository(path) as repo, repo.write() as tx:
        failing = put_local_binding(tx, source=b"raise RuntimeError('intentional failure')\n",
                                    interpreter=sys.executable, timeout_ms=10000)
    failed = run_step(path, head_ref="main", intent_uri="urn:example:failure", binding=failing, inputs=inputs)
    assert failed.outcome == "failure"
    # An explicit retry demonstrates a new attempt with exactly the recorded binding.
    retried = retry_step(path, head_ref="main", request=runs[0].context.request)
    assert retried.request_id == runs[0].request_id and retried.attempt_id != runs[0].attempt_id
    print(json.dumps({"repository": str(path), "result": str(runs[0].result),
                      "attempts": [run.attempt_id for run in runs + [failed, retried]],
                      "pre_dispatch": str(runs[0].context.pre_dispatch),
                      "request": str(runs[0].context.request),
                      "final_attempt": str(runs[0].final_attempt), "final": str(retried.final_commit)}))


if __name__ == "__main__":
    main()
