# Run `RS4-4.4.2-W1`

- mongod **4.4.2** (`15e73dc573`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **300.0 s** (CAPPED: client killed at the cap); 750/755 insertMany calls returned; 1,500,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.12 / 0.72 / 1.29 s
- **stalled calls (≥ 3 s or never returned): 5** on 5 thread(s); longest call 300.00 s; stall type (exploratory): history-store walk
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 7.48 / 14.23 s (straggler gap 6.75 s)
- history store reads missed: **628,636,384** (99% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 1,150,978,206; search_near calls: 631,639,130; prefix-search early exits: –
- eviction: pages evicted by application threads 190.0, forced-eviction pages selected 277.0, pages read into cache 5,896
- checkpoints: {'checkpoints_completed': 5.0, 'seconds_with_checkpoint_running': 1, 'checkpoint_running_during_stalls': True, 'last_checkpoint_ms_max': 170.0}
- noise: other containers' CPU median / peak 8.8 / 797.6 % (302 samples) → **NOISY**; w7264-mongod peak 1,014 %
- while only stalled calls were left (14.2–300.0 s): median 5 connection thread(s) at ≥90% CPU, mongod 5.0 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 8 | 0 | 0.001 | 300.0 | False |
| 11 | 0 | 0.001 | 300.0 | False |
| 16 | 0 | 0.004 | 300.0 | False |
| 5 | 0 | 0.005 | 300.0 | False |
| 3 | 0 | 0.007 | 299.99 | False |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
