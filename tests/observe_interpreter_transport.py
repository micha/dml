"""Expose the actual evidence encoder's source and the input after the call."""

import json
import sys

from run_histories import quint_evidence


if __name__ == "__main__":
    request = json.load(sys.stdin)
    observations = request["observations"]
    try:
        source = quint_evidence(observations, attempt_defaults=request.get("attemptDefaults"),
                                intern_refs=request.get("internRefs", False))
    except ValueError as error:
        raise SystemExit(str(error)) from error
    json.dump(dict(source=source, observations=observations), sys.stdout)
