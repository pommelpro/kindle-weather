#!/bin/sh
# Hand off to the background loop so KUAL can close.
nohup sh /mnt/us/extensions/weather/bin/loop.sh >/dev/null 2>&1 &
