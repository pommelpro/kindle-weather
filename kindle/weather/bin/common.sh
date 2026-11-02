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

show() {  # $1 = "full" for a flashing refresh
    [ -s "$IMG" ] || return 1
    if [ "$1" = "full" ]; then
        eips -c; eips -c
        eips -f -g "$IMG" >/dev/null 2>&1
    else
        eips -g "$IMG" >/dev/null 2>&1
    fi
}
