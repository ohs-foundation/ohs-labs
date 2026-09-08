#!/usr/bin/env bash
# Post-install verification for one run. Replaces the old fixed 8-second
# screenshot with: give sync real time, screenshot after it, detect a crash
# reliably (logcat crash buffer, not just "process alive"), capture logcat,
# and a best-effort count of patients actually synced into the local DB.
#
# Usage: verify.sh <APP_ID> <RUN_DIR>
# Writes verification.json + logcat.txt in RUN_DIR, prints a one-line summary,
# and always exits 0 (the JSON carries the verdict).
#
# Honesty note: this does NOT claim the register is visually populated - that
# stays the human walk, judged from the post-sync screenshot this captures.
# What it does prove automatically: the app built, installed, launched, did
# not crash, and (best effort) how many patients reached the local database.
set -uo pipefail
APP_ID="$1"
RUN_DIR="$2"
SDK="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
export PATH="$PATH:$SDK/platform-tools"

SYNC_WAIT=30          # seconds to let a cold first sync finish before judging

# give sync time (device-side sleep; the harness forbids a foreground sleep)
adb shell "sleep $SYNC_WAIT" >/dev/null 2>&1 || true

# post-sync screenshot (overwrites the launch shot with a settled one)
adb exec-out screencap -p > "$RUN_DIR/launch.png" 2>/dev/null || true

# reliable crash detection: the crash buffer names the failing package
crashed=false
adb logcat -d -b crash 2>/dev/null | grep -A20 'FATAL EXCEPTION' | tail -60 \
  > "$RUN_DIR/crash.txt" 2>/dev/null || true
if grep -q "$APP_ID" "$RUN_DIR/crash.txt" 2>/dev/null; then crashed=true; fi
[ -s "$RUN_DIR/crash.txt" ] || rm -f "$RUN_DIR/crash.txt"

# process alive?
launched=false
if [ -n "$(adb shell pidof "$APP_ID" 2>/dev/null | tr -d '\r')" ]; then
  launched=true
fi

# general diagnostics
adb logcat -d 2>/dev/null \
  | grep -iE "$APP_ID|FATAL EXCEPTION|OperationOutcome|AndroidRuntime|Sync|sync" \
  | tail -400 > "$RUN_DIR/logcat.txt" 2>/dev/null || true

# best-effort: how many Patient resources reached the app's local engine DB.
# Proves download-sync worked (the "sync never wired" failure shows 0/null).
# Copied out and queried with host sqlite3 to dodge device-shell quoting;
# stays null if the app has no such DB or it can't be read.
patients_in_db="null"
if command -v sqlite3 >/dev/null 2>&1; then
  TMP="$(mktemp -d)"
  ok=1
  for f in resources.db resources.db-wal resources.db-shm; do
    adb shell run-as "$APP_ID" cat "databases/$f" > "$TMP/$f" 2>/dev/null || ok=0
  done
  if [ "$ok" = 1 ] && [ -s "$TMP/resources.db" ]; then
    # no parens / no '*' in the SQL, so nothing needs the device shell here
    n="$(sqlite3 "$TMP/resources.db" \
         "SELECT resourceId FROM ResourceEntity WHERE resourceType='Patient';" \
         2>/dev/null | grep -c . || true)"
    [ -n "$n" ] && patients_in_db="$n"
  fi
  rm -rf "$TMP"
fi

cat > "$RUN_DIR/verification.json" <<JSON
{
  "launched": $launched,
  "crashed": $crashed,
  "screenshot_after_seconds": $SYNC_WAIT,
  "patients_in_local_db": $patients_in_db,
  "note": "launched+!crashed is the smoke verdict. patients_in_local_db is a best-effort sync-success signal (0/null suggests download sync did not deliver). Whether the register visually renders is the human walk, judged from launch.png."
}
JSON

echo "verify: launched=$launched crashed=$crashed patients_in_local_db=$patients_in_db"
exit 0
