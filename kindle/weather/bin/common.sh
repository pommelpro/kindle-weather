#!/bin/sh
DIR="/mnt/us/extensions/weather"
. "$DIR/bin/config.sh"
IMG="$DIR/weather.png"
TMP="$DIR/weather.tmp"
LOG="$DIR/weather.log"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }

wifi_state() { lipc-get-prop com.lab126.wifid cmState 2>/dev/null; }

# wait up to $1 seconds for Wi-Fi to report CONNECTED
wifi_wait() {
    t=0
    while [ "$t" -lt "$1" ]; do
        [ "$(wifi_state)" = "CONNECTED" ] && return 0
        sleep 3; t=$((t + 3))
    done
    return 1
}

# Make sure Wi-Fi is connected, escalating through stronger reconnect steps.
wifi_up() {
    wifi_wait 30 && return 0
    log "wifi is '$(wifi_state)'; trying to reconnect"
    for step in enable radio wpa; do
        case "$step" in
            enable) lipc-set-prop com.lab126.wifid enable 1 ;;
            radio)  lipc-set-prop com.lab126.cmd wirelessEnable 0; sleep 5
                    lipc-set-prop com.lab126.cmd wirelessEnable 1 ;;
            wpa)    command -v wpa_cli >/dev/null 2>&1 || continue
                    wpa_cli -i wlan0 reconnect ;;
        esac >/dev/null 2>&1
        if wifi_wait 60; then log "wifi back after '$step'"; return 0; fi
    done
    log "wifi still '$(wifi_state)' after reconnect steps"
    return 1
}

# Last resort: briefly run the normal Kindle interface, which knows how to
# reconnect to Wi-Fi, then shut it down again.
wifi_rescue() {
    log "wifi down for a while; starting the Kindle interface to reconnect"
    start lab126_gui >/dev/null 2>&1 || start framework >/dev/null 2>&1
    if wifi_wait 180; then log "wifi back with the interface running"; fi
    for job in lab126_gui framework; do stop "$job" >/dev/null 2>&1; done
    sleep 5
    show full
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

same_file() {
    if command -v cmp >/dev/null 2>&1; then cmp -s "$1" "$2"; return; fi
    [ "$(md5sum < "$1")" = "$(md5sum < "$2")" ]
}

# After asking for a redraw at time $1 (seconds since 1970), wait until the website
# serves a picture made after that moment, then download it. GitHub Pages can take
# a few minutes to start serving a new picture.
# Sets WAITED to the seconds spent. Returns 1 only if nothing could be downloaded.
STAMP_URL="${IMAGE_URL%/*}/stamp.txt"
fetch_new() {
    asked="$1"
    WAITED=0
    sleep 30; WAITED=30
    while [ "$WAITED" -le 660 ]; do
        url="$STAMP_URL?t=$(date +%s)"
        made="$(curl -fsSL --max-time 30 "$url" 2>/dev/null || curl -fsSLk --max-time 30 "$url" 2>/dev/null)"
        made="$(echo "$made" | tr -dc 0-9)"
        # allow a minute of slack in case the Kindle's clock is a little off
        if [ -n "$made" ] && [ "$made" -ge $((asked - 60)) ]; then
            if fetch; then log "new picture after ${WAITED}s"; return 0; fi
        fi
        sleep 20; WAITED=$((WAITED + 20))
    done
    log "new picture not published after ${WAITED}s; showing what's there"
    fetch
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

# Ask GitHub to redraw the picture now (needs GITHUB_TOKEN in config.sh).
request_redraw() {
    [ -n "$GITHUB_TOKEN" ] || return 1
    api="https://api.github.com/repos/$GITHUB_REPO/actions/workflows/render.yml/dispatches"
    for k in "" "-k"; do
        code="$(curl -sS $k --max-time 30 -o /dev/null -w '%{http_code}' -X POST \
            -H "Accept: application/vnd.github+json" \
            -H "Authorization: Bearer $GITHUB_TOKEN" \
            -H "User-Agent: kindle-weather" \
            -d '{"ref":"main"}' "$api" 2>>"$LOG")"
        [ "$code" = "204" ] && return 0
        [ "$code" = "000" ] || break   # got an answer; retrying without TLS checks won't help
    done
    log "redraw request failed (HTTP $code)"
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
