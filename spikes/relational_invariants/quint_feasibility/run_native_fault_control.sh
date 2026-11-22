#!/usr/bin/env bash
# Build and compare a disposable poisoned-commit mutant against pristine HEAD.
set -euo pipefail

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

[[ $# == 1 ]] || fail "usage: $0 /path/to/quint"
quint=$(realpath -- "$1")
[[ -x "$quint" && -f "$quint" ]] || fail "Quint is not executable: $quint"
spike=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=$(git -C "$spike" rev-parse --show-toplevel)
revision=$(git -C "$root" rev-parse --verify HEAD)
python_bin=$(command -v python) || fail "python not found; enter nix develop"
[[ "$python_bin" = /* ]] || fail "Expected an absolute Python executable"
cache="$root/subprojects/packagecache"
[[ -d "$cache" ]] || fail "Populate the Meson wrap cache in $cache first"

base="$root/build/quint-feasibility"
mkdir -p -- "$base"
run=$(mktemp -d "$base/native-fault.XXXXXX")
work="$run/work"
cleanup() {
  local status=$?
  rm -rf -- "$work" || status=1
  printf '%s\n' "$status" > "$run/exit"
  if (( status != 0 )); then
    printf 'Native fault run failed; see %s\n' "$run" >&2
  fi
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
printf 'Native fault run: %s\n' "$run"
printf '%s\n' "$revision" > "$run/revision"

mkdir -p -- "$work/source-clean" "$work/offline/empty-bin"
git -C "$root" archive "$revision" meson.build include src subprojects tests/c python/daggerml \
  | tar -x -C "$work/source-clean"
cp -R -- "$cache" "$work/source-clean/subprojects/packagecache"
cp -R -- "$work/source-clean" "$work/source-fault"

# Python aborts the native transaction before rejecting a failed commit.
# Mutate that abort so a poisoned writer publishes its pending LMDB changes.
"$python_bin" -I - "$work/source-fault/src/repo.c" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
old = b'''  *txn_ptr = NULL;
  mdb_txn_abort(txn->native);
  txn->repo->active_txns--;
  free(txn);
}

dml_status dml_repo_close('''
new = b'''  *txn_ptr = NULL;
  int code = MDB_SUCCESS;
  if (txn->mode == DML_TXN_WRITE && txn->poisoned) {
    code = mdb_txn_commit(txn->native);
  } else {
    mdb_txn_abort(txn->native);
  }
  txn->repo->active_txns--;
  free(txn);
  /* This void API cannot report a failed native commit. Fail the control. */
  if (code != MDB_SUCCESS) {
    fprintf(stderr, "native fault control commit failed: %s\\n", mdb_strerror(code));
    abort();
  }
}

dml_status dml_repo_close('''
source = path.read_bytes()
if source.count(old) != 1:
    raise SystemExit("Expected exactly one dml_txn_abort cleanup block; review the mutation against HEAD")
path.write_bytes(source.replace(old, new))
PY

patch_status=0
diff -u --label clean/src/repo.c --label fault/src/repo.c \
  "$work/source-clean/src/repo.c" "$work/source-fault/src/repo.c" > "$run/repo.c.diff" || patch_status=$?
[[ "$patch_status" == 1 ]] || fail "Could not record the single-source change"

export NIX_LDFLAGS="${NIX_LDFLAGS-}"
export NIX_LDFLAGS="${NIX_LDFLAGS#-rpath $root/outputs/out/lib}"
for mode in clean fault; do
  source_dir="$work/source-$mode"
  native_dir="$work/native-$mode"
  package_dir="$work/python-$mode/daggerml"
  (
    meson setup "$native_dir" "$source_dir" --wrap-mode=nodownload
    ninja -C "$native_dir" _core.abi3.so
    mkdir -p -- "$package_dir"
    cp -- "$source_dir/python/daggerml/daggerml/__init__.py" "$native_dir/_core.abi3.so" "$package_dir/"
  ) > "$run/$mode-build.log" 2>&1
done

PYTHONHASHSEED=0 "$python_bin" -B "$spike/generate_transactions.py" --quint "$quint" \
  --out "$work/offline/generated_transactions.py" > "$run/generation.log" 2>&1
cp -- "$spike"/{check_transaction_native_fault,transaction_failure_artifact,transaction_graph}.py \
  "$spike"/{transaction_binding,ref_binding}.py "$work/offline/"
(
  cd -- "$spike"
  sha256sum run_native_fault_control.sh generate_python.py generate_transactions.py transaction_rules.qnt
  cd -- "$work"
  sha256sum source-{clean,fault}/src/repo.c source-clean/subprojects/packagecache/*.tar.gz \
    python-{clean,fault}/daggerml/{__init__.py,_core.abi3.so} offline/*.py
) > "$run/inputs.sha256"

(
  cd -- "$work/offline"
  env -i PATH="$PWD/empty-bin" PYTHONPATH="$work/python-clean" "$python_bin" -B check_transaction_native_fault.py \
    "$work/python-clean" "$work/python-fault" --out "$run/evidence"
) 2>&1 | tee "$run/offline.log"
