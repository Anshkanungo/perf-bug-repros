# Run `U07-5.0.33-W0-on`

- mongod **5.0.33** (`20315d70b9`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = True, WT cache 1 GB
- insert phase: **5.29 s**; 1000/1000 insertMany calls returned; 1,839,592 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.10 / 0.16 / 0.18 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.18 s; stall type (exploratory): none
- host power: AC Power → AC Power
- thread finish time median / last: 5.17 / 5.29 s (straggler gap 0.12 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 4,894; search_near calls: 3,678,294; prefix-search early exits: 3,491,401
- eviction: pages evicted by application threads 0.0, forced-eviction pages selected 262.0, pages read into cache 395.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 27.7 / 211.4 % (6 samples) → **NOISY**; w7264-mongod peak 814.7 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
