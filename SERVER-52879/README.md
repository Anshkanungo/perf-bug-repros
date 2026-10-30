# SERVER-52879: periodic latency spikes from closing idle WiredTiger sessions under a mutex

**Bug:** in MongoDB ≤ 4.4.3 (also 4.2.10, 4.0.21, 3.6.21), the `WTIdleSessionSweeper` thread wakes every
10 s and closes cached WiredTiger sessions that have been idle longer than `wiredTigerSessionCloseIdleTimeSecs`
(default 300 s) **while holding the session-cache mutex**. Every operation needs that mutex to get or return
a session. With many tables, each idle session caches thousands of cursors and dhandles, so closing a batch
takes long enough that all operations stall. The stalled operations then return as a burst that needs ~100
fresh sessions, and those all expire together at a later sweep, so the stall repeats periodically. Fixed in
4.4.4 / 4.2.12 / 4.0.23 / 4.9.0 by closing the sessions after releasing the mutex
([`d6a3d7b`](https://github.com/mongodb/mongo/commit/d6a3d7b707df26dfdc64b1ffd7264fae2886ec50)).
Details and the developer discussion: [`discussion/DISCUSSION.md`](discussion/DISCUSSION.md).

**Result:** see [`REPORT.md`](REPORT.md) (one page) and [`results/summary.md`](results/summary.md).

## Layout

| path | what |
|---|---|
| `run.sh` | **one entry point**: start mongod (or use yours) → create 1000×10 indexes → run the workload → sample metrics → collect logs → analyze |
| `profile.sh` | privileged perf/gdb sidecar: on-CPU + off-CPU call graphs and a gdb all-thread snapshot during a sweep |
| `analyze.sh` | per-run summaries and A/B comparison tables and plots (runs `analysis/analyze.py` in a container) |
| `workload/` | original `repro.js` (untouched) + `parallelTester.js`, adapted script, pymongo driver, sampler ([README](workload/README.md)) |
| `profiling/` | profiler image + collection/analysis scripts |
| `analysis/` | `analyze.py` |
| `discussion/` | Jira JSON, attachments, fix diffs, source snapshots, `DISCUSSION.md` |
| `results/` | `summary.md`, `plots/`, `runs/<label>/` (summaries; `raw/` is git-ignored), `profiles` |
| `PLAN.md` | hypothesis, controls, success criteria (written before the main runs) + change log |

### Runs in `results/runs/`

| label | what | why |
|---|---|---|
| `smoke-433-shell` | 4.4.3, 100 colls, 20 threads, 90 s, T=10 | pipeline smoke test |
| `A-4.4.3-shell-idle30` | **4.4.3**, ticket workload, T=30, 12 min | main A/B: buggy |
| `B-4.4.4-shell-idle30` | **4.4.4**, identical | main A/B: fixed |
| `C-4.4.3-shell-idle60` | 4.4.3, T=60, 14 min | causal check (confounded: 70 s = checkpoint cadence) |
| `C2-4.4.3-idle60-syncdelay3600` | 4.4.3, T=60, no checkpoints, 14 min | clean causal check |
| `V1-4.4.3-syncdelay3600` / `V1-4.4.4-syncdelay3600` | A/B with checkpoints pushed out of the window | removes the checkpoint stall confounder |
| `P-4.4.3-profile` / `P-4.4.4-profile` | 4.4.3 / 4.4.4 with perf + gdb sidecar (`profile/`) | symptom function and call stacks; 4.4.4 is the control |

## Prerequisites

- Docker. Nothing else is needed on the host. arm64 or x86-64.
- Resources per run: ~1.2 GiB for mongod (1 GB WT cache, 12k tables), ~1.2 GiB for the legacy-shell client
  (100 threads), about 1 CPU core in total. ~0.5 GB of disk per run (data volume, deleted afterwards) plus
  ~30–60 MB of raw results.
- Images: `mongo:4.4.3`, `mongo:4.4.4` (~0.6 GB each), plus two built here: `s52879-tools:1` (~0.6 GB,
  Python + pymongo + pandas/matplotlib) and `s52879-prof:1` (~0.5 GB, perf + gdb + FlameGraph). If Docker Hub
  refuses anonymous pulls (HTTP 429), the scripts pull the same images from `public.ecr.aws/docker/library/`.

## Reproduce

```bash
cd SERVER-52879
./run.sh 4.4.3                      # buggy: ~13 min (30 s setup + 12 min inserts + collection/analysis)
./run.sh 4.4.4                      # fixed: identical workload
./analyze.sh results/runs/<4.4.3-label> results/runs/<4.4.4-label> --compare-out results --names "4.4.3,4.4.4"
```

Each run prints its result directory, `results/runs/<label>/`, which contains:

- `summary.md`: spike events, inter-spike intervals, latency percentiles, WT session/cursor counters,
  criteria S1/S2 (see `PLAN.md`)
- `timeline.png`: per-second max/p99 insert latency, WT open sessions, and WT cached cursors over time
- `per_second.csv`: client latency per second joined with 1 Hz serverStatus counters
- `raw/`: `client.log` (one line per insert), `serverstatus.jsonl`, `mongod.log`, `diagnostic.data/` (FTDC),
  `docker_stats.jsonl`

**Causal check** (the spike period should follow the timeout, (⌊T/10⌋+1)·10 s):
`./run.sh 4.4.3 --idle-timeout 60` → expect ~70 s between spikes instead of ~40 s.

**Profile the spikes** (exactly what produced `results/runs/P-4.4.3-profile/`):
`./run.sh 4.4.3 --duration 600 --profile --profile-delay 150 --profile-args "--secs 100 --snapshot --snapshot-timeout 200"`,
or start a run with `--keep` and run `./profile.sh` yourself. Output goes to `results/runs/<label>/profile/`:
`profile_summary.md`, `oncpu_sweeper.svg`, `offcpu_sweeps.svg`, `snapshot_summary.md`.

> **Teacher's note: perf inside Docker.** perf needs the kernel's `perf_event_open`, so the sidecar runs
> `--privileged` (which bypasses `kernel.perf_event_paranoid` without changing it) and joins mongod's PID
> namespace with `--pid=container:s52879-mongod`, so `-p <pid>` and `/proc/<pid>/exe` work from the sidecar.
> VMs such as Docker Desktop on Apple Silicon expose no hardware PMU, so the sampling event is the
> software timer `-e cpu-clock` (`--event cycles` on bare-metal x86-64). The official `mongod` is *not
> stripped* (it keeps `.symtab`), so even static WiredTiger functions get names without the 2.3 GB
> debug-symbol tarball. Frame-pointer call graphs (`--call-graph fp`) unwind fine; use `--callgraph dwarf`
> if a build drops frame pointers.

> **Teacher's note: off-CPU analysis.** Lock contention barely shows up in an on-CPU profile, because waiting
> threads are asleep. `profile.sh` also records the scheduler tracepoints `sched:sched_switch` (a thread goes
> to sleep; the stack shows *where*) and `sched:sched_wakeup` (who woke it, and when). The time between the
> two is the blocked time. Summing blocked time per stack during the sweeper's busy windows shows the
> connection threads stuck in `pthread_mutex_lock` under `WiredTigerSessionCache::getSession/releaseSession`.

## Point it at your own (instrumented) mongod

```bash
# 1) an already-running mongod (any host/port reachable from Docker; the idle timeout is set at runtime)
./run.sh --target 10.0.0.5:27017 --idle-timeout 30 --label my-instrumented-run
#    --network host is the default for --target (Linux). On Docker Desktop use host.docker.internal:<port>.
#    Add --skip-setup to reuse an existing 1000x10 dataset, --no-set-idle to leave the server parameter alone.

# 2) your own image (started exactly like the official one: ulimit, cache size, idle timeout, fresh volume)
./run.sh --image registry.example.com/mongod-instrumented:4.4.3 --label instr-4.4.3

# 3) your own binary, run inside the official 4.4.3 image (Ubuntu 20.04 userland)
./run.sh 4.4.3 --mongod-binary /path/to/mongod --label instr-bin

# profile a natively running mongod on a Linux host (sidecar uses --pid=host)
./profile.sh --host-pid $(pgrep -o mongod) --secs 100 --snapshot --event cycles
```

The workload is the only thing that has to reach the server. If your instrumentation needs the exact
timestamps of the stalls, `results/runs/<label>/raw/client.log` has one line per insert
(`O,<thread>,<start_epoch_ms>,<latency_ms>`) and the summary lists every spike event with its start time.

## Expected output

From the runs in this repo (Docker Desktop on an M1 Pro, 10 vCPU). Full table: [`results/summary.md`](results/summary.md).

- **Both versions:** ~945 inserts/s, per-insert p50 ≈1 ms (shell timer resolution), median per-second max
  ≈2 ms, ~1.4–1.7 GiB mongod peak RSS, 12,014 WT files open, ~36k data handles.
- **4.4.3:** a session-close sweep (WT `cached cursor count` drops by 15–36k between two 1 s samples)
  shows up every ~40 s (T=30). **Every** such sweep came with an insert stall: 21–118 ms, median ~30 ms,
  sometimes hitting 90–99 of the 100 threads. Plot titles read e.g. "14 sweeps, 100% with a ≥10 ms insert".
  With `--idle-timeout 60` the sweeps (and their stalls) move to ~70 s apart: the median sweep gap is 40 s at
  T=30 and 70 s at T=60, as predicted by (⌊T/10⌋+1)·10.
- **4.4.4:** the same sweeps still happen (median 24k cursors closed) with **no** stall: 0% of sweep
  intervals contain a ≥10 ms insert, and the median max latency in them is 2 ms, the baseline.
- **Both versions** also show large all-thread stalls (100–700 ms) that are *not* this bug: at WT checkpoint
  starts and during bursts of new sessions opening cursors on thousands of tables. They make the plain
  "count the spikes" comparison noisy (see REPORT caveats). Push checkpoints out with
  `--mongod-arg --syncdelay=3600` for a cleaner trace. Then 4.4.4 is nearly silent (2 events ≥20 ms in
  10 min, peak per-second mean write latency 0.69 ms), while 4.4.3 keeps its sweep-locked stalls (13 events,
  10 at sweeps, peak per-second mean 78 ms): [`results/v1/plots/ab_timeline.png`](results/v1/plots/ab_timeline.png).
- **Profile (4.4.3):** `profile_summary.md` shows one sweep window per heavy sweep (e.g. 57 ms), during which
  ~all inserting threads block in `WiredTigerSessionCache::getSession` (57 threads, longest wait 57.0 ms = the
  longest client insert). `oncpu_sweeper.svg` is 100% `closeExpiredIdleSessions → ~WiredTigerSession →
  __session_close`, and `snapshot_summary.md` shows the frozen sweeper plus 8 threads blocked in `getSession`.
- **Profile (4.4.4, control):** the same sweeper stacks with the same split (90% `__session_close_cached_cursors`,
  10% `__session_discard_dhandle`, a 44 ms sweep), but 0 blocked threads, 0 slow inserts during the sweep, and a
  gdb snapshot with the sweeper closing sessions and nobody waiting.

## Gotchas and troubleshooting (all hit while building this)

- **Docker Hub HTTP 429** on `docker pull mongo:4.4.3`: anonymous rate limit. `run.sh` retries from
  `public.ecr.aws/docker/library/mongo` (same digests). Or `docker login`.
- **Anonymous volumes:** the `mongo` image declares `VOLUME /data/db /data/configdb`, so every container
  started from it (even `docker create`, or a shell-only client) silently creates unnamed volumes. The scripts
  mount a named `s52879-*` volume or `--tmpfs` on both paths, and remove containers with `docker rm -v`.
- **Don't edit `run.sh` while it is running.** bash reads scripts incrementally, so changing earlier bytes
  shifts what the running instance executes next.
- **perf in a container:** use `--privileged` (or CAP_PERFMON + CAP_SYS_ADMIN) and share the PID namespace.
  The kernel refuses `-k CLOCK_REALTIME` for tracepoints (not NMI-safe), so `profile.sh` records
  CLOCK_MONOTONIC and saves the offset. Record `sched:sched_waking` rather than `sched:sched_wakeup` with
  `-p <pid>`: `sched_wakeup` often fires on the wakee's CPU in interrupt context and is dropped by a
  per-process recording.
- **`SIGSTOP` to PID 1 does nothing** from inside the same PID namespace (init protection). That's why profiling
  runs start mongod with `docker --init`, so the snapshot can freeze it the instant the sweeper gets busy.
- **gdb on aarch64 stops unwinding at glibc's `pthread_mutex_lock`** ("previous frame identical"). The
  snapshot script walks the frame-pointer chain for those threads. perf's `--call-graph fp` is not affected.
- **perf report outside the sidecar** needs the binaries: see `profiling/report_offline.sh` (`--symfs`).
- **Checkpoints are a second stall source here.** With ~12k tables / ~36k data handles, WT checkpoints
  (every ~70 s: `syncdelay=60` counted from the end of the previous ~10 s checkpoint) cause their own
  all-thread stalls in *both* 4.4.3 and 4.4.4 (consistent with WT-5479 / SERVER-31704). Use
  `--mongod-arg --syncdelay=3600` to keep checkpoints out of a 12-minute run when you want only this bug.
- **Clock artifacts:** `opLatencies` can record one op in the 2^40 µs overflow bucket after a VM clock
  step. The analysis ignores buckets above 60 s.
