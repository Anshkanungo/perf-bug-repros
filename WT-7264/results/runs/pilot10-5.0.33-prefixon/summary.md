# Run `pilot10-5.0.33-prefixon`

- mongod **5.0.33** (`20315d70b9`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = True, WT cache 1 GB
- insert phase: **5.99 s**; 1000/1000 insertMany calls returned; 1,909,296 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.11 / 0.19 / 0.24 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.24 s; stall type (exploratory): none
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 5.81 / 5.99 s (straggler gap 0.17 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 4,894; search_near calls: 3,817,931; prefix-search early exits: 3,629,038
- eviction: pages evicted by application threads 8.0, forced-eviction pages selected 111.0, pages read into cache 268.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 137.3 / 610.2 % (6 samples) → **NOISY**; w7264-mongod peak 832.1 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
