# Run `A5-5.0.33-W1-off`

- mongod **5.0.33** (`20315d70b9`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **5.24 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.10 / 0.17 / 0.23 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.23 s; stall type (exploratory): none
- host power: AC Power → AC Power
- thread finish time median / last: 5.12 / 5.23 s (straggler gap 0.11 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 9,941,714; search_near calls: 4,000,000; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 13.0, forced-eviction pages selected 527.0, pages read into cache 537.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 14.1 / 18.7 % (8 samples) → not noisy; w7264-mongod peak 834.1 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
