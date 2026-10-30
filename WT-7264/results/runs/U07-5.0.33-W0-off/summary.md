# Run `U07-5.0.33-W0-off`

- mongod **5.0.33** (`20315d70b9`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **6.64 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.10 / 0.37 / 3.11 s
- **stalled calls (≥ 3 s or never returned): 1** on 1 thread(s); longest call 3.11 s; stall type (exploratory): other
- host power: AC Power → AC Power
- thread finish time median / last: 6.15 / 6.64 s (straggler gap 0.49 s)
- history store reads missed: **1,916,224** (8% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 12,711,962; search_near calls: 5,916,224; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 223.0, forced-eviction pages selected 241.0, pages read into cache 385.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 12.5 / 37.9 % (7 samples) → not noisy; w7264-mongod peak 841.5 %

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 8 | 0 | 0.09 | 3.11 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn14 | 3090 | 1000 | 1,079,638 | 661.8 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
