#!/usr/bin/env bash
# Runs ONE clean eval build run: ./runner.sh <condition> <model> <replicate>
#   condition: cold | ohs | ohs-skills
#   model:     fable | sonnet | haiku
#   replicate: 01, 02, ...
# Artifacts land in ../runs/s1-<condition>-<model>-<replicate>/ and results.csv.
set -euo pipefail

COND="$1"; MODEL="$2"; REP="$3"
H="$(cd "$(dirname "$0")" && pwd)"
POC="$(dirname "$H")"
RUN_ID="s1-${COND}-${MODEL}-${REP}"
WORK="$H/work/$RUN_ID"
RUN_DIR="$POC/runs/$RUN_ID"
LOG="$H/logs/$RUN_ID.log"
SDK=/Users/fikrimilano/Library/Android/sdk
export PATH="$PATH:$SDK/platform-tools"
# 'claude' is a zsh alias on this machine - scripts must use the real binary.
CLAUDE_BIN="$HOME/.local/bin/claude"
[ -x "$CLAUDE_BIN" ] || { echo "claude binary not found at $CLAUDE_BIN"; exit 2; }

case "$MODEL" in
  fable)  MODEL_ID="claude-fable-5" ;;
  sonnet) MODEL_ID="claude-sonnet-5" ;;
  opus)   MODEL_ID="claude-opus-5" ;;
  haiku)  MODEL_ID="claude-haiku-4-5-20251001" ;;
  *) echo "unknown model $MODEL"; exit 2 ;;
esac
case "$COND" in
  cold)              PROMPT_SRC="$POC/build-a-prompt.md" ;;
  ohs|ohs-skills)    PROMPT_SRC="$POC/build-b-prompt.md" ;;
  *) echo "unknown condition $COND"; exit 2 ;;
esac

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
fail() { log "HARNESS FAULT: $*"; exit 1; }
mkdir -p "$H/logs"; : > "$LOG"
log "=== $RUN_ID (model $MODEL_ID) ==="

# ---- preflight assertions -------------------------------------------------
[ -d "$RUN_DIR" ] && fail "runs/$RUN_ID already exists"
adb get-state >/dev/null 2>&1 || fail "no emulator/device connected"
API_CODE="$(curl -s -m 10 -o /dev/null -w '%{http_code}' https://api.anthropic.com/ || echo 000)"
[ "$API_CODE" = "000" ] && fail "no connectivity to api.anthropic.com (DNS/network)"
LEFTOVER="$(ls "$H/work" 2>/dev/null | grep -v "^$RUN_ID\$" || true)"
[ -n "$LEFTOVER" ] && fail "work/ not empty (no-interesting-siblings rule): $LEFTOVER"
DASHED="$(echo "$WORK" | sed 's/[^a-zA-Z0-9]/-/g')"
[ -d "$HOME/.claude/projects/$DASHED" ] && fail "claude project dir pre-exists for $WORK"

# ---- fresh scaffold -------------------------------------------------------
git clone -q "$H/templates/$COND" "$WORK"
echo "sdk.dir=$SDK" > "$WORK/local.properties"
BASELINE="$(git -C "$WORK" rev-parse HEAD)"
log "scaffold cloned from templates/$COND @ ${BASELINE:0:7}"

# ---- reset server (all conditions, for a constant environment) ------------
( cd "$POC" && docker-compose down >>"$LOG" 2>&1 && docker-compose up -d >>"$LOG" 2>&1 )
"$POC/load-seed.sh" >>"$LOG" 2>&1 || fail "seed load failed"
log "HAPI reset + reseeded"

# ---- reset device ---------------------------------------------------------
for PKG in $(adb shell pm list packages com.example | tr -d '\r' | sed 's/package://'); do
  adb uninstall "$PKG" >/dev/null 2>&1 || true
done
REMAIN="$(adb shell pm list packages com.example | tr -d '\r' || true)"
[ -n "$REMAIN" ] && fail "device not clean: $REMAIN"
log "device clean"

# ---- run the agent --------------------------------------------------------
# Prompt = everything below the first '---' of the prompt file, verbatim.
PROMPT_FILE="$H/work/.prompt-$RUN_ID.txt"
awk 'flag; /^---$/ && !flag { flag=1 }' "$PROMPT_SRC" > "$PROMPT_FILE"
[ -s "$PROMPT_FILE" ] || fail "empty prompt extracted from $PROMPT_SRC"

