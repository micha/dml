"""DaggerML Python bindings package skeleton."""

__all__ = ["version"]


def version() -> str:
  from . import _core

  return _core.dml_version()
