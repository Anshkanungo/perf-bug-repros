# Run `A1-5.0.33-W1-off`

- mongod **5.0.33** (`20315d70b9`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **562.3 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.12 / 0.45 / 561.32 s
- **stalled calls (≥ 3 s or never returned): 4** on 4 thread(s); longest call 561.32 s; stall type (exploratory): history-store walk
- host power: Battery Power → AC Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 7.90 / 562.30 s (straggler gap 554.40 s)
- history store reads missed: **1,083,053,646** (100% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 1,202,206,995; search_near calls: 1,087,053,682; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 224.0, forced-eviction pages selected 493.0, pages read into cache 2,577
- checkpoints: {'checkpoints_completed': 9.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 109.0}
- noise: other containers' CPU median / peak 8.8 / 781.3 % (565 samples) → **NOISY**; w7264-mongod peak 813.1 %
- while only stalled calls were left (10.4–561.3 s): median 2 connection thread(s) at ≥90% CPU, mongod 2.0 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 1 | 0 | 0.001 | 561.32 | True |
| 10 | 0 | 0.001 | 329.52 | True |
| 8 | 0 | 0.001 | 152.65 | True |
| 13 | 0 | 0.005 | 72.69 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn24 | 72663 | 1000 | 5,003,621 | 675.6 |
| conn22 | 152629 | 1000 | 6,244,292 | 298.7 |
| conn26 | 329492 | 1000 | 3,954,585 | 469.6 |
| conn25 | 561296 | 1000 | 20,158,712 | 469.7 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
