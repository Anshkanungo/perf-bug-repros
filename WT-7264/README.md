# WT-7264 / SERVER-67350: unique-index inserts stuck walking invisible keys through the history store

**Bug:** in MongoDB 4.4 and 5.0, every insert into a **unique index** checks for an existing key with
`WT_CURSOR::search_near` (`WiredTigerIndexUnique::_keyExists`). Since WT-5461 (4.4.0), a `search_near` that
lands on a key its transaction cannot see keeps stepping `next`/`prev` until it finds a *visible* key, and,
with durable history, every invisible key on an evicted page costs a history-store lookup that finds nothing
(`__wt_hs_find_upd`, statistic "history store table reads missed"). With many concurrent inserters into
disjoint ascending key ranges, a transaction whose snapshot predates its neighbours' commits walks over all
of their keys, over and over: one or two inserts get stuck for seconds to many minutes while mongod burns
one core per stuck thread, and nothing shows in the logs or `currentOp`. Fixed by a `prefix_search`
`search_near` option in WiredTiger (WT-7264, 4.4.7/5.0.0) that the server uses since SERVER-61185
(5.3.0; 5.0.14 on by default; 4.4.18 **off** by default) behind `wiredTigerPrefixSearchForUniqueIndexes`.
The first server attempt (SERVER-56509, 4.4.7/5.0.0–5.0.1) broke unique-index enforcement (SERVER-58936)
and was reverted. Details and the developer discussion: [`discussion/DISCUSSION.md`](discussion/DISCUSSION.md).

**Result:** see `REPORT.md` (one page) and [`results/summary.md`](results/summary.md).

> **Status (2026-10-28 11:40): complete.** 63 counted runs (46 before the overnight pause, 17 after it),
> 5 excluded (host sleep / pause), 15 pilot, smoke and test runs. The last 17 runs ran on battery
> (Low Power Mode) at the user's instruction; battery runs are a disclosed condition, and every check is
> also reported on AC-only runs. History of the campaign: [`PLAN.md`](PLAN.md), "Changes from original plan".

## Results at a glance

Docker Desktop on an Apple M1 Pro (linux/arm64 VM, 10 vCPU, 7.75 GiB), shared with 5 unrelated containers.
Full tables: [`results/summary.md`](results/summary.md); every run as a dot: [`results/plots/conditions.png`](results/plots/conditions.png).

**Primary A/B (pre-registered): one binary, `mongo:5.0.33`, barrier workload W1, 5 + 5 runs, cap 600 s.**

| arm | stalled runs | stuck threads per stalled run | how long they stayed stuck (s) | insert phase (s) | history-store reads missed |
|---|---|---|---|---|---|
| `wiredTigerPrefixSearchForUniqueIndexes=false` (bug) | **4 / 5** | 4, 3, 1, 1 | 561, 330, 153, 73 / 247, 207, 198 / 238 / 172 | 562, 248, 239, 173, 5.2 | 0.27 – 1.08 **billion** per stalled run |
| `=true` (fix) | **0 / 5** | – | – | 5.0 – 5.8 | 0 |

