#!/usr/bin/env bash
# Profile a running mongod during a WT-7264 stall with a privileged perf/gdb sidecar container.
#
#   ./profile.sh                                  # mongod container w7264-mongod (run.sh --profile does this for you)
#   ./profile.sh --container my-mongod            # any mongod container
#   ./profile.sh --host-pid 12345                 # a mongod running natively on this (Linux) host
#   ./profile.sh --secs 60 --callgraph dwarf      # longer window, DWARF unwinding instead of frame pointers
#   ./profile.sh --event cycles                   # hardware PMU event (bare-metal x86-64); default cpu-clock
#   ./profile.sh --snapshot                       # + gdb all-thread snapshot when a conn thread spins alone
#   ./profile.sh --snapshot --snapshot-at 8       # + gdb snapshot 8 s after start, unconditionally (control)
#
# What it captures (CLOCK_MONOTONIC timestamps plus the offset to epoch time, so samples line up with the
# client's per-call log):
#   1. on-CPU : perf record -e cpu-clock -F 999 --call-graph fp -p <mongod>   (all threads)
#   2. off-CPU: perf record -e sched:sched_switch -e sched:sched_waking --call-graph fp -p <mongod>
#   3. optional gdb all-thread backtrace, taken *during* the recording when a connection thread has been
#      ~100% on-CPU for --snapshot-busy-s seconds while at most 6 connection threads are busy (the stall),
#      or at a fixed time with --snapshot-at.
# Outputs: <out>/profile_summary.md, oncpu_all.svg, oncpu_stuck.svg, snapshot_summary.md, folded stacks,
#          raw perf.data / perf script (git-ignored).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROF_IMG=w7264-prof:1
SIDECAR=w7264-prof
CONTAINER=w7264-mongod
HOST_PID=""
OUT=""
SECS=45
FREQ=999
CG=fp
EVENT=cpu-clock
OFFCPU=1
SNAPSHOT=0
SNAP_MODE=stall
SNAP_TIMEOUT=""
SNAP_BUSY_S=2
CLIENT_LOG=""

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    --container) CONTAINER="$2"; shift 2 ;;
    --host-pid) HOST_PID="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --secs) SECS="$2"; shift 2 ;;
    --freq) FREQ="$2"; shift 2 ;;
    --callgraph) CG="$2"; shift 2 ;;
    --event) EVENT="$2"; shift 2 ;;
    --no-offcpu) OFFCPU=0; shift ;;
    --snapshot) SNAPSHOT=1; shift ;;
    --snapshot-at) SNAPSHOT=1; SNAP_MODE="at:$2"; shift 2 ;;
    --snapshot-timeout) SNAP_TIMEOUT="$2"; shift 2 ;;
    --snapshot-busy-s) SNAP_BUSY_S="$2"; shift 2 ;;
    --client-log) CLIENT_LOG="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
log() { printf '[%s] profile: %s\n' "$(date +%H:%M:%S)" "$*"; }
[ -n "$SNAP_TIMEOUT" ] || SNAP_TIMEOUT=$((SECS - 5))

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
log "sidecar up ($SIDECAR, ${PIDNS[*]}); recording ${SECS}s, event=$EVENT, call graph=$CG, off-CPU=$OFFCPU, snapshot=$SNAPSHOT ($SNAP_MODE)"
# Watchdog: if collection hangs (e.g. a stuck gdb attach), remove the sidecar after SECS + 900 s so the
# caller (run.sh) is never blocked forever. Removing the sidecar also detaches gdb/perf from mongod.
( sleep $((SECS + 900)); log "watchdog: collection took too long, removing $SIDECAR"; docker rm -f "$SIDECAR" >/dev/null 2>&1 ) &
WATCHDOG=$!
rc=0
docker exec ${EXTRA[@]+"${EXTRA[@]}"} -e TARGET_PID="$HOST_PID" -e SECS="$SECS" -e FREQ="$FREQ" -e CG="$CG" -e EVENT="$EVENT" \
  -e OFFCPU="$OFFCPU" -e SNAPSHOT="$SNAPSHOT" -e SNAP_MODE="$SNAP_MODE" -e SNAP_TIMEOUT="$SNAP_TIMEOUT" \
  -e SNAP_BUSY_S="$SNAP_BUSY_S" "$SIDECAR" bash /prof/collect.sh || rc=$?
kill "$WATCHDOG" 2>/dev/null || true
[ "$rc" = 0 ] || { log "collection failed (exit $rc)"; exit "$rc"; }
log "done: $OUT/profile_summary.md"
