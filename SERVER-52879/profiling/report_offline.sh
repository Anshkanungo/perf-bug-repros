#!/usr/bin/env bash
# Regenerate the sweeper perf reports for a finished profile, outside the live sidecar.
# perf then needs the profiled binaries: pass a directory that mirrors their paths (a "symfs"), e.g.
# /symfs/usr/bin/mongod and /symfs/lib/aarch64-linux-gnu/libc.so.6 copied from the same mongo image.
# Runs inside the s52879-prof image:
#   docker run --rm -v <profile dir>:/p -v <symfs dir>:/symfs:ro -v <this dir>:/prof:ro s52879-prof:1 \
#     bash /prof/report_offline.sh
set -euo pipefail
R=(perf report -i /p/oncpu.perf.data --symfs /symfs --stdio --comms WTIdleS.Sweeper --percentage relative)
"${R[@]}" --no-children -g caller,0.5,callee --percent-limit 5 2>/dev/null > /p/report_sweeper_callgraph.txt
echo "report_offline: wrote report_sweeper_callgraph.txt"
