"""Reuse ONLY successful frozen fixture seeds within this pytest worker/session.

Imported fixture functions have separate pytest FixtureDefs. A config-owned stash
shares their immutable seed, not mutable case repositories or live native handles.
"""

from functools import wraps

import pytest


def worker_seed(builder):
    key = pytest.StashKey()

    @wraps(builder)
    def cached(*args, **kwargs):
        config = kwargs["pytestconfig"]
        if key not in config.stash:
            # Exceptions never publish a partially constructed seed.
            config.stash[key] = builder(*args, **kwargs)
        return config.stash[key]

    return cached
