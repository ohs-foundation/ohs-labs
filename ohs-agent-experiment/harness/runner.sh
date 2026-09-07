#!/usr/bin/env bash
# Runs ONE clean eval build run: ./runner.sh <agent> <model> <condition> <replicate>
#   agent:     always explicit, no default: claude | gemini
#   model:     claude: fable | opus | sonnet | haiku; gemini: raw names (e.g. gemini-3.7-flash)
#   condition: cold | ohs | ohs-skills
#   replicate: 01, 02, ...
# Artifacts land in ../runs/s1-<condition>-<model>-<replicate>/ and results.csv.
set -euo pipefail

# Export agent-neutral Git identity for automated commits
export GIT_AUTHOR_NAME="OHS Agent"
export GIT_AUTHOR_EMAIL="agent@example.com"
export GIT_COMMITTER_NAME="OHS Agent"
export GIT_COMMITTER_EMAIL="agent@example.com"

if [ "$#" -ne 4 ]; then
  echo "usage: runner.sh <agent> <model> <condition> <replicate>   e.g.: runner.sh claude opus ohs 02"
  exit 2
fi
AGENT="$1"; MODEL="$2"; COND="$3"; REP="$4"
case "$AGENT" in
  claude|gemini) ;;
  *) echo "agent '$AGENT' not implemented (claude | gemini)"; exit 2 ;;
esac
H="$(cd "$(dirname "$0")" && pwd)"
POC="$(dirname "$H")"
RUN_ID="s1-${COND}-${MODEL}-${REP}"
WORK="$H/work/$RUN_ID"
RUN_DIR="$POC/runs/$RUN_ID"
LOG="$H/logs/$RUN_ID.log"
SDK="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
export PATH="$PATH:$SDK/platform-tools"
# 'claude' is a zsh alias on this machine - scripts must use the real binary.
CLAUDE_BIN="$HOME/.local/bin/claude"
GEMINI_BIN="$(command -v gemini || echo "$HOME/.nvm/versions/node/v22.20.0/bin/gemini")"

if [ "$AGENT" = "claude" ]; then
  [ -x "$CLAUDE_BIN" ] || { echo "claude binary not found at $CLAUDE_BIN"; exit 2; }
  case "$MODEL" in
    fable)  MODEL_ID="claude-fable-5" ;;
    sonnet) MODEL_ID="claude-sonnet-5" ;;
    opus)   MODEL_ID="claude-opus-5" ;;
    haiku)  MODEL_ID="claude-haiku-4-5-20251001" ;;
    *) echo "unknown claude model $MODEL"; exit 2 ;;
  esac
  API_HOST="https://api.anthropic.com/"
else
  [ -x "$GEMINI_BIN" ] || { echo "gemini binary not found (npm i -g @google/gemini-cli)"; exit 2; }
  case "$MODEL" in
    gemini*) MODEL_ID="$MODEL" ;;   # passed through raw, e.g. gemini-2.5-pro
    *) echo "gemini models must be named explicitly (e.g. gemini-2.5-pro), got '$MODEL'"; exit 2 ;;
  esac
  API_HOST="https://generativelanguage.googleapis.com/"
fi
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
API_CODE="$(curl -s -m 10 -o /dev/null -w '%{http_code}' "$API_HOST" || echo 000)"
[ "$API_CODE" = "000" ] && fail "no connectivity to $API_HOST (DNS/network)"
LEFTOVER="$(ls "$H/work" 2>/dev/null | grep -v "^$RUN_ID\$" || true)"
[ -n "$LEFTOVER" ] && fail "work/ not empty (no-interesting-siblings rule): $LEFTOVER"
DASHED="$(echo "$WORK" | sed 's/[^a-zA-Z0-9]/-/g')"
[ "$AGENT" = "claude" ] && [ -d "$HOME/.claude/projects/$DASHED" ] && \
  fail "claude project dir pre-exists for $WORK"
# gemini's save_memory tool writes to the GLOBAL ~/.gemini/GEMINI.md, which
# would leak into every later session - must not exist before a run
[ "$AGENT" = "gemini" ] && [ -s "$HOME/.gemini/GEMINI.md" ] && \
  fail "~/.gemini/GEMINI.md exists and is non-empty - would coach this run; inspect and remove it"

# ---- fresh scaffold -------------------------------------------------------
# the skills template is agent-specific (.claude/skills vs GEMINI.md)
TEMPLATE="$COND"
if [ "$COND" = "ohs-skills" ]; then
  case "$AGENT" in
    claude) TEMPLATE="ohs-skills-claude" ;;
    gemini) TEMPLATE="ohs-skills-gemini" ;;
  esac
