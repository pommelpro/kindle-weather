#!/bin/sh
# Download and show the picture once, leaving the normal Kindle UI running.
. /mnt/us/extensions/weather/bin/common.sh
log "test run"
if wifi_up && fetch; then
    sleep 3        # let KUAL's menu close first
    show full
else
    eips 2 2 "Weather: could not download. See extensions/weather/weather.log"
fi
