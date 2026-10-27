"""Record composition, not DML execution or proof of computational causality.

Run with a fresh repository path whose parent exists. JSON contains snapshot IDs
and historical bytes for inspection from another process.
"""
import argparse
import json

import daggerml as dml


def literal(tx, value):
    return tx.put_literal(tx.put_datum(value))


def trial(tx, left, right):
    result = left + right  # Python computes; DML records values and structure.
    nodes = {name: literal(tx, value) for name, value in (
        ("left", left), ("right", right), ("result", result)
    )}
    return tx.put_dag(root=nodes["result"], bindings=nodes), result


def comparison(tx, a_node, b_node, a_value, b_value):
    summary = literal(tx, f"A={a_value}; B={b_value}")
    return tx.put_dag(root=summary, bindings={
        "trial-a": a_node, "trial-b": b_node, "summary": summary,
    })


def produce(path):
    saved = {}
    with dml.Repository(path, create=True) as repo:
        with repo.write() as tx:
            a, av = trial(tx, 2, 3)
            b, bv = trial(tx, 2, 4)
            an = tx.put_subdag(a)
            bn = tx.put_subdag(b)
            first = comparison(tx, an, bn, av, bv)
            nested = tx.put_dag(root=an)
            tree = tx.put_tree({"comparison": first, "nested-root": nested})
            c1 = tx.put_commit(tree)
            tx.create_ref("main", c1)
            for kind, object_id in (("dag", a), ("dag", b), ("node", an),
                                    ("node", bn), ("dag", first), ("dag", nested),
                                    ("tree", tree), ("commit", c1)):
                saved[f"{kind}:{object_id}"] = tx.get_record(kind, object_id).hex()
        with repo.write() as tx:
            b2, bv2 = trial(tx, 2, 5)
            bn2 = tx.put_subdag(b2)
            second = comparison(tx, an, bn2, av, bv2)
            tree2 = tx.put_tree({"comparison": second, "nested-root": nested})
            c2 = tx.put_commit(tree2, parents=(c1,))
            tx.update_ref("main", c2)
    return {"c1": str(c1), "c2": str(c2), "comparison1": str(first),
            "comparison2": str(second), "a": str(a), "b": str(b), "b2": str(b2),
            "a_node": str(an), "nested": str(nested), "saved": saved}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository")
    print(json.dumps(produce(parser.parse_args().repository), sort_keys=True))
