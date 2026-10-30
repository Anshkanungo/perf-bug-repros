#!/usr/bin/env bash
# Re-run the profile analysis for a finished run, adding client-latency correlation per sweep window.
#   profiling/reanalyze.sh results/runs/<label>
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN="$(cd "$1" && pwd)"
docker run --rm --name "s52879-reanalyze-$$" -v "$HERE/profiling:/prof:ro" -v "$RUN:/run" s52879-prof:1 \
  bash -c 'python3 /prof/analyze_profile.py --dir /run/profile --client-log /run/raw/client.log &&
           for f in offcpu_sweeps offcpu_long; do
             [ -s /run/profile/$f.folded ] && /opt/FlameGraph/flamegraph.pl --title "mongod off-CPU: $f (weight = blocked microseconds)" \
               --countname us --colors io --width 1600 /run/profile/$f.folded > /run/profile/$f.svg; done;
           [ -f /run/profile/snapshot.txt ] && python3 /prof/analyze_snapshot.py --dir /run/profile || true'
