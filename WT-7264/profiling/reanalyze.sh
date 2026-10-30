#!/usr/bin/env bash
# Re-run the profile analysis for a finished run, using the client log to pick the stuck threads.
#   profiling/reanalyze.sh results/runs/<label>
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN="$(cd "$1" && pwd)"
docker run --rm --name "w7264-reanalyze-$$" -v "$HERE/profiling:/prof:ro" -v "$RUN:/run" w7264-prof:1 \
  bash -c 'python3 /prof/analyze_profile.py --dir /run/profile --client-log /run/raw/client.log &&
           if [ -s /run/profile/oncpu_stuck.folded ]; then /opt/FlameGraph/flamegraph.pl \
             --title "stuck connection thread(s) on-CPU (cpu-clock)" --width 1600 /run/profile/oncpu_stuck.folded \
             > /run/profile/oncpu_stuck.svg; fi;
           if [ -f /run/profile/snapshot.txt ]; then python3 /prof/analyze_snapshot.py --dir /run/profile; fi'
