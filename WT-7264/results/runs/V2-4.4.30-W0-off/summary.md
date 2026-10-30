# Run `V2-4.4.30-W0-off`

- mongod **4.4.30** (`4d7fa6a626`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **300.0 s** (CAPPED: client killed at the cap); 254/269 insertMany calls returned; 408,500 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.06 / 0.90 / 1.31 s
- **stalled calls (≥ 3 s or never returned): 15** on 15 thread(s); longest call 299.94 s; stall type (exploratory): history-store walk
- host power: AC Power → AC Power
- thread finish time median / last: 3.65 / 30.24 s (straggler gap 26.59 s)
- history store reads missed: **468,949,081** (99% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 737,662,016; search_near calls: 469,766,228; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 12.0, forced-eviction pages selected 1,780, pages read into cache 1,360
- checkpoints: {'checkpoints_completed': 5.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 235.0}
- noise: other containers' CPU median / peak 10.6 / 662.3 % (301 samples) → **NOISY**; w7264-mongod peak 1,159 %
- while only stalled calls were left (30.2–300.0 s): median 2 connection thread(s) at ≥90% CPU, mongod 9.92 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 6 | 0 | 0.065 | 299.94 | False |
| 15 | 0 | 0.084 | 299.92 | False |
| 13 | 0 | 0.085 | 299.92 | False |
| 8 | 0 | 0.086 | 299.91 | False |
| 10 | 1 | 0.09 | 299.91 | False |
| 12 | 0 | 0.099 | 299.9 | False |
| 11 | 0 | 0.1 | 299.9 | False |
| 1 | 0 | 0.113 | 299.89 | False |
| 4 | 0 | 0.119 | 299.88 | False |
| 7 | 0 | 0.119 | 299.88 | False |
| 0 | 0 | 0.122 | 299.88 | False |
| 3 | 0 | 0.124 | 299.88 | False |
| 2 | 0 | 0.132 | 299.87 | False |
| 16 | 0 | 0.148 | 299.85 | False |
| 18 | 3 | 0.173 | 299.83 | False |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn19 | 1039 | 1000 | – | 19.3 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
