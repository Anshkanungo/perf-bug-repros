# SERVER-52879 reproduction plan

Written 2026-10-27, before the main runs. Changes made later are logged at the bottom.

## Hypothesis

In MongoDB 4.4.3, the `WTIdleSessionSweeper` thread wakes every 10 s and calls
`WiredTigerSessionCache::closeExpiredIdleSessions()`. That function deletes every cached
WiredTiger session that has been idle longer than `wiredTigerSessionCloseIdleTimeSecs`,
**while holding `_cacheLock`**. `getSession()` and `releaseSession()` take the same latch, so every
operation stalls while the sessions close. Closing a session is expensive with ~12k tables because
each idle session holds thousands of WiredTiger-cached cursors and cached data handles
(`__session_close_cached_cursors`, `__session_discard_dhandle`). The stalled operations then run as a
burst that needs ~100 sessions at once. Those sessions are cached, sit idle, and are all closed at
the same later sweep, so the cycle repeats.

The 4.4.4 fix (commit `d6a3d7b`) only moves the `delete session` calls out of the latch. So with
the identical workload, 4.4.4 should show no periodic spikes.

> **Teacher's note: WiredTiger sessions, cursors, dhandles.** A WT *session* is a per-thread
> context. A *cursor* is an open iterator on one table (collection or index). A *dhandle* (data
> handle) is the shared in-memory handle for one table file. MongoDB keeps idle sessions in a
> cache so operations don't pay for `open_session`. In 4.4 the default `wiredTigerCursorCacheSize=-100`
> means cursors are closed into WiredTiger's *per-session* cursor cache on release. A session that
> has served inserts into many random collections ends up holding a cached cursor (and a cached
> dhandle reference) for each table it touched. That is why closing it costs time proportional to
> the number of tables.

### Derived, falsifiable predictions

| # | Prediction | How it's checked |
|---|---|---|
| P1 | 4.4.3 shows periodic insert-latency spikes far above baseline | per-second max client latency; spike = ≥10x the run's median per-second max (floor 10 ms) |
| P2 | Spike period is **~40 s** with idle timeout 30, not 30 s. The sweeper only checks every 10 s, and the burst sessions become idle a few ms *after* a sweep, so they miss the 30 s check. Predicted period = (⌊T/10⌋+1)·10 s for T a multiple of 10. The ticket's own `spikes.png` and `before.png` measure ~40 s. | median interval between spike events |
| P3 | Spikes line up with WT `open session count` / `cached cursor count` drops followed by a rise | 1 s serverStatus samples |
| P4 | 4.4.4 with the identical workload has no periodic spikes | same detector, same thresholds |
| P5 | Causal: on 4.4.3 with T=60 the period becomes ~70 s | same detector |
| P6 | On-CPU: during a spike the sweeper thread is in `closeExpiredIdleSessions → WiredTigerSession::~WiredTigerSession → __session_close → __session_close_cached_cursors / __wt_session_close_cache → __session_discard_dhandle`. Off-CPU: connection threads block in `pthread_mutex_lock` under `WiredTigerSessionCache::getSession/releaseSession`. | perf `cpu-clock` + `sched:sched_switch` with call graphs |

## Independent variable

The mongod version: official Docker images `mongo:4.4.3` (buggy) vs `mongo:4.4.4` (fixed). Both
are pulled by tag, and the resolved digest is recorded in each run's `meta.json`.

## Controls (identical across the A/B runs)

- Same host (Apple M1 Pro, Docker Desktop VM: 10 vCPU, 7.75 GiB), runs strictly sequential, never two at once.
- mongod: standalone, `--wiredTigerCacheSizeGB 1`, `--setParameter wiredTigerSessionCloseIdleTimeSecs=30`,
  `--ulimit nofile=64000:64000`, fresh named volume per run, everything else default (including `syncdelay=60`).
- Workload: Bruce Lucas's `repro.js`, minimally adapted (see `workload/README.md`): 1000 collections × 10
  secondary indexes (≈12k tables), then 100 threads, each looping `insert` into a random collection then
  `sleep(100 + rand·10)` ms (~950 inserts/s total).
- The **same client** for both versions: the legacy `mongo` shell from the `mongo:4.4.3` image, so only the server changes.
- Same duration, same sampler, same analysis thresholds (fixed before seeing results).
- Unchanged noise source: 5 unrelated Airflow/Postgres containers keep running on the same VM (≈1.4 GiB,
  ~1–2% CPU each). `docker stats` is sampled so their impact can be checked.

## Metrics

- **Client:** per-insert latency (start timestamp, latency), aggregated per second (by completion time) into
  count / p50 / p99 / max. The legacy shell only has 1 ms timer resolution, which is enough for tens-of-ms
  spikes. A pymongo driver (µs resolution, same workload shape) is a cross-check.
