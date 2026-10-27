#!/usr/bin/env bash
set -euo pipefail

# Keep editor builds separate from coverage/mutation builds. The Python binding
# is a separate Meson project, so a symlink to the core database is not enough.
root_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  echo "Usage: scripts/setup-lsp.sh"
  echo "Configure both Meson projects and generate compile_commands.json for clangd."
  exit 0
fi
if [ "$#" -ne 0 ]; then
  echo "error: unexpected arguments; use scripts/setup-lsp.sh --help" >&2
  exit 1
fi

for command in meson ninja python3; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "error: $command is required; run this script in your build environment" >&2
    exit 1
  fi
done

configure() {
  local source_dir="$1"
  local build_dir="$2"
  if [ -f "$build_dir/meson-private/coredata.dat" ]; then
    meson setup --reconfigure "$build_dir" "$source_dir"
  else
    meson setup "$build_dir" "$source_dir"
  fi
}

configure "$root_dir" "$root_dir/build/editor"
configure "$root_dir/python/daggerml" "$root_dir/build/editor-python"

python3 - "$root_dir" <<'PY'
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

root = Path(sys.argv[1])
commands = []
system_flags = {}

for build in ("editor", "editor-python"):
    database = root / "build" / build / "compile_commands.json"
    for entry in json.loads(database.read_text()):
        arguments = entry.get("arguments") or shlex.split(entry["command"])
        compiler = shutil.which(arguments[0])
        if compiler is None:
            sys.exit(f"error: compiler not found: {arguments[0]}; use your build environment")
        if compiler not in system_flags:
            # Nix compiler wrappers supply system paths that are not recorded by
            # Meson. Make them explicit so even an unwrapped clangd can use them,
            # without a global --query-driver allowlist or hard-coded store paths.
            result = subprocess.run(
                [compiler, "-E", "-x", "c", "-", "-v"],
                input="", text=True, capture_output=True, check=True,
                env={**os.environ, "LC_ALL": "C"},
            )
            flags = []
            in_search_list = False
            for line in result.stderr.splitlines():
                if line.strip() == "#include <...> search starts here:":
                    in_search_list = True
                elif line.strip() == "End of search list.":
                    in_search_list = False
                elif in_search_list:
                    path = line.strip()
                    if Path(path).is_dir():
                        flags.extend(["-isystem", path])
            if not flags:
                sys.exit(f"error: could not discover C system headers from {compiler}")
            system_flags[compiler] = flags
        entry.pop("command", None)
        entry["file"] = str((Path(entry["directory"]) / entry["file"]).resolve())
        entry["arguments"] = [compiler, *system_flags[compiler], *arguments[1:]]
        commands.append(entry)

# Replace atomically so a running language server never reads partial JSON.
output = root / "compile_commands.json"
temporary = output.with_suffix(".json.tmp")
temporary.write_text(json.dumps(commands, indent=2) + "\n")
temporary.replace(output)
print(f"Generated {output} ({len(commands)} compile commands)")
PY
