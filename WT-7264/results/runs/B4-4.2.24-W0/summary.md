# Run `B4-4.2.24-W0`

- mongod **4.2.24** (`5e4ec1d244`), workload `bruce`, `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **10.51 s**; 1000/1000 insertMany calls returned; 1,785,960 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.10 / 5.07 / 6.02 s
- **stalled calls (≥ 3 s or never returned): 20** on 20 thread(s); longest call 6.02 s; stall type (exploratory): eviction
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 10.35 / 10.50 s (straggler gap 0.15 s)
- history store reads missed: **–** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): –; search_near calls: 3,570,870; prefix-search early exits: –
- eviction: pages evicted by application threads 210,108, forced-eviction pages selected 521.0, pages read into cache 52.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 9.6 / 31.6 % (11 samples) → not noisy; w7264-mongod peak 1,023 %

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 5 | 1 | 0.094 | 6.02 | True |
| 9 | 0 | 0.085 | 5.99 | True |
| 13 | 6 | 0.915 | 5.14 | True |
| 7 | 8 | 0.924 | 5.12 | True |
| 2 | 8 | 0.941 | 5.1 | True |
| 3 | 6 | 0.937 | 5.1 | True |
| 12 | 5 | 0.899 | 5.09 | True |
| 1 | 7 | 0.923 | 5.09 | True |
| 10 | 9 | 0.931 | 5.08 | True |
| 0 | 6 | 0.999 | 5.07 | True |
| 8 | 3 | 0.97 | 5.07 | True |
| 18 | 8 | 0.969 | 5.07 | True |
| 14 | 6 | 0.965 | 5.07 | True |
| 6 | 6 | 1.019 | 5.06 | True |
| 16 | 5 | 0.936 | 5.06 | True |
| 19 | 8 | 1.036 | 5.04 | True |
| 17 | 7 | 1.024 | 5.04 | True |
| 11 | 6 | 0.956 | 5.04 | True |
| 15 | 6 | 0.966 | 5.03 | True |
| 4 | 9 | 1.017 | 5.03 | True |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
