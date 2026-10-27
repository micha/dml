"""Load Python sources against this checkout's freshly built native extension."""

import importlib.util
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = Path(os.environ.get("DML_BIN", ROOT / "build/check/dml")).resolve().parent
PACKAGE = ROOT / "python/daggerml/daggerml"
spec = importlib.util.spec_from_file_location(
    "daggerml", PACKAGE / "__init__.py",
    submodule_search_locations=[str(PACKAGE), str(BUILD)],
)
module = importlib.util.module_from_spec(spec)
sys.modules["daggerml"] = module
spec.loader.exec_module(module)
sys.path.insert(0, str(ROOT / "python/daggerml-cli"))
