#!/bin/sh
DIR="/mnt/us/extensions/weather"
. "$DIR/bin/config.sh"
IMG="$DIR/weather.png"
TMP="$DIR/weather.tmp"
LOG="$DIR/weather.log"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }

wifi_up() {
    i=0
    while [ $i -lt 60 ]; do
        state="$(lipc-get-prop com.lab126.wifid cmState 2>/dev/null)"
        [ "$state" = "CONNECTED" ] && return 0
        [ $i -eq 10 ] && lipc-set-prop com.lab126.wifid enable 1 2>/dev/null
        sleep 2; i=$((i + 1))
    done
    return 1
}

fetch() {
    rm -f "$TMP"
    # add a changing value so no cache hands us an old picture
    url="$IMAGE_URL?t=$(date +%s)"
    if curl -fsSL --max-time 60 -o "$TMP" "$url" 2>>"$LOG" \
       || curl -fsSLk --max-time 60 -o "$TMP" "$url" 2>>"$LOG"; then
        [ -s "$TMP" ] && mv "$TMP" "$IMG" && return 0
    fi
    log "download failed"
    return 1
}

# Front light: read the percent GitHub publishes next to the picture.
LIGHT_URL="${IMAGE_URL%/*}/light.txt"
set_light() {
    url="$LIGHT_URL?t=$(date +%s)"
    pct="$(curl -fsSL --max-time 30 "$url" 2>/dev/null || curl -fsSLk --max-time 30 "$url" 2>/dev/null)"
    pct="$(echo "$pct" | tr -dc 0-9)"
    [ -n "$pct" ] || return 1
    [ "$pct" -gt 100 ] && pct=100
    # Kindle light levels run 0-24
    lipc-set-prop com.lab126.powerd flIntensity $((pct * 24 / 100)) 2>/dev/null && return 0
    for d in /sys/class/backlight/*; do
        max="$(cat "$d/max_brightness" 2>/dev/null)" || continue
        echo $((pct * max / 100)) > "$d/brightness"
    done
}

show() {  # $1 = "full" for a flashing refresh
    [ -s "$IMG" ] || return 1
    if [ "$1" = "full" ]; then
        eips -c; eips -c
        eips -f -g "$IMG" >/dev/null 2>&1
    else
        eips -g "$IMG" >/dev/null 2>&1
    fi
}
