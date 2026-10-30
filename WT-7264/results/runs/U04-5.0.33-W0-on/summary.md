# Run `U04-5.0.33-W0-on`

- mongod **5.0.33** (`20315d70b9`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = True, WT cache 1 GB
- insert phase: **5.27 s**; 1000/1000 insertMany calls returned; 1,682,472 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.10 / 0.17 / 0.19 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.19 s; stall type (exploratory): none
- host power: AC Power → AC Power
- thread finish time median / last: 5.16 / 5.26 s (straggler gap 0.11 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 4,894; search_near calls: 3,364,173; prefix-search early exits: 3,196,840
- eviction: pages evicted by application threads 0.0, forced-eviction pages selected 208.0, pages read into cache 380.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 15.2 / 28.3 % (6 samples) → not noisy; w7264-mongod peak 824.1 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
