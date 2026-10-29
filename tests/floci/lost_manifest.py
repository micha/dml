"""PRIVATE actual-S3 committed phase response suppression, outside installed package.

Drops one already committed initial-manifest acknowledgement; unchanged worker must
retain/reap, then make its final read-only publication. Not physical network loss.
"""

from daggerml import floci_http as h
import retain

original = h.request


def suppressed(*args, **kwargs):
    result = original(*args, **kwargs)
    if (
        args[2] == "PUT"
        and args[3].endswith("/phases/initial.json")
        and result[0] == 200
    ):
        h.request = original
        raise h.FlociError("private committed-manifest response suppression")
    return result


if __name__ == "__main__":
    h.request = suppressed
    raise SystemExit(retain.main())
