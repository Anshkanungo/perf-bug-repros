#!/usr/bin/env bash
# WT-7264 / SERVER-67350 reproduction pipeline: one entry point. Docker is the only requirement.
#
#   ./run.sh 5.0.33 --prefix-search off      # bug arm: duplicate-key check walks invisible keys (default 5.0.33)
#   ./run.sh 5.0.33 --prefix-search on       # fix arm: same binary, SERVER-61185 prefix_search enabled
#   ./run.sh 4.4.2                           # first release with the regression (SERVER-67350 bisect)
#   ./run.sh 4.4.1 / ./run.sh 4.2.24         # before the regression / pre-durable-history baseline
#   ./run.sh --target 10.0.0.5:27017 --prefix-search off   # drive an already-running (instrumented) mongod
#   ./run.sh --image registry/mongod:instr   # start a custom mongod image instead of mongo:<version>
#   ./run.sh 5.0.33 --mongod-binary ./mongod # run your own mongod binary inside the mongo:5.0.33 image
#   ./run.sh --help                          # all options
#
# Results land in results/runs/<label>/ (small summaries + plots) and results/runs/<label>/raw/
# (bulky raw data, git-ignored). Everything it creates is named w7264-*; it never touches other
# containers. Written for bash 3.2+ (macOS default) and Linux.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NET=w7264-net
MONGOD=w7264-mongod
CLIENT=w7264-client
SAMPLER=w7264-sampler
TOOLS_IMG=w7264-tools:1

VERSION=5.0.33
IMAGE=""
MONGOD_BINARY=""
TARGET=""
NETWORK=""
WORKLOAD=bruce
THREADS=""
COUNT=""
EVERY=""
DOCS=1000000
SYNC_START=0
NON_UNIQUE=0
CAP=600
CACHE_GB=1
CLIENT_IMAGE="mongo:5.0.33"
LABEL=""
SKIP_SETUP=0
KEEP=0
PROFILE=0
PROFILE_ARGS=""
MONGOD_MEM=3g
CLIENT_MEM=2g
ANALYZE=1
SETS=()
EXTRA_MONGOD_ARGS=()

