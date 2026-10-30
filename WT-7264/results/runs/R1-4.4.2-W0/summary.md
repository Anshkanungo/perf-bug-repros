# Run `R1-4.4.2-W0`

- mongod **4.4.2** (`15e73dc573`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **300.0 s** (CAPPED: client killed at the cap); 451/462 insertMany calls returned; 812,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.09 / 0.71 / 170.53 s
- **stalled calls (≥ 3 s or never returned): 12** on 12 thread(s); longest call 299.93 s; stall type (exploratory): history-store walk
- host power: AC Power → AC Power
- thread finish time median / last: 4.78 / 191.54 s (straggler gap 186.76 s)
- history store reads missed: **545,804,355** (99% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 1,235,478,043; search_near calls: 547,426,197; prefix-search early exits: –
- eviction: pages evicted by application threads 63.0, forced-eviction pages selected 1,084, pages read into cache 5,874
- checkpoints: {'checkpoints_completed': 5.0, 'seconds_with_checkpoint_running': 1, 'checkpoint_running_during_stalls': True, 'last_checkpoint_ms_max': 388.0}
- noise: other containers' CPU median / peak 9.0 / 1,230 % (300 samples) → **NOISY**; w7264-mongod peak 1,080 %
- while only stalled calls were left (16.2–300.0 s): median 6 connection thread(s) at ≥90% CPU, mongod 9.93 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 17 | 0 | 0.073 | 299.93 | False |
| 6 | 0 | 0.081 | 299.92 | False |
| 12 | 0 | 0.088 | 299.91 | False |
| 8 | 0 | 0.094 | 299.91 | False |
| 1 | 0 | 0.096 | 299.9 | False |
| 10 | 1 | 0.096 | 299.9 | False |
| 4 | 0 | 0.108 | 299.89 | False |
| 14 | 0 | 0.114 | 299.89 | False |
| 3 | 0 | 0.118 | 299.88 | False |
| 15 | 0 | 0.121 | 299.88 | False |
| 18 | 0 | 0.137 | 299.86 | False |
| 13 | 0 | 0.13 | 170.53 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn26 | 170365 | 1000 | 2,227,975 | 12.8 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
