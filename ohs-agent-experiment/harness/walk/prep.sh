#!/bin/bash
# prep.sh <run_id> : fresh seeded server, clean device, install the run's APK, launch it online.
set -e
RUN=$1; [ -n "$RUN" ] || { echo "usage: prep.sh <run_id>"; exit 2; }
W=$(cd "$(dirname "$0")" && pwd); POC=$(cd "$W/../.." && pwd)
ADB=${ADB:-~/Library/Android/sdk/platform-tools/adb}
APK=$POC/harness/archive/$RUN/app/build/outputs/apk/debug/app-debug.apk
[ -f "$APK" ] || { echo "no APK at $APK"; exit 2; }
( cd "$POC" && docker-compose down >/dev/null 2>&1 && docker-compose up -d >/dev/null 2>&1 )
"$POC/load-seed.sh" >/dev/null || { echo "seed load failed"; exit 1; }
for p in $($ADB shell pm list packages com.example | tr -d '\r' | sed 's/package://'); do $ADB uninstall $p >/dev/null; done
$ADB install "$APK" >/dev/null
bash "$W/input.sh" online
$ADB logcat -c
bash "$W/input.sh" restart
echo "installed $RUN, launched online. server: $(bash "$W/counts.sh")"
