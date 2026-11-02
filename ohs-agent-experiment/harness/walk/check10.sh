#!/bin/bash
# check10.sh : check 10, "still uploads it after the app is closed".
# Run prep.sh first and let the register load. The script turns on airplane
# mode, waits while you save a visit by hand, confirms the save, closes the
# app without force-stop, restores the network and watches the server for
# 5 minutes without reopening the app.
W=$(cd "$(dirname "$0")" && pwd)
ADB=${ADB:-~/Library/Android/sdk/platform-tools/adb}
P=$($ADB shell pm list packages com.example | tr -d '\r' | sed 's/package://' | head -1)
BASE=$(bash "$W/counts.sh"); echo "baseline: $BASE"
bash "$W/input.sh" offline
read -r -p "Airplane mode is on. Save one visit in the app, then press Enter. "
if python3 "$W/ui.py" | grep -q EditText; then
  echo "SAVE NOT CONFIRMED (a form is still open). Aborting."; bash "$W/input.sh" online; exit 2
fi
bash "$W/input.sh" home; sleep 2
$ADB shell am kill $P   # ends the process but keeps scheduled WorkManager work, unlike force-stop
bash "$W/input.sh" online
echo "network on, app closed and not reopened"
for s in 30 60 90 120 180 240 300; do
  sleep $(( s - ${prev:-0} )); prev=$s
  NOW=$(bash "$W/counts.sh"); echo "$s s: $NOW"
  [ "$NOW" != "$BASE" ] && { echo "RESULT: PASS at ${s}s"; exit 0; }
done
echo "RESULT: FAIL, nothing reached the server in 5 minutes"; exit 1
