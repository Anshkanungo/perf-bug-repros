# Run `C2-5.0.33-W1-off-nonunique`

- mongod **5.0.33** (`20315d70b9`), workload `bruce` (sync start) (NON-unique control), `wiredTigerPrefixSearchForUniqueIndexes` = False, WT cache 1 GB
- insert phase: **3.08 s**; 1000/1000 insertMany calls returned; 2,000,000 docs inserted (server)
- call latency p50 / p99 / max (returned calls): 0.06 / 0.11 / 0.16 s
- **stalled calls (≥ 3 s or never returned): 0** on 0 thread(s); longest call 0.16 s; stall type (exploratory): none
- host power: Battery Power → Battery Power (battery = Low Power Mode on this laptop)
- thread finish time median / last: 2.97 / 3.07 s (straggler gap 0.10 s)
- history store reads missed: **0.0** (– while a call had been running ≥ 3 s); cursor entries skipped (next+prev): 0; search_near calls: 0.0; prefix-search early exits: 0.0
- eviction: pages evicted by application threads 17.0, forced-eviction pages selected 527.0, pages read into cache 20.0
- checkpoints: {'checkpoints_completed': 0.0, 'seconds_with_checkpoint_running': 0, 'checkpoint_running_during_stalls': False, 'last_checkpoint_ms_max': 0.0}
- noise: other containers' CPU median / peak 12.2 / 18.0 % (5 samples) → not noisy; w7264-mongod peak 722.0 %

Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).