**Verdict: reproduced** (S1 4/5 ≥ 3; S2 0/5; S3 one-sided Fisher p = 0.024; S4 every stalled run ≥ 2.7×10^8
misses, ≥ 99% of them accrued while a call had been stuck ≥ 3 s, fix arm 0; S5 profile below). Every stuck
call was the thread's **first** insertMany, started within 10 ms of the barrier; healthy calls take ~0.1 s.
While only stuck calls were left, mongod used exactly one core per stuck thread (SERVER-67350's "one or two
cores at 100% CPU"). All 10 runs were on AC power except A1-off, which started on battery and switched to
AC 8 minutes into its 9-minute stall; without it the verdict is the same (S1 3/4, S3 p = 0.048).

**Secondary conditions** (pre-registered checks are descriptive, not part of the verdict; every number is in
[`results/summary.md`](results/summary.md)). "Battery" = Low Power Mode on this laptop. The stall type is an
exploratory label from server counters (PLAN.md change 10): *HS walk* = history-store misses during the stall
(WT-7264), *in-memory walk* = cursor entries skipped without history-store misses (4.4.1),
*eviction* = application threads evicting pages, all threads at once (only seen on battery).

| condition | power | stalled runs | what the stalls look like | history-store misses per run |
|---|---|---|---|---|
| 5.0.33, Bruce's script unmodified (W0), prefix_search off / on | AC | **2/10** / 0/10 | one thread's first call: 68 s and 3.1 s | up to 1.0×10^8 / 0 |
| 4.4.30 (latest 4.4) W0, prefix_search **off = its default** / on | AC | **3/3, all capped at 300 s** / 0/3 | 12–15 threads stuck on their first one or two calls; mongod pins all 10 vCPUs; HS walk | ~4.7×10^8 / 0 |
| 4.4.2 W0 (first release after the SERVER-67350 bisect commit) | AC, AC, battery | **3/3, all capped** | 10–12 threads stuck from the first second; HS walk | 5.2–5.5×10^8 |
| 4.4.1 W0 (last release before it) | AC, AC, battery | 2/3 | **short**: 14–16 threads' early calls take 4–5 s together, then everything proceeds (battery run: 2.9 s, under the threshold); in-memory walk | 1–2×10^5 |
| 4.2.24 W0 (before durable history) | AC, AC, battery | 1/3 (the battery run) | AC: none (longest call 0.3 s). Battery: all 20 threads 3–6 s at once, 2.1×10^5 pages evicted by application threads; eviction | n/a (no history store) |
| 4.4.2 / 4.4.1 / 4.2.24 with the barrier (W1) | battery | 3/3 capped / 2/3 / 2/3 | 4.4.2: 3–7 threads stuck, HS walk. 4.4.1: one or two 5.3 s calls, in-memory walk. 4.2.24: all 20 threads 5–7 s, eviction | 5.9–7.5×10^8 / ≤ 3.6×10^5 / n/a |
| non-unique control: 5.0.33 off, W1, same indexes without `unique` | battery | **0/2** | runs take 3.1–3.6 s, longest call 0.19 s | 0 |
| SERVER-67350-like variant (W2): 5.0.33 off / on, 4.2.24 | battery | 0/2 / 0/2 / 0/1 | not reproduced: no stall, longest call 2.5–2.8 s (100,000-document calls) | 0 |

- **The bisect, from the inside.** On 4.4.1 the walk over invisible keys happens in memory (cursor entries
  skipped 0.7–1.3×10^8 per run, almost no history-store misses) and costs every thread a few seconds once;
  from 4.4.2 on, each invisible key on an evicted page costs a history-store lookup, and the first
  transactions never catch up. Bruce's 441/442 FTDC charts show the same split ("reads missed" late on
  4.4.1, immediately on 4.4.2). R1/R2 and R′1/R′2 hold.
- **B1 ("4.2.24 never stalls") does not hold as pre-registered**: 1/3 (W0) and 2/3 (W1) runs had calls
  ≥ 3 s. All three were battery runs, and their stalls are a different thing: all 20 threads at once for
  3–7 s, with 1.5–2.6×10^5 pages evicted by application threads, on a version without a history store. On
  AC, 4.2.24 never had a call over 0.31 s (B1 holds on AC-only runs, 0/2). The 3 s stall threshold is
  therefore not specific to WT-7264 when the CPU is throttled; the history-store signature is.
- **The non-unique control holds** (C1): same workload, same binary, `prefix_search` off, no `unique` → no
  stall and no history-store misses, because no `_keyExists` walk happens at all.
