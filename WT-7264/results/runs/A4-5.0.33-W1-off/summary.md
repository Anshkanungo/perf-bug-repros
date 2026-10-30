# Run `A4-5.0.33-W1-off`

- mongod **5.0.33** (`20315d70b9`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **172.58 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.11 / 0.37 / 171.54 s
- **stalled calls (≥ 3 s or never returned): 1** on 1 thread(s); longest call 171.54 s; stall type (exploratory): history-store walk
- host power: AC Power → AC Power
- thread finish time median / last: 7.12 / 172.57 s (straggler gap 165.45 s)
- history store reads missed: **272,498,848** (99% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 341,680,092; search_near calls: 276,498,850; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 426.0, forced-eviction pages selected 363.0, pages read into cache 2,812
- checkpoints: {'checkpoints_completed': 2.0, 'seconds_with_checkpoint_running': 1, 'checkpoint_running_during_stalls': True, 'last_checkpoint_ms_max': 121.0}
- noise: other containers' CPU median / peak 7.4 / 707.6 % (174 samples) → **NOISY**; w7264-mongod peak 773.0 %
- while only stalled calls were left (8.3–171.5 s): median 1 connection thread(s) at ≥90% CPU, mongod 1.01 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 1 | 0 | 0.004 | 171.54 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn23 | 171514 | 1000 | 36,812,779 | 1,544 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
