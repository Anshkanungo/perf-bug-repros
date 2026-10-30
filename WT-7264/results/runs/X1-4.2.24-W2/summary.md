# Run `X1-4.2.24-W2`

- mongod **4.2.24** (`5e4ec1d244`), workload `67350`, `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **4.32 s**; 10/10 insertMany calls returned; 1,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 1.92 / 2.42 / 2.42 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 2.42 s; stall type (exploratory): none
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 4.23 / 4.30 s (straggler gap 0.07 s)
- history store reads missed: **–** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): –; search_near calls: 1,000,000; prefix-search early exits: –
- eviction: pages evicted by application threads 0.0, forced-eviction pages selected 120.0, pages read into cache 0.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 9.2 / 30.8 % (6 samples) → not noisy; w7264-mongod peak 257.5 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
