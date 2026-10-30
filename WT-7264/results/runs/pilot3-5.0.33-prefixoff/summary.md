# Run `pilot3-5.0.33-prefixoff`

- mongod **5.0.33** (`20315d70b9`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **5.63 s**; 1000/1000 insertMany calls returned; 1,955,640 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.11 / 0.17 / 0.22 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.22 s; stall type (exploratory): none
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 5.54 / 5.62 s (straggler gap 0.09 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 4,547,725; search_near calls: 3,910,324; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 16.0, forced-eviction pages selected 296.0, pages read into cache 201.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 9.5 / 120.0 % (6 samples) → not noisy; w7264-mongod peak 834.2 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
