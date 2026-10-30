# Run `U03-5.0.33-W0-off`

- mongod **5.0.33** (`20315d70b9`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **69.02 s**; 1000/1000 insertMany calls returned; 1,833,920 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.12 / 0.36 / 67.99 s
- **stalled calls (≥ 3 s or never returned): 1** on 1 thread(s); longest call 67.99 s; stall type (exploratory): history-store walk
- host power: AC Power → AC Power
- thread finish time median / last: 7.20 / 69.02 s (straggler gap 61.81 s)
- history store reads missed: **102,669,894** (98% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 122,121,735; search_near calls: 106,336,748; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 360.0, forced-eviction pages selected 138.0, pages read into cache 2,364
- checkpoints: {'checkpoints_completed': 1.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 204.0}
- noise: other containers' CPU median / peak 9.1 / 603.9 % (70 samples) → **NOISY**; w7264-mongod peak 757.2 %
- while only stalled calls were left (7.3–68.0 s): median 1 connection thread(s) at ≥90% CPU, mongod 1.09 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 2 | 0 | 0.058 | 67.99 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn9 | 67969 | 1000 | 30,681,705 | 1,051 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
