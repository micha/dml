#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  -h|--help)
    echo "Usage: scripts/check.sh"
    echo "Configure and build the C core. No maintained tests are registered yet."
    exit 0
    ;;
esac
if [ "$#" -ne 0 ]; then
  echo "error: unexpected arguments; use scripts/check.sh --help" >&2
  exit 1
fi

root_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
build_dir="$root_dir/build/core-check"
setup_args=()
if [ -f "$build_dir/meson-private/coredata.dat" ]; then
  setup_args+=(--reconfigure)
fi

meson setup "${setup_args[@]}" "$build_dir" "$root_dir" --wrap-mode=forcefallback -Dbuildtype=debug
meson compile -C "$build_dir"
echo "==> C core build passed; no maintained tests or coverage checks ran."
