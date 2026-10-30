# Run `U06-5.0.33-W0-on`

- mongod **5.0.33** (`20315d70b9`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = True, WT cache 1 GB
- insert phase: **5.88 s**; 1000/1000 insertMany calls returned; 1,886,280 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.11 / 0.20 / 0.28 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.28 s; stall type (exploratory): none
- host power: AC Power → AC Power
- thread finish time median / last: 5.75 / 5.87 s (straggler gap 0.13 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 4,894; search_near calls: 3,772,028; prefix-search early exits: 3,579,134
- eviction: pages evicted by application threads 0.0, forced-eviction pages selected 262.0, pages read into cache 460.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 67.0 / 488.5 % (7 samples) → **NOISY**; w7264-mongod peak 813.4 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
