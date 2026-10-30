# Run `X1-5.0.33-W2-off`

- mongod **5.0.33** (`20315d70b9`), workload `67350`, `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **4.34 s**; 10/10 insertMany calls returned; 1,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 1.88 / 2.78 / 2.80 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 2.80 s; stall type (exploratory): none
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 4.25 / 4.32 s (straggler gap 0.08 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 1,428,853; search_near calls: 1,000,000; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 0.0, forced-eviction pages selected 82.0, pages read into cache 9.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 25.6 / 305.2 % (6 samples) → **NOISY**; w7264-mongod peak 294.8 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