- **Server, every 1 s:** `serverStatus({opLatencies:{histograms:true}})`.
  - `opLatencies.writes`: per-second mean latency, plus approximate p99/max from histogram deltas.
  - `wiredTiger.session` "open session count"; `wiredTiger.cursor` "cached cursor count" / "open cursor count";
    `wiredTiger.connection` "files currently open"; data-handle counters; checkpoint-running flag.
  - `connections.current`.
- **Resources:** `docker stats` every 5 s (memory/CPU of mongod and client).
- **Timestamps:** epoch ms everywhere, so spikes can be lined up with sweeps and checkpoints.

> **Teacher's note: FTDC vs our sampler.** mongod already records `serverStatus` once per second into
> `diagnostic.data` (FTDC, "full-time diagnostic data capture"). Bruce's charts are FTDC plots. FTDC is a
> compressed binary format that needs a decoder, so we sample the same counters ourselves into
> plain JSON lines. The `diagnostic.data` directory is still copied out of each run for anyone with FTDC tools.

## Success criteria (fixed before the runs)

Measurement window = after a 120 s warm-up (cached cursor count needs a few cycles to build up, as in `spikes.png`).
A **spike event** is a run of consecutive seconds whose client max latency is ≥ max(10 × median per-second max, 10 ms).

- **S1, symptom (4.4.3):** ≥8 spike events in the window.
- **S2, periodicity (4.4.3):** median inter-spike interval within 40 ± 5 s, and ≥75% of intervals in [35, 45] s.
- **S3, fix (4.4.4):** the same detector finds ≤2 spike events, and the 99.5th percentile of per-second max
  latency is ≥5x lower than on 4.4.3.
- **S4, causal (optional):** 4.4.3 with T=60 → median interval 70 ± 5 s.
- **S5, mechanism:** the profile shows the P6 stacks.

**Verdict rule:** *reproduced* = S1+S2+S3. *Partially* = S1 holds but S2 or S3 fails.
*Not reproduced* = S1 fails after the variations below.

## Steps

1. Smoke test the pipeline at small scale (100 collections, 20 threads, 90 s, T=10).
2. **Run A:** 4.4.3, full workload, 12 min of inserts (2 min warm-up + 10 min ≈ 15 cycles).
3. **Run B:** 4.4.4, identical.
4. Analyze A vs B: summary table and plots.
5. **Run C (causal):** 4.4.3 with T=60, 12 min. T=60 is chosen because its predicted 70 s period does *not* coincide with the 60 s checkpoint interval.
6. **Profiling run:** 4.4.3 with a privileged perf sidecar in mongod's PID namespace:
   on-CPU `perf record -e cpu-clock --call-graph fp` (dwarf as fallback) across ≥3 cycles, plus off-CPU
   `sched:sched_switch` call graphs across ≥2 cycles. This is kept separate from Run A so profiling
   overhead never touches the A/B numbers.
7. Optional cross-checks: pymongo driver on both versions, and more variations if anything is ambiguous.
8. Write README, DISCUSSION, REPORT; update PROGRESS; remove containers and volumes.

## Risks and fallbacks

| Risk | Fallback |
|---|---|
| Docker Hub anonymous rate limit (hit on the first pull) | pull the identical official images from `public.ecr.aws/docker/library/*` (same per-platform digests, verified) |
| Memory: 100 shell threads + 12k tables on a 7.75 GiB VM | measured: shell ≈1 GiB; watch `docker stats`; fall back to the pymongo driver |
| The M1 is fast, so spikes may be smaller than on Bruce's machine | more tables (2000 colls), longer runs, single-node replica set, more threads; record every attempt |
| 60 s WT checkpoints add their own latency bumps | log checkpoint-running state; P2's 40 s period is distinct from 60 s |
| No hardware PMU in the VM | `-e cpu-clock` (software timer); verified working |
| Release binary lacks DWARF | the image's `mongod` is *not stripped* (`.symtab` has the WT static functions, verified), so names resolve without the 2.3 GB debug-symbol tarball; dwarf unwinding uses `.eh_frame` |
| Shell timer is 1 ms | server-side histograms and the µs pymongo cross-check |

## Changes from original plan

1. **2026-10-27, after the smoke test, before Run A started: added a secondary, server-side detector (D2).**
   In the smoke test (100 colls, 20 threads) the legacy shell's client-side tail was noisy: the median
   per-second max was 7 ms on the client but ≤2 ms in the server's own histogram, so the client rule's
   threshold became 70 ms. The ticket's evidence is FTDC's per-second *mean* write latency, so the same rule
   now also runs on `opLatencies.writes` deltas from our 1 Hz sampler:
   **D2 spike second = server mean write latency ≥ max(10 × run median, 1 ms)**, clustered the same way.
   The client rule (D1) stays the primary, pre-registered detector for S1–S3. D2 is reported next to it,
   and any disagreement between them is reported, not resolved in favour of the "better" one.
   Plot change: the gray reference line is per-second p99 rather than median, because the shell's 1 ms
   timer makes the median a flat 0/1 ms line.
