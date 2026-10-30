# Run `R3-4.4.1-W0`

- mongod **4.4.1** (`ad91a93a5a`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **13.24 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.17 / 2.14 / 4.76 s
- **stalled calls (≥ 3 s or never returned): 5** on 5 thread(s); longest call 4.76 s; stall type (exploratory): in-memory walk
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 13.00 / 13.24 s (straggler gap 0.24 s)
- history store reads missed: **1,000** (0% while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 71,845,405; search_near calls: 4,071,482; prefix-search early exits: –
- eviction: pages evicted by application threads 5,257, forced-eviction pages selected 344.0, pages read into cache 74.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 28.3 / 568.5 % (15 samples) → **NOISY**; w7264-mongod peak 1,212 %

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 10 | 1 | 0.647 | 4.76 | True |
| 7 | 0 | 0.625 | 4.74 | True |
| 16 | 0 | 0.671 | 4.74 | True |
| 15 | 0 | 0.68 | 4.65 | True |
| 6 | 0 | 0.797 | 4.53 | True |

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn23 | 1925 | 1000 | – | 0.0 |
| conn18 | 1052 | 1000 | – | 582.1 |
| conn26 | 1620 | 1000 | – | 1,150 |
| conn25 | 2091 | 1000 | – | 1,753 |
| conn17 | 1996 | 1000 | – | 875.8 |
| conn11 | 1952 | 1000 | – | 1,653 |
| conn20 | 1677 | 1000 | – | 1,492 |
| conn19 | 2027 | 1000 | – | 1,292 |
| conn12 | 1930 | 1000 | – | 1,573 |
| conn22 | 1969 | 1000 | – | 1,828 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
