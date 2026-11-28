"""Public core helpers used by the argument-map workflow replay adapters."""

from contextlib import contextmanager

from daggerml import core


@contextmanager
def transaction(path, mode=core.TXN_READ, *, create=False):
    repo = core.repo_open(path, create)
    try:
        txn = core.txn_begin(repo, mode)
        try:
            yield txn
        finally:
            core.txn_abort(txn)
    finally:
        core.repo_close(repo)


def put(txn, kind, *operands):
    return core.txn_put_object(txn, kind, core.object_encode(kind, *operands))


def literal(txn, kind, value):
    datum = core.txn_put_datum(txn, core.datum_encode(kind, value))
    return put(txn, core.REC_NODE, core.NODE_LITERAL, datum)


def view(txn, kind, object_id):
    return core.object_decode(core.txn_get_object(txn, kind, object_id))
