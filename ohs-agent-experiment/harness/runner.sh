#!/usr/bin/env bash
# Runs ONE clean eval build run: ./runner.sh <agent> <model> <condition> <replicate>
#   agent:     always explicit, no default: claude | gemini | antigravity
#   model:     claude: fable | opus | sonnet | haiku; gemini: raw names (e.g. gemini-3.7-flash);
#              antigravity: raw `agy models` ids, gemini only (e.g. gemini-3.8-flash-high)
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
  claude|gemini|antigravity) ;;
  *) echo "agent '$AGENT' not implemented (claude | gemini | antigravity)"; exit 2 ;;
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
AGY_BIN="$(command -v agy || echo "$HOME/.local/bin/agy")"
AGY_HOME="$HOME/.gemini/antigravity-cli"   # agy's own state; ~/.gemini root is shared with gemini-cli

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
elif [ "$AGENT" = "gemini" ]; then
  [ -x "$GEMINI_BIN" ] || { echo "gemini binary not found (npm i -g @google/gemini-cli)"; exit 2; }
  case "$MODEL" in
    gemini*) MODEL_ID="$MODEL" ;;   # passed through raw, e.g. gemini-2.5-pro
    *) echo "gemini models must be named explicitly (e.g. gemini-2.5-pro), got '$MODEL'"; exit 2 ;;
  esac
  API_HOST="https://generativelanguage.googleapis.com/"
