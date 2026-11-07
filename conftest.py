"""Load resource-aware test hooks before xdist creates its workers."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "tests"))
pytest_plugins = ["parallel_validation"]
