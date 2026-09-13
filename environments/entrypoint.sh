#!/bin/sh
# Retain bounded tmpfs output until the supervisor has durably collected it.
mkdir -p /work/output
if [ "$STAGED_INPUTS" = "1" ]; then
    mkdir -p /work/input
    until [ -f /work/input-ready ]; do sleep 1; done
fi
/usr/bin/timeout -s TERM -k 5 "$WALL_SECONDS" Rscript /app/run.R > /work/output/stdout.log 2> /work/output/stderr.log
result=$?
printf '%s\n' "$result" > /work/output/exit-code
# Atomic completion signal is created only after every output is closed.
printf 'done\n' > /work/done
sleep 3600
