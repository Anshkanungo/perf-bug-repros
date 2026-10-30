# Run `U04-5.0.33-W0-off`

- mongod **5.0.33** (`20315d70b9`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **5.75 s**; 1000/1000 insertMany calls returned; 1,936,552 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.11 / 0.21 / 0.56 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.56 s; stall type (exploratory): none
- host power: AC Power → AC Power
- thread finish time median / last: 5.62 / 5.75 s (straggler gap 0.13 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 7,817,277; search_near calls: 3,872,334; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 10.0, forced-eviction pages selected 287.0, pages read into cache 384.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 46.5 / 553.9 % (6 samples) → **NOISY**; w7264-mongod peak 826.7 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