- **The SERVER-67350-like pymongo variant did not stall** in any of its 5 runs (2 with prefix_search off).
  Its five first 100,000-document commands reached the server 65–293 ms apart (pymongo encodes each batch
  under Python's GIL), while the reporter's Java program started its five within ~36 ms (first 5.0.9 run in
  `discussion/server67350_logs.md`); the stall needs first transactions that overlap. Treat W2 as not
  reproduced; W1 is the reliable trigger.
- **Power sensitivity:** 43 of 63 counted runs were entirely on AC. On AC-only runs every criterion and every
  secondary check that has AC data gives the same answer, except B1 (W0), which flips to "holds".

**Excluded runs** (kept in `results/runs/`, reasons in [`results/excluded_runs.txt`](results/excluded_runs.txt)):
R3-4.4.2-W0, R3-4.4.1-W0, B3-4.2.24-W0 and RS1-4.4.2-W1 (the laptop slept 23:59–00:15, or the run started
right after the wake) and RS2-4.4.2-W1 (aborted when the work was paused for the night). Every run with its
role, result and power source: [`results/run_index.md`](results/run_index.md).

### Symptom function and call stack

The stuck connection thread spends its time in **`mongo::WiredTigerIndexUnique::_keyExists`** (the
duplicate-key check), inside WiredTiger's `search_near` walk, doing one history-store lookup
(**`__wt_hs_find_upd`**) per invisible key. gdb snapshot of a stuck thread, taken while mongod was frozen
([`results/runs/P1-5.0.33-W1-off-profile/profile/snapshot_summary.md`](results/runs/P1-5.0.33-W1-off-profile/profile/snapshot_summary.md)):

```
#0  __wt_struct_packv
#1  __wt_cursor_set_keyv
#2  __wt_cursor_set_key
#3  __curhs_set_key                         history-store cursor: build the lookup key
#4  __wt_hs_find_upd                        look for an older version in the history store -> nothing
#5  __wt_txn_read                           the on-page version is newer than this snapshot
#6  __wt_btcur_prev                         search_near walks past invisible keys (next, then prev)
#7  __wt_btcur_search_near
#8  __curfile_search_near
#9  mongo::wiredTigerPrepareConflictRetry<WiredTigerIndexUnique::_keyExists(...)::{lambda()#1}>
#10 mongo::WiredTigerIndexUnique::_keyExists
#11 mongo::WiredTigerIndexUnique::_insert
#12 mongo::WiredTigerIndex::insert
#13 mongo::AbstractIndexAccessMethod::insertKeys
#14 mongo::AbstractIndexAccessMethod::insertKeysAndUpdateMultikeyPaths
#15 mongo::IndexCatalogImpl::_indexKeys
#16 mongo::IndexCatalogImpl::_indexFilteredRecords
#17 mongo::IndexCatalogImpl::_indexRecords
#18 mongo::IndexCatalogImpl::indexRecords
#19 mongo::CollectionImpl::_insertDocuments
#20 mongo::CollectionImpl::insertDocuments
#21 mongo::write_ops_exec::(anonymous namespace)::insertDocuments
#22 mongo::write_ops_exec::performInserts
#23 mongo::(anonymous namespace)::CmdInsert::Invocation::typedRun
```

On-CPU profile (perf `cpu-clock` 999 Hz, frame pointers) of the 2 stuck threads over 32 s of their stalled
calls: 59,978 samples; 99.9% under `_keyExists`, 89% under `__wt_txn_read`, 82% under `__wt_hs_find_upd`.
Call tree under `_keyExists`, next to the ticket's [`hs.png`](discussion/attachments/hs.png) (29,272
samples, WiredTiger 4.4 era):

| frame (cursor/transaction frames only) | this repro | `hs.png` |
|---|---|---|
| `__curfile_search_near` → `__wt_btcur_search_near` | 67.7% | 66.8% |
| └ `__wt_btcur_next[_prefix]` → `__wt_txn_read` → `__wt_hs_find_upd` | 34.6% → 31.1% → 28.3% | 32.7% → 32.7% → 32.7% |
| └ `__wt_btcur_prev` → `__wt_txn_read` → `__wt_hs_find_upd` | 33.1% → 29.2% → 27.0% | 34.1% → 34.0% → 34.0% |
| `__curfile_next` (the follow-up `next` in `_keyExists`) → `__wt_txn_read` → `__wt_hs_find_upd` | 32.3% → 29.2% → 26.6% | 33.2% → 33.2% → 33.2% |

