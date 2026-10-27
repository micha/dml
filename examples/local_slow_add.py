"""Trusted cooperative example gates around ordinary durable result publication."""

import time
from pathlib import Path

from daggerml import Repository
from daggerml.local import child_context, publish_result


def gate(directory, phase):
    deadline = time.monotonic() + 15
    while not (directory / (phase + "-release")).exists():
        if time.monotonic() >= deadline:
            raise TimeoutError("finite example gate expired")
        time.sleep(0.02)


def main():
    context = child_context()
    with Repository(context.repository_path) as repo, repo.read() as tx:
        node = tx.get_node(tx.lookup_node(context.inputs, "gate"))
        directory = Path(tx.get_datum(node.datum).value)
    gate(directory, "initial")
    with Repository(context.repository_path) as repo, repo.write() as tx:
        values = []
        for name in ("left", "right"):
            node = tx.get_node(tx.lookup_node(context.inputs, name))
            datum = tx.get_datum(node.datum)
            if datum.kind != "i64":
                raise ValueError("addition requires named I64 inputs")
            values.append(datum.value)
        result = tx.put_literal(tx.put_datum(sum(values)))
        publish_result(
            tx, context, tx.put_dag(root=result, bindings={"result": result})
        )
    gate(directory, "publication")  # U is provisional while the child remains live.


if __name__ == "__main__":
    main()
