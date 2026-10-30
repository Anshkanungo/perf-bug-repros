#!/usr/bin/env bash
# Profile a running mongod during SERVER-52879 spikes with a privileged perf/gdb sidecar container.
#
#   ./profile.sh                                  # mongod container s52879-mongod (started by run.sh --keep or --profile)
#   ./profile.sh --container my-mongod            # any mongod container
#   ./profile.sh --host-pid 12345                 # a mongod running natively on this (Linux) host
#   ./profile.sh --secs 120 --callgraph dwarf     # longer window, DWARF unwinding instead of frame pointers
#   ./profile.sh --event cycles                   # hardware PMU event (bare-metal x86-64); default cpu-clock
#
# What it captures (all with CLOCK_REALTIME timestamps, so they line up with the client's latency log):
#   1. on-CPU : perf record -e cpu-clock -F 999 --call-graph fp -p <mongod>
#   2. off-CPU: perf record -e sched:sched_switch -e sched:sched_wakeup --call-graph fp -p <mongod>
#               (where threads block, and for how long), run concurrently with 1.
#   3. optional --snapshot: gdb all-thread backtrace taken *during* a heavy idle-session sweep, triggered
#      when the WTIdleSessionSweeper thread has been on-CPU for >= 5 ms out of the last 10 ms.
# Outputs: <out>/profile_summary.md, flame graphs (*.svg), folded stacks, perf report text,
#          raw perf.data / perf script (git-ignored).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROF_IMG=s52879-prof:1
SIDECAR=s52879-prof
CONTAINER=s52879-mongod
HOST_PID=""
OUT=""
SECS=100
FREQ=999
CG=fp
EVENT=cpu-clock
OFFCPU=1
SNAPSHOT=0
SNAP_TIMEOUT=150
SNAP_BUSY_MS=5
CLIENT_LOG=""

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    --container) CONTAINER="$2"; shift 2 ;;
    --host-pid) HOST_PID="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --secs) SECS="$2"; shift 2 ;;
    --freq) FREQ="$2"; shift 2 ;;
    --callgraph) CG="$2"; shift 2 ;;
    --event) EVENT="$2"; shift 2 ;;
    --no-offcpu) OFFCPU=0; shift ;;
    --snapshot) SNAPSHOT=1; shift ;;
    --snapshot-timeout) SNAP_TIMEOUT="$2"; shift 2 ;;
    --snapshot-busy-ms) SNAP_BUSY_MS="$2"; shift 2 ;;
    --client-log) CLIENT_LOG="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
log() { printf '[%s] profile: %s\n' "$(date +%H:%M:%S)" "$*"; }

[ -n "$OUT" ] || OUT="$HERE/results/profile-$(date +%Y%m%dT%H%M%S)"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"

if ! docker image inspect "$PROF_IMG" >/dev/null 2>&1; then
  base=debian:bookworm-slim
  docker pull -q "$base" >/dev/null 2>&1 || base=public.ecr.aws/docker/library/debian:bookworm-slim
  log "building $PROF_IMG (base $base)"
  docker build -q -t "$PROF_IMG" --build-arg BASE="$base" -f "$HERE/profiling/Dockerfile" "$HERE/profiling" >/dev/null
fi

if [ -n "$HOST_PID" ]; then PIDNS=(--pid=host); else PIDNS=(--pid="container:$CONTAINER"); fi
docker rm -f "$SIDECAR" >/dev/null 2>&1 || true
trap 'docker rm -f "$SIDECAR" >/dev/null 2>&1 || true' EXIT
# --privileged: perf_event_open / tracefs / ptrace without changing any host sysctl.
docker run -d --name "$SIDECAR" --privileged "${PIDNS[@]}" \
  -v "$HERE/profiling:/prof:ro" -v "$OUT:/out" \
  "$PROF_IMG" sleep infinity >/dev/null

EXTRA=()
if [ -n "$CLIENT_LOG" ]; then
  docker cp "$CLIENT_LOG" "$SIDECAR:/tmp/client.log"
  EXTRA=(-e CLIENT_LOG=/tmp/client.log)
fi
log "sidecar up ($SIDECAR, ${PIDNS[*]}); recording ${SECS}s, event=$EVENT, call graph=$CG, off-CPU=$OFFCPU, snapshot=$SNAPSHOT"
docker exec ${EXTRA[@]+"${EXTRA[@]}"} -e TARGET_PID="$HOST_PID" -e SECS="$SECS" -e FREQ="$FREQ" -e CG="$CG" -e EVENT="$EVENT" \
  -e OFFCPU="$OFFCPU" -e SNAPSHOT="$SNAPSHOT" -e SNAP_TIMEOUT="$SNAP_TIMEOUT" -e SNAP_BUSY_MS="$SNAP_BUSY_MS" \
  "$SIDECAR" bash /prof/collect.sh
log "done: $OUT/profile_summary.md"