Inside `__wt_hs_find_upd`, each lookup opens a history-store cursor (33%), positions it (32%), builds its
key (19%) and closes it (15%), and finds nothing. The stall is pure CPU: over the 2 × 32 s window the two
stuck threads blocked for 67 ms with a recorded wakeup and at most 1.9 s more without one (off-CPU
`sched_switch`/`sched_waking` recording). In 5.0.33 `__wt_btcur_next` is a thin wrapper over
`__wt_btcur_next_prefix` (added by WT-7264 itself) and does not appear as its own frame. The fixed arm's
profile has `__wt_hs_find_upd` in 0.0% of connection-thread samples and `_keyExists` in 4%.


## Layout

| path | what |
|---|---|
| `run.sh` | **one entry point**: start mongod (official image, your image, your binary, or use `--target`) → create the unique indexes → run the workload (hard cap) → sample metrics → collect logs/FTDC → analyze |
| `campaign.sh` | the exact sequence of `run.sh` calls behind `results/` (blocks A, U, P, V, R, R1, C, X, and Z for the resume; see `PLAN.md`); waits for AC power before each run on a Mac laptop |
| `profile.sh` | privileged perf/gdb sidecar: on-CPU + off-CPU call graphs of every mongod thread, plus a gdb all-thread snapshot taken *while* a thread is stuck |
| `analyze.sh` | per-run summaries and the cross-run comparison (runs `analysis/analyze.py` in a container) |
| `workload/` | original `repro.sh` (untouched) + `parallelTester.js`, adapted script, SERVER-67350-like variant, sampler ([README](workload/README.md)) |
| `profiling/` | profiler image + collection/analysis scripts (adapted from SERVER-52879) |
| `analysis/` | `analyze.py` (per-run + cross-run analysis), `power_from_pmset.py` (host power source of runs from `pmset -g log`) |
| `discussion/` | Jira JSON (12 tickets), attachments, cause/fix diffs, source snapshots at the tags used, the SERVER-67350 reporter's logs/FTDC decoded, `DISCUSSION.md` |
| `results/` | `summary.md` (criteria, conditions, sensitivity checks), `run_index.md` (every run: role, result, power source), `excluded_runs.txt`, `power_timeline.csv`, `plots/`, `runs/<label>/` (per-run `summary.md`, `timeline.png`, `calls.csv`, `per_second.csv`; `raw/` is git-ignored) |
| `PLAN.md` | hypothesis, pre-registered criteria (written before the main runs), pilot runs, change log |

## Prerequisites

- Docker. Nothing else on the host. arm64 or x86-64 (all images used are multi-arch).
- Per run: mongod in a 3 GB container with a 1 GB WiredTiger cache (peak RSS ~0.4–0.6 GB here), the legacy
  shell client ~150 MB. A healthy run uses ~8 cores for ~6 s; a stuck run uses one core per stuck thread
  until it ends or hits the cap. ~0.3 GB disk per run (volume deleted afterwards) + 1–30 MB of raw results.
- Images pulled: `mongo:5.0.33` (also the client), `mongo:4.4.30`, `mongo:4.4.2`, `mongo:4.4.1`,
  `mongo:4.2.24`. Built here: `w7264-tools:1` (Python + pymongo + pandas/matplotlib) and `w7264-prof:1`
  (perf + gdb + FlameGraph). Docker Hub HTTP 429 → the scripts pull the same images from
  `public.ecr.aws/docker/library/`.

## Reproduce

```bash
cd WT-7264
./run.sh 5.0.33 --sync-start --prefix-search off     # bug arm (barrier workload, W1)
./run.sh 5.0.33 --sync-start --prefix-search on      # fix arm: same binary, prefix_search used
./run.sh 5.0.33 --prefix-search off                  # Bruce's workload unmodified (W0): stalls less often
./run.sh 4.4.30                                      # 4.4 latest with its default (prefix search off)
./run.sh 4.2.24                                      # pre-durable-history baseline
./campaign.sh A U                                    # the primary A/B (5+5) and the W0 A/B (10+10)
POWER_POLICY=wait-ac ./campaign.sh A                 # on a laptop: only start runs on AC power
./analyze.sh $(ls -d results/runs/*) --compare-out results   # cross-run summary.md, run_index.md, plots
```

