#!/usr/bin/env bash
# SERVER-52879 reproduction pipeline: one entry point. Docker is the only requirement.
#
#   ./run.sh 4.4.3                          # buggy build, original workload (~15 min)
#   ./run.sh 4.4.4                          # fixed build, identical workload
#   ./run.sh 4.4.3 --idle-timeout 60        # causal check: spike period should follow the timeout
#   ./run.sh --target 10.0.0.5:27017        # drive an already-running (e.g. instrumented) mongod
#   ./run.sh --image registry/mongod:instr  # start a custom mongod image instead of mongo:<version>
#   ./run.sh 4.4.3 --mongod-binary ./mongod # run your own mongod binary inside the mongo:4.4.3 image
#   ./run.sh --help                         # all options
#
# Results land in results/runs/<label>/ (small summaries + plots) and results/runs/<label>/raw/
# (bulky raw data, git-ignored). Everything it creates is named s52879-*; it never touches other
# containers. Written for bash 3.2+ (macOS default) and Linux.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NET=s52879-net
MONGOD=s52879-mongod
CLIENT=s52879-client
SAMPLER=s52879-sampler
TOOLS_IMG=s52879-tools:1

VERSION=4.4.3
IMAGE=""
MONGOD_BINARY=""
TARGET=""
NETWORK=""
DURATION=720
COLLS=1000
INDEXES=10
THREADS=100
IDLE=30
SET_IDLE_ON_TARGET=1
CACHE_GB=1
REPLSET=0
DRIVER=shell
CLIENT_IMAGE=""
LABEL=""
SKIP_SETUP=0
KEEP=0
PROFILE=0
PROFILE_DELAY=150
PROFILE_ARGS=""
MONGOD_MEM=4g
CLIENT_MEM=3g
ANALYZE=1
EXTRA_MONGOD_ARGS=()

usage() {
  sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
  cat <<'EOF'

Options:
  <version>               mongod version for the official image mongo:<version> (default 4.4.3)
  --image IMG             mongod image to start instead of mongo:<version>
  --mongod-binary PATH    host path of a mongod binary to run inside the mongo:<version> image
  --target HOST:PORT      use an already-running mongod; nothing is started or stopped
  --network NET           docker network for client containers (default: s52879-net, or host with --target)
  --duration SECS         length of the insert phase (default 720 = 2 min warm-up + 10 min)
  --colls N               collections (default 1000)
  --indexes K             secondary indexes per collection (default 10)
  --threads T             client threads (default 100)
  --idle-timeout SECS     wiredTigerSessionCloseIdleTimeSecs (default 30; mongod default is 300)
  --no-set-idle           with --target: don't change the server's idle timeout at runtime
  --cache-gb N            --wiredTigerCacheSizeGB (default 1)
  --replset               run as a single-node replica set (rs0) instead of standalone
  --mongod-arg ARG        extra mongod argument (repeatable)
  --driver shell|py       shell = legacy mongo shell running workload/repro-adapted.js (default)
                          py    = pymongo driver (workload/driver.py), same workload, µs timing
  --client-image IMG      image providing the legacy shell (default mongo:4.4.3, for every server version)
  --label NAME            results/runs/<NAME> (default: <version>-<driver>-idle<T>-<timestamp>)
  --skip-setup            don't create collections/indexes (reuse an existing dataset)
  --keep                  leave the mongod container and its volume running at the end
  --profile               also run ./profile.sh against mongod, starting --profile-delay s after inserts start
  --profile-delay SECS    default 150
  --profile-args "ARGS"   extra arguments passed to profile.sh
  --mongod-mem SIZE       docker --memory for mongod (default 4g; 0 = unlimited)
  --client-mem SIZE       docker --memory for the client (default 3g; 0 = unlimited)
  --no-analyze            skip the per-run analysis at the end
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --image) IMAGE="$2"; shift 2 ;;
    --mongod-binary) MONGOD_BINARY="$2"; shift 2 ;;
    --target) TARGET="$2"; shift 2 ;;
    --network) NETWORK="$2"; shift 2 ;;
    --duration) DURATION="$2"; shift 2 ;;
    --colls) COLLS="$2"; shift 2 ;;
    --indexes) INDEXES="$2"; shift 2 ;;
    --threads) THREADS="$2"; shift 2 ;;
    --idle-timeout) IDLE="$2"; shift 2 ;;
    --no-set-idle) SET_IDLE_ON_TARGET=0; shift ;;
    --cache-gb) CACHE_GB="$2"; shift 2 ;;
    --replset) REPLSET=1; shift ;;
    --mongod-arg) EXTRA_MONGOD_ARGS+=("$2"); shift 2 ;;
    --driver) DRIVER="$2"; shift 2 ;;
    --client-image) CLIENT_IMAGE="$2"; shift 2 ;;
    --label) LABEL="$2"; shift 2 ;;
    --skip-setup) SKIP_SETUP=1; shift ;;
    --keep) KEEP=1; shift ;;
    --profile) PROFILE=1; shift ;;
    --profile-delay) PROFILE_DELAY="$2"; shift 2 ;;
    --profile-args) PROFILE_ARGS="$2"; shift 2 ;;
    --mongod-mem) MONGOD_MEM="$2"; shift 2 ;;
    --client-mem) CLIENT_MEM="$2"; shift 2 ;;
    --no-analyze) ANALYZE=0; shift ;;
    [0-9]*) VERSION="$1"; shift ;;
    *) echo "unknown argument: $1 (see --help)" >&2; exit 2 ;;
  esac