log "agent starting (cap: 60 min wall clock)"
START=$(date +%s)
set +e
( cd "$WORK" && perl -e 'alarm 3600; exec @ARGV' -- \
    "$CLAUDE_BIN" -p --model "$MODEL_ID" --dangerously-skip-permissions \
    < "$PROMPT_FILE" ) >>"$LOG" 2>&1
AGENT_EXIT=$?
set -e
WALL=$(( ($(date +%s) - START) / 60 ))
log "agent finished: exit=$AGENT_EXIT after ${WALL} min"
rm -f "$PROMPT_FILE"

# Environment faults are not data. Discard the run and stop the campaign when:
#  (a) the agent did zero tool calls (API/network/auth error, whatever the text), or
#  (b) the session was cut off by the subscription usage limit (even mid-run).
SESSION_GLOB="$HOME/.claude/projects/$DASHED"/*.jsonl
TOOL_USES="$(grep -o '"type":"tool_use"' $SESSION_GLOB 2>/dev/null | wc -l | tr -d ' ')"
if [ "${TOOL_USES:-0}" -eq 0 ]; then
  rm -rf "$WORK" "$HOME/.claude/projects/$DASHED"
  fail "agent did no work (0 tool calls, exit=$AGENT_EXIT) - environment error (API/network/limit); run discarded"
fi
if grep -q "hit your session limit\|usage limit reached" $SESSION_GLOB 2>/dev/null; then
  rm -rf "$WORK" "$HOME/.claude/projects/$DASHED"
  fail "run truncated by subscription usage limit - discarded; resume the campaign after the limit resets"
fi

# ---- smoke check ----------------------------------------------------------
mkdir -p "$RUN_DIR"
SMOKE=fail
if ( cd "$WORK" && ./gradlew -q :app:assembleDebug ) >>"$LOG" 2>&1; then
  APK="$WORK/app/build/outputs/apk/debug/app-debug.apk"
  APP_ID="$(grep -o 'applicationId *= *"[^"]*"' "$WORK/app/build.gradle.kts" | sed 's/.*"\(.*\)"/\1/')"
  if [ -f "$APK" ] && adb install -r "$APK" >>"$LOG" 2>&1; then
    adb shell monkey -p "$APP_ID" -c android.intent.category.LAUNCHER 1 >>"$LOG" 2>&1 || true
    sleep 8
    adb exec-out screencap -p > "$RUN_DIR/launch.png" 2>>"$LOG" || true
    CRASH="$(adb shell dumpsys activity processes | grep -c "$APP_ID" || true)"
    [ "${CRASH:-0}" -gt 0 ] && SMOKE=pass
  fi
fi
log "smoke: $SMOKE"

# ---- collect the four artifacts ------------------------------------------
git -C "$WORK" add -A
git -C "$WORK" commit -q -m "$RUN_ID result" --allow-empty
git -C "$WORK" diff "$BASELINE" HEAD > "$RUN_DIR/code.diff"

PROJ="$HOME/.claude/projects/$DASHED"
JSONL="$(ls -t "$PROJ"/*.jsonl 2>/dev/null | head -1 || true)"
[ -n "$JSONL" ] || fail "no session jsonl found in $PROJ"
cp "$JSONL" "$RUN_DIR/transcript.jsonl"

python3 "$H/extract.py" \
  --jsonl "$RUN_DIR/transcript.jsonl" --run-dir "$RUN_DIR" --run-id "$RUN_ID" \
  --condition "$COND" --model "$MODEL" --replicate "$((10#$REP))" \
  --scaffold-repo "templates/$COND" --baseline "${BASELINE:0:7}" \
  --smoke "$SMOKE" --results "$POC/results.csv" \
  --notes "agent_exit=$AGENT_EXIT" | tee -a "$LOG"

# ---- teardown (no interesting siblings for the next run) -------------------
mv "$WORK" "$H/archive/$RUN_ID"
for PKG in $(adb shell pm list packages com.example | tr -d '\r' | sed 's/package://'); do
  adb uninstall "$PKG" >/dev/null 2>&1 || true
done
log "=== $RUN_ID complete: artifacts in runs/$RUN_ID, work archived ==="
