# Run `smoke-433-shell`

- mongod **4.4.3** (`913d6b62acfb`), standalone, driver `shell`
- workload: 100 colls × 10 indexes, 20 threads; setup 3.1 s; inserts 90.1 s; analysis window 20–89 s after insert start
- idle timeout 10 s → predicted spike period 20 s

| metric | value |
|---|---|
| inserts/s (window) | 185.7 |
| per-op latency p50 / p99 / p99.9 / max (ms) | 1.00 / 5.00 / 12.19 / 22.0 |
| per-second max latency: median (baseline) / p99.5 / max (ms) | 7.00 / 20.0 / 22.0 |
| spike threshold (ms) | 70.0 |
| spike events | 0 |
| spike peak latency, median (ms) | – |
| slow inserts per spike / threads hit, median | – / – |
| inter-spike interval median [IQR] (s) | – [–––] |
| intervals within ±5 s of prediction | – |
| autocorrelation peak (lag s, r) | 18, 0.254 |
| server mean write latency per second: median / max (ms) | 0.221 / 0.40 |
| server histogram max per second: median / max (≤ ms) | 2.0 / 24.6 |
| WT open sessions min / median / max | 19 / 19 / 21 |
| WT cached cursors min / median / max | 8,338 / 8,483 / 10,652 |
| WT files open (max) / dhandles (max) | 1,214 / 2,421 |
| session-close sweeps seen (cached-cursor drops) | 2 (median drop 1757) |
| spikes coinciding with a sweep / sweeps coinciding with a spike | 0/0 / 0/2 |
| checkpoints during run | 1 |
| longest gap between serverStatus samples (s) | 1.01 |
| D2 (server mean/s ≥ 10× median 0.221 ms, floor 1 ms): threshold (ms) | 2.21 |
| D2 spike events / coinciding with D1 events | 0 / 0 |
| D2 peak server mean latency, median (ms) | – |
| D2 interval median [IQR] (s) | – [–––] |
| *exploratory:* sweeps / max client latency in sweep intervals, median (ms) | 2 / 8.0 |
| *exploratory:* max client latency in non-sweep intervals, median (ms) | 6.0 |
| *exploratory:* share of intervals with max ≥ spike threshold: sweep / non-sweep | 0.00 / 0.000 |
| *exploratory:* share with max ≥ 10 ms: sweep / non-sweep | 0.50 / 0.258 |
| *exploratory:* cursors closed per sweep, median | 1757 |
| *exploratory:* interval between session-close sweeps, median (s) | 60.0 |
| mongod slow-query log: inserts > 100 ms / slowest (ms) | 0 / 0 |
| s52879-client: peak memory (MiB) / peak CPU (%) | 263 / 28 |
| s52879-mongod: peak memory (MiB) / peak CPU (%) | 200 / 12 |
| s52879-sampler: peak memory (MiB) / peak CPU (%) | 21 / 0 |

Criteria: S1 (≥8 spike events) **False**, S2 (period 20±5 s) **False**

Session-close sweeps (s) and max client latency in that 1 s interval (ms): 26s:6, 86s:10
