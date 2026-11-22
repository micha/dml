#!/usr/bin/env bash
# Run the design-to-conformance experiment without modifying the real binding.
set -euo pipefail

[[ $# == 1 ]] || { printf 'usage: %s /path/to/quint\n' "$0" >&2; exit 1; }
quint=$(realpath -- "$1")
spike=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=$(git -C "$spike" rev-parse --show-toplevel)
python_bin=$(command -v python)
base="$root/build/quint-feasibility"
mkdir -p -- "$base"
run=$(mktemp -d "$base/read-context.XXXXXX")
work="$run/work"
trap 'status=$?; rm -rf -- "$work" || status=1; printf "%s\n" "$status" > "$run/exit"; exit "$status"' EXIT
printf 'Read context run: %s\n' "$run"
git -C "$root" rev-parse HEAD > "$run/revision"

"$quint" typecheck "$spike/read_context_model.qnt" > "$run/typecheck.log" 2>&1
"$quint" test "$spike/read_context_model.qnt" --backend=typescript --max-samples=1 > "$run/design.log" 2>&1

mkdir -p -- "$work/offline/empty-bin" "$work/regen" "$work/pristine/daggerml"
for stage in offline regen; do
  hash_seed=1
  if [[ "$stage" == regen ]]; then hash_seed=2; fi
  PYTHONHASHSEED="$hash_seed" "$python_bin" -B "$spike/generate_read_contexts.py" --quint "$quint" \
    --out "$work/$stage/generated_read_contexts.py" > "$run/$stage-generation.log" 2>&1
done
cmp "$work"/{offline,regen}/generated_read_contexts.py
cp -- "$spike"/{read_context_binding,check_read_contexts}.py "$work/offline/"

export NIX_LDFLAGS="${NIX_LDFLAGS-}"
export NIX_LDFLAGS="${NIX_LDFLAGS#-rpath $root/outputs/out/lib}"
(
  meson setup "$work/native" "$root" --wrap-mode=nodownload
  ninja -C "$work/native" _core.abi3.so
) > "$run/native.log" 2>&1
cp -- "$root/python/daggerml/daggerml/__init__.py" "$work/native/_core.abi3.so" "$work/pristine/daggerml/"
cp -R -- "$work/pristine" "$work/fault"
"$python_bin" -I - "$work/fault/daggerml/__init__.py" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_bytes()
needle = b"        self._check(write=True)\n        try:\n            _call(_core.txn_end, self._handle, True)"
fault = b"        if not self._write:\n            self.abort()  # disposable premature-ending control\n"
if source.count(needle) != 1:
    raise SystemExit("Expected one commit guard in the Python binding")
path.write_bytes(source.replace(needle, fault + needle))
PY
status=0
diff -u --label pristine/__init__.py --label fault/__init__.py \
  "$work/pristine/daggerml/__init__.py" "$work/fault/daggerml/__init__.py" > "$run/binding.diff" || status=$?
[[ "$status" == 1 ]]
sha256sum "$spike"/{read_context_{rules,model}.qnt,generate_{python,transactions,read_contexts}.py,run_read_context_control.sh} \
  "$work"/offline/*.py "$work"/{pristine,fault}/daggerml/{__init__.py,_core.abi3.so} > "$run/inputs.sha256"

cd -- "$work/offline"
execute_offline() {
  local mode=$1
  shift
  env -i PATH="$PWD/empty-bin" PYTHONPATH="$work/$mode" "$python_bin" -B check_read_contexts.py "$@"
}
execute_offline pristine --clean > "$run/clean.json"
execute_offline fault --fault "$run/failure.json" > "$run/fault.json"
execute_offline pristine --replay "$run/failure.json" > "$run/replay.json"
PYTHONPATH="$work/pristine" "$python_bin" -B check_read_contexts.py --replay "$run/failure.json" \
  --quint "$quint" --rules "$spike/read_context_rules.qnt" > "$run/differential.json"
printf 'Saved the clean, fault, replay and differential receipts in %s\n' "$run"
