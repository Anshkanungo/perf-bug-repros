# Run `B3-4.2.24-W0`

- mongod **4.2.24** (`5e4ec1d244`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **8.34 s**; 1000/1000 insertMany calls returned; 1,845,552 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.11 / 2.42 / 3.20 s
- **stalled calls (≥ 3 s or never returned): 1** on 1 thread(s); longest call 3.20 s; stall type (exploratory): eviction
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 8.11 / 8.33 s (straggler gap 0.22 s)
- history store reads missed: **–** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): –; search_near calls: 3,690,469; prefix-search early exits: –
- eviction: pages evicted by application threads 97,013, forced-eviction pages selected 431.0, pages read into cache 17.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 14.3 / 66.3 % (9 samples) → not noisy; w7264-mongod peak 810.9 %

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 13 | 1 | 0.235 | 3.2 | True |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
