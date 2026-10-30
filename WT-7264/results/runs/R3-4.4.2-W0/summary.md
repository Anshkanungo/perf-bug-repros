# Run `R3-4.4.2-W0`

- mongod **4.4.2** (`15e73dc573`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **300.0 s** (CAPPED: client killed at the cap); 400/412 insertMany calls returned; 804,500 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.09 / 0.65 / 1.16 s
- **stalled calls (≥ 3 s or never returned): 12** on 12 thread(s); longest call 299.92 s; stall type (exploratory): history-store walk
- host power: AC Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 5.01 / 23.04 s (straggler gap 18.04 s)
- history store reads missed: **284,391,091** (98% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 754,691,032; search_near calls: 286,004,949; prefix-search early exits: –
- eviction: pages evicted by application threads 110.0, forced-eviction pages selected 1,071, pages read into cache 8,252
- checkpoints: {'checkpoints_completed': 2.0, 'seconds_with_checkpoint_running': 1, 'checkpoint_running_during_stalls': True, 'last_checkpoint_ms_max': 433.0}
- noise: other containers' CPU median / peak 11.3 / 923.3 % (159 samples) → **NOISY**; w7264-mongod peak 2,536 %
- while only stalled calls were left (23.0–300.0 s): median 5 connection thread(s) at ≥90% CPU, mongod 9.91 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 11 | 0 | 0.084 | 299.92 | False |
| 8 | 0 | 0.086 | 299.91 | False |
| 0 | 0 | 0.113 | 299.89 | False |
| 9 | 0 | 0.117 | 299.88 | False |
| 2 | 0 | 0.123 | 299.88 | False |
| 16 | 0 | 0.123 | 299.88 | False |
| 17 | 0 | 0.134 | 299.87 | False |
| 6 | 0 | 0.138 | 299.86 | False |
| 12 | 0 | 0.152 | 299.85 | False |
| 15 | 0 | 0.157 | 299.84 | False |
| 14 | 0 | 0.161 | 299.84 | False |
| 1 | 0 | 0.162 | 299.84 | False |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
