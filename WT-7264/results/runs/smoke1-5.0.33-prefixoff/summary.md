# Run `smoke1-5.0.33-prefixoff`

- mongod **5.0.33** (`20315d70b9`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **5.65 s**; 1000/1000 insertMany calls returned; 1,944,408 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.11 / 0.17 / 0.20 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.20 s; stall type (exploratory): none
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 5.53 / 5.64 s (straggler gap 0.11 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 4,276,498; search_near calls: 3,888,688; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 0.0, forced-eviction pages selected 348.0, pages read into cache 305.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 11.6 / 56.5 % (6 samples) → not noisy; w7264-mongod peak 844.1 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