usage() {
  sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
  cat <<'EOF'

Options:
  <version>               mongod version for the official image mongo:<version> (default 5.0.33)
  --image IMG             mongod image to start instead of mongo:<version>
  --mongod-binary PATH    host path of a mongod binary to run inside the mongo:<version> image
  --target HOST:PORT      use an already-running mongod; nothing is started or stopped. The workload
                          writes to db test (collection c, or test_data_mongo_issue.mainthings for
                          --workload 67350) and drops nothing: give it an empty database.
  --network NET           docker network for client containers (default: w7264-net, or host with --target)
  --prefix-search on|off  shorthand for --set wiredTigerPrefixSearchForUniqueIndexes=true|false
                          (exists in 4.4.18+ (default off) and 5.0.14+ (default on); absent earlier)
  --set NAME=VALUE        server parameter: --setParameter at startup, or setParameter at runtime with
                          --target (repeatable)
  --cache-gb N            --wiredTigerCacheSizeGB (default 1; always passed explicitly)
  --mongod-arg ARG        extra mongod argument (repeatable)
  --workload bruce|67350  bruce = Bruce Lucas's repro.sh workload (default): 20 threads x 100k docs
                          {_id,a,b}, unique indexes on a and b, insertMany batches of 2000
                          67350 = SERVER-67350-like variant (labelled): 5 pymongo threads insert 1M
                          {someId: ObjectId} docs with a unique index, 100k docs per insert_many
  --threads N / --count N / --every N   bruce workload: threads, docs per thread, docs per insertMany
  --docs N                67350 workload: total documents (default 1,000,000)
  --sync-start            bruce workload: all threads wait for a common start time (labelled variant)
  --non-unique            control: create the same indexes without {unique: true}
  --cap SECS              hard cap on the insert phase (default 600). A run that hits it is a valid
                          "stalled >= cap" result: the client is killed and the run is analyzed.
  --client-image IMG      image providing the legacy mongo shell (default mongo:5.0.33, for every server)
  --label NAME            results/runs/<NAME> (default: <version>-<workload>-<settings>-<timestamp>)
  --skip-setup            don't create the indexes (the collection must exist and be empty)
  --keep                  leave the mongod container and its volume running at the end
  --profile               run ./profile.sh against mongod while the workload runs (starts just before
                          the client); mongod is started with docker --init so it can be SIGSTOPped
  --profile-args "ARGS"   extra arguments for profile.sh (default: --secs 45 --snapshot)
  --mongod-mem SIZE       docker --memory for mongod (default 3g; 0 = unlimited)
  --client-mem SIZE       docker --memory for the client (default 2g; 0 = unlimited)
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
    --prefix-search)
      case "$2" in on|true) SETS+=("wiredTigerPrefixSearchForUniqueIndexes=true") ;;
                   off|false) SETS+=("wiredTigerPrefixSearchForUniqueIndexes=false") ;;
                   *) echo "--prefix-search takes on or off" >&2; exit 2 ;; esac
      shift 2 ;;
    --set) SETS+=("$2"); shift 2 ;;
    --cache-gb) CACHE_GB="$2"; shift 2 ;;
    --mongod-arg) EXTRA_MONGOD_ARGS+=("$2"); shift 2 ;;
    --workload) WORKLOAD="$2"; shift 2 ;;
    --threads) THREADS="$2"; shift 2 ;;
    --count) COUNT="$2"; shift 2 ;;
    --every) EVERY="$2"; shift 2 ;;
    --docs) DOCS="$2"; shift 2 ;;
    --sync-start) SYNC_START=1; shift ;;
    --non-unique) NON_UNIQUE=1; shift ;;
    --cap) CAP="$2"; shift 2 ;;
    --client-image) CLIENT_IMAGE="$2"; shift 2 ;;
    --label) LABEL="$2"; shift 2 ;;
    --skip-setup) SKIP_SETUP=1; shift ;;
    --keep) KEEP=1; shift ;;
    --profile) PROFILE=1; shift ;;
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

# Host power state as JSON (macOS: pmset; elsewhere "unknown"). On a laptop, battery power can mean
# Low Power Mode, which slows the CPU, so every run records it at start (meta.json) and end (outcome.json).
power_json() {
  if command -v pmset >/dev/null 2>&1; then
    local src chg lpm
    src=$(pmset -g batt 2>/dev/null | head -1 | sed -n "s/.*'\(.*\)'.*/\1/p")
    chg=$(pmset -g batt 2>/dev/null | sed -n 2p | grep -oE '[0-9]+%' | head -1 | tr -d '%')
    lpm=$(pmset -g 2>/dev/null | awk '/lowpowermode/ {print $2; exit}')
    printf '{"source": "%s", "charge_pct": %s, "low_power_mode": %s}' "${src:-unknown}" "${chg:-null}" "${lpm:-null}"
  else
    printf '{"source": "unknown", "charge_pct": null, "low_power_mode": null}'
  fi
}

case "$WORKLOAD" in bruce|67350) ;; *) die "--workload must be bruce or 67350" ;; esac
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
if [ "$WORKLOAD" = bruce ]; then CIMG="$(resolve_image "$CLIENT_IMAGE")"; else CIMG="$TOOLS_IMG"; fi

SET_TAG=""
for kv in ${SETS[@]+"${SETS[@]}"}; do
  case "$kv" in
    wiredTigerPrefixSearchForUniqueIndexes=true) SET_TAG="${SET_TAG}-prefixon" ;;
    wiredTigerPrefixSearchForUniqueIndexes=false) SET_TAG="${SET_TAG}-prefixoff" ;;
    *) SET_TAG="${SET_TAG}-$(printf '%s' "$kv" | tr -c 'a-zA-Z0-9.' '_')" ;;
  esac
