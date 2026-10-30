# Run `R2-4.4.2-W0`

- mongod **4.4.2** (`15e73dc573`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **300.0 s** (CAPPED: client killed at the cap); 503/513 insertMany calls returned; 893,500 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.10 / 0.61 / 1.29 s
- **stalled calls (≥ 3 s or never returned): 10** on 10 thread(s); longest call 299.91 s; stall type (exploratory): history-store walk
- host power: AC Power → AC Power
- thread finish time median / last: 5.29 / 22.02 s (straggler gap 16.73 s)
- history store reads missed: **543,399,586** (99% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 942,694,478; search_near calls: 545,182,996; prefix-search early exits: –
- eviction: pages evicted by application threads 184.0, forced-eviction pages selected 444.0, pages read into cache 5,489
- checkpoints: {'checkpoints_completed': 5.0, 'seconds_with_checkpoint_running': 1, 'checkpoint_running_during_stalls': True, 'last_checkpoint_ms_max': 601.0}
- noise: other containers' CPU median / peak 10.1 / 486.9 % (301 samples) → **NOISY**; w7264-mongod peak 1,099 %
- while only stalled calls were left (22.0–300.0 s): median 10 connection thread(s) at ≥90% CPU, mongod 9.93 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 2 | 0 | 0.092 | 299.91 | False |
| 15 | 0 | 0.109 | 299.89 | False |
| 6 | 1 | 0.113 | 299.89 | False |
| 9 | 0 | 0.141 | 299.86 | False |
| 4 | 0 | 0.145 | 299.86 | False |
| 8 | 0 | 0.146 | 299.85 | False |
| 12 | 1 | 0.148 | 299.85 | False |
| 7 | 0 | 0.15 | 299.85 | False |
| 16 | 0 | 0.157 | 299.84 | False |
| 0 | 1 | 0.168 | 299.83 | False |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
