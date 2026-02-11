#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <commit-message-file>" >&2
  exit 2
fi

msg_file="$1"

if [ ! -f "$msg_file" ]; then
  echo "error: commit message file not found: $msg_file" >&2
  exit 2
fi

violations="$({
  awk '
    NR == 1 { next }
    /^#/ { next }
    {
      sub(/\r$/, "", $0)
      if (length($0) > 80) {
        printf "%d:%d:%s\n", NR, length($0), $0
      }
    }
  ' "$msg_file"
} || true)"

if [ -n "$violations" ]; then
  echo "error: commit message body lines must be 80 chars or fewer" >&2
  echo "offending lines (line:length:text):" >&2
  printf '%s\n' "$violations" >&2
  echo "hint: wrap body lines before committing" >&2
  exit 1
fi

exit 0
