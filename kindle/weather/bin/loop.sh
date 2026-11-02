#!/bin/sh
# Turns the Kindle into a dedicated weather screen until it is restarted.
. /mnt/us/extensions/weather/bin/common.sh
sleep 3
log "starting display loop"

# Keep the Kindle awake and turn off its normal interface.
lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
stop framework 2>/dev/null || /etc/init.d/framework stop 2>/dev/null
initctl stop webreader 2>/dev/null
sleep 5

n=0
while true; do
    if wifi_up && fetch; then
        if [ $((n % FULL_REFRESH_EVERY)) -eq 0 ]; then show full; else show; fi
        n=$((n + 1))
    else
        log "no update this round (wifi or download problem)"
    fi
    sleep $((REFRESH_MINUTES * 60))
done
