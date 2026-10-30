# Run `A2-5.0.33-W1-off`

- mongod **5.0.33** (`20315d70b9`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **247.6 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.11 / 0.36 / 246.66 s
- **stalled calls (≥ 3 s or never returned): 3** on 3 thread(s); longest call 246.66 s; stall type (exploratory): history-store walk
- host power: AC Power → AC Power
- thread finish time median / last: 6.82 / 247.60 s (straggler gap 240.78 s)
- history store reads missed: **689,428,808** (99% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 798,020,704; search_near calls: 693,428,812; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 282.0, forced-eviction pages selected 323.0, pages read into cache 2,174
- checkpoints: {'checkpoints_completed': 4.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 116.0}
- noise: other containers' CPU median / peak 8.2 / 636.1 % (250 samples) → **NOISY**; w7264-mongod peak 837.8 %
- while only stalled calls were left (8.5–246.7 s): median 3 connection thread(s) at ≥90% CPU, mongod 3.0 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 6 | 0 | 0.001 | 246.66 | True |
| 9 | 0 | 0.005 | 206.99 | True |
| 7 | 0 | 0.0 | 197.84 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn20 | 197821 | 1000 | 9,939,011 | 751.9 |
| conn18 | 206970 | 1000 | 15,310,367 | 938.3 |
| conn24 | 246638 | 1000 | 4,031,322 | 886.5 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
