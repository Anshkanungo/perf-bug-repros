# Run `RS5-4.4.2-W1`

- mongod **4.4.2** (`15e73dc573`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **300.0 s** (CAPPED: client killed at the cap); 650/657 insertMany calls returned; 1,300,500 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.13 / 0.80 / 0.99 s
- **stalled calls (≥ 3 s or never returned): 7** on 7 thread(s); longest call 300.00 s; stall type (exploratory): history-store walk
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 6.53 / 17.00 s (straggler gap 10.47 s)
- history store reads missed: **585,469,205** (99% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 1,238,337,758; search_near calls: 588,075,499; prefix-search early exits: –
- eviction: pages evicted by application threads 234.0, forced-eviction pages selected 329.0, pages read into cache 7,411
- checkpoints: {'checkpoints_completed': 5.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 99.0}
- noise: other containers' CPU median / peak 8.8 / 780.2 % (302 samples) → **NOISY**; w7264-mongod peak 1,055 %
- while only stalled calls were left (17.0–300.0 s): median 7 connection thread(s) at ≥90% CPU, mongod 7.0 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 0 | 0 | 0.002 | 300.0 | False |
| 1 | 0 | 0.002 | 300.0 | False |
| 4 | 0 | 0.002 | 300.0 | False |
| 18 | 0 | 0.002 | 300.0 | False |
| 7 | 0 | 0.003 | 300.0 | False |
| 15 | 0 | 0.004 | 300.0 | False |
| 14 | 0 | 0.006 | 299.99 | False |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
