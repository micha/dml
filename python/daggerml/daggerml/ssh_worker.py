"""Fixed installed SSH helper: stage, execute or fetch; never arbitrary commands."""

from __future__ import annotations

from pathlib import Path
import sys

from . import exchange, transfer
from .ssh import (
    SSHError,
    _eof,
    _expected,
    _owned_spec,
    _posix_path,
    _read_file,
    _read_frame,
    _write_frame,
)


def serve(action: str, workspace, stdin, stdout) -> None:
    """One fixed transport action; all streams are binary and caller-owned."""
    workspace = Path(_posix_path(str(workspace)))
    if action == "stage":
        descriptor, bundle = _read_frame(stdin, "stage")
        _expected(_owned_spec(descriptor))
        workspace.mkdir()
        for name, data in (("input.bundle", bundle), ("job.json", descriptor)):
            with open(workspace / name, "xb") as stream:
                stream.write(data)
        _write_frame(stdout, "ack", ())
    elif action == "execute":
        _eof(stdin)
        _expected(exchange.read_exchange_spec(workspace))
        exchange.execute_exchange(workspace)
    elif action == "fetch":
        _eof(stdin)
        descriptor = _read_file(workspace / "job.json", exchange.MAX_DESCRIPTOR_BYTES)
        _expected(_owned_spec(descriptor))
        completion = _read_file(
            workspace / "completion.json", exchange.MAX_DESCRIPTOR_BYTES
        )
        bundle = _read_file(workspace / "output.bundle", transfer.MAX_BUNDLE_BYTES)
        _write_frame(stdout, "fetch", (descriptor, completion, bundle))
    else:
        raise SSHError("unsupported SSH helper action")
    stdout.flush()


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != 2:
        print("SSH helper requires a fixed action and workspace", file=sys.stderr)
        return 2
    try:
        serve(args[0], args[1], sys.stdin.buffer, sys.stdout.buffer)
    except Exception as error:
        # No incoming payload, credential values, traceback or outcome inference.
        print("SSH helper failed: " + type(error).__name__, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
