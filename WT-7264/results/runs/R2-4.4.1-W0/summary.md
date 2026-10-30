# Run `R2-4.4.1-W0`

- mongod **4.4.1** (`ad91a93a5a`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **12.33 s**; 1000/1000 insertMany calls returned; 1,903,500 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.14 / 3.11 / 4.68 s
- **stalled calls (≥ 3 s or never returned): 14** on 14 thread(s); longest call 4.68 s; stall type (exploratory): in-memory walk
- host power: AC Power → AC Power
- thread finish time median / last: 12.21 / 12.33 s (straggler gap 0.12 s)
- history store reads missed: **106,170** (5% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 133,648,027; search_near calls: 3,959,786; prefix-search early exits: –
- eviction: pages evicted by application threads 12,831, forced-eviction pages selected 1,438, pages read into cache 42.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 33.6 / 399.4 % (13 samples) → **NOISY**; w7264-mongod peak 1,002 %

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 12 | 5 | 1.158 | 4.68 | True |
| 4 | 0 | 0.144 | 3.28 | True |
| 10 | 1 | 0.113 | 3.24 | True |
| 3 | 0 | 0.138 | 3.16 | True |
| 1 | 0 | 0.133 | 3.15 | True |
| 16 | 0 | 0.148 | 3.14 | True |
| 8 | 0 | 0.119 | 3.13 | True |
| 14 | 0 | 0.13 | 3.12 | True |
| 17 | 0 | 0.153 | 3.12 | True |
| 7 | 0 | 0.111 | 3.12 | True |
| 0 | 0 | 0.155 | 3.11 | True |
| 2 | 0 | 0.122 | 3.1 | True |
| 15 | 0 | 0.141 | 3.06 | True |
| 13 | 0 | 0.129 | 3.01 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn21 | 1766 | 1000 | – | 1,642 |
| conn14 | 1769 | 1000 | 3,948 | 1,448 |
| conn15 | 1778 | 1000 | – | 1,557 |
| conn16 | 2954 | 1000 | – | 1,007 |
| conn18 | 1642 | 1000 | – | 1,525 |
| conn8 | 1530 | 1000 | – | 1,439 |
| conn12 | 1658 | 1000 | – | 1,550 |
| conn24 | 2985 | 1000 | – | 1,314 |
| conn20 | 2999 | 1000 | 520 | 1,110 |
| conn17 | 3040 | 1000 | 4,828 | 901.2 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
