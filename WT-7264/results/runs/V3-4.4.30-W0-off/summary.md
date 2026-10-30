# Run `V3-4.4.30-W0-off`

- mongod **4.4.30** (`4d7fa6a626`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **300.0 s** (CAPPED: client killed at the cap); 403/415 insertMany calls returned; 731,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.08 / 1.17 / 1.82 s
- **stalled calls (≥ 3 s or never returned): 12** on 12 thread(s); longest call 299.93 s; stall type (exploratory): history-store walk
- host power: AC Power → AC Power
- thread finish time median / last: 4.20 / 40.59 s (straggler gap 36.40 s)
- history store reads missed: **472,393,693** (99% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 1,062,061,050; search_near calls: 473,854,200; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 121.0, forced-eviction pages selected 68.0, pages read into cache 1,461
- checkpoints: {'checkpoints_completed': 5.0, 'seconds_with_checkpoint_running': 1, 'checkpoint_running_during_stalls': True, 'last_checkpoint_ms_max': 286.0}
- noise: other containers' CPU median / peak 10.7 / 624.0 % (301 samples) → **NOISY**; w7264-mongod peak 1,088 %
- while only stalled calls were left (40.6–300.0 s): median 5 connection thread(s) at ≥90% CPU, mongod 9.92 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 15 | 0 | 0.073 | 299.93 | False |
| 3 | 0 | 0.075 | 299.93 | False |
| 7 | 1 | 0.078 | 299.92 | False |
| 16 | 0 | 0.084 | 299.92 | False |
| 10 | 0 | 0.087 | 299.91 | False |
| 1 | 0 | 0.093 | 299.91 | False |
| 9 | 0 | 0.094 | 299.91 | False |
| 2 | 0 | 0.102 | 299.9 | False |
| 13 | 0 | 0.102 | 299.9 | False |
| 5 | 1 | 0.119 | 299.88 | False |
| 11 | 0 | 0.138 | 299.86 | False |
| 18 | 1 | 0.194 | 299.81 | False |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn25 | 1025 | 1000 | – | 127.3 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
