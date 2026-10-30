# Run `V1-4.4.30-W0-off`

- mongod **4.4.30** (`4d7fa6a626`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **300.0 s** (CAPPED: client killed at the cap); 353/366 insertMany calls returned; 702,500 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.07 / 0.25 / 1.07 s
- **stalled calls (≥ 3 s or never returned): 13** on 13 thread(s); longest call 299.92 s; stall type (exploratory): history-store walk
- host power: AC Power → AC Power
- thread finish time median / last: 4.31 / 4.95 s (straggler gap 0.64 s)
- history store reads missed: **472,184,302** (99% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 557,754,471; search_near calls: 473,590,078; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 107.0, forced-eviction pages selected 1,630, pages read into cache 1,149
- checkpoints: {'checkpoints_completed': 5.0, 'seconds_with_checkpoint_running': 1, 'checkpoint_running_during_stalls': True, 'last_checkpoint_ms_max': 296.0}
- noise: other containers' CPU median / peak 10.7 / 655.2 % (300 samples) → **NOISY**; w7264-mongod peak 1,081 %
- while only stalled calls were left (4.9–300.0 s): median 4 connection thread(s) at ≥90% CPU, mongod 9.92 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 3 | 0 | 0.08 | 299.92 | False |
| 4 | 0 | 0.082 | 299.92 | False |
| 12 | 0 | 0.097 | 299.9 | False |
| 14 | 0 | 0.103 | 299.9 | False |
| 15 | 0 | 0.121 | 299.88 | False |
| 1 | 0 | 0.124 | 299.88 | False |
| 18 | 0 | 0.126 | 299.87 | False |
| 17 | 1 | 0.13 | 299.87 | False |
| 13 | 0 | 0.142 | 299.86 | False |
| 6 | 1 | 0.152 | 299.85 | False |
| 9 | 0 | 0.163 | 299.84 | False |
| 8 | 1 | 0.166 | 299.83 | False |
| 10 | 0 | 0.171 | 299.83 | False |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
