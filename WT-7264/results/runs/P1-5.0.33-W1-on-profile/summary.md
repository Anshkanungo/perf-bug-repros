# Run `P1-5.0.33-W1-on-profile`

- mongod **5.0.33** (`20315d70b9`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = True, WT cache 1 GB
- insert phase: **5.36 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.10 / 0.27 / 0.32 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.32 s; stall type (exploratory): none
- host power: AC Power → AC Power
- thread finish time median / last: 5.29 / 5.36 s (straggler gap 0.07 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 4,894; search_near calls: 4,000,000; prefix-search early exits: 3,792,728
- eviction: pages evicted by application threads 14.0, forced-eviction pages selected 351.0, pages read into cache 400.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 16.6 / 602.5 % (8 samples) → **NOISY**; w7264-mongod peak 812.8 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
