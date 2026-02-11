#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/check.sh [-v] [-f] [-m]

Runs full validation:
  - Configures and builds with Meson
  - Runs C tests via meson test
  - Runs Python/CLI tests via pytest when present
  - Runs Python source coverage via coverage.py when Python sources exist
  - Runs Mull mutation testing (when -m is passed)
  - Captures gcov/lcov coverage and generates HTML report
  - Enforces 100% line/function/branch coverage

Options:
  -v  Run C tests under Valgrind
  -f  Remove build artifacts before rebuilding
  -m  Enable Mull mutation testing

Environment:
  MULL_TARGETS   Space-separated test binaries for mull-runner
                 (defaults to build/check/test_version when present)
  SKIP_MULL=1    Skip Mull mutation testing (legacy override)
  LCOV_EXCLUDES  Colon-separated lcov --remove patterns
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: required command not found: $1" >&2
    exit 1
  fi
}

run_python_tests_and_coverage_if_present() {
  local root="$1"
  local coverage_out="$2"
  local omit_patterns="$root/tests/*,$root/subprojects/*,$root/build/*"
  local source_count

  if [ ! -d "$root/tests" ]; then
    echo "==> No tests/ directory found; skipping pytest"
    return 0
  fi

  if ! find "$root/tests" -type f \( -name 'test_*.py' -o -name '*_test.py' \) | grep -q .; then
    echo "==> No pytest files found under tests/; skipping pytest"
    return 0
  fi

  if ! python3 -m pytest --version >/dev/null 2>&1; then
    echo "error: pytest is required for Python/CLI tests" >&2
    echo "       install dev deps: python3 -m pip install -r requirements-dev.txt" >&2
    exit 1
  fi

  source_count="$(
    python3 - "$root" <<'PY'
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
excluded_parts = {"tests", "subprojects", "build", ".venv", "venv"}
count = 0

for path in root.rglob("*.py"):
    rel = path.relative_to(root)
    if any(part in excluded_parts for part in rel.parts):
        continue
    count += 1

print(count)
PY
  )"

  if [ "$source_count" -eq 0 ]; then
    echo "==> Running Python and CLI tests (pytest)"
    python3 -m pytest -q
    echo "==> No non-test Python sources found; skipping python coverage gate"
    return 0
  fi

  if ! python3 -m coverage --version >/dev/null 2>&1; then
    echo "error: coverage.py is required for Python source coverage" >&2
    echo "       install dev deps: python3 -m pip install -r requirements-dev.txt" >&2
    exit 1
  fi

  echo "==> Running Python and CLI tests with coverage"
  python3 -m coverage erase
  python3 -m coverage run --source "$root" --omit "$omit_patterns" -m pytest -q

  echo "==> Enforcing 100% Python source coverage"
  python3 -m coverage report --omit "$omit_patterns" --fail-under=100

  echo "==> Generating Python coverage reports"
  python3 -m coverage xml -o "$coverage_out/python-coverage.xml"
  python3 -m coverage html -d "$coverage_out/python-html"
}

run_mull() {
  local root="$1"
  local report_path="$2"
  local mull_bin="${MULL_RUNNER_BIN:-}"
  local config_path="$root/.mull.yml"

  if [ "${SKIP_MULL:-0}" = "1" ]; then
    echo "==> SKIP_MULL=1 set; skipping mutation tests"
    return 0
  fi

  if [ -z "$mull_bin" ]; then
    if command -v mull-runner >/dev/null 2>&1; then
      mull_bin="mull-runner"
    elif command -v mull-runner-19 >/dev/null 2>&1; then
      mull_bin="mull-runner-19"
    else
      echo "error: required command not found: mull-runner (or mull-runner-19)" >&2
      exit 1
    fi
  fi

  if [ ! -f "$config_path" ]; then
    echo "error: .mull.yml is required for mutation testing" >&2
    echo "       add configuration or set SKIP_MULL=1 for bootstrap runs" >&2
    exit 1
  fi

  if [ -z "${MULL_TARGETS:-}" ]; then
    if [ -x "$root/build/check/test_version" ]; then
      MULL_TARGETS="$root/build/check/test_version"
    else
      echo "error: MULL_TARGETS is required (space-separated test binaries)" >&2
      exit 1
    fi
  fi

  # shellcheck disable=SC2206
  local targets=( ${MULL_TARGETS} )

  echo "==> Running Mull mutation tests"
  if [ "$mull_bin" = "mull-runner-19" ]; then
    local target
    for target in "${targets[@]}"; do
      MULL_CONFIG="$config_path" "$mull_bin" \
        --reporters IDE \
        --report-name "$(basename "$target").mull.txt" \
        "$target"
    done
  else
    "$mull_bin" \
      --config "$config_path" \
      --reporters Summary \
      --reporters IDE \
      --report-name "$report_path" \
      "${targets[@]}"
  fi
}

