#!/usr/bin/env bash
# Run analysis/analyze.py inside the s52879-tools image (no local Python needed).
#   ./analyze.sh results/runs/<A>                                  # one run
#   ./analyze.sh results/runs/<A> results/runs/<B> --compare-out results --names "4.4.3,4.4.4"
# Paths may be relative to this directory or absolute under it.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_IMG=s52879-tools:1
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
docker run --rm --name "s52879-analyze-$$" -v "$HERE:/repo" -w /repo "$TOOLS_IMG" \
  python /repo/analysis/analyze.py "${ARGS[@]}"
