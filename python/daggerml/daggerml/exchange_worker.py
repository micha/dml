"""Fixed installed one-shot worker. No caller commands or A path in this protocol."""

import sys

from .exchange import execute_exchange


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise SystemExit("usage: python -m daggerml.exchange_worker WORKSPACE")
    execute_exchange(args[0])


if __name__ == "__main__":
    main()
