# Run `smoke2-4.2.24`

- mongod **4.2.24** (`5e4ec1d244`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **5.37 s**; 1000/1000 insertMany calls returned; 1,957,016 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.10 / 0.19 / 0.22 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.22 s; stall type (exploratory): none
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 5.25 / 5.37 s (straggler gap 0.12 s)
- history store reads missed: **–** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): –; search_near calls: 3,912,527; prefix-search early exits: –
- eviction: pages evicted by application threads 0.0, forced-eviction pages selected 623.0, pages read into cache 22.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 114.7 / 621.3 % (6 samples) → **NOISY**; w7264-mongod peak 822.2 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
