#!/bin/sh
# Launch the loop fully detached (own session), so it survives the Kindle
# interface shutting down - otherwise it gets killed along with KUAL.
LOOP=/mnt/us/extensions/weather/bin/loop.sh
if command -v setsid >/dev/null 2>&1; then
    setsid sh "$LOOP" </dev/null >/dev/null 2>&1 &
elif command -v start-stop-daemon >/dev/null 2>&1; then
    start-stop-daemon -S -b -x /bin/sh -- "$LOOP"
else
    nohup sh "$LOOP" </dev/null >/dev/null 2>&1 &
fi