2. **2026-10-27, during Run A: added a 4.4.4 profiling control.** `r4.4.3...r4.4.4` is 64 commits, including
   7 WiredTiger imports that touch WT `cursor/`, `conn/`, and `schema/` code. So "no spikes on 4.4.4" alone
   can't tell the mutex fix apart from "WT made session close cheaper". The control profiles 4.4.4 the same
   way: if its sweeper still spends comparable CPU in `closeExpiredIdleSessions` / session close while no
   threads wait on the session-cache mutex, the improvement comes from moving the close out of the latch.
   A source build of r4.4.3 + only `d6a3d7b` would be the cleanest test. It's out of scope here (hours of
   build) and is listed as a next step for the team, who build mongod themselves anyway.
3. **2026-10-27, after Run A: added an exploratory, sweep-locked analysis.** It is labeled *exploratory*
   wherever it appears and is not part of the S1–S3 verdict. For every 1 s sampling interval it records
   whether a session-close sweep happened (cached-cursor count drop ≥5% and ≥500 cursors between two
   serverStatus samples) and the max client insert latency in that interval. It was added because Run A's
   on-grid spikes all lined up with sweeps while some sweep stalls fell between 10 and 20 ms, under D1's
   20 ms threshold. It was written before Run B's data was analyzed and is applied unchanged to every run.
4. **2026-10-27, after Run B: added variation V1 (checkpoints pushed out of the window).** Run B (4.4.4) had
   large stalls not tied to sweeps. They start at WiredTiger checkpoint starts and continue while the burst of
   new sessions opens cursors. This matches the known, separate issue WT-5479 / SERVER-31704
   ("checkpoint schema lock can cause long stalls … with many active data handles"), present in both builds.
   V1 repeats the A/B with `--syncdelay=3600` (no checkpoint during the 12 min run) and nothing else changed.
   The main A/B with default settings stays the primary result; V1 is reported next to it.
5. **Profiling mechanics (no effect on the A/B runs):** profiling runs start mongod with `docker --init`, so
   mongod isn't PID 1 and the gdb snapshot can freeze it with SIGSTOP. Both perf recordings use
   `CLOCK_MONOTONIC`, because the kernel rejects `CLOCK_REALTIME` for tracepoints, and they're converted to
   epoch time through a recorded offset.
6. **Run order (all sequential):** smoke test → A (4.4.3) → B (4.4.4) → profiler functional tests →
   P-4.4.3 (profile) → C (4.4.3, T=60, 14 min) → V1-4.4.3 → V1-4.4.4 → P-4.4.4 (profiling control) → C2.
7. **2026-10-27, after Run C: correction and added run C2.** Step 5 above assumed checkpoints every 60 s.
   Measured in Run A, checkpoints *start* every ~70 s (30, 99, 172, 241, 310 s, …): `syncdelay=60` counts from
   the end of the previous checkpoint, and each takes ~10 s here. So T=60's predicted 70 s period coincides
   with the checkpoint cadence, and C's symptom-level periodicity (spike intervals, autocorrelation) is
   confounded by checkpoint-start stalls (4 of its 10 spike events). The mechanism-level evidence in C
   (cursor-drop sweeps 70 s apart) is unaffected. **C2** repeats C with `--syncdelay=3600`, which is the clean
   causal test. While C was running I also ran a few analysis containers (≈1 core for a few minutes), a small
   extra perturbation recorded in C's caveats. Measurement runs after C had no such side jobs.

## Outcome against the criteria (filled in after all runs; details in `results/summary.md`)

| criterion | main A/B (default config) | V1 (checkpoints pushed out) | C / C2 (T=60) |
|---|---|---|---|
| S1 ≥8 spike events on 4.4.3 | **met** (14) | **met** (13) | met (10 / 19) |
| S2 median gap 40±5 s and ≥75% of gaps in [35,45] | median 40.0 s, but only 38% of gaps → **not met** | median 40.1 s, 42% → **not met** | – |
| S3 4.4.4 ≤2 events and p99.5 ≥5× lower | 13 events, ratio 0.4× → **not met** | 2 events, ratio 4.9× → **not met (narrowly)** | – |
| S4 T=60 → median gap 70±5 s | – | – | 49.9 s / 32.3 s → **not met** (interleaved non-sweep events); median gap between *sweeps* 70.9 s / 70.0 s and autocorrelation peak 70 s → met at the mechanism level |
| S5 profile shows the P6 stacks | **met**: sweeper 100% in `closeExpiredIdleSessions → ~WiredTigerSession → __session_close` (91% `__session_close_cached_cursors`, 9% `__session_discard_dhandle`); 57 threads blocked in `WiredTigerSessionCache::getSession` during a 57 ms sweep; 4.4.4 control has the same sweeper work and 0 blocked threads | | |

**Verdict by the pre-registered rule: partially reproduced** (S1 holds, S2/S3 do not). The exploratory
sweep-locked analysis (change 3) is unambiguous in every run: on 4.4.3, 100% of session-close sweeps carry a
≥10 ms insert stall (median 29–65 ms); on 4.4.4, 0%.