else
  [ -x "$AGY_BIN" ] || { echo "agy binary not found (install the Antigravity CLI, then \`agy install\`)"; exit 2; }
  # agy also lists Claude and GPT-OSS models; this experiment runs it on Gemini only.
  # Its ids always carry an effort suffix (-low|-medium|-high), which keeps the run id
  # distinct from the gemini-cli rows for the same base model.
  case "$MODEL" in
    gemini*-low|gemini*-medium|gemini*-high) MODEL_ID="$MODEL" ;;
    *) echo "antigravity models must be a gemini id from \`agy models\` (e.g. gemini-3.8-flash-high), got '$MODEL'"; exit 2 ;;
  esac
  API_HOST="https://daily-cloudcode-pa.googleapis.com/"
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
# self-heal orphans an interrupted run leaves behind (never "interesting siblings"):
rm -f "$H/work/".prompt-*.txt 2>/dev/null || true          # stale prompt files
find "$H/work" -mindepth 1 -maxdepth 1 -type d -empty -exec rm -rf {} + 2>/dev/null || true
for D in "$H/work"/*/; do   # build-output husk a Gradle daemon rewrote after a discard: no .git, no sources
  [ -d "$D" ] && [ ! -d "$D/.git" ] && [ ! -d "$D/app/src" ] && rm -rf "$D"
done
# a genuinely non-empty leftover work dir is still a hard fault (could hide a prior solution)
LEFTOVER="$(ls "$H/work" 2>/dev/null | grep -v "^$RUN_ID\$" || true)"
[ -n "$LEFTOVER" ] && fail "work/ not empty (no-interesting-siblings rule): $LEFTOVER - inspect harness/work/, then remove it if it is a leftover from an interrupted run"
DASHED="$(echo "$WORK" | sed 's/[^a-zA-Z0-9]/-/g')"
[ "$AGENT" = "claude" ] && [ -d "$HOME/.claude/projects/$DASHED" ] && \
  fail "claude project dir pre-exists for $WORK"
# gemini's save_memory tool writes to the GLOBAL ~/.gemini/GEMINI.md, which
# would leak into every later session - must not exist before a run
[ "$AGENT" = "gemini" ] && [ -s "$HOME/.gemini/GEMINI.md" ] && \
  fail "~/.gemini/GEMINI.md exists and is non-empty - would coach this run; inspect and remove it"
if [ "$AGENT" = "antigravity" ]; then
  # agy's global customization root is ~/.gemini/config/ (rules/skills there load into every
  # session) and it shares ~/.gemini/GEMINI.md discovery with gemini-cli
  [ -s "$HOME/.gemini/GEMINI.md" ] && fail "~/.gemini/GEMINI.md exists and is non-empty - would coach this run; inspect and remove it"
  for G in rules skills GEMINI.md AGENTS.md; do
    [ -e "$HOME/.gemini/config/$G" ] && fail "~/.gemini/config/$G exists - global agy customization would coach this run; inspect and remove it"
  done
  # agy's knowledge store is the cross-run memory channel (delete_knowledge tool exists);
  # it must be empty before a run
  AGY_KNOWLEDGE_BEFORE="$(find "$AGY_HOME/knowledge" -type f ! -name '*.lock' 2>/dev/null || true)"
  [ -n "$AGY_KNOWLEDGE_BEFORE" ] && fail "agy knowledge store is not empty ($AGY_HOME/knowledge) - would carry memory into this run; inspect and remove it"
  # agy resumes the last conversation per cwd; a fresh work path must have none
  grep -q "\"$WORK\"" "$AGY_HOME/cache/last_conversations.json" 2>/dev/null && \
    fail "agy already has a conversation recorded for $WORK"
fi

# ---- fresh scaffold -------------------------------------------------------
# the skills template is agent-specific (.claude/skills vs GEMINI.md)
TEMPLATE="$COND"
if [ "$COND" = "ohs-skills" ]; then
  case "$AGENT" in
    claude)      TEMPLATE="ohs-skills-claude" ;;
    gemini)      TEMPLATE="ohs-skills-gemini" ;;
    antigravity) TEMPLATE="ohs-skills-antigravity" ;;
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
GEMINI_STREAM="$H/work/.stream-$RUN_ID.jsonl"   # gemini and antigravity: stream-json stdout
set +e
if [ "$AGENT" = "claude" ]; then
  ( cd "$WORK" && perl -e 'alarm 3600; exec @ARGV' -- \
      "$CLAUDE_BIN" -p --model "$MODEL_ID" --dangerously-skip-permissions \
      < "$PROMPT_FILE" ) >>"$LOG" 2>&1
elif [ "$AGENT" = "gemini" ]; then
  # stream-json on stdout IS the transcript; stderr goes to the log
  ( cd "$WORK" && perl -e 'alarm 3600; exec @ARGV' -- \
      "$GEMINI_BIN" -m "$MODEL_ID" -o stream-json --approval-mode yolo --skip-trust \
      -p "$(cat "$PROMPT_FILE")" ) > "$GEMINI_STREAM" 2>>"$LOG"
else
  # --add-dir is load-bearing: without it agy's agent works in its private scratch folder
  # (~/.gemini/antigravity-cli/scratch), not the cwd, even inside a trusted workspace.
  # --print must carry the prompt as --print=... (Go flag parsing; a separate argument is
  # swallowed). Headless mode auto-denies every permission prompt, hence skip-permissions.
  ( cd "$WORK" && perl -e 'alarm 3600; exec @ARGV' -- \
      "$AGY_BIN" --add-dir "$WORK" --model "$MODEL_ID" --output-format stream-json \
      --dangerously-skip-permissions --print="$(cat "$PROMPT_FILE")" ) > "$GEMINI_STREAM" 2>>"$LOG"
  # agy backgrounds any command that outlives its WaitMsBeforeAsync (a Gradle build easily
  # does) and then tells the model to either carry on or "update the user with a short
  # message". In the TUI the task's completion wakes the agent; in headless --print mode the
  # turn simply ends and the session with it, with the build half-done and nothing written
  # (two ohs-skills runs shipped 0 lines this way). The TUI-equivalent fix: while the
  # conversation's last recorded step is a still-RUNNING background task, resume the same
  # conversation with a neutral continue prompt. Each resume is logged and counted in
  # run.json as resume_turns; the prompt says nothing about the task itself.
  AGY_RESUMES=0
  AGY_CONV_LIVE="$(grep -m1 -o '"conversation_id":"[^"]*"' "$GEMINI_STREAM" | cut -d'"' -f4 || true)"
  agy_yielded() {
    python3 - "$AGY_HOME/brain/$AGY_CONV_LIVE/.system_generated/logs/transcript_full.jsonl" <<'PY'
import json,sys
try: rows=[json.loads(l) for l in open(sys.argv[1],errors="replace")]
except Exception: sys.exit(1)
gen=[d for d in rows if d.get("type")=="GENERIC"]
sys.exit(0 if gen and gen[-1].get("status")=="RUNNING" else 1)
PY
  }
  while [ -n "$AGY_CONV_LIVE" ] && agy_yielded; do
    # an API failure (quota, auth) leaves the stale background step in place; resuming would
    # only burn more quota - let the fault gate below handle it
    grep -q 'AGY_ERROR' "$LOG" && { log "agy reported an API error; not resuming"; break; }
    REMAINING=$(( 3600 - ($(date +%s) - START) ))
    [ "$REMAINING" -gt 60 ] || { log "agy yielded on a background task but the wall-clock cap is reached; not resuming"; break; }
    [ "$AGY_RESUMES" -lt 12 ] || { log "agy yielded on a background task 12 times; not resuming further"; break; }
    AGY_RESUMES=$((AGY_RESUMES + 1))
    log "agy ended its turn waiting on a background task - resuming conversation ${AGY_CONV_LIVE:0:8} (resume #$AGY_RESUMES, ${REMAINING}s left)"
    ( cd "$WORK" && perl -e "alarm $REMAINING; exec @ARGV" -- \
        "$AGY_BIN" --add-dir "$WORK" --model "$MODEL_ID" --conversation "$AGY_CONV_LIVE" \
        --output-format stream-json --dangerously-skip-permissions \
        --print="Continue from where you left off. Any command you launched in the background was terminated when your previous turn ended, so re-run it if you still need its result. Finish the original task." \
      ) >> "$GEMINI_STREAM" 2>>"$LOG"
  done
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
elif [ "$AGENT" = "gemini" ]; then
  TOOL_USES="$(grep -c 'tool_call\|toolCall\|"type": *"tool' "$GEMINI_STREAM" 2>/dev/null || true)"
  LIMIT_HIT="$(grep -l 'RESOURCE_EXHAUSTED\|"code": *429\|rate limit\|quota' "$GEMINI_STREAM" 2>/dev/null || true)"
else
  # one ACTIVE event per tool step; API failures land on stderr (= the log) as an AGY_ERROR json line
  TOOL_USES="$(grep -c '"state":"ACTIVE","step_type":"tool"' "$GEMINI_STREAM" 2>/dev/null || true)"
  LIMIT_HIT="$(grep 'AGY_ERROR' "$LOG" 2>/dev/null | grep -l 'RESOURCE_EXHAUSTED\|429\|quota\|rate limit' - 2>/dev/null || true)"
fi
discard_work() {  # stop project daemons first, else a running Gradle build re-creates app/build
  ( cd "$WORK" 2>/dev/null && ./gradlew --stop ) >/dev/null 2>&1 || true
  rm -rf "$WORK" "$HOME/.claude/projects/$DASHED"; rm -f "$GEMINI_STREAM"
}
if [ "${TOOL_USES:-0}" -eq 0 ]; then
  discard_work
  fail "agent did no work (0 tool calls, exit=$AGENT_EXIT) - environment error (API/auth/network/limit); run discarded"
fi
if [ -n "$LIMIT_HIT" ]; then
  discard_work
  fail "run truncated by usage/quota limit - discarded; resume the campaign after the limit resets"
fi
# The CLI must have called the model we asked for. gemini-cli 0.60 silently rewrites any
# model name ending in "flash" to its default flash model (gemini-3.5-flash) when the account
# has 3.5 Flash GA access - every sweep-1 gemini row was served by 3.5 while labelled 3.8.
# A served/requested mismatch is a harness fault, not data.
if [ "$AGENT" = "gemini" ]; then
  # the model that carried the most input tokens. gemini-cli also bills ~1% of a run to a side
  # model (gemini-3-flash-preview: classifier / next-speaker calls), so the check is on the
  # dominant model, not on the whole list; run.json keeps the full list as model_served.
  SERVED="$(python3 -c '
import json,sys
m={}
for l in open(sys.argv[1],errors="replace"):
    try: d=json.loads(l)
    except Exception: continue
    if d.get("type")=="result" and isinstance(d.get("stats"),dict) and isinstance(d["stats"].get("models"),dict): m=d["stats"]["models"]
print(max(m, key=lambda k: m[k].get("input_tokens",0)) if m else "")' "$GEMINI_STREAM" 2>/dev/null || true)"
elif [ "$AGENT" = "antigravity" ]; then
  SERVED="$(grep -m1 -o '"init":{"model":"[^"]*"' "$GEMINI_STREAM" | cut -d'"' -f6 || true)"
else
  SERVED="$MODEL_ID"
fi
if [ -n "$SERVED" ] && [ "$SERVED" != "$MODEL_ID" ]; then
  discard_work
  fail "requested model $MODEL_ID but the CLI served $SERVED - run discarded (relabel would be silent data corruption); pick a model id the CLI honours"
fi
[ -z "$SERVED" ] && log "WARNING: could not read the served model from the stream; run.json will say null"

# ---- smoke check ----------------------------------------------------------
mkdir -p "$RUN_DIR"
SMOKE=fail
if ( cd "$WORK" && ./gradlew -q :app:assembleDebug ) >>"$LOG" 2>&1; then
  APK="$WORK/app/build/outputs/apk/debug/app-debug.apk"
  APP_ID="$(grep -o 'applicationId *= *"[^"]*"' "$WORK/app/build.gradle.kts" | sed 's/.*"\(.*\)"/\1/')"
  if [ -f "$APK" ] && adb install -r "$APK" >>"$LOG" 2>&1; then
    adb logcat -b all -c >/dev/null 2>&1 || true   # clear ALL buffers (incl crash) so crash detection is this-run-only
    adb shell monkey -p "$APP_ID" -c android.intent.category.LAUNCHER 1 >>"$LOG" 2>&1 || true
    # verify.sh waits for sync, checks the register populated, writes verification.json + logcat
    "$H/verify.sh" "$APP_ID" "$RUN_DIR" | tee -a "$LOG"
    # smoke = launched without crashing (build+install already succeeded to get here)
    if command -v python3 >/dev/null 2>&1 && [ -f "$RUN_DIR/verification.json" ]; then
      python3 -c "import json,sys; d=json.load(open('$RUN_DIR/verification.json')); sys.exit(0 if d['launched'] and not d['crashed'] else 1)" && SMOKE=pass
    fi
  fi
fi
log "smoke: $SMOKE"

# ---- collect the four artifacts ------------------------------------------
git -C "$WORK" add -A
git -C "$WORK" commit -q -m "$RUN_ID result" --allow-empty
git -C "$WORK" diff --no-ext-diff "$BASELINE" HEAD > "$RUN_DIR/code.diff"
# the template itself builds and launches, so a passing smoke check on an unchanged tree
# means the agent shipped nothing - flag it loudly (kept as data: the agent failed)
DIFF_NOTE=""
[ -s "$RUN_DIR/code.diff" ] || { DIFF_NOTE=" | EMPTY DIFF: agent changed no files; smoke verdict is the untouched template"; log "WARNING: code.diff is empty - the agent shipped nothing"; }

if [ "$AGENT" = "claude" ]; then
  PROJ="$HOME/.claude/projects/$DASHED"
  JSONL="$(ls -t "$PROJ"/*.jsonl 2>/dev/null | head -1 || true)"
  [ -n "$JSONL" ] || fail "no session jsonl found in $PROJ"
  cp "$JSONL" "$RUN_DIR/transcript.jsonl"
else
  [ -s "$GEMINI_STREAM" ] || fail "no gemini stream output captured"
  mv "$GEMINI_STREAM" "$RUN_DIR/transcript.jsonl"
fi

if [ "$AGENT" = "antigravity" ]; then
  # the stream has no tool outputs; agy's own conversation log does. Copy it as a fifth
  # artifact so the extractor can count BUILD FAILED / OperationOutcome from it.
  AGY_CONV="$(grep -m1 -o '"conversation_id":"[^"]*"' "$RUN_DIR/transcript.jsonl" | cut -d'"' -f4 || true)"
  AGY_FULL="$AGY_HOME/brain/$AGY_CONV/.system_generated/logs/transcript_full.jsonl"
  if [ -n "$AGY_CONV" ] && [ -s "$AGY_FULL" ]; then
    cp "$AGY_FULL" "$RUN_DIR/transcript_full.jsonl"
  else
    log "WARNING: agy conversation log not found ($AGY_FULL) - build/validation counts come from the stream only"
  fi
fi

case "$AGENT" in
  claude)      EXTRACTOR="extract-claude.py" ;;
  gemini)      EXTRACTOR="extract-gemini.py" ;;
  antigravity) EXTRACTOR="extract-antigravity.py" ;;
esac
python3 "$H/$EXTRACTOR" \
  --jsonl "$RUN_DIR/transcript.jsonl" --run-dir "$RUN_DIR" --run-id "$RUN_ID" \
  --condition "$COND" --model "$MODEL" --replicate "$((10#$REP))" \
  --scaffold-repo "templates/$TEMPLATE" --baseline "${BASELINE:0:7}" \
  --smoke "$SMOKE" --results "$POC/results.csv" \
  --wall-minutes "$WALL" \
  --notes "gen=2 agent_exit=$AGENT_EXIT${DIFF_NOTE}${AGY_RESUMES:+ | agy_resumes=$AGY_RESUMES}" | tee -a "$LOG"

# ---- teardown (no interesting siblings for the next run) -------------------
# quarantine any global memory a gemini agent left behind (cross-run leak)
if [ "$AGENT" = "gemini" ] && [ -s "$HOME/.gemini/GEMINI.md" ]; then
  mv "$HOME/.gemini/GEMINI.md" "$RUN_DIR/global-memory-left-by-agent.md"
  log "WARNING: agent wrote global ~/.gemini/GEMINI.md - quarantined into runs/$RUN_ID/"
fi
if [ "$AGENT" = "antigravity" ]; then
  # same channel as gemini's global memory, different store: anything new in agy's
  # knowledge dir is quarantined into the run folder, never fed forward
  AGY_KNOWLEDGE_AFTER="$(find "$AGY_HOME/knowledge" -type f ! -name '*.lock' 2>/dev/null || true)"
  if [ -n "$AGY_KNOWLEDGE_AFTER" ]; then
    mkdir -p "$RUN_DIR/knowledge-left-by-agent"
    echo "$AGY_KNOWLEDGE_AFTER" | while read -r F; do mv "$F" "$RUN_DIR/knowledge-left-by-agent/"; done
    log "WARNING: agent wrote to agy's knowledge store - quarantined into runs/$RUN_ID/knowledge-left-by-agent/"
  fi
  [ -s "$HOME/.gemini/GEMINI.md" ] && { mv "$HOME/.gemini/GEMINI.md" "$RUN_DIR/global-memory-left-by-agent.md"; log "WARNING: agent wrote global ~/.gemini/GEMINI.md - quarantined into runs/$RUN_ID/"; }
fi
mv "$WORK" "$H/archive/$RUN_ID"
for PKG in $(adb shell pm list packages com.example | tr -d '\r' | sed 's/package://'); do
  adb uninstall "$PKG" >/dev/null 2>&1 || true
done
log "=== $RUN_ID complete: artifacts in runs/$RUN_ID, work archived ==="
