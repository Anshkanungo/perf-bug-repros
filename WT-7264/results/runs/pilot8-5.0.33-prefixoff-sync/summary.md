# Run `pilot8-5.0.33-prefixoff-sync`

- mongod **5.0.33** (`20315d70b9`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **352.46 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.12 / 0.41 / 348.35 s
- **stalled calls (≥ 3 s or never returned): 2** on 2 thread(s); longest call 348.35 s; stall type (exploratory): history-store walk
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 10.75 / 352.46 s (straggler gap 341.71 s)
- history store reads missed: **625,541,499** (100% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 742,479,827; search_near calls: 629,541,529; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 302.0, forced-eviction pages selected 403.0, pages read into cache 2,703
- checkpoints: {'checkpoints_completed': 5.0, 'seconds_with_checkpoint_running': 1, 'checkpoint_running_during_stalls': True, 'last_checkpoint_ms_max': 129.0}
- noise: other containers' CPU median / peak 7.6 / 778.0 % (353 samples) → **NOISY**; w7264-mongod peak 712.9 %
- while only stalled calls were left (12.6–351.4 s): median 2 connection thread(s) at ≥90% CPU, mongod 2.0 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 5 | 0 | 3.002 | 348.35 | True |
| 7 | 0 | 3.001 | 235.3 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn8 | 2245 | 1000 | 2,391,797 | 485.5 |
| conn15 | 235268 | 1000 | 13,564,482 | 1,485 |
| conn18 | 348329 | 1000 | 19,692,493 | 1,335 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
