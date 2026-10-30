# Run `R4-4.4.1-W0`

- mongod **4.4.1** (`ad91a93a5a`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **10.65 s**; 1000/1000 insertMany calls returned; 1,874,297 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.16 / 2.29 / 2.94 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 2.94 s; stall type (exploratory): none
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 10.47 / 10.64 s (straggler gap 0.17 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 19,564,895; search_near calls: 3,761,959; prefix-search early exits: –
- eviction: pages evicted by application threads 6,933, forced-eviction pages selected 121.0, pages read into cache 169.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 101.1 / 620.5 % (11 samples) → **NOISY**; w7264-mongod peak 980.8 %

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn8 | 2079 | 1000 | – | 2,003 |
| conn9 | 2114 | 1000 | – | 1,975 |
| conn23 | 2092 | 1000 | – | 2,008 |
| conn15 | 2215 | 1000 | – | 1,970 |
| conn24 | 2075 | 1000 | – | 1,177 |
| conn11 | 2780 | 1000 | – | 339.5 |
| conn22 | 2121 | 1000 | – | 1,961 |
| conn14 | 2287 | 1000 | – | 1,908 |
| conn27 | 2177 | 1000 | 3,692 | 1,755 |
| conn18 | 2175 | 1000 | 6,427 | 1,721 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
