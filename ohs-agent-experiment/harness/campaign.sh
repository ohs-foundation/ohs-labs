#!/usr/bin/env bash
# Runs the campaign manifest sequentially: ./campaign.sh [manifest]
# Each manifest line: <condition> <model> <replicate>   (# comments allowed)
# A harness fault stops the campaign; an agent failure does not (it's data).
set -uo pipefail
H="$(cd "$(dirname "$0")" && pwd)"
MANIFEST="${1:-$H/manifest.txt}"

grep -Ev '^\s*(#|$)' "$MANIFEST" | while read -r COND MODEL REP; do
  RUN_ID="s1-${COND}-${MODEL}-${REP}"
  if [ -d "$H/../runs/$RUN_ID" ]; then
    echo "skip $RUN_ID (already collected)"
    continue
  fi
  echo ">>> $RUN_ID"
  if ! "$H/runner.sh" "$COND" "$MODEL" "$REP" < /dev/null; then
    echo "HARNESS FAULT on $RUN_ID - campaign stopped. Fix, then rerun campaign.sh (completed runs are skipped)."
    exit 1
  fi
done
echo "campaign manifest complete"
