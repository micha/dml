"""Audit graph identity across the transaction profile's bounded recipe set."""

import argparse
from collections import Counter
from itertools import product
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import generated_transactions as generated

from transaction_graph import load_batch, save_batch


EXPECTED_MATCHES = {"commitClean": 45, "commitPoisoned": 210, "continuity": 510,
                    "explicitAbort": 255, "freshMarker": 510, "stepEffects": 504}


def audit(reverse: bool) -> dict:
    operations = tuple(product(generated.OPERATIONS, generated.TARGETS))
    recipes = [
        (initial, requests, finish)
        for length in range(generated.MAX_STEPS + 1)
        for requests in product(operations, repeat=length)
        for initial in (None, *generated.TARGETS)
        for finish in generated.FINISHES
    ]
    assert len(recipes) == 510, len(recipes)
    if reverse:
        recipes.reverse()
    records = {}
    roots = set()
    counts = Counter()
    for initial, requests, finish in recipes:
        recipe = (initial, requests, finish)
        live = generated.execute(initial, requests, finish)
        verdicts = generated.check(initial, requests, finish, live)
        with TemporaryDirectory(prefix="quint-graph-audit-") as workspace:
            path = Path(workspace) / "evidence"
            root = save_batch(path, live)
            reopened = load_batch(path, root, initial=initial, requests=requests, finish=finish)
        assert reopened == live, recipe
        assert generated.check(initial, requests, finish, reopened) == verdicts, recipe
        counts.update(verdicts)
        assert root not in roots, recipe
        roots.add(root)
        records[json.dumps(recipe)] = str(root)

    generated.require_witnesses(counts)
    matches = {rule: counts[rule, "pass"] for rule in generated.RULE_IDS}
    assert matches == EXPECTED_MATCHES, matches
    return {"roots": records, "matches": matches}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reverse", action="store_true", help="Audit recipes in reverse traversal order")
    args = parser.parse_args()
    if not __debug__:
        parser.error("Run without Python optimizations to keep the evidence checks enabled")
    print(json.dumps(audit(args.reverse), sort_keys=True))


if __name__ == "__main__":
    main()