fi
[ -d "$H/templates/$TEMPLATE/.git" ] || fail "template missing: harness/templates/$TEMPLATE - run harness/setup-templates.sh"
git clone -q "$H/templates/$TEMPLATE" "$WORK"
echo "sdk.dir=$SDK" > "$WORK/local.properties"
BASELINE="$(git -C "$WORK" rev-parse HEAD)"
log "scaffold cloned from templates/$TEMPLATE @ ${BASELINE:0:7}"

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
GEMINI_STREAM="$H/work/.stream-$RUN_ID.jsonl"
set +e
if [ "$AGENT" = "claude" ]; then
  ( cd "$WORK" && perl -e 'alarm 3600; exec @ARGV' -- \
      "$CLAUDE_BIN" -p --model "$MODEL_ID" --dangerously-skip-permissions \
      < "$PROMPT_FILE" ) >>"$LOG" 2>&1
else
  # stream-json on stdout IS the transcript; stderr goes to the log
  ( cd "$WORK" && perl -e 'alarm 3600; exec @ARGV' -- \
      "$GEMINI_BIN" -m "$MODEL_ID" -o stream-json --approval-mode yolo --skip-trust \
      -p "$(cat "$PROMPT_FILE")" ) > "$GEMINI_STREAM" 2>>"$LOG"
fi
AGENT_EXIT=$?
set -e
WALL=$(( ($(date +%s) - START) / 60 ))
log "agent finished: exit=$AGENT_EXIT after ${WALL} min"
rm -f "$PROMPT_FILE"

# Environment faults are not data. Discard the run and stop the campaign when:
#  (a) the agent did zero tool calls (API/network/auth error, whatever the text), or
#  (b) the session was cut off by the subscription usage limit (even mid-run).
if [ "$AGENT" = "claude" ]; then
  SESSION_GLOB="$HOME/.claude/projects/$DASHED"/*.jsonl
  TOOL_USES="$(grep -o '"type":"tool_use"' $SESSION_GLOB 2>/dev/null | wc -l | tr -d ' ')"
  LIMIT_HIT="$(grep -l "hit your session limit\|usage limit reached" $SESSION_GLOB 2>/dev/null || true)"
else
  TOOL_USES="$(grep -c 'tool_call\|toolCall\|"type": *"tool' "$GEMINI_STREAM" 2>/dev/null || echo 0)"
  LIMIT_HIT="$(grep -l 'RESOURCE_EXHAUSTED\|"code": *429\|rate limit\|quota' "$GEMINI_STREAM" 2>/dev/null || true)"
fi
if [ "${TOOL_USES:-0}" -eq 0 ]; then
  rm -rf "$WORK" "$HOME/.claude/projects/$DASHED"; rm -f "$GEMINI_STREAM"
  fail "agent did no work (0 tool calls, exit=$AGENT_EXIT) - environment error (API/auth/network/limit); run discarded"
fi
if [ -n "$LIMIT_HIT" ]; then
  rm -rf "$WORK" "$HOME/.claude/projects/$DASHED"; rm -f "$GEMINI_STREAM"
  fail "run truncated by usage/quota limit - discarded; resume the campaign after the limit resets"
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
git -C "$WORK" diff --no-ext-diff "$BASELINE" HEAD > "$RUN_DIR/code.diff"

if [ "$AGENT" = "claude" ]; then
  PROJ="$HOME/.claude/projects/$DASHED"
  JSONL="$(ls -t "$PROJ"/*.jsonl 2>/dev/null | head -1 || true)"
  [ -n "$JSONL" ] || fail "no session jsonl found in $PROJ"
  cp "$JSONL" "$RUN_DIR/transcript.jsonl"
else
  [ -s "$GEMINI_STREAM" ] || fail "no gemini stream output captured"
  mv "$GEMINI_STREAM" "$RUN_DIR/transcript.jsonl"
fi

case "$AGENT" in
  claude) EXTRACTOR="extract-claude.py" ;;
  gemini) EXTRACTOR="extract-gemini.py" ;;
esac
python3 "$H/$EXTRACTOR" \
  --jsonl "$RUN_DIR/transcript.jsonl" --run-dir "$RUN_DIR" --run-id "$RUN_ID" \
  --condition "$COND" --model "$MODEL" --replicate "$((10#$REP))" \
  --scaffold-repo "templates/$TEMPLATE" --baseline "${BASELINE:0:7}" \
  --smoke "$SMOKE" --results "$POC/results.csv" \
  --wall-minutes "$WALL" \
  --notes "agent_exit=$AGENT_EXIT" | tee -a "$LOG"

# ---- teardown (no interesting siblings for the next run) -------------------
# quarantine any global memory a gemini agent left behind (cross-run leak)
if [ "$AGENT" = "gemini" ] && [ -s "$HOME/.gemini/GEMINI.md" ]; then
  mv "$HOME/.gemini/GEMINI.md" "$RUN_DIR/global-memory-left-by-agent.md"
  log "WARNING: agent wrote global ~/.gemini/GEMINI.md - quarantined into runs/$RUN_ID/"
fi
mv "$WORK" "$H/archive/$RUN_ID"
for PKG in $(adb shell pm list packages com.example | tr -d '\r' | sed 's/package://'); do
  adb uninstall "$PKG" >/dev/null 2>&1 || true
done
log "=== $RUN_ID complete: artifacts in runs/$RUN_ID, work archived ==="
