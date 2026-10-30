# Run `B2-4.2.24-W0`

- mongod **4.2.24** (`5e4ec1d244`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **4.74 s**; 1000/1000 insertMany calls returned; 1,983,984 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.09 / 0.15 / 0.31 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.31 s; stall type (exploratory): none
- host power: AC Power → AC Power
- thread finish time median / last: 4.65 / 4.74 s (straggler gap 0.09 s)
- history store reads missed: **–** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): –; search_near calls: 3,966,920; prefix-search early exits: –
- eviction: pages evicted by application threads 0.0, forced-eviction pages selected 546.0, pages read into cache 14.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 21.1 / 55.6 % (5 samples) → not noisy; w7264-mongod peak 802.5 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
