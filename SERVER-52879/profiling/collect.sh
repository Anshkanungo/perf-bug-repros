#!/usr/bin/env bash
# Runs inside the privileged s52879-prof sidecar (see ../profile.sh). Writes everything to /out.
set -euo pipefail
OUT=/out
SECS=${SECS:-100}; FREQ=${FREQ:-999}; CG=${CG:-fp}; EVENT=${EVENT:-cpu-clock}
OFFCPU=${OFFCPU:-1}; SNAPSHOT=${SNAPSHOT:-0}; SNAP_TIMEOUT=${SNAP_TIMEOUT:-150}; SNAP_BUSY_MS=${SNAP_BUSY_MS:-5}
FG=/opt/FlameGraph

PID=${TARGET_PID:-}
[ -n "$PID" ] || PID=$(pgrep -o -x mongod || pgrep -o mongod || true)
[ -n "$PID" ] || { echo "collect: no mongod process visible" >&2; exit 1; }

mountpoint -q /sys/kernel/tracing || mount -t tracefs nodev /sys/kernel/tracing 2>/dev/null || true
mountpoint -q /sys/kernel/debug || mount -t debugfs nodev /sys/kernel/debug 2>/dev/null || true

{
  echo "date_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "kernel: $(uname -r) $(uname -m)"
  echo "perf: $(perf --version)"
  echo "gdb: $(gdb --version | head -1)"
  echo "perf_event_paranoid: $(cat /proc/sys/kernel/perf_event_paranoid) (bypassed: privileged container)"
  echo "mongod pid (in this pid namespace): $PID"
  echo "mongod exe: $(readlink /proc/$PID/exe)"
  echo "mongod build-id: $(readelf -n /proc/$PID/exe 2>/dev/null | awk '/Build ID/{print $3}')"
  echo "mongod sections: $(readelf -S -W /proc/$PID/exe | grep -oE '\.(symtab|eh_frame|debug_info|gnu_debuglink)' | sort -u | tr '\n' ' ')"
  echo "threads: $(ls /proc/$PID/task | wc -l)"
  echo "event: $EVENT  freq: $FREQ  callgraph: $CG  secs: $SECS"
} > $OUT/environment.txt
for t in /proc/$PID/task/*; do echo "$(basename $t) $(cat $t/comm)"; done > $OUT/threads.txt
SWEEPER_TID=$(awk '$2 ~ /^WTIdleS/ {print $1; exit}' $OUT/threads.txt)
echo "sweeper tid: ${SWEEPER_TID:-not found}" >> $OUT/environment.txt

case "$CG" in
  fp) CGOPT=(--call-graph fp) ;;
  dwarf) CGOPT=(--call-graph dwarf,16384) ;;
  *) CGOPT=(--call-graph "$CG") ;;
esac

# Timestamps: CLOCK_MONOTONIC for both recordings (the kernel rejects CLOCK_REALTIME for tracepoints:
# it is not NMI-safe). The realtime-monotonic offset lets the analysis map samples to epoch time,
# which is what the client latency log uses. Containers share the kernel, so the clocks are the same.
python3 -c 'import time; print("%.6f" % (time.clock_gettime(time.CLOCK_REALTIME) - time.clock_gettime(time.CLOCK_MONOTONIC)))' > $OUT/clock_offset.txt
echo "collect: recording ${SECS}s"
perf record -q -e "$EVENT" -F "$FREQ" "${CGOPT[@]}" -k CLOCK_MONOTONIC -p "$PID" \
  -o $OUT/oncpu.perf.data -- sleep "$SECS" 2> $OUT/oncpu.record.log &
P1=$!
if [ "$OFFCPU" = 1 ]; then
  # sched_waking fires in the waker's context (a mongod thread unlocking the mutex), so a -p recording
  # sees it; sched_wakeup often fires on the target CPU from interrupt context and is then missed.
  WAKE_EV=sched:sched_waking
  perf list 2>/dev/null | grep -q "sched:sched_waking" || WAKE_EV=sched:sched_wakeup
  perf record -q -e sched:sched_switch -e "$WAKE_EV" --call-graph fp -k CLOCK_MONOTONIC -p "$PID" \
    -o $OUT/offcpu.perf.data -- sleep "$SECS" 2> $OUT/offcpu.record.log &
  P2=$!
fi
wait $P1 || { echo "collect: on-CPU perf record failed:" >&2; cat $OUT/oncpu.record.log >&2; exit 1; }
if [ "$OFFCPU" = 1 ] && ! wait $P2; then
  echo "collect: off-CPU perf record failed (continuing without it):" >&2; cat $OUT/offcpu.record.log >&2
  OFFCPU=0; rm -f $OUT/offcpu.perf.data
fi

echo "collect: post-processing on-CPU"
perf script -i $OUT/oncpu.perf.data -F comm,tid,time,ip,sym,dso --no-inline 2>/dev/null > $OUT/oncpu.perf.script
$FG/stackcollapse-perf.pl $OUT/oncpu.perf.script > $OUT/oncpu.folded
$FG/flamegraph.pl --title "mongod on-CPU ($EVENT, all threads)" --width 1600 $OUT/oncpu.folded > $OUT/oncpu_all.svg
grep '^WTIdleS' $OUT/oncpu.folded > $OUT/oncpu_sweeper.folded || true
if [ -s $OUT/oncpu_sweeper.folded ]; then
  $FG/flamegraph.pl --title "WTIdleSessionSweeper thread on-CPU ($EVENT)" --width 1600 \
    $OUT/oncpu_sweeper.folded > $OUT/oncpu_sweeper.svg
fi
# Sweeper thread only; --percentage relative = share of the sweeper's own samples. (perf 6.1's flat
# --children / -g none views misreport percentages with a comm filter, so only the call-graph view is kept;
# inclusive per-function shares are computed by analyze_profile.py from perf script.)
perf report -i $OUT/oncpu.perf.data --stdio --no-children --comms WTIdleS.Sweeper --percentage relative \
  -g caller,0.5,callee --percent-limit 5 2>/dev/null > $OUT/report_sweeper_callgraph.txt || true
perf report -i $OUT/oncpu.perf.data --stdio --no-children --sort comm,sym --percent-limit 1 -g none \
  2>/dev/null > $OUT/report_all_self.txt || true

if [ "$OFFCPU" = 1 ]; then
  echo "collect: post-processing off-CPU"
  perf script -i $OUT/offcpu.perf.data -F comm,pid,tid,time,event,trace,ip,sym,dso --no-inline 2>/dev/null \
    > $OUT/offcpu.perf.script
fi

echo "collect: analysing"
python3 /prof/analyze_profile.py --dir $OUT ${CLIENT_LOG:+--client-log $CLIENT_LOG}
for f in offcpu_sweeps offcpu_long; do
  if [ -s $OUT/$f.folded ]; then
    $FG/flamegraph.pl --title "mongod off-CPU: $f (weight = blocked microseconds)" --countname us \
      --colors io --width 1600 $OUT/$f.folded > $OUT/$f.svg
  fi
done

if [ "$SNAPSHOT" = 1 ] && [ -n "$SWEEPER_TID" ]; then
  echo "collect: waiting (<= ${SNAP_TIMEOUT}s) for a heavy sweep to take a gdb all-thread snapshot"
  SNAP_PID=$PID SNAP_TID=$SWEEPER_TID SNAP_OUT=$OUT SNAP_TIMEOUT=$SNAP_TIMEOUT SNAP_BUSY_MS=$SNAP_BUSY_MS \
    gdb -q -batch -nx -ex "set pagination off" -ex "set confirm off" -ex "set sysroot /proc/$PID/root" \
      -ex "file /proc/$PID/exe" -x /prof/snapshot_gdb.py > $OUT/snapshot.gdb.log 2>&1 || true
  python3 /prof/analyze_snapshot.py --dir $OUT || true
fi

gzip -f $OUT/oncpu.perf.script
[ -f $OUT/offcpu.perf.script ] && gzip -f $OUT/offcpu.perf.script
echo "collect: done"
