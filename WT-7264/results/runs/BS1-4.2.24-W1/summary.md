# Run `BS1-4.2.24-W1`

- mongod **4.2.24** (`5e4ec1d244`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **5.44 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.10 / 0.52 / 1.23 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 1.23 s; stall type (exploratory): none
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 5.30 / 5.43 s (straggler gap 0.13 s)
- history store reads missed: **–** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): –; search_near calls: 4,000,000; prefix-search early exits: –
- eviction: pages evicted by application threads 8,932, forced-eviction pages selected 815.0, pages read into cache 12.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 11.6 / 14.9 % (8 samples) → not noisy; w7264-mongod peak 862.3 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
