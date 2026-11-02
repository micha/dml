"""Capture standalone trusted wrapper/support; no uninstalled child imports.

Compilation retains actual owning source filenames for host coverage. Captured
bytes are supplied explicitly, not re-read from those paths by the child.
"""

from pathlib import Path

MODULES = ("explicit_reuse", "reuse_selection", "recorded_maps", "argument_map_funcs")


def capture(func, *, directory=None):
    if func not in ("add", "double"):
        raise ValueError("fixed example supports only add/double")
    directory = Path(__file__).resolve().parent if directory is None else Path(directory)
    sources = tuple((module, str(directory / (module + ".py")), (directory / (module + ".py")).read_bytes()) for module in MODULES)
    prefix = b"import sys, types\n"
    for module, filename, source in sources:
        prefix += ("_module = types.ModuleType(%r)\n_module.__file__ = %r\nsys.modules[%r] = _module\nexec(compile(%r, %r, 'exec'), _module.__dict__)\n" % (module, filename, module, source, filename)).encode("utf-8")
    wrapper = ("from daggerml.local import child_context\nimport recorded_maps, argument_map_funcs\nrecorded_maps.publish_callable(child_context(), argument_map_funcs.%s)\n" % func).encode("ascii")
    return prefix + wrapper
