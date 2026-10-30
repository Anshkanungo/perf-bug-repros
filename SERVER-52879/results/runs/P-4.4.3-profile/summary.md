# Run `P-4.4.3-profile`

- mongod **4.4.3** (`913d6b62acfb`), standalone, driver `shell`
- workload: 1000 colls × 10 indexes, 100 threads; setup 26.6 s; inserts 600.1 s; analysis window 120–599 s after insert start
- idle timeout 30 s → predicted spike period 40 s

| metric | value |
|---|---|
| inserts/s (window) | 947.8 |
| per-op latency p50 / p99 / p99.9 / max (ms) | 0.00 / 1.00 / 7.00 / 253.0 |
| per-second max latency: median (baseline) / p99.5 / max (ms) | 2.00 / 48.0 / 253.0 |
| spike threshold (ms) | 20.0 |
| spike events | 8 |
| spike peak latency, median (ms) | 33.5 |
| slow inserts per spike / threads hit, median | 20 / 20 |
| inter-spike interval median [IQR] (s) | 60.0 [40.1–75.1] |
| intervals within ±5 s of prediction | 0.43 |
| autocorrelation peak (lag s, r) | 40, 0.227 |
| server mean write latency per second: median / max (ms) | 0.172 / 5.46 |
| server histogram max per second: median / max (≤ ms) | 1.0 / 262.1 |
| WT open sessions min / median / max | 18 / 20 / 77 |
| WT cached cursors min / median / max | 71,452 / 84,392 / 118,382 |
| WT files open (max) / dhandles (max) | 12,014 / 36,025 |
| session-close sweeps seen (cached-cursor drops) | 10 (median drop 14190) |
| spikes coinciding with a sweep / sweeps coinciding with a spike | 6/8 / 6/10 |
| checkpoints during run | 9 |
| longest gap between serverStatus samples (s) | 1.02 |
| D2 (server mean/s ≥ 10× median 0.172 ms, floor 1 ms): threshold (ms) | 1.72 |
| D2 spike events / coinciding with D1 events | 3 / 3 |
| D2 peak server mean latency, median (ms) | 3.88 |
| D2 interval median [IQR] (s) | 185.5 [132.8–238.2] |
| *exploratory:* sweeps / max client latency in sweep intervals, median (ms) | 10 / 26.5 |
| *exploratory:* max client latency in non-sweep intervals, median (ms) | 2.0 |
| *exploratory:* share of intervals with max ≥ spike threshold: sweep / non-sweep | 0.60 / 0.006 |
| *exploratory:* share with max ≥ 10 ms: sweep / non-sweep | 0.90 / 0.019 |
| *exploratory:* cursors closed per sweep, median | 14190 |
| *exploratory:* interval between session-close sweeps, median (s) | 40.0 |
| spike events by coincidence (sweep / checkpoint start / other) | checkpoint start: 1, other: 1, sweep: 6 |
| mongod slow-query log: inserts > 100 ms / slowest (ms) | 9 / 252 |
| (other containers, summed): CPU % median / peak | 5 / 309 |
| s52879-analyze-76413: peak memory (MiB) / peak CPU (%) | 143 / 99 |
| s52879-client: peak memory (MiB) / peak CPU (%) | 1393 / 82 |
| s52879-mongod: peak memory (MiB) / peak CPU (%) | 1420 / 262 |
| s52879-prof: peak memory (MiB) / peak CPU (%) | 279 / 99 |
| s52879-sampler: peak memory (MiB) / peak CPU (%) | 22 / 0 |

Criteria: S1 (≥8 spike events) **True**, S2 (period 40±5 s) **False**

Spike events (s after insert start / peak ms / slow inserts / threads / coincides with):

184.9s/29ms/2/2/other, 222.3s/57ms/44/44/sweep, 302.3s/253ms/100/100/sweep, 342.6s/28ms/8/8/sweep, 412.6s/25ms/3/3/sweep, 472.6s/33ms/21/21/sweep, 512.7s/34ms/19/19/sweep, 592.8s/86ms/59/59/checkpoint start

Session-close sweeps (s) and max client latency in that 1 s interval (ms): 133s:13, 223s:57, 263s:11, 303s:253, 343s:28, 383s:9, 413s:25, 473s:33, 514s:34, 554s:12

Intervals (s): 37.3, 80.1, 40.2, 70.0, 60.0, 40.0, 80.2
