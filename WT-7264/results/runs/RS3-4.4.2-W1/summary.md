# Run `RS3-4.4.2-W1`

- mongod **4.4.2** (`15e73dc573`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **300.0 s** (CAPPED: client killed at the cap); 900/902 insertMany calls returned; 1,800,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.15 / 0.76 / 70.84 s
- **stalled calls (≥ 3 s or never returned): 3** on 3 thread(s); longest call 300.00 s; stall type (exploratory): history-store walk
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 9.04 / 71.99 s (straggler gap 62.95 s)
- history store reads missed: **751,376,571** (99% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 1,349,284,014; search_near calls: 754,982,915; prefix-search early exits: –
- eviction: pages evicted by application threads 531.0, forced-eviction pages selected 341.0, pages read into cache 12,621
- checkpoints: {'checkpoints_completed': 5.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 147.0}
- noise: other containers' CPU median / peak 8.5 / 736.0 % (302 samples) → **NOISY**; w7264-mongod peak 760.3 %
- while only stalled calls were left (21.6–300.0 s): median 2 connection thread(s) at ≥90% CPU, mongod 2.0 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 14 | 0 | 0.001 | 300.0 | False |
| 0 | 0 | 0.003 | 300.0 | False |
| 9 | 0 | 0.009 | 70.84 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn11 | 70819 | 1000 | 12,387,686 | 1,275 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
