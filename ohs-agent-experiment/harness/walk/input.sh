#!/bin/bash
# Emulator input helpers for walking an app. Coordinates come from ui.py.
#   input.sh tap X Y          tap
#   input.sh type X Y TEXT    tap a field, clear it, type TEXT, hide the keyboard
#   input.sh down | up        scroll the screen down or up
#   input.sh back | home      Back or Home key
#   input.sh offline | online airplane mode on or off
#   input.sh restart          force-stop and relaunch the app
ADB=${ADB:-~/Library/Android/sdk/platform-tools/adb}
pkg() { $ADB shell pm list packages com.example | tr -d '\r' | sed 's/package://' | head -1; }
hidekb() { $ADB shell dumpsys input_method | grep -q 'mInputShown=true' && $ADB shell input keyevent 4; }
case $1 in
  tap) $ADB shell input tap $2 $3 ;;
  type) $ADB shell input tap $2 $3; sleep 0.5; $ADB shell input keyevent 123
        for i in $(seq 30); do $ADB shell input keyevent 67; done
        $ADB shell input text "$4"; hidekb ;;
  down) $ADB shell input swipe 700 2200 700 900 400 ;;
  up) $ADB shell input swipe 700 900 700 2200 400 ;;
  back) $ADB shell input keyevent 4 ;;
  home) $ADB shell input keyevent 3 ;;
  offline) $ADB shell cmd connectivity airplane-mode enable ;;
  online) $ADB shell cmd connectivity airplane-mode disable ;;
  restart) P=$(pkg); $ADB shell am force-stop $P; $ADB shell am force-stop com.google.android.gms
           sleep 1; $ADB shell monkey -p $P -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 ;;
  *) sed -n '2,8p' $0; exit 2 ;;
esac
