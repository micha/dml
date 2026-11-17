"""Python-only regressions for `nix flake check`; never import the DML extension."""

from dataclasses import dataclass
from pathlib import Path
import sys


@dataclass(frozen=True)
class ObjectId:
    value: bytes


# These independently reproduce both CPython string-scanner report contexts in
# the pinned GCC-built ARM64 interpreter without the loop-vectorization workaround.
assert ObjectId(b"probe").value == b"probe"
assert str(Path("/a/long/enough/path")) == "/a/long/enough/path"
assert not any(name == "daggerml" or name.startswith("daggerml.") for name in sys.modules)
print("Python-only Valgrind runtime checks passed")
