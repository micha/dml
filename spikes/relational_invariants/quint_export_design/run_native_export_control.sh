#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 /path/to/quint" >&2
  exit 2
fi
quint=$(realpath -- "$1")
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
cd "$root"
spike=spikes/relational_invariants/quint_export_design
mkdir -p build
out=$(mktemp -d "$root/build/export-native-control.XXXXXX")
printf 'Receipts: %s\n' "$out"

# Use private source copies (including wrap archives), never edit the checkout or gate builds.
clean="$out/clean"
mutant="$out/first-parent"
mkdir -p "$clean/source/subprojects" "$mutant"
cp -a meson.build meson.options include python src tests "$clean/source/"
cp -a subprojects/*.wrap subprojects/packagefiles subprojects/packagecache "$clean/source/subprojects/"
mkdir -p "$out/checks"
cp "$spike/"{check_export_baseline.py,check_native_export.py,check_native_export_boundaries.py} \
  "$spike/"{export_fault_sweep.py,export_walk_rules.qnt} "$out/checks/"
cp -a "$clean/source" "$mutant/source"
python3 - "$mutant/source/src/export_walk.c" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_bytes()
needle = b"case DML_REC_COMMIT: return 1 + frame->view.object.count;"
if source.count(needle) != 1:
    raise SystemExit("First-parent control no longer identifies exactly one edge-count rule")
path.write_bytes(source.replace(needle, b"case DML_REC_COMMIT: return 1 + (frame->view.object.count != 0);"))
PY
status=0
diff -u "$clean/source/src/export_walk.c" "$mutant/source/src/export_walk.c" > "$out/first-parent.diff" || status=$?
test "$status" = 1

git rev-parse HEAD > "$out/revision"
sha256sum "$clean/source/"{meson.build,meson.options,src/export_walk.c,src/export_walk.h,python/daggerml/src/_core_module.c} \
  "$mutant/source/src/export_walk.c" "$out/checks/"* > "$out/inputs.sha256"

export NIX_LDFLAGS="${NIX_LDFLAGS-}"
export NIX_LDFLAGS="${NIX_LDFLAGS#-rpath $root/outputs/out/lib}"

build_core() {
  local variant="$1"
  shift
  meson setup "$variant/native" "$variant/source" --wrap-mode=nodownload \
    --buildtype=debugoptimized -Dexperimental_export_walk=true > "$variant/setup.log" 2>&1
  meson compile -C "$variant/native" _core.abi3.so "$@" > "$variant/compile.log" 2>&1
  mkdir -p "$variant/python/daggerml"
  cp "$variant/source/python/daggerml/daggerml/"{__init__.py,transfer.py} \
    "$variant/native/"_core*.so "$variant/python/daggerml/"
}

build_core "$clean" _core_fault.abi3.so test_core_driver
build_core "$mutant"
sha256sum "$clean/native/"_core*.so "$mutant/native/_core.abi3.so" > "$out/binaries.sha256"
PYTHONPATH="$clean/python" python3 -B "$out/checks/check_native_export.py" \
  --quint "$quint" --out "$clean/evidence" | tee "$clean/export.log"
PYTHONPATH="$mutant/python" python3 -B "$out/checks/check_native_export.py" \
  --quint "$quint" --out "$mutant/evidence" --first-parent-control | tee "$mutant/export.log"
PYTHONPATH="$clean/python" python3 -B "$out/checks/check_native_export_boundaries.py" \
  --core-driver "$clean/native/test_core_driver" --out "$clean/boundaries" | tee "$clean/boundaries.log"

# Keep unrelated imports and CPython source parsing out of the allocation check.
# Trace the actual interpreter through the Nix Python executable wrapper.
python3 -m compileall -q "$clean/python/daggerml"
python3 -c 'import py_compile, sys; py_compile.compile(sys.argv[1], sys.argv[2], doraise=True)' \
  "$out/checks/export_fault_sweep.py" "$clean/export_fault_sweep.pyc"
PYTHONPATH="$clean/python" PYTHONMALLOC=malloc valgrind \
  --trace-children=yes --error-exitcode=101 --leak-check=full --show-leak-kinds=definite \
  --errors-for-leak-kinds=definite --track-origins=yes \
  --suppressions="$root/tests/valgrind-cpython.supp" --log-file="$clean/valgrind.%p.log" \
  python3 -B "$clean/export_fault_sweep.pyc" "$clean/boundaries/limits.dml" | tee "$clean/fault-sweep.log"
pid=$(awk '/^Interpreter PID: [0-9]+$/ { print $3 }' "$clean/fault-sweep.log")
grep -F 'ERROR SUMMARY: 0 errors from 0 contexts' "$clean/valgrind.$pid.log"
