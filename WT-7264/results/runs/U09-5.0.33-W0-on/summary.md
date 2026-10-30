# Run `U09-5.0.33-W0-on`

- mongod **5.0.33** (`20315d70b9`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = True, WT cache 1 GB
- insert phase: **5.23 s**; 1000/1000 insertMany calls returned; 1,904,792 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.10 / 0.16 / 0.24 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.24 s; stall type (exploratory): none
- host power: AC Power → AC Power
- thread finish time median / last: 5.10 / 5.22 s (straggler gap 0.13 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 4,894; search_near calls: 3,809,271; prefix-search early exits: 3,618,378
- eviction: pages evicted by application threads 12.0, forced-eviction pages selected 220.0, pages read into cache 454.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 8.9 / 41.3 % (5 samples) → not noisy; w7264-mongod peak 817.5 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
