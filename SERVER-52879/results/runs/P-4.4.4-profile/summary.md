# Run `P-4.4.4-profile`

- mongod **4.4.4** (`8db30a63db1a`), standalone, driver `shell`
- workload: 1000 colls × 10 indexes, 100 threads; setup 29.8 s; inserts 600.1 s; analysis window 120–599 s after insert start
- idle timeout 30 s → predicted spike period 40 s

| metric | value |
|---|---|
| inserts/s (window) | 947.4 |
| per-op latency p50 / p99 / p99.9 / max (ms) | 1.00 / 2.00 / 12.00 / 230.0 |
| per-second max latency: median (baseline) / p99.5 / max (ms) | 2.00 / 71.7 / 230.0 |
| spike threshold (ms) | 20.0 |
| spike events | 10 |
| spike peak latency, median (ms) | 45.5 |
| slow inserts per spike / threads hit, median | 12 / 12 |
| inter-spike interval median [IQR] (s) | 18.3 [5.9–97.4] |
| intervals within ±5 s of prediction | 0.00 |
| autocorrelation peak (lag s, r) | 36, 0.2 |
| server mean write latency per second: median / max (ms) | 0.181 / 3.18 |
| server histogram max per second: median / max (≤ ms) | 1.0 / 98.3 |
| WT open sessions min / median / max | 17 / 19 / 70 |
| WT cached cursors min / median / max | 60,174 / 83,963 / 306,864 |
| WT files open (max) / dhandles (max) | 12,014 / 36,025 |
| session-close sweeps seen (cached-cursor drops) | 10 (median drop 18001) |
| spikes coinciding with a sweep / sweeps coinciding with a spike | 2/10 / 2/10 |
| checkpoints during run | 8 |
| longest gap between serverStatus samples (s) | 1.05 |
| D2 (server mean/s ≥ 10× median 0.181 ms, floor 1 ms): threshold (ms) | 1.81 |
| D2 spike events / coinciding with D1 events | 1 / 1 |
| D2 peak server mean latency, median (ms) | 3.18 |
| D2 interval median [IQR] (s) | – [–––] |
| *exploratory:* sweeps / max client latency in sweep intervals, median (ms) | 10 / 2.0 |
| *exploratory:* max client latency in non-sweep intervals, median (ms) | 2.0 |
| *exploratory:* share of intervals with max ≥ spike threshold: sweep / non-sweep | 0.10 / 0.030 |
| *exploratory:* share with max ≥ 10 ms: sweep / non-sweep | 0.10 / 0.049 |
| *exploratory:* cursors closed per sweep, median | 18001 |
| *exploratory:* interval between session-close sweeps, median (s) | 40.0 |
| spike events by coincidence (sweep / checkpoint start / other) | checkpoint start: 1, other: 7, sweep: 2 |
| mongod slow-query log: inserts > 100 ms / slowest (ms) | 0 / 0 |
| (other containers, summed): CPU % median / peak | 5 / 148 |
| s52879-analyze-81680: peak memory (MiB) / peak CPU (%) | 151 / 97 |
| s52879-client: peak memory (MiB) / peak CPU (%) | 1380 / 360 |
| s52879-mongod: peak memory (MiB) / peak CPU (%) | 1537 / 197 |
| s52879-prof: peak memory (MiB) / peak CPU (%) | 309 / 104 |
| s52879-sampler: peak memory (MiB) / peak CPU (%) | 22 / 0 |

Criteria: S1 (≥8 spike events) **True**, S2 (period 40±5 s) **False**

Spike events (s after insert start / peak ms / slow inserts / threads / coincides with):

231.5s/34ms/2/2/sweep, 339.1s/230ms/100/100/sweep, 436.5s/20ms/3/3/other, 440.1s/60ms/12/12/other, 450.8s/22ms/1/1/other, 456.7s/76ms/11/11/checkpoint start, 474.9s/44ms/5/5/other, 477.0s/47ms/24/24/other, 495.8s/41ms/14/14/other, 598.0s/112ms/93/76/other

Session-close sweeps (s) and max client latency in that 1 s interval (ms): 180s:2, 230s:2, 270s:2, 340s:230, 370s:8, 410s:2, 510s:2, 530s:6, 531s:1, 571s:1

Intervals (s): 107.6, 97.4, 3.6, 10.8, 5.8, 18.3, 2.1, 18.8, 102.2
