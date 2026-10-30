#!/usr/bin/env bash
# The exact run sequence behind results/ (see PLAN.md, "Run order"). Each block is independent:
#   ./campaign.sh A            # primary A/B: 5.0.33, barrier workload (W1), prefix_search off vs on, 5 + 5 runs
#   ./campaign.sh U V R R1 B C X P
# Blocks:
#   A   5.0.33 W1 off/on x5 (alternating, cap 600 s)       U   5.0.33 W0 off/on x10 (cap 300 s)
#   P   profiling: 5.0.33 W1 off (until a stall is captured, <= 3 tries), then 5.0.33 W1 on
#   V   4.4.30 W0 off/on x3 (cap 300 s)                     R   4.4.2 / 4.4.1 / 4.2.24 with W0 x3 (cap 300 s)
#   R1  4.4.2 / 4.4.1 / 4.2.24 with W1 x3 (cap 300 s)       C   5.0.33 W1 off, non-unique indexes x2
#   X   SERVER-67350-like pymongo variant: 5.0.33 off x2, 5.0.33 on x2, 4.2.24 x1
#   Z   resume block after the 2026-10-28 pause: the missing R/R1 runs (see PLAN.md changes 5-6)
# Afterwards: ./analyze.sh results/runs/[A-Z]* --compare-out results --reuse
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Power policy (PLAN.md changes 7 and 9). On a Mac laptop, battery power turns on Low Power Mode, which slows
# the CPU; run.sh records the power source and Low Power Mode at the start and end of every run either way.
#   POWER_POLICY=min-charge (default): run on AC or battery, but never start a run on battery below
#                                      MIN_CHARGE percent (default 15); the campaign then stops cleanly.
#   POWER_POLICY=wait-ac             : start a run only on AC power (re-check every 30 s; flag after 20 min).
#   POWER_POLICY=off                 : no check. Hosts without pmset (Linux) skip the check automatically.
power_check() {
  command -v pmset >/dev/null 2>&1 || return 0
  case "${POWER_POLICY:-min-charge}" in
    off) return 0 ;;
    wait-ac)
      local t0 waited warned=0
      t0=$(date +%s)
      until pmset -g batt 2>/dev/null | head -1 | grep -q "AC Power"; do
        waited=$(( $(date +%s) - t0 ))
        printf '[%s] power guard: on battery power, waiting for AC (%s s so far)\n' "$(date +%H:%M:%S)" "$waited"
        if [ "$waited" -ge 1200 ] && [ "$warned" = 0 ]; then
          printf '[%s] POWER GUARD: still on battery after 20 min\n' "$(date +%H:%M:%S)"; warned=1
        fi
        sleep 30
      done ;;
    *)
      if pmset -g batt 2>/dev/null | head -1 | grep -q "Battery Power"; then
        local chg
        chg=$(pmset -g batt 2>/dev/null | sed -n 2p | grep -oE '[0-9]+%' | head -1 | tr -d '%')
        if [ -n "$chg" ] && [ "$chg" -lt "${MIN_CHARGE:-15}" ]; then
          printf '[%s] BATTERY STOP: on battery at %s%% (< %s%%); not starting another run\n' \
            "$(date +%H:%M:%S)" "$chg" "${MIN_CHARGE:-15}"
          exit 3
        fi
      fi ;;
  esac
}

run() {
  power_check
  printf '[%s] ./run.sh %s\n' "$(date +%H:%M:%S)" "$*"
  "$HERE/run.sh" "$@" 2>&1 | grep -E 'stalled calls|ERROR|CAP reached|profiler' || true
}

stalled() {  # did the run at results/runs/$1 have a stalled call?
  grep -q '"stalled": true' "$HERE/results/runs/$1/summary.json" 2>/dev/null
}

for blk in "$@"; do
  case "$blk" in
    A) for i in 1 2 3 4 5; do
         run 5.0.33 --sync-start --prefix-search off --cap 600 --label "A$i-5.0.33-W1-off"
         run 5.0.33 --sync-start --prefix-search on --cap 600 --label "A$i-5.0.33-W1-on"
       done ;;
    U) for i in 01 02 03 04 05 06 07 08 09 10; do
         run 5.0.33 --prefix-search off --cap 300 --label "U$i-5.0.33-W0-off"
         run 5.0.33 --prefix-search on --cap 300 --label "U$i-5.0.33-W0-on"
       done ;;
    P) for i in 1 2 3; do
         run 5.0.33 --sync-start --prefix-search off --cap 300 --profile \
             --profile-args "--secs 40 --snapshot" --label "P$i-5.0.33-W1-off-profile"
         stalled "P$i-5.0.33-W1-off-profile" && break
       done
       run 5.0.33 --sync-start --prefix-search on --cap 300 --profile \
           --profile-args "--secs 25 --snapshot-at 9" --label "P1-5.0.33-W1-on-profile" ;;
    V) for i in 1 2 3; do
         run 4.4.30 --prefix-search off --cap 300 --label "V$i-4.4.30-W0-off"
         run 4.4.30 --prefix-search on --cap 300 --label "V$i-4.4.30-W0-on"
       done ;;
    R) for i in 1 2 3; do
         run 4.4.2 --cap 300 --label "R$i-4.4.2-W0"
         run 4.4.1 --cap 300 --label "R$i-4.4.1-W0"
         run 4.2.24 --cap 300 --label "B$i-4.2.24-W0"
       done ;;
    R1) for i in 1 2 3; do
         run 4.4.2 --sync-start --cap 300 --label "RS$i-4.4.2-W1"
         run 4.4.1 --sync-start --cap 300 --label "RS$i-4.4.1-W1"
         run 4.2.24 --sync-start --cap 300 --label "BS$i-4.2.24-W1"
       done ;;
    C) for i in 1 2; do
         run 5.0.33 --sync-start --prefix-search off --non-unique --cap 300 --label "C$i-5.0.33-W1-off-nonunique"
       done ;;
    X) for i in 1 2; do
         run 5.0.33 --workload 67350 --prefix-search off --cap 300 --label "X$i-5.0.33-W2-off"
         run 5.0.33 --workload 67350 --prefix-search on --cap 300 --label "X$i-5.0.33-W2-on"
       done
       run 4.2.24 --workload 67350 --cap 300 --label "X1-4.2.24-W2" ;;
    Z) # Resume after the 2026-10-28 pause (PLAN.md changes 5 and 6): the runs of blocks R and R1 that are
       # still missing, with fresh labels for the ones excluded (host sleep) or aborted (pause).
       run 4.4.2 --cap 300 --label "R4-4.4.2-W0"
       run 4.4.1 --cap 300 --label "R4-4.4.1-W0"
       run 4.2.24 --cap 300 --label "B4-4.2.24-W0"
       for i in 3 4 5; do run 4.4.2 --sync-start --cap 300 --label "RS$i-4.4.2-W1"; done
       for i in 2 3; do
         run 4.4.1 --sync-start --cap 300 --label "RS$i-4.4.1-W1"
         run 4.2.24 --sync-start --cap 300 --label "BS$i-4.2.24-W1"
       done ;;
    *) echo "unknown block $blk" >&2; exit 2 ;;
  esac
done
