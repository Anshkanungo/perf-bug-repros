# Run `BS3-4.2.24-W1`

- mongod **4.2.24** (`5e4ec1d244`), workload `bruce` (sync start), `wiredTigerPrefixSearchForUniqueIndexes` = absent, WT cache 1 GB
- insert phase: **11.64 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.10 / 6.45 / 7.21 s
- **stalled calls (≥ 3 s or never returned): 20** on 20 thread(s); longest call 7.21 s; stall type (exploratory): eviction
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 11.43 / 11.64 s (straggler gap 0.21 s)
- history store reads missed: **–** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): –; search_near calls: 4,000,011; prefix-search early exits: –
- eviction: pages evicted by application threads 257,148, forced-eviction pages selected 638.0, pages read into cache 42.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 9.7 / 108.9 % (14 samples) → not noisy; w7264-mongod peak 971.1 %

| client thread | batch | start (s) | duration (s) | returned |
|---|---|---|---|---|
| 6 | 0 | 0.001 | 7.21 | True |
| 5 | 0 | 0.002 | 7.18 | True |
| 2 | 6 | 0.768 | 6.5 | True |
| 0 | 8 | 0.642 | 6.48 | True |
| 10 | 6 | 0.722 | 6.46 | True |
| 11 | 7 | 0.713 | 6.46 | True |
| 18 | 6 | 0.653 | 6.46 | True |
| 14 | 7 | 0.772 | 6.46 | True |
| 12 | 5 | 0.674 | 6.45 | True |
| 19 | 9 | 0.736 | 6.45 | True |
| 7 | 5 | 0.728 | 6.45 | True |
| 1 | 7 | 0.757 | 6.44 | True |
| 9 | 7 | 0.706 | 6.43 | True |
| 16 | 6 | 0.686 | 6.43 | True |
| 13 | 7 | 0.758 | 6.42 | True |
| 8 | 7 | 0.768 | 6.42 | True |
| 15 | 8 | 0.773 | 6.42 | True |
| 17 | 8 | 0.757 | 6.42 | True |
| 3 | 8 | 0.732 | 6.4 | True |
| 4 | 7 | 0.831 | 6.37 | True |

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
