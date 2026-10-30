# Run `B1-4.2.24-W0`

- mongod **4.2.24** (`5e4ec1d244`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **4.77 s**; 1000/1000 insertMany calls returned; 1,792,600 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.09 / 0.15 / 0.21 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.21 s; stall type (exploratory): none
- host power: AC Power → AC Power
- thread finish time median / last: 4.66 / 4.77 s (straggler gap 0.11 s)
- history store reads missed: **–** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): –; search_near calls: 3,584,208; prefix-search early exits: –
- eviction: pages evicted by application threads 0.0, forced-eviction pages selected 384.0, pages read into cache 5.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 29.3 / 275.4 % (6 samples) → **NOISY**; w7264-mongod peak 814.1 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
