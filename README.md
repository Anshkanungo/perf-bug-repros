# perf-bug-repros

Reproductions of real performance bugs in C/C++ systems, packaged so that someone else can rerun them
(including against their own instrumented build) and get the same symptom. Each bug lives in its own
directory with a plan, a one-command pipeline, raw-data conventions, a profile of the symptom, the developer
discussion, and a one-page report.

## Bugs

| bug | system | symptom | reproduced? | entry point | report |
|---|---|---|---|---|---|
| [SERVER-52879](SERVER-52879/) | MongoDB 4.4 (WiredTiger) | periodic write-latency spikes when idle cached WT sessions are closed under the session-cache mutex | **partially**: mechanism reproduced and profiled (4.4.3 vs 4.4.4); pre-registered periodicity/fix thresholds not met on a 10-vCPU laptop VM | `SERVER-52879/run.sh` | [REPORT.md](SERVER-52879/REPORT.md) |
| [WT-7264 / SERVER-67350](WT-7264/) | MongoDB 4.4 / 5.0 (WiredTiger) | inserts into a unique index get stuck for seconds to many minutes at 100% CPU: the duplicate-key `search_near` walks keys its snapshot can't see, one history-store lookup per key | **yes**: all pre-registered criteria met on one binary (5.0.33, `wiredTigerPrefixSearchForUniqueIndexes` off vs on, barrier variant of Bruce's workload; same with AC-only runs); profiled stack matches the ticket's `hs.png`. One secondary check fails (4.2.24 stalls, only on battery / Low Power Mode, a different eviction stall) | `WT-7264/run.sh` | [REPORT.md](WT-7264/REPORT.md) |

## Common prerequisites

- **Docker** (Engine ≥ 20 or Docker Desktop). Nothing else is needed on the host: mongod, the workload
  client, the analysis (Python/pandas/matplotlib), and the profiler (perf/gdb/FlameGraph) all run in containers.
- **Architecture:** arm64 and x86-64 both work. Images are multi-arch and the scripts never assume a CPU type.
  Developed on Apple Silicon (Docker Desktop, linux/arm64 VM); intended to run on x86-64 Linux servers.
- **Profiling** needs a `--privileged` sidecar container (for `perf_event_open`, tracefs, and ptrace). No host
  sysctl is changed.
- **Disk/RAM:** see each bug's README.
- **Docker Hub rate limits:** the scripts fall back to the AWS ECR Public mirror of Docker Official Images
  (`public.ecr.aws/docker/library/*`, same image digests) when an anonymous Docker Hub pull is refused.

## Conventions

- Everything a pipeline creates in Docker (containers, volumes, networks, images) is prefixed with the bug's
  short name (e.g. `s52879-`), and nothing else on the Docker host is touched.
- `results/runs/<label>/` holds small, committed artifacts (summaries, per-second CSVs, plots).
  `results/runs/<label>/raw/` holds bulky raw data and is git-ignored.
- Each bug directory has `PLAN.md`, written before the main runs, with a "changes from original plan" log.
- Progress across bugs is tracked in [PROGRESS.md](PROGRESS.md).

## WT-7264 / SERVER-67350 in one paragraph

Since MongoDB 4.4, the duplicate-key check of a unique-index insert (`WiredTigerIndexUnique::_keyExists` →
WiredTiger `search_near`) walks over every key its transaction cannot see, and with durable history each such
key on an evicted page costs a history-store lookup that finds nothing (`__wt_hs_find_upd`, "history store
table reads missed"). Concurrent `insertMany` streams into disjoint ascending key ranges make one or a few
transactions do this for minutes at 100% CPU. `WT-7264/` reproduces it on a single binary (`mongo:5.0.33`,
`wiredTigerPrefixSearchForUniqueIndexes` off vs on: 4/5 runs stuck for 172–562 s vs 0/5), also with Bruce
Lucas's unmodified script (2/10 on 5.0.33; 3/3 on 4.4.30 with its defaults), shows the 4.4.1 → 4.4.2 change
from the SERVER-67350 bisect, and profiles the stuck thread: the stack matches the ticket's `hs.png`
call graph almost frame for frame. The laptop's power source is recorded per run (battery = Low Power Mode,
which causes a different, eviction-type stall even on 4.2.24). Start at [`WT-7264/README.md`](WT-7264/README.md).
