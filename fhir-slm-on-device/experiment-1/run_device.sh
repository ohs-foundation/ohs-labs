#!/bin/bash
# Run one prompt on the connected device and append the SlmBench line to results/device-runs.txt.
# Usage: ./run_device.sh <data-file> <max_tokens> [cpu|gpu]
# The prompt is a fixed instruction followed by the data, so replies stay short and comparable.
set -e
FILE=$1; MAX=$2; BACKEND=${3:-cpu}
ADB=${ADB:-~/Library/Android/sdk/platform-tools/adb}
PKG=dev.ohs.slm.smoketest
NAME=$(echo "$FILE" | sed 's#^data/##; s#/#_#g')
TMP=$(mktemp)
{ echo "Summarize this patient record in 3 bullet points."; echo; cat "$FILE"; } > "$TMP"
$ADB push "$TMP" /data/local/tmp/$NAME >/dev/null
$ADB shell run-as $PKG cp /data/local/tmp/$NAME files/$NAME
$ADB shell rm /data/local/tmp/$NAME
rm "$TMP"
$ADB logcat -c
$ADB shell am start -S -n $PKG/.MainActivity --es prompt_file "$NAME" --ei max_tokens "$MAX" --es backend "$BACKEND" >/dev/null
for _ in $(seq 1 360); do
  sleep 5
  LINE=$($ADB logcat -d -s SlmBench | grep "prompt=" | sed 's/.*SlmBench: //')
  [ -n "$LINE" ] && break
done
if [ -z "$LINE" ]; then
  # No result in 30 minutes: record what the app process looks like, then stop it.
  LINE="prompt=$NAME max_tokens=$MAX error=timeout app_alive=$($ADB shell pidof $PKG | tr -d '\r' | grep -q . && echo yes || echo no)"
  $ADB shell am force-stop $PKG
fi
echo "$LINE" | tee -a results/device-runs.txt
# Keep what the model wrote, for checking the answers later.
mkdir -p results/replies
$ADB shell run-as $PKG cat "files/$NAME.reply.txt" > "results/replies/$NAME.txt" 2>/dev/null || true
