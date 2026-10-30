# Run `V1-4.4.3-syncdelay3600`

- mongod **4.4.3** (`913d6b62acfb`), standalone, driver `shell`
- workload: 1000 colls × 10 indexes, 100 threads; setup 31.4 s; inserts 720.1 s; analysis window 120–719 s after insert start
- idle timeout 30 s → predicted spike period 40 s

| metric | value |
|---|---|
| inserts/s (window) | 945.5 |
| per-op latency p50 / p99 / p99.9 / max (ms) | 1.00 / 2.00 / 26.00 / 726.0 |
| per-second max latency: median (baseline) / p99.5 / max (ms) | 2.00 / 118.3 / 726.0 |
| spike threshold (ms) | 20.0 |
| spike events | 13 |
| spike peak latency, median (ms) | 58.0 |
| slow inserts per spike / threads hit, median | 36 / 36 |
| inter-spike interval median [IQR] (s) | 40.1 [32.9–42.8] |
| intervals within ±5 s of prediction | 0.42 |
| autocorrelation peak (lag s, r) | 40, 0.237 |
| server mean write latency per second: median / max (ms) | 0.192 / 78.38 |
| server histogram max per second: median / max (≤ ms) | 2.0 / 786.4 |
| WT open sessions min / median / max | 19 / 22 / 75 |
| WT cached cursors min / median / max | 75,966 / 106,011 / 180,959 |
| WT files open (max) / dhandles (max) | 12,014 / 24,021 |
| session-close sweeps seen (cached-cursor drops) | 14 (median drop 28830) |
| spikes coinciding with a sweep / sweeps coinciding with a spike | 10/13 / 10/14 |
| checkpoints during run | 0 |
| longest gap between serverStatus samples (s) | 1.02 |
| D2 (server mean/s ≥ 10× median 0.192 ms, floor 1 ms): threshold (ms) | 1.92 |
| D2 spike events / coinciding with D1 events | 5 / 5 |
| D2 peak server mean latency, median (ms) | 6.95 |
| D2 interval median [IQR] (s) | 40.0 [39.7–52.7] |
| *exploratory:* sweeps / max client latency in sweep intervals, median (ms) | 14 / 31.0 |
| *exploratory:* max client latency in non-sweep intervals, median (ms) | 2.0 |
| *exploratory:* share of intervals with max ≥ spike threshold: sweep / non-sweep | 0.71 / 0.010 |
| *exploratory:* share with max ≥ 10 ms: sweep / non-sweep | 1.00 / 0.021 |
| *exploratory:* cursors closed per sweep, median | 28830 |
| *exploratory:* interval between session-close sweeps, median (s) | 40.0 |
| spike events by coincidence (sweep / checkpoint start / other) | other: 3, sweep: 10 |
| mongod slow-query log: inserts > 100 ms / slowest (ms) | 70 / 643 |
| (other containers, summed): CPU % median / peak | 5 / 301 |
| s52879-client: peak memory (MiB) / peak CPU (%) | 1374 / 88 |
| s52879-mongod: peak memory (MiB) / peak CPU (%) | 1320 / 118 |
| s52879-sampler: peak memory (MiB) / peak CPU (%) | 22 / 1 |

Criteria: S1 (≥8 spike events) **True**, S2 (period 40±5 s) **False**

Spike events (s after insert start / peak ms / slow inserts / threads / coincides with):

137.3s/58ms/29/29/sweep, 177.4s/53ms/41/41/sweep, 317.5s/21ms/3/3/sweep, 344.7s/74ms/36/36/other, 377.5s/118ms/99/99/sweep, 417.6s/70ms/49/49/sweep, 457.7s/29ms/11/11/sweep, 508.7s/726ms/186/97/other, 547.7s/109ms/91/90/sweep, 554.9s/23ms/2/2/other, 587.8s/106ms/91/91/sweep, 628.0s/33ms/16/16/sweep, 718.0s/23ms/6/6/sweep

Session-close sweeps (s) and max client latency in that 1 s interval (ms): 137s:58, 177s:53, 208s:11, 218s:10, 318s:21, 378s:118, 418s:70, 458s:29, 498s:10, 548s:109, 588s:106, 628s:33, 688s:13, 718s:23

Intervals (s): 40.1, 140.1, 27.2, 32.8, 40.1, 40.1, 51.0, 39.1, 7.1, 33.0, 40.1, 90.0
