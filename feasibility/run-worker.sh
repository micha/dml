#!/usr/bin/env bash
# Launch one bounded Pi specialist. Run from a dedicated tmux window.
set -u
set -o pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
worker="${1:?usage: run-worker.sh WORKER [task.md|followup.md]}"
task="${2:-task.md}"
case "$task" in
  task.md|followup.md) ;;
  *) printf 'Unknown assignment file: %s\n' "$task" >&2; exit 2 ;;
esac
suffix=""
if [[ "$task" == followup.md ]]; then suffix="-followup"; fi
case "$worker" in
  opentofu|history|retention|adversarial|integration|review|journal|gate|artifact|hardening-review) ;;
  *) printf 'Unknown worker: %s\n' "$worker" >&2; exit 2 ;;
esac
cd "$root" || exit 2
mkdir -p "feasibility/runtime/$worker"
printf '%s\n' "$$" > "feasibility/runtime/$worker/runner${suffix}.pid"
printf 'Starting %s specialist in %s\n' "$worker" "$root"
timeout --signal=TERM --kill-after=30s 1800s \
  pi --print --offline --no-extensions --no-approve \
  --provider amazon-bedrock --model us.openai.gpt-6.1-sol --thinking high \
  --tools read,bash,edit,write \
  --session-id "dml-feasibility-$worker" --name "DML feasibility: $worker" \
  "@feasibility/WORKER.md" "@feasibility/$worker/$task" \
  'Execute this assigned feasibility work now. Follow the worker contract and the current assignment, publish the report before its atomic done marker, then exit.' \
  2>&1 | tee "feasibility/runtime/$worker/agent${suffix}.log"
status=${PIPESTATUS[0]}
printf '%s\n' "$status" > "feasibility/runtime/$worker/exit-code${suffix}.tmp"
mv "feasibility/runtime/$worker/exit-code${suffix}.tmp" "feasibility/runtime/$worker/exit-code${suffix}"
printf '\n%s specialist exited with status %s\n' "$worker" "$status"
exit "$status"
