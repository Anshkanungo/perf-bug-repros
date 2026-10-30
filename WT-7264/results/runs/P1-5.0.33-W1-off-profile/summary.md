# Run `P1-5.0.33-W1-off-profile`

- mongod **5.0.33** (`20315d70b9`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **300.0 s** (CAPPED: client killed at the cap); 950/951 insertMany calls returned; 1,900,320 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.12 / 0.34 / 290.14 s
- **stalled calls (≥ 3 s or never returned): 2** on 2 thread(s); longest call 300.00 s; stall type (exploratory): history-store walk
- host power: AC Power → AC Power
- thread finish time median / last: 7.28 / 291.35 s (straggler gap 284.07 s)
- history store reads missed: **645,846,154** (99% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 668,494,772; search_near calls: 649,646,941; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 309.0, forced-eviction pages selected 397.0, pages read into cache 4,012
- checkpoints: {'checkpoints_completed': 5.0, 'seconds_with_checkpoint_running': 1, 'checkpoint_running_during_stalls': True, 'last_checkpoint_ms_max': 203.0}
- noise: other containers' CPU median / peak 9.1 / 655.9 % (301 samples) → **NOISY**; w7264-mongod peak 735.6 %
- while only stalled calls were left (7.5–300.0 s): median 2 connection thread(s) at ≥90% CPU, mongod 2.0 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 7 | 0 | 0.002 | 300.0 | False |
| 8 | 0 | 0.001 | 290.14 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn13 | 290099 | 1000 | 27,414,142 | 913.9 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
