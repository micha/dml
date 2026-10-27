"""Forward to the native executable bundled in daggerml, never to PATH's dml."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import subprocess
import sys


def main() -> int:
    daggerml = importlib.import_module("daggerml")
    executable = Path(daggerml.__file__).resolve().parent / "_bin" / ("dml.exe" if os.name == "nt" else "dml")
    try:
        result = subprocess.run([str(executable), *sys.argv[1:]], check=False)
    except OSError as error:
        print(f"dml: cannot run bundled native executable: {error}", file=sys.stderr)
        return 1
    return result.returncode if result.returncode >= 0 else 128 - result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