check_coverage_100() {
  local info_file="$1"
  python3 - "$info_file" <<'PY'
import re
import subprocess
import sys

info = sys.argv[1]
cmd = [
    "lcov",
    "--summary",
    info,
    "--rc",
    "branch_coverage=1",
]
result = subprocess.run(cmd, check=True, text=True, capture_output=True)
text = result.stdout
print(text, end="")

targets = {"lines": None, "functions": None, "branches": None}
for line in text.splitlines():
    for key in targets:
        if key in line:
            match = re.search(r"([0-9]+(?:\.[0-9]+)?)%", line)
            if match:
                targets[key] = float(match.group(1))

missing = [k for k, v in targets.items() if v is None]
if missing:
    print(f"error: failed to parse coverage summary for: {', '.join(missing)}", file=sys.stderr)
    sys.exit(1)

below = [f"{k}={v:.2f}%" for k, v in targets.items() if v < 100.0]
if below:
    print("error: coverage must be 100% for lines/functions/branches", file=sys.stderr)
    print("       below threshold: " + ", ".join(below), file=sys.stderr)
    sys.exit(1)
PY
}

use_valgrind=0
force_clean=0
enable_mutation=0

while getopts ":vfm" opt; do
  case "$opt" in
    v) use_valgrind=1 ;;
    f) force_clean=1 ;;
    m) enable_mutation=1 ;;
    *)
      usage
      exit 1
      ;;
  esac
done

root_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
build_dir="$root_dir/build/check"
coverage_dir="$root_dir/build/coverage"
coverage_raw="$coverage_dir/lcov.info"
coverage_filtered="$coverage_dir/lcov.filtered.info"
mull_report="$coverage_dir/mull.txt"

require_cmd meson
require_cmd ninja
require_cmd python3
require_cmd lcov
require_cmd genhtml
require_cmd gcov

if [ "$force_clean" -eq 1 ]; then
  echo "==> Cleaning build artifacts"
  rm -rf "$build_dir" "$coverage_dir"
fi

mkdir -p "$coverage_dir"

echo "==> Configuring Meson build"
if [ -d "$build_dir" ]; then
  meson setup "$build_dir" \
    --wipe \
    --wrap-mode=forcefallback \
    --force-fallback-for='*' \
    -Db_coverage=true \
    -Dbuildtype=debug
else
  meson setup "$build_dir" \
    --wrap-mode=forcefallback \
    --force-fallback-for='*' \
    -Db_coverage=true \
    -Dbuildtype=debug
fi

echo "==> Building"
meson compile -C "$build_dir"

echo "==> Resetting coverage counters"
lcov --zerocounters --directory "$build_dir" || true

echo "==> Running C tests"
if [ "$use_valgrind" -eq 1 ]; then
  require_cmd valgrind
  meson test -C "$build_dir" \
    --print-errorlogs \
    --wrapper='valgrind --error-exitcode=101 --leak-check=full --show-leak-kinds=all --track-origins=yes'
else
  echo "==> Valgrind checks disabled (use -v to enable)"
  meson test -C "$build_dir" --print-errorlogs
fi

export DML_BIN="$build_dir/dml"
run_python_tests_and_coverage_if_present "$root_dir" "$coverage_dir"

if [ "$enable_mutation" -eq 1 ]; then
  run_mull "$root_dir" "$mull_report"
else
  echo "==> Mutation testing disabled (use -m to enable)"
fi

echo "==> Capturing coverage"
lcov \
  --capture \
  --directory "$build_dir" \
  --output-file "$coverage_raw" \
  --rc branch_coverage=1

remove_patterns=(
  '/usr/*'
  '*/subprojects/*'
  '*/tests/*'
  '*/build/check/*'
)

if [ -n "${LCOV_EXCLUDES:-}" ]; then
  IFS=':' read -r -a extra_patterns <<< "$LCOV_EXCLUDES"
  remove_patterns+=("${extra_patterns[@]}")
fi

lcov \
  --ignore-errors unused \
  --remove "$coverage_raw" \
  "${remove_patterns[@]}" \
  --output-file "$coverage_filtered" \
  --rc branch_coverage=1

echo "==> Generating HTML coverage report"
genhtml \
  "$coverage_filtered" \
  --branch-coverage \
  --function-coverage \
  --output-directory "$coverage_dir/html"

echo "==> Enforcing 100% coverage thresholds"
check_coverage_100 "$coverage_filtered"

echo "==> Check completed successfully"
echo "Coverage report: $coverage_dir/html/index.html"
