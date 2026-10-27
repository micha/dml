"""Create two immutable snapshots and a fork, then print IDs for CLI inspection.

Run against installed packages: python examples/repository_history.py NEW_REPO_PATH
The parent directory must already exist. Use fresh scratch, not research data.
"""

import json
import sys

import daggerml as dml


def record_snapshot(tx, value, parents=()):
    datum = tx.put_datum(value)
    node = tx.put_literal(datum)
    dag = tx.put_dag(root=node)
    tree = tx.put_tree({"example": dag})
    commit = tx.put_commit(tree, parents=parents)
    return {"datum": datum, "node": node, "dag": dag, "tree": tree, "commit": commit}


def main(path):
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            first = record_snapshot(tx, 42)
            tx.create_ref("main", first["commit"])
            frozen = {kind: tx.get_record(kind, identity).hex() for kind, identity in first.items()}
        with repo.write() as tx:
            second = record_snapshot(tx, 43, [first["commit"]])
            tx.update_ref("main", second["commit"])
            third = record_snapshot(tx, 44, [first["commit"]])
            tx.create_ref("branch", third["commit"])
        with repo.read() as tx:
            for kind, identity in first.items():
                assert tx.get_record(kind, identity).hex() == frozen[kind]
            assert tx.get_datum(second["datum"]).value == 43
    print(json.dumps({"first": {kind: str(identity) for kind, identity in first.items()},
                      "second": {kind: str(identity) for kind, identity in second.items()},
                      "third": {kind: str(identity) for kind, identity in third.items()},
                      "first_records": frozen}, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1])