done
[ "$SYNC_START" = 1 ] && SET_TAG="${SET_TAG}-sync"
[ "$NON_UNIQUE" = 1 ] && SET_TAG="${SET_TAG}-nonunique"
[ -n "$LABEL" ] || LABEL="${VER_TAG}-${WORKLOAD}${SET_TAG}-$(date +%Y%m%dT%H%M%S)"
RUN_DIR="$HERE/results/runs/$LABEL"
RAW="$RUN_DIR/raw"
VOL="w7264-db-$(printf '%s' "$LABEL" | tr -c 'a-zA-Z0-9_.-' '_')"
[ -e "$RUN_DIR/meta.json" ] && die "$RUN_DIR already exists; pick another --label"
mkdir -p "$RAW"

json_list() { local out="" x; for x in "$@"; do out="$out\"$x\","; done; printf '[%s]' "${out%,}"; }
digest_of() { docker image inspect -f '{{if .RepoDigests}}{{index .RepoDigests 0}}{{else}}{{.Id}}{{end}}' "$1" 2>/dev/null || echo unknown; }
cat > "$RUN_DIR/meta.json" <<EOF
{
  "label": "$LABEL",
  "started_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "mongod_image": "${MIMG:-external}",
  "mongod_image_digest": "$( [ -n "$MIMG" ] && digest_of "$MIMG" || echo external)",
  "mongod_binary": "${MONGOD_BINARY}",
  "target": "${TARGET}",
  "workload": "$WORKLOAD",
  "client_image": "$CIMG",
  "client_image_digest": "$(digest_of "$CIMG")",
  "threads": "${THREADS}",
  "count_per_thread": "${COUNT}",
  "docs_per_insertMany": "${EVERY}",
  "docs_total_67350": $DOCS,
  "sync_start": $SYNC_START,
  "non_unique": $NON_UNIQUE,
  "set_parameters": $(json_list ${SETS[@]+"${SETS[@]}"}),
  "cache_gb": $CACHE_GB,
  "cap_s": $CAP,
  "skip_setup": $SKIP_SETUP,
  "profile": $PROFILE,
  "extra_mongod_args": "${EXTRA_MONGOD_ARGS[*]:-}",
  "mongod_mem_limit": "$MONGOD_MEM",
  "client_mem_limit": "$CLIENT_MEM",
  "other_containers_at_start": $(json_list $(docker ps --format '{{.Names}}' | grep -v '^w7264-' || true)),
  "power_start": $(power_json),
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
stop_stats() {
  if [ -n "$STATS_PID" ]; then
    pkill -P "$STATS_PID" 2>/dev/null || true
    kill "$STATS_PID" 2>/dev/null || true
    STATS_PID=""
  fi
}
cleanup() {
  local rc=$?
  set +e
  stop_stats
  [ -n "$PROF_PID" ] && kill "$PROF_PID" 2>/dev/null && docker rm -f w7264-prof >/dev/null 2>&1
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
  MARGS=(--bind_ip_all --wiredTigerCacheSizeGB "$CACHE_GB")
  for kv in ${SETS[@]+"${SETS[@]}"}; do MARGS+=(--setParameter "$kv"); done
  [ ${#EXTRA_MONGOD_ARGS[@]} -gt 0 ] && MARGS+=("${EXTRA_MONGOD_ARGS[@]}")
  docker volume create "$VOL" >/dev/null
  DOCKER_ARGS=(-d --name "$MONGOD" --hostname "$MONGOD" --network "$NET" --ulimit nofile=64000:64000
               -v "$VOL:/data/db" --tmpfs /data/configdb)
  [ "$MONGOD_MEM" != 0 ] && DOCKER_ARGS+=("--memory=$MONGOD_MEM" "--memory-swap=$MONGOD_MEM")
  # With --profile, a tiny init (tini) runs as PID 1 so mongod is not its namespace's init: the gdb
  # snapshot can then freeze mongod with SIGSTOP. mongod itself is unchanged.
  [ "$PROFILE" = 1 ] && DOCKER_ARGS+=(--init)
  if [ -n "$MONGOD_BINARY" ]; then
    [ -f "$MONGOD_BINARY" ] || die "no such file: $MONGOD_BINARY"
    BIN_ABS="$(cd "$(dirname "$MONGOD_BINARY")" && pwd)/$(basename "$MONGOD_BINARY")"
    DOCKER_ARGS+=(-v "$BIN_ABS:/usr/local/bin/mongod-custom:ro" --entrypoint /usr/local/bin/mongod-custom)
  fi
  log "starting $MONGOD from $MIMG: mongod ${MARGS[*]}"
  docker run "${DOCKER_ARGS[@]}" "$MIMG" "${MARGS[@]}" >/dev/null
fi

READY_ARGS=(--uri "$URI" --out /out/server.json)
if [ -n "$TARGET" ]; then for kv in ${SETS[@]+"${SETS[@]}"}; do READY_ARGS+=(--set "$kv"); done; fi
docker run --rm --name w7264-ready --network "$CNET" -v "$HERE/workload:/workload:ro" -v "$RUN_DIR:/out" \
  "$TOOLS_IMG" python /workload/ready.py "${READY_ARGS[@]}"

# ---------------------------------------------------------------- sampler + docker stats
SAMPLER_ARGS=(--uri "$URI" --out /out/serverstatus.jsonl --dump-full /out/serverstatus_first_full.json)
SAMPLER_DOCKER=(-d --name "$SAMPLER" --network "$CNET" -v "$HERE/workload:/workload:ro" -v "$RAW:/out")
if [ -z "$TARGET" ]; then
  # share mongod's PID namespace (read-only use of /proc) for per-thread CPU at 1 Hz
  SAMPLER_DOCKER+=(--pid "container:$MONGOD")
  SAMPLER_ARGS+=(--threads-out /out/threads.jsonl)
fi
docker run "${SAMPLER_DOCKER[@]}" "$TOOLS_IMG" python /workload/sampler.py "${SAMPLER_ARGS[@]}" >/dev/null

# All running containers are sampled (read-only, ~1 Hz stream) so CPU used by unrelated containers on
# the same Docker host is on record as a noise source; the analysis reports them as an aggregate.
( docker stats --format '{{json .}}' 2>/dev/null | while IFS= read -r line; do
    case "$line" in
      *'{"'*) j="{${line#*\{}"; j="${j%%$'\e'*}"; printf '%s %s\n' "$(date +%s)" "$j" ;;
    esac
  done >> "$RAW/docker_stats.txt" ) &
STATS_PID=$!

if [ "$PROFILE" = 1 ]; then
  [ -n "$TARGET" ] && die "--profile needs a mongod container started by run.sh (use ./profile.sh --host-pid for a native mongod)"
  # shellcheck disable=SC2086
  "$HERE/profile.sh" --container "$MONGOD" --out "$RUN_DIR/profile" ${PROFILE_ARGS:---secs 45 --snapshot} \
    > "$RAW/profile.log" 2>&1 &
  PROF_PID=$!
  log "profiler started (log: $RAW/profile.log); waiting 5 s for perf to attach"
  sleep 5
fi

# ---------------------------------------------------------------- client workload
CARGS=(-d --name "$CLIENT" --network "$CNET" -v "$HERE/workload:/workload:ro")
[ "$CLIENT_MEM" != 0 ] && CARGS+=("--memory=$CLIENT_MEM")
if [ "$WORKLOAD" = bruce ]; then
  CFG="var CFG={parallelTester:'/workload/original/parallelTester.js'"
  [ -n "$THREADS" ] && CFG="$CFG,nthreads:$THREADS"
  [ -n "$COUNT" ] && CFG="$CFG,count:$COUNT"
  [ -n "$EVERY" ] && CFG="$CFG,every:$EVERY"
  [ "$SYNC_START" = 1 ] && CFG="$CFG,syncStart:true"
  [ "$NON_UNIQUE" = 1 ] && CFG="$CFG,unique:false"
  [ "$SKIP_SETUP" = 1 ] && CFG="$CFG,skipSetup:true"
  CFG="$CFG}"
  # tmpfs over the image's declared volumes so no anonymous volumes are left behind
  docker run "${CARGS[@]}" --tmpfs /data/db --tmpfs /data/configdb --entrypoint mongo "$CIMG" \
    --host "$HOSTPORT" --quiet --eval "$CFG" /workload/repro-adapted.js >/dev/null
  log "client started (bruce workload: $CFG)"
else
  PYARGS=(--uri "$URI" --docs "$DOCS")
  [ -n "$THREADS" ] && PYARGS+=(--threads "$THREADS")
  [ "$NON_UNIQUE" = 1 ] && PYARGS+=(--non-unique)
  [ "$SKIP_SETUP" = 1 ] && PYARGS+=(--skip-setup)
  docker run "${CARGS[@]}" "$TOOLS_IMG" python /workload/insertmany_67350.py "${PYARGS[@]}" >/dev/null
  log "client started (67350 variant: ${PYARGS[*]:2})"
fi

# ---------------------------------------------------------------- wait (with the hard cap)
CAPPED=0
T_START=$(date +%s)
T_INS=""
while :; do
  if [ "$(docker inspect -f '{{.State.Running}}' "$CLIENT" 2>/dev/null)" != true ]; then break; fi
  now=$(date +%s)
  if [ -z "$T_INS" ]; then
    docker logs "$CLIENT" > "$RAW/.client_peek" 2>/dev/null || true
    if grep -q '^P,insert_start' "$RAW/.client_peek"; then
      # time the cap from the client's own insert_start stamp, not from when this loop noticed it
      ms=$(grep -m1 '^P,insert_start' "$RAW/.client_peek" | cut -d, -f3)
      T_INS=$(( ${ms:-$(( now * 1000 ))} / 1000 ))
      log "inserts started; cap ${CAP}s"
    fi
    # setup is two createIndex calls on an empty collection; anything over 120 s is a failure
    [ $((now - T_START)) -gt 120 ] && [ -z "$T_INS" ] && die "client did not reach the insert phase in 120 s"
  elif [ $((now - T_INS)) -ge "$CAP" ]; then
    log "CAP reached (${CAP}s): killing the client; this run counts as stalled >= cap"
    CAPPED=1
    docker kill "$CLIENT" >/dev/null 2>&1 || true
    break
  fi
  sleep 1
done
rm -f "$RAW/.client_peek"
RC=$(docker wait "$CLIENT" 2>/dev/null || echo 255)
echo "{\"capped\": $CAPPED, \"cap_s\": $CAP, \"client_exit\": $RC, \"ended_utc\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\", \"power_end\": $(power_json)}" > "$RUN_DIR/outcome.json"
log "client exited with code $RC (capped=$CAPPED)"
if [ -n "$PROF_PID" ]; then
  log "waiting for profiler to finish"
  wait "$PROF_PID" || log "profiler exited non-zero (see $RAW/profile.log)"
  PROF_PID=""
fi
sleep 2   # one more serverStatus sample after the last insert
docker stop -t 5 "$SAMPLER" >/dev/null 2>&1 || true
stop_stats
collect_logs
[ "$CAPPED" = 1 ] || [ "$RC" = 0 ] || die "client failed; see $RAW/client.log and $RAW/client.stderr"

if [ "$ANALYZE" = 1 ]; then
  "$HERE/analyze.sh" "$RUN_DIR" || log "analysis failed (raw data kept in $RAW)"
  if [ "$PROFILE" = 1 ] && [ -d "$RUN_DIR/profile" ]; then
    "$HERE/profiling/reanalyze.sh" "$RUN_DIR" || log "profile re-analysis failed"
  fi
fi
log "done: $RUN_DIR"
