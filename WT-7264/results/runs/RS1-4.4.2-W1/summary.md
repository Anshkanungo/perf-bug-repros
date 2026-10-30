# Run `RS1-4.4.2-W1`

- mongod **4.4.2** (`15e73dc573`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **300.0 s** (CAPPED: client killed at the cap); 950/951 insertMany calls returned; 1,900,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.17 / 0.47 / 0.68 s
- **stalled calls (≥ 3 s or never returned): 1** on 1 thread(s); longest call 300.00 s; stall type (exploratory): history-store walk
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 9.64 / 10.69 s (straggler gap 1.05 s)
- history store reads missed: **511,918,173** (100% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 599,996,227; search_near calls: 515,722,067; prefix-search early exits: –
- eviction: pages evicted by application threads 474.0, forced-eviction pages selected 794.0, pages read into cache 5,533
- checkpoints: {'checkpoints_completed': 5.0, 'seconds_with_checkpoint_running': 1, 'checkpoint_running_during_stalls': True, 'last_checkpoint_ms_max': 336.0}
- noise: other containers' CPU median / peak 9.0 / 706.0 % (300 samples) → **NOISY**; w7264-mongod peak 704.0 %
- while only stalled calls were left (10.7–300.0 s): median 1 connection thread(s) at ≥90% CPU, mongod 1.0 cores

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 10 | 0 | 0.002 | 300.0 | False |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
