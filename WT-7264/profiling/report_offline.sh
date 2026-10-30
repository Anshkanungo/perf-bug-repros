#!/usr/bin/env bash
# Regenerate perf call-graph reports for a finished profile, outside the live sidecar.
# perf then needs the profiled binaries: pass a directory that mirrors their paths (a "symfs"), e.g.
# /symfs/usr/bin/mongod and /symfs/lib/aarch64-linux-gnu/libc.so.6 copied from the same mongo image:
#   id=$(docker create mongo:5.0.33); mkdir -p symfs/usr/bin && docker cp $id:/usr/bin/mongod symfs/usr/bin/
#   docker rm -v $id
# Runs inside the w7264-prof image (TID = a stuck connection thread from profile_summary.md):
#   docker run --rm -v <profile dir>:/p -v <symfs dir>:/symfs:ro -v <this dir>:/prof:ro -e TID=123 \
#     w7264-prof:1 bash /prof/report_offline.sh
set -euo pipefail
R=(perf report -i /p/oncpu.perf.data --symfs /symfs --stdio --percentage relative)
[ -n "${TID:-}" ] && R+=(--tid "$TID")
"${R[@]}" --children -g caller,0.5,callee --percent-limit 5 2>/dev/null > /p/report_callgraph${TID:+_tid$TID}.txt
echo "report_offline: wrote report_callgraph${TID:+_tid$TID}.txt"
