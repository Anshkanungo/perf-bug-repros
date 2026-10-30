# WT-7264 / SERVER-67350 reproduction plan

Written 2026-10-27, after the pilot runs listed below and **before the main runs**. Changes made later are
logged at the bottom with their date. The pilots are disclosed, kept in `results/runs/pilot*` /
`results/runs/smoke*`, and are **not** part of any criterion.

## Hypothesis

A unique-index insert in MongoDB 4.4/5.0 does, inside the inserting transaction
(`WiredTigerIndexUnique::_insert`, `wiredtiger_index.cpp`): insert the prefix key (the index key without
the RecordId), remove it again, then `_keyExists()` → `WT_CURSOR::search_near(prefix)` (+ one `next`/`prev`)
to look for an existing `(key, RecordId)` entry, then insert the full key. Since WT-5461 (4.4.0), a
`search_near` that lands on a key that is not visible to the transaction does not return the on-page value;
it keeps calling next (then prev) until it finds a *visible* key, however far away. With durable history
(4.4+), a key whose page has been evicted and whose on-disk version is newer than the reader's snapshot
costs a history-store lookup (`__wt_hs_find_upd`) that finds nothing ("history store table reads missed").

In Bruce Lucas's workload each of 20 threads appends ascending keys in its own key range. The keys
"next" of a thread's insert point belong to the threads with higher ranges. **Refinement (my prediction,
not stated in the ticket):** a thread's *first* transaction can take its snapshot before the higher-range
threads have committed anything; then every key they insert while that transaction is open is invisible
to it, so each of its `search_near` calls walks over all of them (and, once their pages are evicted, does
one history-store lookup per key). The slower the walk, the longer the transaction stays open and the more
invisible keys pile up: a feedback loop that ends only when the other threads stop inserting. Later
transactions get fresh snapshots and are fast. The fix (SERVER-61185, `wiredTigerPrefixSearchForUniqueIndexes`)
reconfigures the cursor with `prefix_search=true` around `_keyExists`, so the walk stops at the first key
that no longer matches the prefix (WT-7264's new search_near option).

> **Teacher's note: snapshots and "invisible" keys.** Each WiredTiger transaction reads from a snapshot:
> it sees only changes committed before the snapshot was taken. A key committed by another thread a
> millisecond later is "invisible" to it, physically present in the B-tree but skipped by every cursor
> operation. Walking over invisible keys costs time even though nothing is returned, and that time is the bug.

### Derived, falsifiable predictions

| # | prediction | checked with |
|---|---|---|
| P1 | Bug arm: some insertMany calls stall for seconds to minutes while the other threads finish normally | client per-call log |
| P2 | Stalls fall on a thread's **first** insertMany call (batch 0) | client per-call log |
| P3 | During a stall "history store table reads missed" and "entries skipped by cursor next/prev" grow by ~10^6/s, and the number of connection threads at ≈100% CPU equals the number of stuck threads (SERVER-67350: "one or two cores at 100% CPU") | 1 Hz serverStatus, 1 Hz /proc per-thread CPU |
| P4 | Fix arm (same binary, `prefix_search` on): no stall, ~0 history-store misses, nonzero "search near has exited due to prefix config" | same |
| P5 | Stuck thread on-CPU stack: `WiredTigerIndexUnique::_insert → _keyExists → search_near → __wt_btcur_search_near → __wt_btcur_next/prev → (__wt_txn_read) → __wt_hs_find_upd` as in the ticket's `hs.png` | perf + gdb snapshot |
| P6 | 4.2.24: no stall (no durable history; pages with unresolved updates stay in memory) | same detector |
| P7 | 4.4.2 stalls; 4.4.1 stalls less or later, with fewer history-store misses (Bruce's 441/442 FTDC; SERVER-67350 bisect to `30e753ec`, between 4.4.1 and 4.4.2) | same detector |
| P8 | Control: the same workload with **non-unique** indexes does not stall (no `_keyExists`) | same detector |

## Independent variable (primary A/B)

`wiredTigerPrefixSearchForUniqueIndexes` **false (bug arm) vs true (fix arm)** on one binary, official
image `mongo:5.0.33` (resolved digest in each run's `meta.json`). Verified before the runs:

- Source at tag `r5.0.33` (`src/mongo/db/storage/wiredtiger/wiredtiger_parameters.idl`): name
  `wiredTigerPrefixSearchForUniqueIndexes`, `set_at: [startup, runtime]`, `AtomicWord<bool>`,
  **default true**. At `r4.4.30`: same definition, **default false**. Copies in `discussion/source/`.
- `wiredtiger_index.cpp` at `r5.0.33`: the parameter only decides whether `c->reconfigure(c,
  "prefix_search=true")` wraps the `_keyExists()` call in `WiredTigerIndexUnique::_insert`.
- Runtime: `getParameter` returned `false` when started with `--setParameter ...=false`; every run records
  the value in `server.json` (`ready.py`).

## Controls (identical across arms)

- Same host (Apple M1 Pro, Docker Desktop VM: 10 vCPU, 7.75 GiB), runs strictly sequential, arms alternated
  (bug, fix, bug, fix, ...).
- mongod: standalone, `--wiredTigerCacheSizeGB 1` (always explicit), container `--memory 3g` (no swap),
  `--ulimit nofile=64000:64000`, fresh named volume per run, everything else default (`syncdelay` 60).
- Client: the legacy `mongo` shell from `mongo:5.0.33` for **every** server version, `--memory 2g`;
  `jstests/libs/parallelTester.js` from `r5.0.33`. The shell splits each 2000-document insertMany into two
  insert commands of 1000 (`bulk_api.js`, `maxNumberOfDocsInBatch = 1000` at r5.0.33 and r4.4.2).
- Unchanged noise sources: 5 unrelated Airflow/Postgres containers (measured bursts of ~3–6 cores for
  1–2 s every ~30 s). Sampled, never stopped.

## Workloads

- **W0, unmodified**: Bruce Lucas's `repro.sh` workload (`workload/repro-adapted.js`, all changes listed in
  `workload/README.md`): unique indexes on `a` and `b`, 20 threads, each inserting 100,000 `{_id, a, b}`
  documents (`inx = t*100000 + i + j`) with insertMany batches of 2000; threads start one after another as
  in the original.
- **W1, barrier (labelled variant)**: identical, except every thread waits for a common start time before
  its first insertMany (`--sync-start`), so all first transactions overlap. Motivation: P2 says the stall
  needs a first transaction that predates its neighbours' commits; SERVER-67350's program started its 5
  connections within ~2 ms of each other.
- W2 (optional, labelled): SERVER-67350-like: 5 pymongo threads, 1,000,000 `{someId: ObjectId}` documents
  in contiguous ascending ranges, one unique index, 100,000 documents per insert_many (`--workload 67350`).

### Pilot runs (before this plan; excluded from every criterion)

| pilot | condition | result |
|---|---|---|
| pilot0 (manual) | 5.0.33 off, W0 | thread 4's first call took **14.4 s**, others 0.1–0.4 s; 14.4 M HS reads missed |
| smoke1, pilot2–5 | 5.0.33 off, W0 | 0/5 calls ≥ 3 s; pilot2 had a 2.5 s first call with 0.96 M HS misses; others 0–12 k |
| pilot6–8 | 5.0.33 off, W1 | 3/3 stalled: 11 s, 83 s, 348 s (two threads stuck, both on batch 0); 10 M – 626 M HS misses |
| pilot9–10 | 5.0.33 on, W0 | no stall, longest call 0.24 s, 0 HS misses |
| smoke2 | 4.2.24, W0 | 5.4 s, no stall |
| smoke3 | 4.4.1, W0 | 14 threads' first calls took ~4.2 s; 432 M entries skipped but only 0.43 M HS misses |
| smoke4 | 4.4.30 (default: off), W0 | **capped at 600 s**: 12 stalled calls, 837 M HS misses |

So W0 stalls in only ~1 of 6 runs on 5.0.33 on this machine (but stalls badly on 4.4.30), while W1 stalled
3/3. A 5-vs-5 test with W0 on 5.0.33 would have little power, hence the design below.

## Metrics

- **Client** (`raw/client.log`): `S`/`B` records per insertMany call (thread, batch, start epoch ms,
  latency ms), `T` per finished thread, phase markers. A call that never returns is visible from its `S`
  record.
- **Server, 1 Hz** (`raw/serverstatus.jsonl`, our plain-text stand-in for FTDC): whole `wiredTiger.cache`,
  `.cursor`, `.transaction` sections, `opcounters`, `opLatencies`, `globalLock.activeClients`. Names used
  (checked on 5.0.33, 4.4.x): `history store table reads missed`, `history store table reads`,
  `Total number of entries skipped by cursor next calls` / `... prev calls`, `cursor search near calls`,
  `Total number of times a search near has exited due to prefix config`, `pages evicted by application
  threads`, `forced eviction - pages selected count`, `transaction checkpoint currently running`,
  `transaction checkpoints`. 4.2 has no history store (these are reported as n/a).
- **mongod per-thread CPU, 1 Hz** (`raw/threads.jsonl`): utime+stime of every mongod thread read from
  `/proc` by the sampler sharing mongod's PID namespace.
- **Docker stats, ~1 Hz** (`raw/docker_stats.txt`): every container; other containers' summed CPU = noise.
- FTDC (`raw/diagnostic.data`), `mongod.log` (slow-query lines carry per-command `bytesRead` and cache wait).

## Definitions and success criteria (fixed now)

- **Stalled call**: an insertMany call that takes **≥ 3 s**, or is still running when the run ends.
  (Pilot calls without the bug: max 0.26 s on 5.0.33.)
- **Stalled run**: a run with ≥ 1 stalled call.
- **HS misses**: increase of `history store table reads missed` from the last sample before the insert
  phase to the first sample ≥ 0.5 s after it.
- **Stall share**: fraction of a run's HS-miss increase that accrues while some call has already been
  running ≥ 3 s.
- **Run cap**: 600 s of insert phase for the primary A/B, 300 s for every other condition (time budget).
  A capped run is a valid "stalled ≥ cap" result.
- **Noisy run**: other containers' summed CPU ≥ 200% in any docker-stats sample of the insert phase.
  Reported per run; criteria use all runs; a sensitivity check without noisy runs is reported, not used
  for the verdict.

**Primary A/B: 5.0.33, W1 (barrier), bug arm off vs fix arm on, n = 5 per arm, cap 600 s.**

- **S1, symptom:** ≥ 3 of 5 bug-arm runs are stalled runs.
- **S2, fix:** 0 of 5 fix-arm runs are stalled runs.
- **S3, separation:** one-sided Fisher exact test on stalled-run counts, bug vs fix: p < 0.05
  (with 5 vs 5 and a clean fix arm this needs ≥ 4/5).
- **S4, mechanism counters:** (a) every stalled bug-arm run has ≥ 1,000,000 HS misses; (b) the largest
  fix-arm HS-miss count is < 1% of the smallest stalled bug-arm count; (c) in every stalled bug-arm run
  the stall share is ≥ 80%.
- **S5, stack:** in a profiled bug-arm stall, the stuck connection thread(s) (chosen by timing only: on-CPU
  ≥ 30% of the time after every other client thread finished) have `WiredTigerIndexUnique::_keyExists`
  in ≥ 50% of their samples and `__wt_hs_find_upd` in ≥ 50% of their samples; the gdb snapshot shows the
  stuck thread inside `_keyExists`. In the profiled fix-arm run, `__wt_hs_find_upd` is in < 1% of
  connection-thread samples.

**Verdict rule:** *reproduced* = S1–S5 all met. *Partially reproduced* = S1 met, any of S2–S5 not met.
*Not reproduced* = S1 not met.

### Secondary conditions (pre-registered checks; descriptive, not part of the verdict)

| id | condition | n | check |
|---|---|---|---|
| U | 5.0.33 W0 (unmodified) off vs on | 10 + 10 | U1: stalled runs off > on; U2: HS misses > 0 in ≥ 1 off run and = 0 in all on runs |
| V | 4.4.30 W0 off (default) vs on | 3 + 3 | V1: ≥ 2/3 off runs stalled, 0/3 on runs |
| R | 4.4.2 vs 4.4.1, W0 | 3 + 3 | R1: ≥ 2/3 4.4.2 runs stalled; R2: 4.4.1 has fewer stalled runs **or** a lower median HS-miss count than 4.4.2 |
| R' | 4.4.2 vs 4.4.1, W1 | 3 + 3 | same R1/R2 |
| B | 4.2.24, W0 and W1 | 3 + 3 | B1: 0 stalled runs |
| C | 5.0.33 off, W1, non-unique indexes | 2 | C1: 0 stalled runs |
| X | W2 (SERVER-67350-like): 5.0.33 off / on, 4.2.24 | 2 / 2 / 1 | descriptive |

## Profiling (separate runs, so overhead never touches the A/B numbers)

`run.sh --profile`: privileged perf/gdb sidecar in mongod's PID namespace (adapted from SERVER-52879):
on-CPU `perf record -e cpu-clock -F 999 --call-graph fp` of all mongod threads for 45 s from just before the
client starts, off-CPU `sched_switch`/`sched_waking`, and a gdb all-thread snapshot (mongod frozen with
SIGSTOP) triggered when a connection thread has been ≥ 85% on-CPU for 2 s while ≤ 3 connection threads
are busy. Bug arm: 5.0.33 off W1, repeated (≤ 3 attempts) until a stall is captured. Fix arm: 5.0.33 on W1
with a control snapshot at a fixed time. Stuck threads are identified by timing (see S5), then their
stacks are summarised and compared with the ticket's `hs.png`.

## Run order (priority order; cut from the bottom if time runs out)

1. Primary A/B (5.0.33 W1 off/on ×5, alternating).
2. U (5.0.33 W0 off/on ×10, alternating).
3. Profiling (bug, then fix).
4. V (4.4.30 W0 off/on ×3).
5. R and B with W0 (4.4.2, 4.4.1, 4.2.24 ×3, rotating).
6. R' and B with W1 (×3, rotating).
7. C, then X.

## Risks and fallbacks

| risk | fallback |
|---|---|
| a bug-arm run stalls for the full cap | counted as stalled ≥ cap; the cap bounds the time budget |
| a runaway stall exhausts memory | mongod `--memory 3g --memory-swap 3g`, cache 1 GB; the 5 other containers are protected by the limit |
| Docker Hub rate limit | `public.ecr.aws/docker/library/*` (same digests) |
| no PMU in the VM | `perf -e cpu-clock` (worked for SERVER-52879) |
| release mongod lacks DWARF | `.symtab` is present (perf/gdb names resolve); `__wt_txn_read` is `static inline`, so it may not appear as its own frame |

## Changes from original plan

1. **2026-10-27, during block A (before any profiling run): gdb snapshot trigger relaxed** from "≤ 3
   connection threads busy" to "≤ 6". Run A1 had 4 threads stuck at once, which the old condition would
   never have caught. A healthy run has ~20 busy connection threads until they all finish within ~0.2 s, so
   ≤ 6 still means "the others are done". Criterion S5 is unchanged (it identifies stuck threads from the
   client log, not from this trigger).
2. **2026-10-27, during block A: added an exploratory analysis** (labelled as such in `results/summary.md`,
   not a criterion): rank correlation between a stalled thread's index (its key range) and its stall
   duration, plus `per_second.csv` per run and a "latest stalled-call start" column. Motivation: in A1 the
   lowest-numbered stuck thread stalled longest, which the hypothesis predicts (more keys "next" of it).
3. **2026-10-27, after blocks A and U: the pre-registered noise sensitivity check turned out uninformative,
   so an exploratory replacement was added.** Every stalled run lasts minutes and the other containers burst
   to ≥ 2 cores about every 30 s, so every long run is flagged "noisy" and the non-noisy subset is just
   the runs that did not stall. The pre-registered check is still reported as is. The added check looks
   only at the first 10 s of the insert phase, where every stall starts (`noisy_onset`).
4. **2026-10-27, before block P: fix-arm control snapshot moved from 7 s to 9 s after the profiler starts.**
   A functional test (`ptest-5.0.33-W1-on-profile`, not used anywhere) showed 7 s lands 0.08 s before the
   barrier releases the threads (all connections idle); 9 s lands ~2 s into the insert phase.
5. **2026-10-28 00:17, during block R: the host laptop went to sleep** (lid closed, on battery: "Clamshell
   Sleep" at 23:59:29, 45 s maintenance wake at 00:04:39, asleep again 00:05:24–00:15:20, per `pmset -g
   log`). Docker Desktop's VM is frozen while the host sleeps. **Rule added:** a run whose insert phase
   overlaps a host sleep, or that starts within 60 s after a wake, is excluded from every comparison and
   repeated once at the end of the campaign with the next free repetition number. Excluded:
   `R3-4.4.2-W0`, `R3-4.4.1-W0`, `B3-4.2.24-W0`, `RS1-4.4.2-W1` (listed with reasons in
   `results/excluded_runs.txt`; kept in `results/runs/`). Replacements: `R4-4.4.2-W0`, `R4-4.4.1-W0`,
   `B4-4.2.24-W0`, `RS4-4.4.2-W1`. From 00:16 on, `caffeinate -i -w <campaign pid>` prevents *idle* sleep
   (a lid-close on battery can still sleep the host). Each run summary now also records the longest gap
   in the host-side `docker stats` stream (`host_stream_max_gap_s`) so a pause is visible.
6. **2026-10-28 00:22: work paused for the night at the user's request.** `campaign.sh` was stopped and
   the run that had just started (`RS2-4.4.2-W1`, ~1 min in) was aborted through run.sh's own cleanup;
   its partial data is kept and it is listed as aborted in `results/excluded_runs.txt`. Nothing is left
   running (no `w7264-*` containers, sampler, perf, monitor or caffeinate of ours); images kept; the
   network `w7264-net` is kept for the resume (no volumes remained: run.sh deletes each run's volume).

7. **2026-10-28 10:00, before resuming: power source added as a recorded condition, with a guard and a
   disclosed sensitivity check.** The host is a laptop whose battery settings turn on Low Power Mode
   (`pmset -g custom`: Battery Power `lowpowermode 1`), which slows the CPU. Reconstructed from the
   "Using AC / Using Batt" tags in `pmset -g log` (`analysis/power_from_pmset.py`,
   `results/power_timeline.csv`, one `power.json` per earlier run): battery from 16:07:06 (80%) to
   22:59:03 (13%), AC from 22:59:03 to 23:59:17, battery from 23:59:17 on. So **all pilot and smoke runs,
   the first ~8 of the 9.4 minutes of A1-5.0.33-W1-off, RS1-4.4.1-W1, BS1-4.2.24-W1 and the excluded
   R3/RS1/RS2/B3 runs** ran on battery; every other counted run (A1-on through R2/B2, the profiles, U, V)
   ran entirely on AC. From now on: `campaign.sh` starts a run only on AC power (re-checks every 30 s;
   flags it after 20 min), and `run.sh` records `power_start` (meta.json) and `power_end` (outcome.json).
   The verdict rule is unchanged; the comparison additionally reports every criterion and secondary
   check on AC-only runs (runs whose whole insert phase was on AC), as a disclosed sensitivity check.

8. **2026-10-28 10:11, before resuming: run.sh times the cap from the client's own `P,insert_start` stamp**
   instead of from when its polling loop noticed the insert phase. This only changes how promptly a capped
   run is killed (R3-4.4.2-W0 was killed at 459 s); capped runs are classified "stalled ≥ cap" either way.

9. **2026-10-28 11:13, at the user's instruction: the remaining 17 runs start now, on battery if needed.**
   The wait-for-AC guard (change 7) is replaced by a battery floor: `campaign.sh` (`POWER_POLICY=min-charge`)
   does not start a run on battery below 15% and then stops cleanly; `POWER_POLICY=wait-ac` keeps the old
   behaviour for future campaigns. run.sh still records the power source and Low Power Mode at the start
   and end of every run. **Battery runs are a disclosed condition, not an exclusion reason**; the AC-only
   sensitivity check is reported next to the main results. From 10:01 to 11:13 the host stayed on battery
   (67% → 48%) and no run was started.

10. **2026-10-28 11:20, after the first battery runs of block Z: Low Power Mode produces a different kind
    of multi-second stall, so an exploratory stall-type label was added** (not a criterion; thresholds set
    after seeing these runs). B4-4.2.24-W0 (battery) had 20 calls of 3–6 s, all threads at once ~0.9 s into
    the run, with 210,108 pages evicted by application threads; the two AC runs of 4.2.24 had 0 such pages
    and no call over 0.31 s. 4.2.24 has no history store, so this cannot be the WT-7264 mechanism: it is
    cache eviction falling behind on a slowed CPU. B3-4.2.24 (excluded; battery, right after the wake) and
    BS1-4.2.24-W1 (battery, 1.23 s call) fit the same pattern (97,013 and 8,932 application-thread
    evictions). Each stalled run is now labelled from its server counters: *history-store walk* (≥ 10^6 HS
    misses, ≥ 50% during stalls: WT-7264 on 4.4.2+/5.0), *in-memory walk* (≥ 5×10^7 cursor entries skipped,
    < 10^6 HS misses: 4.4.1), *eviction* (≥ 5×10^4 pages evicted by application threads, no walk
    signature), or *other*. The pre-registered checks are still evaluated as written, on all counted runs,
    with the AC-only result next to them.

### Where the work stopped (2026-10-28 00:22) (historical; the campaign was finished 11:13–11:38, change 9)

**Complete and valid (counted):** A1–A5 off/on (10, primary A/B); U01–U10 off/on (20); P1-5.0.33-W1-off-profile
(stalled, capped 300 s, perf + gdb snapshot captured) and P1-5.0.33-W1-on-profile; V1–V3 off/on (6);
R1/R2-4.4.2-W0, R1/R2-4.4.1-W0, B1/B2-4.2.24-W0 (6); RS1-4.4.1-W1, BS1-4.2.24-W1 (2).
Interim primary result (from per-run summaries, before the final analysis pass): S1–S4 met
(bug 4/5 stalled, fix 0/5, one-sided Fisher p = 0.024, HS misses 0.27–1.08 × 10^9 per stalled run vs 0,
≥ 99% accrued during stalls); S5 met on both halves (bug: stuck threads 99.9% in `_keyExists`, 81.9% in
`__wt_hs_find_upd`, gdb snapshot inside `_keyExists → … → __wt_hs_find_upd`; fix: `__wt_hs_find_upd`
0.0% of 35,600 connection-thread samples, snapshot mid-insert with no thread in a history-store lookup).

**Excluded (kept in `results/runs/`, reasons in `results/excluded_runs.txt`):** R3-4.4.2-W0, R3-4.4.1-W0,
B3-4.2.24-W0, RS1-4.4.2-W1 (host sleep, change 5); RS2-4.4.2-W1 (aborted by the pause).

**Left in the run order** (`./campaign.sh Z C X`, ~45 min): block Z = R4-4.4.2-W0, R4-4.4.1-W0,
B4-4.2.24-W0, RS3/RS4/RS5-4.4.2-W1, RS2/RS3-4.4.1-W1, BS2/BS3-4.2.24-W1; then block C (2 non-unique
controls) and block X (5 SERVER-67350-like runs).

**Analysis not done yet:** (1) final per-run re-analysis of every counted run with the current
`analysis/analyze.py` (adds `per_second.csv`, onset-noise and host-gap fields) and the cross-run comparison
(`./analyze.sh results/runs/[A-Z]* --compare-out results`, which reads `results/excluded_runs.txt`);
(2) `profiling/reanalyze.sh` for both P1 runs: their current `profile_summary.md` predates the fix that maps
the off-CPU tracepoints' global PIDs to the namespace TIDs, so their stuck-thread off-CPU line is wrong
(empty) until regenerated; (3) copy representative timelines into `results/plots/`; (4) README secondary
results (`SECONDARY_PLACEHOLDER`) and run index; the "Outcome against the criteria" section below; the
REPORT text; (5) at the very end, remove `w7264-net`.

**Open checks:**
- `B3-4.2.24-W0` (excluded: started 6 s after the host woke) had one 3.2 s call (thread 13, batch 1, start
  0.24 s). B1 ("4.2.24: 0 stalled runs") will be evaluated on B1, B2, B4 and reported together with what B3
  showed. `BS1-4.2.24-W1` (valid) had a 1.23 s longest call, above the 0.2–0.3 s of other 4.2.24 runs but
  under the 3 s threshold; check BS2/BS3.
- S5, fix-arm half: the run is done and meets the criterion (0.0%); only the re-analysis pass in (2)
  remains, which does not change the on-CPU shares.
- R2: every 4.4.1 W0 run counts as "stalled" (all threads' first calls take ~4–5 s, an in-memory walk with
  0.1–0.4 M HS misses, vs ≥ 300 s and ~0.5 × 10^9 misses on 4.4.2), so R2 will rest on its HS-miss half.
- run.sh measures the cap from when it *sees* the insert phase start, so a frozen host delays the kill
  (R3-4.4.2-W0 was killed at 459 s). Harmless for classification (capped runs are "stalled ≥ cap"); a fix
  that uses the client's own `P,insert_start` timestamp is optional.

## Outcome against the criteria (filled in after all runs; details in `results/summary.md`)

63 counted runs, 5 excluded (`results/excluded_runs.txt`), 15 pilot/smoke/test runs (`results/run_index.md`).

| criterion | result (all counted runs) | AC-only runs (disclosed sensitivity check, change 7) |
|---|---|---|
| S1 ≥ 3/5 bug-arm runs stalled | **met**: 4/5 (A1–A4: stalls 172–562 s; 4, 3, 1, 1 threads) | met: 3/4 (A1 started on battery) |
| S2 0/5 fix-arm runs stalled | **met**: 0/5 (longest call 0.33 s) | met: 0/5 |
| S3 one-sided Fisher p < 0.05 | **met**: p = 0.024 | met: p = 0.048 |
| S4a every stalled run ≥ 10^6 HS misses | **met**: 2.7–10.8 × 10^8 | met |
| S4b fix max < 1% of bug min | **met**: fix max 0 | met |
| S4c ≥ 80% of HS misses during stalls | **met**: 99–100% | met |
| S5 stack | **met**: stuck threads 99.9% `_keyExists`, 81.9% `__wt_hs_find_upd` (59,978 samples); gdb snapshot inside `_keyExists → __curfile_search_near → __wt_btcur_search_near → __wt_btcur_prev → __wt_txn_read → __wt_hs_find_upd`; fix arm `__wt_hs_find_upd` 0.0% of 35,600 | met (both profiled runs were on AC) |

**Verdict by the pre-registered rule: reproduced** (S1–S5 met), with or without the battery run.

| secondary check | all counted runs | AC-only runs |
|---|---|---|
| U1 W0 5.0.33 off > on | holds (2/10 vs 0/10) | holds |
| U2 W0 5.0.33 HS misses only with off | holds (max 1.0 × 10^8 vs 0) | holds |
| V1 4.4.30 off ≥ 2/3, on 0/3 | holds (3/3 capped vs 0/3) | holds |
| R1 4.4.2 W0 ≥ 2/3 | holds (3/3 capped) | holds (2/2) |
| R2 4.4.1 W0 fewer stalled runs or lower HS misses | holds (2/3 vs 3/3; median 1.1 × 10^5 vs 5.4 × 10^8) | holds (on HS misses) |
| R′1 / R′2 (W1) | hold (3/3 capped; 4.4.1 2/3 with 0 median HS misses) | no AC runs |
| B1 4.2.24 W0: 0 stalled runs | **does not hold** (1/3: B4, battery) | holds (0/2) |
| B1 4.2.24 W1: 0 stalled runs | **does not hold** (2/3: BS2, BS3, battery) | no AC runs |
| C1 non-unique control: 0 stalled runs | holds (0/2) | no AC runs |
| X (descriptive) SERVER-67350-like variant | no stall in 5 runs | no AC runs |

B1 fails only through battery runs, whose stalls are of a different kind (all 20 threads at once for 3–7 s,
1.5–2.6 × 10^5 pages evicted by application threads, no history store in 4.2): see change 10. The X variant
did not reproduce the stall: its first commands reached mongod 65–293 ms apart (GIL-serialized BSON encoding)
instead of together. Exploratory: in the primary bug arm, the stuck threads' stall duration correlates weakly
and negatively with their thread index (Spearman ρ = −0.30, 9 stalled calls), the direction the hypothesis
predicts (lower key range → more invisible keys "next" of it), but too weak to lean on.
