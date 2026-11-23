#!/usr/bin/env bash
set -euo pipefail

quint_tests=false
case "${1:-}" in
  -h|--help)
    echo "Usage: scripts/check.sh [--quint]"
    echo "Configure and build the C core. With --quint, also run behavior and native fault checks."
    exit 0
    ;;
  --quint)
    quint_tests=true
    shift
    ;;
esac
if [ "$#" -ne 0 ]; then
  echo "error: unexpected arguments; use scripts/check.sh --help" >&2
  exit 1
fi

root_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
build_dir="$root_dir/build/core-check"
# Bash 3.2 treats empty arrays as unset under nounset.
setup_args=(--wrap-mode=forcefallback -Dbuildtype=debug)
if [ "$quint_tests" = true ]; then
  build_dir="$root_dir/build/core-check-quint"
  setup_args+=(-Dquint_tests=true)
fi
if [ -f "$build_dir/meson-private/coredata.dat" ]; then
  setup_args+=(--reconfigure)
fi

meson setup "${setup_args[@]}" "$build_dir" "$root_dir"
meson compile -C "$build_dir"
if [ "$quint_tests" = true ]; then
  meson test -C "$build_dir" --print-errorlogs
else
  echo "==> C core build passed; behavioral checks did not run (use --quint)."
fi