On a Mac laptop, record the power source of runs made before run.sh did so with
`pmset -g log > /tmp/pmset.log && python3 -I analysis/power_from_pmset.py /tmp/pmset.log results/runs
--timeline results/power_timeline.csv` before the cross-run analysis.

Each run prints its directory, `results/runs/<label>/`:

- `summary.md`: insert-phase time, stalled calls (thread, batch, duration), history-store misses and the
  share accrued during stalls, cursor entries skipped, eviction counters, checkpoints, noise from other
  containers.
- `timeline.png`: per-call latency (stalled calls drawn as bars), inserts/s and threads still running,
  history-store misses/s and cursor entries skipped/s, mongod CPU and threads at ≥ 90% CPU, other
  containers' CPU, checkpoints.
- `calls.csv`: one row per insertMany call. `raw/`: `client.log`, `serverstatus.jsonl`, `threads.jsonl`,
  `docker_stats.txt`, `mongod.log`, `diagnostic.data/` (FTDC).

> **Teacher's note: the unique-index duplicate check.** A secondary unique index in 4.2+ stores
> `(key, RecordId)` entries, so the key alone is a *prefix*. To insert `a: 5` MongoDB (1) inserts the bare
> prefix `5`, (2) removes it again, which leaves a deleted entry that makes any concurrent inserter of `5`
> hit a write conflict, (3) calls `_keyExists`: `search_near(5)` and checks whether the key it lands on
> starts with `5`, (4) inserts `(5, RecordId)`. All four steps run in the inserting transaction. Step 3 is
> where this bug lives.

