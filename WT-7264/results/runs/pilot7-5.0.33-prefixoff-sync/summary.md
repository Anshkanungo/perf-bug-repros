# Run `pilot7-5.0.33-prefixoff-sync`

- mongod **5.0.33** (`20315d70b9`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **87.4 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.13 / 0.37 / 83.01 s
- **stalled calls (≥ 3 s or never returned): 1** on 1 thread(s); longest call 83.01 s; stall type (exploratory): history-store walk
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 10.75 / 87.39 s (straggler gap 76.65 s)
- history store reads missed: **110,901,066** (98% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 172,284,785; search_near calls: 114,901,067; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 420.0, forced-eviction pages selected 287.0, pages read into cache 2,103
- checkpoints: {'checkpoints_completed': 1.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 56.0}
- noise: other containers' CPU median / peak 8.8 / 600.7 % (88 samples) → **NOISY**; w7264-mongod peak 652.3 %
- while only stalled calls were left (12.5–86.0 s): median 1 connection thread(s) at ≥90% CPU, mongod 1.0 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 1 | 0 | 3.005 | 83.01 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn12 | 82985 | 1000 | 25,696,765 | 1,551 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
