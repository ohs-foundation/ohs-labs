#!/usr/bin/env bash
# Runs a campaign manifest sequentially: ./campaign.sh <manifest>
# The manifest is explicit, no default: manifest-claude.txt or manifest-gemini.txt.
# Each manifest line: <agent> <model> <condition> <replicate>   (# comments allowed)
# A harness fault stops the campaign; an agent failure does not (it's data).
set -uo pipefail
H="$(cd "$(dirname "$0")" && pwd)"
if [ "$#" -ne 1 ]; then
  echo "usage: campaign.sh <manifest>   e.g.: campaign.sh manifest-claude.txt"
  exit 2
fi
MANIFEST="$1"
[ -f "$MANIFEST" ] || MANIFEST="$H/$1"
[ -f "$MANIFEST" ] || { echo "manifest not found: $1"; exit 2; }

grep -Ev '^\s*(#|$)' "$MANIFEST" | while read -r AGENT MODEL COND REP; do
  RUN_ID="s1-${COND}-${MODEL}-${REP}"
  if [ -d "$H/../runs/$RUN_ID" ]; then
    echo "skip $RUN_ID (already collected)"
    continue
  fi
  echo ">>> $RUN_ID"
  if ! "$H/runner.sh" "$AGENT" "$MODEL" "$COND" "$REP" < /dev/null; then
    echo "HARNESS FAULT on $RUN_ID - campaign stopped. Fix, then rerun campaign.sh (completed runs are skipped)."
    exit 1
  fi
done
echo "campaign manifest complete"
