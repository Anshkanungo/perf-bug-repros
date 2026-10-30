# Run `A-4.4.3-shell-idle30`

- mongod **4.4.3** (`913d6b62acfb`), standalone, driver `shell`
- workload: 1000 colls × 10 indexes, 100 threads; setup 28.3 s; inserts 720.1 s; analysis window 120–719 s after insert start
- idle timeout 30 s → predicted spike period 40 s

| metric | value |
|---|---|
| inserts/s (window) | 947.1 |
| per-op latency p50 / p99 / p99.9 / max (ms) | 1.00 / 1.00 / 9.00 / 365.0 |
| per-second max latency: median (baseline) / p99.5 / max (ms) | 2.00 / 81.4 / 365.0 |
| spike threshold (ms) | 20.0 |
| spike events | 14 |
| spike peak latency, median (ms) | 36.5 |
| slow inserts per spike / threads hit, median | 14 / 14 |
| inter-spike interval median [IQR] (s) | 40.0 [36.5–50.0] |
| intervals within ±5 s of prediction | 0.38 |
| autocorrelation peak (lag s, r) | 35, 0.169 |
| server mean write latency per second: median / max (ms) | 0.191 / 46.86 |
| server histogram max per second: median / max (≤ ms) | 2.0 / 393.2 |
| WT open sessions min / median / max | 19 / 21 / 113 |
| WT cached cursors min / median / max | 73,046 / 96,066 / 164,323 |
| WT files open (max) / dhandles (max) | 12,014 / 36,025 |
| session-close sweeps seen (cached-cursor drops) | 14 (median drop 15738) |
| spikes coinciding with a sweep / sweeps coinciding with a spike | 11/14 / 10/14 |
| checkpoints during run | 10 |
| longest gap between serverStatus samples (s) | 1.02 |
| D2 (server mean/s ≥ 10× median 0.191 ms, floor 1 ms): threshold (ms) | 1.91 |
| D2 spike events / coinciding with D1 events | 3 / 3 |
| D2 peak server mean latency, median (ms) | 4.25 |
| D2 interval median [IQR] (s) | 36.0 [34.0–38.0] |
| *exploratory:* sweeps / max client latency in sweep intervals, median (ms) | 14 / 29.0 |
| *exploratory:* max client latency in non-sweep intervals, median (ms) | 2.0 |
| *exploratory:* share of intervals with max ≥ spike threshold: sweep / non-sweep | 0.71 / 0.009 |
| *exploratory:* share with max ≥ 10 ms: sweep / non-sweep | 1.00 / 0.032 |
| *exploratory:* cursors closed per sweep, median | 15738 |
| *exploratory:* interval between session-close sweeps, median (s) | 40.0 |
| spike events by coincidence (sweep / checkpoint start / other) | checkpoint start: 1, other: 2, sweep: 8, sweep+checkpoint: 3 |
| mongod slow-query log: inserts > 100 ms / slowest (ms) | 101 / 362 |
| (other containers, summed): CPU % median / peak | 5 / 325 |
| s52879-client: peak memory (MiB) / peak CPU (%) | 1382 / 61 |
| s52879-mongod: peak memory (MiB) / peak CPU (%) | 1444 / 243 |
| s52879-sampler: peak memory (MiB) / peak CPU (%) | 22 / 0 |

Criteria: S1 (≥8 spike events) **True**, S2 (period 40±5 s) **False**

Spike events (s after insert start / peak ms / slow inserts / threads / coincides with):

130.5s/52ms/30/30/sweep, 210.6s/25ms/4/4/sweep, 273.8s/32ms/3/3/other, 320.6s/39ms/25/25/sweep, 360.7s/31ms/11/11/sweep, 410.7s/28ms/8/8/sweep, 450.7s/21ms/1/1/sweep+checkpoint, 490.8s/34ms/17/17/sweep, 598.8s/365ms/101/100/checkpoint start, 630.8s/64ms/49/49/sweep, 634.4s/78ms/38/34/other, 670.9s/81ms/66/66/sweep+checkpoint, 673.4s/117ms/1/1/sweep+checkpoint, 711.0s/30ms/8/8/sweep

Session-close sweeps (s) and max client latency in that 1 s interval (ms): 132s:52, 212s:25, 252s:13, 322s:39, 362s:31, 402s:11, 412s:28, 452s:21, 492s:34, 532s:15, 572s:12, 632s:64, 672s:81, 712s:30

Intervals (s): 80.1, 63.2, 46.8, 40.0, 50.0, 40.0, 40.0, 108.0, 32.1, 3.6, 36.5, 2.5, 37.6
