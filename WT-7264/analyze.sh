#!/usr/bin/env bash
# Run analysis/analyze.py inside the w7264-tools image (no local Python needed).
#   ./analyze.sh results/runs/<A>                                       # one run (summary.md, timeline.png)
#   ./analyze.sh results/runs/[A-Z]* --compare-out results --reuse       # cross-run summary + criteria
#   (--reuse takes each run's existing summary.json; --bug-key/--fix-key pick the A/B arms by condition name)
# Paths may be relative to this directory or absolute under it.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_IMG=w7264-tools:1
if ! docker image inspect "$TOOLS_IMG" >/dev/null 2>&1; then
  base=python:3.12-slim-bookworm
  docker pull -q "$base" >/dev/null 2>&1 || base=public.ecr.aws/docker/library/python:3.12-slim-bookworm
  docker build -q -t "$TOOLS_IMG" --build-arg BASE="$base" -f "$HERE/workload/Dockerfile" "$HERE/workload" >/dev/null
fi
ARGS=()
for a in "$@"; do
  case "$a" in
    "$HERE"/*) ARGS+=("/repo/${a#"$HERE"/}") ;;
    *) ARGS+=("$a") ;;
  esac
done
docker run --rm --name "w7264-analyze-$$" -v "$HERE:/repo" -w /repo "$TOOLS_IMG" \
  python /repo/analysis/analyze.py "${ARGS[@]}"
