# Run `U06-5.0.33-W0-off`

- mongod **5.0.33** (`20315d70b9`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **5.47 s**; 1000/1000 insertMany calls returned; 1,959,384 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.10 / 0.23 / 0.96 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.96 s; stall type (exploratory): none
- host power: AC Power → AC Power
- thread finish time median / last: 5.33 / 5.46 s (straggler gap 0.13 s)
- history store reads missed: **36,675** (0% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 10,752,581; search_near calls: 3,954,411; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 20.0, forced-eviction pages selected 129.0, pages read into cache 377.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 9.2 / 58.5 % (6 samples) → not noisy; w7264-mongod peak 832.7 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