done

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }

# Pull an image; for Docker Official Images fall back to the AWS ECR Public mirror (identical
# digests) when Docker Hub refuses anonymous pulls (HTTP 429). Prints the usable reference.
resolve_image() {
  local ref="$1"
  if docker image inspect "$ref" >/dev/null 2>&1; then echo "$ref"; return 0; fi
  if docker pull -q "$ref" >/dev/null 2>&1; then echo "$ref"; return 0; fi
  case "$ref" in
    */*) ;;
    *) local m="public.ecr.aws/docker/library/$ref"
       if docker image inspect "$m" >/dev/null 2>&1 || docker pull -q "$m" >/dev/null 2>&1; then
         echo "$m"; return 0
       fi ;;
  esac
  echo "cannot pull $ref" >&2; return 1
}

ensure_tools_image() {
  docker image inspect "$TOOLS_IMG" >/dev/null 2>&1 && return 0
  local base; base="$(resolve_image python:3.12-slim-bookworm)"
  log "building $TOOLS_IMG (base $base)"
  docker build -q -t "$TOOLS_IMG" --build-arg BASE="$base" -f "$HERE/workload/Dockerfile" "$HERE/workload" >/dev/null
}

mem_flag() { [ "$1" = 0 ] && return 0; printf -- '--memory=%s' "$1"; }

case "$DRIVER" in shell|py) ;; *) die "--driver must be shell or py" ;; esac
for c in $MONGOD $CLIENT $SAMPLER; do
  if docker container inspect "$c" >/dev/null 2>&1; then
    [ -n "$TARGET" ] && [ "$c" = "$MONGOD" ] && continue
    die "container $c already exists (another run in progress?). Remove it with: docker rm -f -v $c"
  fi
done

ensure_tools_image
docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET" >/dev/null

if [ -z "$TARGET" ]; then
  if [ -n "$IMAGE" ]; then MIMG="$(resolve_image "$IMAGE")"; VER_TAG="$(echo "$IMAGE" | tr '/:@' '___')"
  else MIMG="$(resolve_image "mongo:$VERSION")"; VER_TAG="$VERSION"; fi
  [ -n "$MONGOD_BINARY" ] && VER_TAG="${VER_TAG}-custombin"
  HOSTPORT="$MONGOD:27017"
  CNET="${NETWORK:-$NET}"
else
  MIMG=""; VER_TAG="target"
  HOSTPORT="$TARGET"
  CNET="${NETWORK:-host}"
fi
URI="mongodb://$HOSTPORT/?directConnection=true"

if [ "$DRIVER" = shell ]; then CIMG="$(resolve_image "${CLIENT_IMAGE:-mongo:4.4.3}")"; else CIMG="$TOOLS_IMG"; fi

[ -n "$LABEL" ] || LABEL="${VER_TAG}-${DRIVER}-idle${IDLE}-$(date +%Y%m%dT%H%M%S)"
RUN_DIR="$HERE/results/runs/$LABEL"
RAW="$RUN_DIR/raw"
VOL="s52879-db-$(printf '%s' "$LABEL" | tr -c 'a-zA-Z0-9_.-' '_')"
mkdir -p "$RAW"

digest_of() { docker image inspect -f '{{if .RepoDigests}}{{index .RepoDigests 0}}{{else}}{{.Id}}{{end}}' "$1" 2>/dev/null || echo unknown; }
cat > "$RUN_DIR/meta.json" <<EOF
{
  "label": "$LABEL",
  "started_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "mongod_image": "${MIMG:-external}",
  "mongod_image_digest": "$( [ -n "$MIMG" ] && digest_of "$MIMG" || echo external)",
  "mongod_binary": "${MONGOD_BINARY}",
  "target": "${TARGET}",
  "topology": "$( [ "$REPLSET" = 1 ] && echo replset-1node || echo standalone)",
  "driver": "$DRIVER",
  "client_image": "$CIMG",
  "client_image_digest": "$(digest_of "$CIMG")",
  "duration_s": $DURATION,
  "collections": $COLLS,
  "indexes_per_collection": $INDEXES,
  "threads": $THREADS,
  "idle_timeout_s": $IDLE,
  "cache_gb": $CACHE_GB,
  "skip_setup": $SKIP_SETUP,
  "extra_mongod_args": "${EXTRA_MONGOD_ARGS[*]:-}",
  "mongod_mem_limit": "$MONGOD_MEM",
  "client_mem_limit": "$CLIENT_MEM",
  "docker_host": "$(docker info --format '{{.OperatingSystem}} {{.KernelVersion}} {{.Architecture}} cpus={{.NCPU}} mem={{.MemTotal}}' 2>/dev/null)"
}
EOF

STATS_PID=""
PROF_PID=""
collect_logs() {
  [ -s "$RAW/client.log" ] || docker logs "$CLIENT" > "$RAW/client.log" 2> "$RAW/client.stderr" || true
  if [ -z "$TARGET" ] && docker container inspect "$MONGOD" >/dev/null 2>&1; then
    [ -s "$RAW/mongod.log" ] || docker logs "$MONGOD" > "$RAW/mongod.log" 2>&1 || true
    [ -d "$RAW/diagnostic.data" ] || docker cp "$MONGOD:/data/db/diagnostic.data" "$RAW/diagnostic.data" >/dev/null 2>&1 || true
  fi
}
cleanup() {
  local rc=$?
  set +e
  [ -n "$STATS_PID" ] && kill "$STATS_PID" 2>/dev/null
  [ -n "$PROF_PID" ] && kill "$PROF_PID" 2>/dev/null
  docker stop -t 5 "$SAMPLER" >/dev/null 2>&1
  collect_logs
  docker rm -f -v "$CLIENT" "$SAMPLER" >/dev/null 2>&1
  if [ -z "$TARGET" ]; then
    if [ "$KEEP" = 0 ]; then
      docker rm -f -v "$MONGOD" >/dev/null 2>&1
      docker volume rm "$VOL" >/dev/null 2>&1
    else
      log "--keep: $MONGOD and volume $VOL left running"
    fi
  fi
  exit $rc
}
trap cleanup EXIT
trap 'exit 130' INT TERM

log "run $LABEL"
log "results: $RUN_DIR"

# ---------------------------------------------------------------- mongod
if [ -z "$TARGET" ]; then
  MARGS=(--bind_ip_all --wiredTigerCacheSizeGB "$CACHE_GB" --setParameter "wiredTigerSessionCloseIdleTimeSecs=$IDLE")
  [ "$REPLSET" = 1 ] && MARGS+=(--replSet rs0)
  [ ${#EXTRA_MONGOD_ARGS[@]} -gt 0 ] && MARGS+=("${EXTRA_MONGOD_ARGS[@]}")
  docker volume create "$VOL" >/dev/null
  DOCKER_ARGS=(-d --name "$MONGOD" --hostname "$MONGOD" --network "$NET" --ulimit nofile=64000:64000
               -v "$VOL:/data/db" --tmpfs /data/configdb)
  [ "$MONGOD_MEM" != 0 ] && DOCKER_ARGS+=("--memory=$MONGOD_MEM")
  # With --profile, a tiny init (tini) runs as PID 1 so mongod is not its namespace's init: the
  # profiler's snapshot can then freeze mongod with SIGSTOP (the kernel ignores SIGSTOP sent to a
  # namespace init from inside the namespace). mongod itself is unchanged.
  [ "$PROFILE" = 1 ] && DOCKER_ARGS+=(--init)
  if [ -n "$MONGOD_BINARY" ]; then
    [ -f "$MONGOD_BINARY" ] || die "no such file: $MONGOD_BINARY"
    BIN_ABS="$(cd "$(dirname "$MONGOD_BINARY")" && pwd)/$(basename "$MONGOD_BINARY")"
    DOCKER_ARGS+=(-v "$BIN_ABS:/usr/local/bin/mongod-custom:ro" --entrypoint /usr/local/bin/mongod-custom)
  fi
  log "starting $MONGOD from $MIMG: mongod ${MARGS[*]}"
  docker run "${DOCKER_ARGS[@]}" "$MIMG" "${MARGS[@]}" >/dev/null
fi

READY_ARGS=(--uri "$URI" --hostport "$HOSTPORT" --out /out/server.json)
[ "$REPLSET" = 1 ] && [ -z "$TARGET" ] && READY_ARGS+=(--replset rs0)
[ -n "$TARGET" ] && [ "$SET_IDLE_ON_TARGET" = 1 ] && READY_ARGS+=(--set-idle-timeout "$IDLE")
docker run --rm --name s52879-ready --network "$CNET" -v "$HERE/workload:/workload:ro" -v "$RUN_DIR:/out" \
  "$TOOLS_IMG" python /workload/ready.py "${READY_ARGS[@]}"

# ---------------------------------------------------------------- sampler + docker stats
docker run -d --name "$SAMPLER" --network "$CNET" -v "$HERE/workload:/workload:ro" -v "$RAW:/out" \
  "$TOOLS_IMG" python /workload/sampler.py --uri "$URI" --out /out/serverstatus.jsonl \
  --dump-full /out/serverstatus_first_full.json >/dev/null

# All running containers are sampled (read-only) so CPU used by unrelated containers on the same
# Docker host is on record as a noise source; the analysis reports them only as an aggregate.
( set +e
  while :; do
    ts=$(date +%s)
    docker stats --no-stream --format '{{json .}}' 2>/dev/null | sed "s/^/{\"t\":$ts,\"s\":/; s/\$/}/" >> "$RAW/docker_stats.jsonl"
    sleep 5
  done ) &
STATS_PID=$!

# ---------------------------------------------------------------- client workload
CARGS=(-d --name "$CLIENT" --network "$CNET" -v "$HERE/workload:/workload:ro")
[ "$CLIENT_MEM" != 0 ] && CARGS+=("--memory=$CLIENT_MEM")
if [ "$DRIVER" = shell ]; then
  SKIPJS=false; [ "$SKIP_SETUP" = 1 ] && SKIPJS=true
  CFG="var CFG={ncollections:$COLLS,nindexes:$INDEXES,nthreads:$THREADS,durationSecs:$DURATION,skipSetup:$SKIPJS,parallelTester:'/workload/original/parallelTester.js'}"
  # tmpfs over the image's declared volumes so no anonymous volumes are left behind
  docker run "${CARGS[@]}" --tmpfs /data/db --tmpfs /data/configdb --entrypoint mongo "$CIMG" \
    --host "$HOSTPORT" --quiet --eval "$CFG" /workload/repro-adapted.js >/dev/null
else
  PYARGS=(--uri "$URI" --colls "$COLLS" --indexes "$INDEXES" --threads "$THREADS" --duration "$DURATION")
  [ "$SKIP_SETUP" = 1 ] && PYARGS+=(--skip-setup)
  docker run "${CARGS[@]}" "$TOOLS_IMG" python /workload/driver.py "${PYARGS[@]}" >/dev/null
fi
log "client started ($DRIVER driver: $COLLS colls x $INDEXES indexes, $THREADS threads, ${DURATION}s of inserts)"

# Wait for the insert phase to start (setup of 10k indexes takes a few minutes).
# (poll via a file: "docker logs | grep -q" can misfire under pipefail when grep exits early)
while docker logs "$CLIENT" > "$RAW/.client_peek" 2>/dev/null; ! grep -q '^P,insert_start' "$RAW/.client_peek"; do
  if [ "$(docker inspect -f '{{.State.Running}}' "$CLIENT" 2>/dev/null)" != true ]; then
    docker logs "$CLIENT" 2>&1 | tail -20 >&2; die "client exited before inserts started"
  fi
  sleep 2
done
rm -f "$RAW/.client_peek"
log "inserts started; expected end in ~${DURATION}s"

if [ "$PROFILE" = 1 ]; then
  ( sleep "$PROFILE_DELAY"
    # shellcheck disable=SC2086
    "$HERE/profile.sh" --container "$MONGOD" --out "$RUN_DIR/profile" $PROFILE_ARGS ) > "$RAW/profile.log" 2>&1 &
  PROF_PID=$!
  log "profiling starts in ${PROFILE_DELAY}s (log: $RAW/profile.log)"
fi

RC=$(docker wait "$CLIENT")
log "client exited with code $RC"
if [ -n "$PROF_PID" ]; then
  log "waiting for profiler to finish"
  wait "$PROF_PID" || log "profiler exited non-zero (see $RAW/profile.log)"
  PROF_PID=""
fi
docker stop -t 5 "$SAMPLER" >/dev/null 2>&1 || true
kill "$STATS_PID" 2>/dev/null || true; STATS_PID=""
collect_logs
[ "$RC" = 0 ] || die "client failed; see $RAW/client.log and $RAW/client.stderr"

if [ "$ANALYZE" = 1 ]; then
  "$HERE/analyze.sh" "$RUN_DIR" || log "analysis failed (raw data kept in $RAW)"
fi
log "done: $RUN_DIR"
