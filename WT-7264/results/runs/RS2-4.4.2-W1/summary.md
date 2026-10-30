# Run `RS2-4.4.2-W1`

- mongod **4.4.2** (`15e73dc573`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **17.87 s**; 900/902 insertMany calls returned; 1,800,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.16 / 0.72 / 1.26 s
- **stalled calls (≥ 3 s or never returned): 2** on 2 thread(s); longest call 17.86 s; stall type (exploratory): history-store walk
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 9.18 / 17.87 s (straggler gap 8.68 s)
- history store reads missed: **38,824,950** (90% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 464,962,932; search_near calls: 42,427,365; prefix-search early exits: –
- eviction: pages evicted by application threads 476.0, forced-eviction pages selected 493.0, pages read into cache 13,537
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 7.5 / 614.1 % (20 samples) → **NOISY**; w7264-mongod peak 855.8 %

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 0 | 0 | 0.001 | 17.86 | False |
| 13 | 0 | 0.002 | 17.86 | False |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
