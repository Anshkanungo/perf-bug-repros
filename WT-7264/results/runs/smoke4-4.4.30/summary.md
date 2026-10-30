# Run `smoke4-4.4.30`

- mongod **4.4.30** (`4d7fa6a626`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **600.0 s** (CAPPED: client killed at the cap); 454/465 insertMany calls returned; 910,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.10 / 0.75 / 499.66 s
- **stalled calls (≥ 3 s or never returned): 12** on 12 thread(s); longest call 599.91 s; stall type (exploratory): history-store walk
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 5.63 / 525.73 s (straggler gap 520.10 s)
- history store reads missed: **837,437,181** (100% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 1,275,089,940; search_near calls: 839,263,229; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 89.0, forced-eviction pages selected 556.0, pages read into cache 2,113
- checkpoints: {'checkpoints_completed': 10.0, 'seconds_with_checkpoint_running': 2, 'checkpoint_running_during_stalls': True, 'last_checkpoint_ms_max': 337.0}
- noise: other containers' CPU median / peak 10.6 / 724.8 % (601 samples) → **NOISY**; w7264-mongod peak 1,264 %
- while only stalled calls were left (11.7–600.0 s): median 6 connection thread(s) at ≥90% CPU, mongod 9.92 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 6 | 1 | 0.085 | 599.91 | False |
| 11 | 0 | 0.091 | 599.91 | False |
| 10 | 0 | 0.096 | 599.9 | False |
| 12 | 0 | 0.096 | 599.9 | False |
| 17 | 1 | 0.112 | 599.89 | False |
| 2 | 1 | 0.154 | 599.85 | False |
| 3 | 0 | 0.156 | 599.84 | False |
| 13 | 1 | 0.161 | 599.84 | False |
| 0 | 0 | 0.162 | 599.84 | False |
| 7 | 0 | 0.18 | 599.82 | False |
| 15 | 0 | 0.199 | 599.8 | False |
| 14 | 0 | 0.167 | 499.66 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn20 | 499449 | 1000 | 935,247 | 163.9 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
