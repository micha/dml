"""Locate test extensions without confusing linker artifacts with Python modules."""

import importlib.machinery
from pathlib import Path


def native_extension_path(build: Path, name: str) -> Path:
    candidates = {path.name: path for path in build.glob(name + ".*") if path.is_file()}
    for suffix in importlib.machinery.EXTENSION_SUFFIXES:
        candidate = candidates.get(name + suffix)
        if candidate is not None:
            return candidate
    raise FileNotFoundError(f"native test extension {name!r} is missing from {build}")
