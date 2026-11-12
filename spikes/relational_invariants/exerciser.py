"""Exercise shipped builtin map/get and retain immutable checkpoint roots."""

import argparse
import json
from pathlib import Path

import daggerml as dml
from daggerml import builtin


def exercise(directory, checkpoints=8):
    if checkpoints < 2:
        raise ValueError("at least two checkpoints required")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    repository = directory / "repository"
    roots = []
    with dml.Repository(repository, create=True) as repo:
        with repo.write() as tx:
            key = tx.put_datum("x")
            value = tx.put_datum(42)
            map_value = tx.put_datum(dml.Datum.map(((key, value),)))
            node = tx.put_literal(map_value)
            sources = [tx.put_dag(root=node, bindings={
                "sample": node, "origin": tx.put_literal(tx.put_datum(label)),
            }) for label in ("source-a", "source-b")]
            bindings = [builtin.put_binding(tx, source_uri=f"dml://source/builtin/map/get/v{v}")
                        for v in (1, 2)]
            entries = dict(zip(("source-a", "source-b", "v1", "v2"), (*sources, *bindings)))
            base = tx.put_commit(tx.put_tree(entries))
            tx.create_ref("main", base)
            roots.append(str(base))
        parent = base
        for step in range(checkpoints):
            with repo.write() as tx:
                # The last checkpoint is a fork from base, not from moving main.
                basis = base if step == checkpoints - 1 else parent
                with builtin.Recorder(tx, commit=basis) as recorder:
                    left, right = [recorder.source(source, "sample") for source in sources]
                    key_node = recorder.literal("x")
                    for source in (left, left, right):
                        args = recorder.arguments({"map": source, "key": key_node})
                        recorder.call(builtin.MAP_GET, bindings[step % 2], args)
                    trace = recorder.trace()
                commit = tx.put_commit(tx.put_tree({**entries, "trace": trace}), parents=(basis,))
                if step == checkpoints - 1:
                    tx.create_ref("fork", commit)
                else:
                    tx.update_ref("main", commit)
                    parent = commit
                roots.append(str(commit))
    manifest = {"repository": str(repository.resolve()), "roots": roots,
                "checkpoints": checkpoints, "expected_trace_positions": 3,
                "note": "actual internal builtins; no ordinary requests/attempts or OS launches"}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--checkpoints", type=int, default=8)
    args = parser.parse_args()
    print(json.dumps(exercise(args.directory, args.checkpoints), indent=2))
