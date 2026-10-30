# Run `RS3-4.4.1-W1`

- mongod **4.4.1** (`ad91a93a5a`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **10.33 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.15 / 2.13 / 2.99 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 2.99 s; stall type (exploratory): none
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 10.13 / 10.33 s (straggler gap 0.20 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 102,481,568; search_near calls: 4,057,928; prefix-search early exits: –
- eviction: pages evicted by application threads 5,423, forced-eviction pages selected 601.0, pages read into cache 184.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 10.0 / 17.1 % (12 samples) → not noisy; w7264-mongod peak 1,032 %

mongod slow-query log, insert commands ≥ 1 s:

| conn | ms | docs | bytes read | cache wait (ms) |
|---|---|---|---|---|
| conn13 | 1996 | 1000 | – | 1,919 |
| conn9 | 2017 | 1000 | 18,725 | 1,915 |
| conn17 | 1971 | 1000 | 14,164 | 1,901 |
| conn18 | 2047 | 1000 | – | 1,858 |
| conn16 | 1979 | 1000 | 3,664 | 1,771 |
| conn19 | 2047 | 1000 | – | 1,889 |
| conn11 | 1895 | 1000 | – | 1,836 |
| conn24 | 2045 | 1000 | – | 1,127 |
| conn12 | 2024 | 1000 | – | 1,883 |
| conn8 | 2052 | 1000 | – | 1,897 |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
