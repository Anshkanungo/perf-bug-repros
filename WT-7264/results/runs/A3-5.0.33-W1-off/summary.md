# Run `A3-5.0.33-W1-off`

- mongod **5.0.33** (`20315d70b9`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **239.01 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.12 / 0.38 / 238.02 s
- **stalled calls (≥ 3 s or never returned): 1** on 1 thread(s); longest call 238.02 s; stall type (exploratory): history-store walk
- host power: AC Power → AC Power
- thread finish time median / last: 7.35 / 239.00 s (straggler gap 231.65 s)
- history store reads missed: **388,598,870** (99% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 415,735,106; search_near calls: 392,598,874; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 385.0, forced-eviction pages selected 523.0, pages read into cache 4,074
- checkpoints: {'checkpoints_completed': 4.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 117.0}
- noise: other containers' CPU median / peak 7.5 / 610.6 % (241 samples) → **NOISY**; w7264-mongod peak 754.2 %
- while only stalled calls were left (7.6–238.0 s): median 1 connection thread(s) at ≥90% CPU, mongod 1.0 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 9 | 0 | 0.001 | 238.02 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn15 | 237991 | 1000 | 53,478,597 | 1,412 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
