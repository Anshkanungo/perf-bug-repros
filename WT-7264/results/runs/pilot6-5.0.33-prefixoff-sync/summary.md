# Run `pilot6-5.0.33-prefixoff-sync`

- mongod **5.0.33** (`20315d70b9`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **15.05 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.12 / 0.35 / 10.99 s
- **stalled calls (≥ 3 s or never returned): 1** on 1 thread(s); longest call 10.99 s; stall type (exploratory): history-store walk
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 10.41 / 15.05 s (straggler gap 4.64 s)
- history store reads missed: **10,203,220** (84% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 40,428,110; search_near calls: 14,203,220; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 322.0, forced-eviction pages selected 383.0, pages read into cache 890.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 13.5 / 130.8 % (16 samples) → not noisy; w7264-mongod peak 695.4 %
- while only stalled calls were left (10.7–14.0 s): median 1 connection thread(s) at ≥90% CPU, mongod 1.06 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 15 | 0 | 3.001 | 10.99 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn11 | 1052 | 1000 | 584,386 | 101.8 |
| conn25 | 10966 | 1000 | 9,116,189 | 823.2 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
