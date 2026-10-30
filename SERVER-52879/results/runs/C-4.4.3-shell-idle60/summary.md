# Run `C-4.4.3-shell-idle60`

- mongod **4.4.3** (`913d6b62acfb`), standalone, driver `shell`
- workload: 1000 colls × 10 indexes, 100 threads; setup 30.2 s; inserts 840.1 s; analysis window 120–839 s after insert start
- idle timeout 60 s → predicted spike period 70 s

| metric | value |
|---|---|
| inserts/s (window) | 945.3 |
| per-op latency p50 / p99 / p99.9 / max (ms) | 1.00 / 2.00 / 69.00 / 565.0 |
| per-second max latency: median (baseline) / p99.5 / max (ms) | 2.00 / 229.2 / 565.0 |
| spike threshold (ms) | 20.0 |
| spike events | 10 |
| spike peak latency, median (ms) | 160.5 |
| slow inserts per spike / threads hit, median | 100 / 100 |
| inter-spike interval median [IQR] (s) | 49.9 [18.2–68.5] |
| intervals within ±5 s of prediction | 0.33 |
| autocorrelation peak (lag s, r) | 70, 0.285 |
| server mean write latency per second: median / max (ms) | 0.195 / 137.15 |
| server histogram max per second: median / max (≤ ms) | 1.0 / 786.4 |
| WT open sessions min / median / max | 19 / 24 / 115 |
| WT cached cursors min / median / max | 73,359 / 120,209 / 290,441 |
| WT files open (max) / dhandles (max) | 12,014 / 36,025 |
| session-close sweeps seen (cached-cursor drops) | 6 (median drop 36022) |
| spikes coinciding with a sweep / sweeps coinciding with a spike | 4/10 / 4/6 |
| checkpoints during run | 12 |
| longest gap between serverStatus samples (s) | 1.05 |
| D2 (server mean/s ≥ 10× median 0.195 ms, floor 1 ms): threshold (ms) | 1.95 |
| D2 spike events / coinciding with D1 events | 7 / 7 |
| D2 peak server mean latency, median (ms) | 20.63 |
| D2 interval median [IQR] (s) | 62.0 [22.2–66.5] |
| *exploratory:* sweeps / max client latency in sweep intervals, median (ms) | 6 / 65.0 |
| *exploratory:* max client latency in non-sweep intervals, median (ms) | 2.0 |
| *exploratory:* share of intervals with max ≥ spike threshold: sweep / non-sweep | 0.67 / 0.020 |
| *exploratory:* share with max ≥ 10 ms: sweep / non-sweep | 1.00 / 0.032 |
| *exploratory:* cursors closed per sweep, median | 36022 |
| *exploratory:* interval between session-close sweeps, median (s) | 70.9 |
| spike events by coincidence (sweep / checkpoint start / other) | checkpoint start: 4, other: 2, sweep: 4 |
| mongod slow-query log: inserts > 100 ms / slowest (ms) | 572 / 560 |
| (other containers, summed): CPU % median / peak | 4 / 348 |
| s52879-client: peak memory (MiB) / peak CPU (%) | 1382 / 94 |
| s52879-mongod: peak memory (MiB) / peak CPU (%) | 1630 / 310 |
| s52879-offcheck: peak memory (MiB) / peak CPU (%) | 1035 / 100 |
| s52879-reanalyze-77589: peak memory (MiB) / peak CPU (%) | 10 / 98 |
| s52879-reanalyze-77839: peak memory (MiB) / peak CPU (%) | 43 / 99 |
| s52879-reanalyze-78370: peak memory (MiB) / peak CPU (%) | 53 / 99 |
| s52879-rep: peak memory (MiB) / peak CPU (%) | 112 / 42 |
| s52879-sampler: peak memory (MiB) / peak CPU (%) | 22 / 1 |

Criteria: S1 (≥8 spike events) **True**, S2 (period 70±5 s) **False**

Spike events (s after insert start / peak ms / slow inserts / threads / coincides with):

399.6s/116ms/48/45/other, 468.5s/90ms/69/69/sweep, 538.7s/40ms/19/19/sweep, 588.6s/267ms/116/100/checkpoint start, 657.1s/565ms/203/100/checkpoint start, 718.7s/203ms/100/100/sweep, 726.5s/431ms/101/100/checkpoint start, 770.7s/102ms/82/66/other, 788.9s/118ms/100/100/sweep, 797.6s/421ms/100/100/checkpoint start

Session-close sweeps (s) and max client latency in that 1 s interval (ms): 199s:19, 469s:90, 529s:16, 539s:40, 719s:203, 790s:118

Intervals (s): 69.0, 70.1, 50.0, 68.5, 61.6, 7.8, 44.2, 18.2, 8.7
