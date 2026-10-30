# Run `RS1-4.4.1-W1`

- mongod **4.4.1** (`ad91a93a5a`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **12.84 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.17 / 2.08 / 5.33 s
- **stalled calls (≥ 3 s or never returned): 1** on 1 thread(s); longest call 5.33 s; stall type (exploratory): in-memory walk
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 12.62 / 12.84 s (straggler gap 0.22 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 112,012,741; search_near calls: 4,053,024; prefix-search early exits: –
- eviction: pages evicted by application threads 9,505, forced-eviction pages selected 443.0, pages read into cache 182.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 15.1 / 668.6 % (14 samples) → **NOISY**; w7264-mongod peak 989.3 %

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 16 | 0 | 0.001 | 5.33 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn16 | 1743 | 1000 | – | 1,672 |
| conn14 | 1761 | 1000 | – | 1,672 |
| conn18 | 1823 | 1000 | – | 1,399 |
| conn12 | 1773 | 1000 | – | 1,566 |
| conn10 | 1750 | 1000 | – | 734.4 |
| conn17 | 1744 | 1000 | – | 1,659 |
| conn8 | 1767 | 1000 | – | 1,616 |
| conn20 | 1724 | 1000 | – | 1,644 |
| conn27 | 1729 | 1000 | – | 1,649 |
| conn24 | 1759 | 1000 | – | 723.7 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
