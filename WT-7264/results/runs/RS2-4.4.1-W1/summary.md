# Run `RS2-4.4.1-W1`

- mongod **4.4.1** (`ad91a93a5a`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **12.39 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.16 / 2.17 / 5.28 s
- **stalled calls (≥ 3 s or never returned): 2** on 2 thread(s); longest call 5.28 s; stall type (exploratory): in-memory walk
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 12.21 / 12.39 s (straggler gap 0.18 s)
- history store reads missed: **364,360** (27% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 95,161,904; search_near calls: 4,417,938; prefix-search early exits: –
- eviction: pages evicted by application threads 12,002, forced-eviction pages selected 388.0, pages read into cache 57.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 13.0 / 175.2 % (15 samples) → not noisy; w7264-mongod peak 1,016 %

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 11 | 0 | 0.005 | 5.28 | True |
| 14 | 0 | 0.008 | 3.02 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn23 | 1811 | 1000 | – | 1,620 |
| conn15 | 1959 | 1000 | – | 1,477 |
| conn11 | 1827 | 1000 | – | 1,354 |
| conn14 | 1973 | 1000 | – | 1,678 |
| conn8 | 1807 | 1000 | – | 1,615 |
| conn25 | 1786 | 1000 | – | 1,716 |
| conn10 | 1800 | 1000 | – | 1,584 |
| conn21 | 1493 | 1000 | – | 1,380 |
| conn27 | 1912 | 1000 | – | 1,665 |
| conn9 | 1800 | 1000 | – | 1,562 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