> **Teacher's note: `search_near`.** WiredTiger's `search_near(k)` returns `k` if it exists and is visible,
> otherwise the nearest *visible* key, larger or smaller. It finds that key by walking `next` (to the end of
> the table if necessary) and then `prev`. If thousands of keys around `k` are invisible to the caller (not
> yet committed from its snapshot's point of view, or deleted), the walk visits every one of them. The
> fix's `prefix_search=true` lets the walk stop as soon as the keys no longer start with the searched
> prefix: a unique-index check only cares about `(5, *)`.

> **Teacher's note: the history store.** Since 4.4 ("durable history") WiredTiger writes the *newest*
> committed version of a row to the data page when it evicts or checkpoints it, and older versions to a
> separate table, the history store (`WiredTigerHS.wt`). A reader whose snapshot is older than the
> on-page version must look for an older version there (`__wt_hs_find_upd`). For a freshly inserted key
> there is no older version, so the lookup always misses: "history store table reads missed". In 4.2 a page
> holding updates that some reader could not see yet simply was not evicted, so walking invisible keys
> stayed in memory and cheap.

> **Teacher's note: setParameter.** mongod's tunables are *server parameters*. `--setParameter
> name=value` sets one at startup; `db.adminCommand({setParameter: 1, name: value})` changes it at runtime
> if the parameter allows it (`set_at: [startup, runtime]` in its `.idl` file), and `getParameter` reads it
> back. `wiredTigerPrefixSearchForUniqueIndexes` allows both and is read on every unique-index insert, so it
> can be flipped on a live server. That is why the primary A/B can use a single binary.

## Point it at your own (instrumented) mongod

```bash
# 1) an already-running mongod (any host/port reachable from Docker; the parameter is set at runtime)
./run.sh --target 10.0.0.5:27017 --sync-start --prefix-search off --label my-instrumented-run
#    --network host is the default for --target (Linux). On Docker Desktop use host.docker.internal:<port>.
#    The workload writes to test.c: give it an empty database. 4.4.18+/5.0.14+ only for --prefix-search;
#    older builds don't have the parameter (they always take the slow path).

# 2) your own image (started exactly like the official one: cache size, memory limit, fresh volume)
./run.sh --image registry.example.com/mongod-instrumented:5.0.33 --sync-start --prefix-search off

# 3) your own binary, run inside the official 5.0.33 image (Ubuntu 20.04 userland)
./run.sh 5.0.33 --mongod-binary /path/to/mongod --sync-start --prefix-search off

# profile it (perf + gdb snapshot while a thread is stuck); or run ./profile.sh by hand
./run.sh 5.0.33 --sync-start --prefix-search off --profile --profile-args "--secs 40 --snapshot"
./profile.sh --host-pid $(pgrep -o mongod) --secs 40 --snapshot --event cycles   # native mongod, Linux host
```

The stall's timestamps are in `results/runs/<label>/raw/client.log`: `S,<thread>,<batch>,<start_ms>` when a
call starts and `B,<thread>,<batch>,<start_ms>,<latency_ms>` when it returns (a stuck call has an `S` line
and no `B` line until it finishes). In this workload the stuck call is a thread's **first** insertMany, so
it starts within ~10 ms of the barrier.

## Gotchas and troubleshooting (all hit while building this)

- **The stall is intermittent with Bruce's original start timing.** On this 10-vCPU VM, 5.0.33 with
  `--prefix-search off` stalled in about 1 of 6 pilot runs of the unmodified workload (W0), but 3 of 3 with
  `--sync-start` (W1). Use `--sync-start` when you need the stall every time; use W0 to measure how often
  the original recipe hits it. 4.4.30 with its default settings stalls with W0 too.
- **Stalls can last many minutes** (SERVER-67350 saw 40 min). Every run has a hard cap (`--cap`, default
  600 s); a capped run is a result ("stalled ≥ cap"), not an error. The stuck operation keeps running inside
  mongod until the container is removed.
- **Always pass `--wiredTigerCacheSizeGB`** (run.sh does): mongod sizes its cache from the memory it sees,
  and on Docker Desktop that can be the whole VM. run.sh also sets `--memory 3g --memory-swap 3g` so a
  runaway can't take down other containers on the same VM.
- **`wiredTigerPrefixSearchForUniqueIndexes` only exists in 4.4.18+ and 5.0.14+.** Passing it to an older
  mongod makes startup fail ("unknown parameter"); run.sh only passes it when you ask. Its default differs:
  false in 4.4, true in 5.0. Always check `server.json` → `parameters` (read back with `getParameter`).
- **Don't use 4.4.7, 5.0.0 or 5.0.1** for comparisons: SERVER-56509's first attempt at the fix is in them and
  can violate unique constraints (SERVER-58936).
- **4.2 has no history store**, so the history-store counters are absent there (reported as "–"/n/a).
- **The legacy shell splits each 2000-document insertMany into two 1000-document insert commands**, and
  mongod commits every 64 documents. The client log is per `insertMany` call; the mongod slow-query log is
  per command.
- **`docker stats` in streaming mode** prints ANSI clear-screen codes around its JSON lines; run.sh strips
  them and stamps each line with the epoch second.
- **Noise:** the Airflow containers on this VM burst to 3–7 cores for 1–2 s about every 30 s. Runs that see
  such a burst are flagged "noisy". A burst can slow a 0.2 s call, but cannot make a 3 s stall (the noisy
  fix-arm runs show no stall).
- **Checkpoints run during long stalls** (every 60 s). They are recorded (`checkpoints` in each
  `summary.md`) and don't start or end stalls.
- **Profiling** (inherited from SERVER-52879): perf needs the `--privileged` sidecar in mongod's PID
  namespace; the VM has no PMU, so `-e cpu-clock`; the gdb snapshot freezes mongod with SIGSTOP, which only
  works when mongod is not PID 1 (`run.sh --profile` adds `docker --init`). perf script output for 40 s of
  a busy mongod is a few hundred MB before gzip (git-ignored).
- **Laptop power and sleep.** On this Mac, battery power turns on Low Power Mode (`pmset -g custom`), which
  slows the CPU, and closing the lid on battery sleeps the host and freezes Docker's VM mid-run (it
  happened at 23:59; four runs were excluded, see `results/excluded_runs.txt`). `campaign.sh` therefore
  waits for AC power before every run (`POWER_GUARD=0` to skip), `run.sh` records the power source at the
  start and end of each run, and `analysis/power_from_pmset.py` reconstructs it from `pmset -g log` for older
  runs. Keep the lid open and use `caffeinate -i -w <campaign pid>` for unattended campaigns.
- **zsh:** `echo ======` fails with "= not found" (zsh `=command` expansion); quote it.
