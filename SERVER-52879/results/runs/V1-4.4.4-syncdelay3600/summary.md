# Run `V1-4.4.4-syncdelay3600`

- mongod **4.4.4** (`8db30a63db1a`), standalone, driver `shell`
- workload: 1000 colls × 10 indexes, 100 threads; setup 29.5 s; inserts 720.1 s; analysis window 120–719 s after insert start
- idle timeout 30 s → predicted spike period 40 s

| metric | value |
|---|---|
| inserts/s (window) | 947.8 |
| per-op latency p50 / p99 / p99.9 / max (ms) | 1.00 / 1.00 / 5.00 / 51.0 |
| per-second max latency: median (baseline) / p99.5 / max (ms) | 2.00 / 24.1 / 51.0 |
| spike threshold (ms) | 20.0 |
| spike events | 2 |
| spike peak latency, median (ms) | 41.5 |
| slow inserts per spike / threads hit, median | 8 / 8 |
| inter-spike interval median [IQR] (s) | 445.0 [445.0–445.0] |
| intervals within ±5 s of prediction | 0.00 |
| autocorrelation peak (lag s, r) | 35, 0.365 |
| server mean write latency per second: median / max (ms) | 0.181 / 0.69 |
| server histogram max per second: median / max (≤ ms) | 1.0 / 49.2 |
| WT open sessions min / median / max | 17 / 19 / 29 |
| WT cached cursors min / median / max | 59,785 / 76,424 / 142,874 |
| WT files open (max) / dhandles (max) | 12,014 / 24,021 |
| session-close sweeps seen (cached-cursor drops) | 6 (median drop 11990) |
| spikes coinciding with a sweep / sweeps coinciding with a spike | 0/2 / 0/6 |
| checkpoints during run | 0 |
| longest gap between serverStatus samples (s) | 1.01 |
| D2 (server mean/s ≥ 10× median 0.181 ms, floor 1 ms): threshold (ms) | 1.81 |
| D2 spike events / coinciding with D1 events | 0 / 0 |
| D2 peak server mean latency, median (ms) | – |
| D2 interval median [IQR] (s) | – [–––] |
| *exploratory:* sweeps / max client latency in sweep intervals, median (ms) | 6 / 2.0 |
| *exploratory:* max client latency in non-sweep intervals, median (ms) | 2.0 |
| *exploratory:* share of intervals with max ≥ spike threshold: sweep / non-sweep | 0.00 / 0.005 |
| *exploratory:* share with max ≥ 10 ms: sweep / non-sweep | 0.00 / 0.015 |
| *exploratory:* cursors closed per sweep, median | 11990 |
| *exploratory:* interval between session-close sweeps, median (s) | 60.0 |
| spike events by coincidence (sweep / checkpoint start / other) | other: 2 |
| mongod slow-query log: inserts > 100 ms / slowest (ms) | 0 / 0 |
| (other containers, summed): CPU % median / peak | 5 / 299 |
| s52879-client: peak memory (MiB) / peak CPU (%) | 1393 / 371 |
| s52879-mongod: peak memory (MiB) / peak CPU (%) | 1329 / 161 |
| s52879-sampler: peak memory (MiB) / peak CPU (%) | 22 / 1 |

Criteria: S1 (≥8 spike events) **False**, S2 (period 40±5 s) **False**

Spike events (s after insert start / peak ms / slow inserts / threads / coincides with):

185.8s/51ms/14/14/other, 630.9s/32ms/1/1/other

Session-close sweeps (s) and max client latency in that 1 s interval (ms): 180s:1, 220s:2, 280s:6, 430s:1, 610s:2, 620s:2

Intervals (s): 445.0
