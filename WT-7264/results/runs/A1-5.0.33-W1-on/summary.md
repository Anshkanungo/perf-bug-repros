# Run `A1-5.0.33-W1-on`

- mongod **5.0.33** (`20315d70b9`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = True, WT cache 1 GB
- insert phase: **5.59 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.10 / 0.20 / 0.24 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.24 s; stall type (exploratory): none
- host power: AC Power → AC Power
- thread finish time median / last: 5.41 / 5.58 s (straggler gap 0.17 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 4,894; search_near calls: 4,000,000; prefix-search early exits: 3,793,620
- eviction: pages evicted by application threads 11.0, forced-eviction pages selected 297.0, pages read into cache 307.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 15.2 / 499.9 % (7 samples) → **NOISY**; w7264-mongod peak 843.2 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
