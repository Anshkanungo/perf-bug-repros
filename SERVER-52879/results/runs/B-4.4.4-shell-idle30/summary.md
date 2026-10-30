# Run `B-4.4.4-shell-idle30`

- mongod **4.4.4** (`8db30a63db1a`), standalone, driver `shell`
- workload: 1000 colls × 10 indexes, 100 threads; setup 29.1 s; inserts 720.1 s; analysis window 120–719 s after insert start
- idle timeout 30 s → predicted spike period 40 s

| metric | value |
|---|---|
| inserts/s (window) | 943.8 |
| per-op latency p50 / p99 / p99.9 / max (ms) | 1.00 / 5.00 / 65.00 / 556.0 |
| per-second max latency: median (baseline) / p99.5 / max (ms) | 2.00 / 199.0 / 556.0 |
| spike threshold (ms) | 20.0 |
| spike events | 13 |
| spike peak latency, median (ms) | 76.0 |
| slow inserts per spike / threads hit, median | 14 / 14 |
| inter-spike interval median [IQR] (s) | 24.7 [16.0–45.8] |
| intervals within ±5 s of prediction | 0.08 |
| autocorrelation peak (lag s, r) | 11, 0.234 |
| server mean write latency per second: median / max (ms) | 0.190 / 49.69 |
| server histogram max per second: median / max (≤ ms) | 1.0 / 524.3 |
| WT open sessions min / median / max | 17 / 19 / 115 |
| WT cached cursors min / median / max | 60,642 / 83,960 / 325,715 |
| WT files open (max) / dhandles (max) | 12,014 / 36,025 |
| session-close sweeps seen (cached-cursor drops) | 11 (median drop 24345) |
| spikes coinciding with a sweep / sweeps coinciding with a spike | 2/13 / 2/11 |
| checkpoints during run | 10 |
| longest gap between serverStatus samples (s) | 1.16 |
| D2 (server mean/s ≥ 10× median 0.190 ms, floor 1 ms): threshold (ms) | 1.90 |
| D2 spike events / coinciding with D1 events | 8 / 6 |
| D2 peak server mean latency, median (ms) | 4.11 |
| D2 interval median [IQR] (s) | 17.0 [7.5–47.0] |
| *exploratory:* sweeps / max client latency in sweep intervals, median (ms) | 11 / 2.0 |
| *exploratory:* max client latency in non-sweep intervals, median (ms) | 2.0 |
| *exploratory:* share of intervals with max ≥ spike threshold: sweep / non-sweep | 0.00 / 0.053 |
| *exploratory:* share with max ≥ 10 ms: sweep / non-sweep | 0.00 / 0.085 |
| *exploratory:* cursors closed per sweep, median | 24345 |
| *exploratory:* interval between session-close sweeps, median (s) | 45.0 |
| spike events by coincidence (sweep / checkpoint start / other) | checkpoint start: 3, other: 8, sweep: 2 |
| mongod slow-query log: inserts > 100 ms / slowest (ms) | 125 / 458 |
| (other containers, summed): CPU % median / peak | 5 / 327 |
| s52879-client: peak memory (MiB) / peak CPU (%) | 1402 / 600 |
| s52879-mongod: peak memory (MiB) / peak CPU (%) | 1717 / 280 |
| s52879-sampler: peak memory (MiB) / peak CPU (%) | 22 / 3 |

Criteria: S1 (≥8 spike events) **True**, S2 (period 40±5 s) **False**

Spike events (s after insert start / peak ms / slow inserts / threads / coincides with):

151.3s/56ms/14/14/sweep, 380.4s/204ms/467/100/checkpoint start, 396.8s/167ms/228/96/other, 407.4s/556ms/316/99/other, 488.1s/103ms/7/7/other, 544.4s/32ms/9/9/other, 566.8s/199ms/296/96/other, 594.6s/453ms/344/100/checkpoint start, 607.2s/31ms/2/2/other, 624.4s/23ms/1/1/other, 639.3s/33ms/4/4/sweep, 666.2s/76ms/69/69/checkpoint start, 708.6s/25ms/4/4/other

Session-close sweeps (s) and max client latency in that 1 s interval (ms): 150s:1, 190s:4, 210s:1, 341s:2, 441s:2, 451s:3, 521s:2, 631s:2, 641s:5, 651s:2, 701s:1

Intervals (s): 229.1, 16.4, 10.6, 80.8, 56.2, 22.4, 27.8, 12.7, 17.2, 14.8, 26.9, 42.4
