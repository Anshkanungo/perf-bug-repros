# Run `C2-4.4.3-idle60-syncdelay3600`

- mongod **4.4.3** (`913d6b62acfb`), standalone, driver `shell`
- workload: 1000 colls × 10 indexes, 100 threads; setup 33.7 s; inserts 840.1 s; analysis window 120–839 s after insert start
- idle timeout 60 s → predicted spike period 70 s

| metric | value |
|---|---|
| inserts/s (window) | 947.2 |
| per-op latency p50 / p99 / p99.9 / max (ms) | 1.00 / 2.00 / 17.00 / 304.0 |
| per-second max latency: median (baseline) / p99.5 / max (ms) | 2.00 / 56.5 / 304.0 |
| spike threshold (ms) | 20.0 |
| spike events | 19 |
| spike peak latency, median (ms) | 44.0 |
| slow inserts per spike / threads hit, median | 23 / 22 |
| inter-spike interval median [IQR] (s) | 32.3 [17.8–66.8] |
| intervals within ±5 s of prediction | 0.33 |
| autocorrelation peak (lag s, r) | 70, 0.275 |
| server mean write latency per second: median / max (ms) | 0.204 / 37.62 |
| server histogram max per second: median / max (≤ ms) | 2.0 / 393.2 |
| WT open sessions min / median / max | 20 / 27 / 55 |
| WT cached cursors min / median / max | 74,672 / 138,238 / 237,241 |
| WT files open (max) / dhandles (max) | 12,015 / 24,021 |
| session-close sweeps seen (cached-cursor drops) | 11 (median drop 46234) |
| spikes coinciding with a sweep / sweeps coinciding with a spike | 10/19 / 10/11 |
| checkpoints during run | 0 |
| longest gap between serverStatus samples (s) | 1.14 |
| D2 (server mean/s ≥ 10× median 0.204 ms, floor 1 ms): threshold (ms) | 2.04 |
| D2 spike events / coinciding with D1 events | 4 / 4 |
| D2 peak server mean latency, median (ms) | 6.25 |
| D2 interval median [IQR] (s) | 240.0 [154.0–251.0] |
| *exploratory:* sweeps / max client latency in sweep intervals, median (ms) | 11 / 48.0 |
| *exploratory:* max client latency in non-sweep intervals, median (ms) | 2.0 |
| *exploratory:* share of intervals with max ≥ spike threshold: sweep / non-sweep | 0.91 / 0.018 |
| *exploratory:* share with max ≥ 10 ms: sweep / non-sweep | 1.00 / 0.042 |
| *exploratory:* cursors closed per sweep, median | 46234 |
| *exploratory:* interval between session-close sweeps, median (s) | 70.0 |
| spike events by coincidence (sweep / checkpoint start / other) | other: 9, sweep: 10 |
| mongod slow-query log: inserts > 100 ms / slowest (ms) | 126 / 302 |
| (other containers, summed): CPU % median / peak | 5 / 235 |
| s52879-client: peak memory (MiB) / peak CPU (%) | 1382 / 237 |
| s52879-mongod: peak memory (MiB) / peak CPU (%) | 1364 / 138 |
| s52879-reanalyze-82720: peak memory (MiB) / peak CPU (%) | 45 / 98 |
| s52879-reanalyze-82801: peak memory (MiB) / peak CPU (%) | 40 / 100 |
| s52879-sampler: peak memory (MiB) / peak CPU (%) | 22 / 2 |

Criteria: S1 (≥8 spike events) **True**, S2 (period 70±5 s) **False**

Spike events (s after insert start / peak ms / slow inserts / threads / coincides with):

154.7s/304ms/100/100/sweep, 158.7s/42ms/32/32/other, 175.0s/41ms/23/20/other, 225.0s/38ms/22/22/sweep, 245.1s/52ms/39/39/sweep, 315.1s/51ms/20/20/sweep, 385.2s/48ms/33/33/sweep, 416.6s/96ms/87/73/other, 485.2s/138ms/100/100/sweep, 555.4s/47ms/30/30/sweep, 588.5s/50ms/14/14/other, 655.4s/26ms/4/4/sweep, 659.2s/44ms/26/26/other, 725.5s/63ms/55/55/sweep, 751.7s/40ms/5/5/other, 785.5s/37ms/17/17/sweep, 802.5s/29ms/5/5/other, 807.1s/30ms/3/3/other, 832.2s/44ms/13/13/other

Session-close sweeps (s) and max client latency in that 1 s interval (ms): 156s:304, 226s:38, 246s:52, 316s:51, 386s:48, 486s:138, 556s:47, 656s:26, 726s:63, 786s:37, 816s:11

Intervals (s): 4.0, 16.2, 50.1, 20.0, 70.0, 70.1, 31.4, 68.6, 70.1, 33.1, 66.9, 3.7, 66.3, 26.2, 33.8, 17.0, 4.6, 25.0
