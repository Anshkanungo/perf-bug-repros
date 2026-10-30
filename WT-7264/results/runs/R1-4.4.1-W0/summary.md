# Run `R1-4.4.1-W0`

- mongod **4.4.1** (`ad91a93a5a`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **11.26 s**; 1000/1000 insertMany calls returned; 1,886,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.14 / 4.28 / 4.47 s
- **stalled calls (≥ 3 s or never returned): 16** on 16 thread(s); longest call 4.47 s; stall type (exploratory): in-memory walk
- host power: AC Power → AC Power
- thread finish time median / last: 11.08 / 11.26 s (straggler gap 0.17 s)
- history store reads missed: **241,315** (27% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 74,347,272; search_near calls: 4,067,399; prefix-search early exits: –
- eviction: pages evicted by application threads 11,302, forced-eviction pages selected 157.0, pages read into cache 76.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 9.0 / 15.1 % (12 samples) → not noisy; w7264-mongod peak 1,017 %

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 2 | 1 | 0.118 | 4.47 | True |
| 12 | 0 | 0.127 | 4.39 | True |
| 11 | 0 | 0.144 | 4.37 | True |
| 15 | 0 | 0.126 | 4.35 | True |
| 6 | 0 | 0.148 | 4.35 | True |
| 5 | 0 | 0.113 | 4.34 | True |
| 7 | 0 | 0.155 | 4.32 | True |
| 10 | 0 | 0.137 | 4.32 | True |
| 8 | 0 | 0.155 | 4.31 | True |
| 9 | 0 | 0.152 | 4.29 | True |
| 18 | 1 | 0.156 | 4.28 | True |
| 17 | 9 | 0.884 | 3.58 | True |
| 13 | 6 | 0.868 | 3.54 | True |
| 3 | 7 | 0.893 | 3.52 | True |
| 19 | 11 | 0.899 | 3.51 | True |
| 14 | 9 | 1.026 | 3.42 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn23 | 2053 | 1000 | – | 1,657 |
| conn9 | 2137 | 1000 | – | 1,968 |
| conn26 | 2183 | 1000 | – | 1,830 |
| conn15 | 2198 | 1000 | – | 2,012 |
| conn18 | 2199 | 1000 | – | 1,640 |
| conn12 | 1410 | 1000 | – | 1,270 |
| conn10 | 2270 | 1000 | – | 2,071 |
| conn24 | 3067 | 1000 | – | 1,304 |
| conn13 | 3116 | 1000 | – | 1,019 |
| conn11 | 3124 | 1000 | – | 1,513 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
