# Run `R4-4.4.2-W0`

- mongod **4.4.2** (`15e73dc573`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **300.0 s** (CAPPED: client killed at the cap); 551/560 insertMany calls returned; 1,092,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.11 / 0.96 / 115.54 s
- **stalled calls (≥ 3 s or never returned): 10** on 10 thread(s); longest call 299.94 s; stall type (exploratory): history-store walk
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 5.94 / 117.88 s (straggler gap 111.94 s)
- history store reads missed: **524,062,341** (99% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 1,302,215,397; search_near calls: 526,245,822; prefix-search early exits: –
- eviction: pages evicted by application threads 150.0, forced-eviction pages selected 472.0, pages read into cache 6,631
- checkpoints: {'checkpoints_completed': 5.0, 'seconds_with_checkpoint_running': 1, 'checkpoint_running_during_stalls': True, 'last_checkpoint_ms_max': 274.0}
- noise: other containers' CPU median / peak 11.6 / 662.9 % (300 samples) → **NOISY**; w7264-mongod peak 1,301 %
- while only stalled calls were left (22.9–300.0 s): median 9 connection thread(s) at ≥90% CPU, mongod 8.99 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 7 | 0 | 0.059 | 299.94 | False |
| 10 | 0 | 0.089 | 299.91 | False |
| 8 | 1 | 0.09 | 299.91 | False |
| 4 | 0 | 0.098 | 299.9 | False |
| 14 | 0 | 0.1 | 299.9 | False |
| 2 | 0 | 0.108 | 299.89 | False |
| 17 | 0 | 0.11 | 299.89 | False |
| 0 | 0 | 0.118 | 299.88 | False |
| 9 | 0 | 0.14 | 299.86 | False |
| 12 | 0 | 0.078 | 115.54 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn26 | 1004 | 1000 | – | 0.0 |
| conn10 | 115502 | 1000 | 2,681,250 | 302.8 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
