# Run `V3-4.4.30-W0-on`

- mongod **4.4.30** (`4d7fa6a626`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = True, WT cache 1 GB
- insert phase: **5.34 s**; 1000/1000 insertMany calls returned; 1,903,500 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.10 / 0.16 / 0.20 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.20 s; stall type (exploratory): none
- host power: AC Power → AC Power
- thread finish time median / last: 5.14 / 5.34 s (straggler gap 0.20 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 4,894; search_near calls: 3,801,071; prefix-search early exits: 3,610,177
- eviction: pages evicted by application threads 0.0, forced-eviction pages selected 172.0, pages read into cache 240.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 10.9 / 50.1 % (5 samples) → not noisy; w7264-mongod peak 827.1 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
