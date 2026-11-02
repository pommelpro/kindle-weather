#!/bin/sh
# Turns the Kindle into a dedicated weather screen until it is restarted.
. /mnt/us/extensions/weather/bin/common.sh
trap '' HUP          # ignore hang-up signals from the interface closing
sleep 3
log "starting display loop (pid $$)"

# Keep the Kindle awake and turn off its normal interface.
lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
# The interface's job name differs between firmware versions, so try each.
for job in lab126_gui framework; do
    if stop "$job" >/dev/null 2>&1; then log "stopped $job"; fi
done
[ -x /etc/init.d/framework ] && /etc/init.d/framework stop >/dev/null 2>&1 && log "stopped framework (init.d)"
initctl stop webreader >/dev/null 2>&1
sleep 5
log "still running; interface jobs now: $(initctl list 2>/dev/null | grep -E 'lab126_gui|framework|pillow' | tr '\n' ' ')"

# Show the last picture right away so the screen is never blank.
show full

n=0
while true; do
    waited=0
    if wifi_up && request_redraw; then
        sleep "$REDRAW_WAIT"      # give GitHub time to draw and publish
        waited=$REDRAW_WAIT
    fi
    if wifi_up && fetch; then
        if [ $((n % FULL_REFRESH_EVERY)) -eq 0 ]; then show full; else show; fi
        n=$((n + 1))
        set_light
        log "updated"
        rest=$((REFRESH_MINUTES * 60 - waited))
        [ "$rest" -gt 60 ] || rest=60
        sleep "$rest"
    else
        log "no update this round (wifi or download problem), retrying in 1 minute"
        sleep 60
    fi
done
