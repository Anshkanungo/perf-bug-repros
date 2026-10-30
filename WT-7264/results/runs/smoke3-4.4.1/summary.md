# Run `smoke3-4.4.1`

- mongod **4.4.1** (`ad91a93a5a`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **11.66 s**; 1000/1000 insertMany calls returned; 1,987,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.15 / 4.21 / 4.35 s
- **stalled calls (≥ 3 s or never returned): 15** on 15 thread(s); longest call 4.35 s; stall type (exploratory): in-memory walk
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 11.49 / 11.65 s (straggler gap 0.16 s)
- history store reads missed: **433,557** (9% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 432,018,250; search_near calls: 4,479,326; prefix-search early exits: –
- eviction: pages evicted by application threads 6,076, forced-eviction pages selected 3,613, pages read into cache 27.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 9.0 / 178.8 % (12 samples) → not noisy; w7264-mongod peak 998.6 %

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 15 | 0 | 0.091 | 4.35 | True |
| 9 | 0 | 0.081 | 4.34 | True |
| 8 | 0 | 0.107 | 4.33 | True |
| 7 | 0 | 0.09 | 4.32 | True |
| 2 | 0 | 0.083 | 4.32 | True |
| 1 | 0 | 0.104 | 4.31 | True |
| 13 | 0 | 0.088 | 4.3 | True |
| 3 | 0 | 0.097 | 4.29 | True |
| 6 | 0 | 0.101 | 4.28 | True |
| 17 | 0 | 0.116 | 4.23 | True |
| 4 | 0 | 0.104 | 4.21 | True |
| 18 | 0 | 0.114 | 4.2 | True |
| 16 | 0 | 0.083 | 4.17 | True |
| 12 | 0 | 0.071 | 4.16 | True |
| 19 | 9 | 0.681 | 3.6 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn23 | 1980 | 1000 | – | 1,669 |
| conn8 | 2852 | 1000 | – | 1,687 |
| conn25 | 4088 | 1000 | – | 1,197 |
| conn26 | 3534 | 1000 | – | 1,803 |
| conn10 | 4139 | 1000 | 1,864 | 791.0 |
| conn22 | 4126 | 1000 | – | 1,061 |
| conn14 | 4123 | 1000 | 5,832 | 1,150 |
| conn15 | 4162 | 1000 | – | 1,043 |
| conn13 | 2117 | 1000 | – | 1,710 |
| conn9 | 2049 | 1000 | 5,704 | 1,816 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
