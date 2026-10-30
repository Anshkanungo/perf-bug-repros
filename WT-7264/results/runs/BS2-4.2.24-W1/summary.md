# Run `BS2-4.2.24-W1`

- mongod **4.2.24** (`5e4ec1d244`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **9.66 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.10 / 4.27 / 5.10 s
- **stalled calls (≥ 3 s or never returned): 20** on 20 thread(s); longest call 5.10 s; stall type (exploratory): eviction
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 9.44 / 9.65 s (straggler gap 0.22 s)
- history store reads missed: **–** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): –; search_near calls: 4,000,015; prefix-search early exits: –
- eviction: pages evicted by application threads 150,659, forced-eviction pages selected 485.0, pages read into cache 45.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 42.9 / 582.0 % (11 samples) → **NOISY**; w7264-mongod peak 959.0 %

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 4 | 0 | 0.002 | 5.1 | True |
| 9 | 0 | 0.005 | 5.09 | True |
| 3 | 3 | 0.668 | 4.36 | True |
| 6 | 8 | 0.83 | 4.29 | True |
| 15 | 8 | 0.833 | 4.29 | True |
| 8 | 8 | 0.838 | 4.28 | True |
| 16 | 6 | 0.806 | 4.28 | True |
| 14 | 5 | 0.74 | 4.28 | True |
| 5 | 6 | 0.784 | 4.28 | True |
| 17 | 6 | 0.762 | 4.27 | True |
| 19 | 11 | 0.772 | 4.27 | True |
| 13 | 6 | 0.734 | 4.26 | True |
| 18 | 6 | 0.842 | 4.25 | True |
| 11 | 7 | 0.826 | 4.25 | True |
| 1 | 8 | 0.788 | 4.25 | True |
| 12 | 9 | 0.784 | 4.24 | True |
| 7 | 6 | 0.809 | 4.23 | True |
| 2 | 6 | 0.826 | 4.23 | True |
| 0 | 8 | 0.825 | 4.21 | True |
| 10 | 7 | 0.817 | 4.18 | True |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
