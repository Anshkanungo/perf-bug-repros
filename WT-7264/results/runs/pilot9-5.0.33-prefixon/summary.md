# Run `pilot9-5.0.33-prefixon`

- mongod **5.0.33** (`20315d70b9`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = True, WT cache 1 GB
- insert phase: **5.59 s**; 1000/1000 insertMany calls returned; 1,901,320 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.11 / 0.16 / 0.20 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.20 s; stall type (exploratory): none
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 5.48 / 5.59 s (straggler gap 0.11 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 4,894; search_near calls: 3,801,732; prefix-search early exits: 3,611,780
- eviction: pages evicted by application threads 0.0, forced-eviction pages selected 166.0, pages read into cache 286.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 11.0 / 55.5 % (6 samples) → not noisy; w7264-mongod peak 837.0 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
