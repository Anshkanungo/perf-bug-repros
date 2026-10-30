# SERVER-52879 comparison

| metric | A 4.4.3 | B 4.4.4 | V1 4.4.3 no-ckpt | V1 4.4.4 no-ckpt | C 4.4.3 T=60 | C2 4.4.3 T=60 no-ckpt |
|---|---|---|---|---|---|---|
| mongod version | 4.4.3 | 4.4.4 | 4.4.3 | 4.4.4 | 4.4.3 | 4.4.3 |
| driver / topology | shell / standalone | shell / standalone | shell / standalone | shell / standalone | shell / standalone | shell / standalone |
| idle timeout (s) → predicted period (s) | 30 → 40 | 30 → 40 | 30 → 40 | 30 → 40 | 60 → 70 | 60 → 70 |
| inserts/s | 947.1 | 943.8 | 945.5 | 947.8 | 945.3 | 947.2 |
| per-op p50 / p99 (ms) | 1.00 / 1.00 | 1.00 / 5.00 | 1.00 / 2.00 | 1.00 / 1.00 | 1.00 / 2.00 | 1.00 / 2.00 |
| per-op p99.9 / max (ms) | 9.0 / 365.0 | 65.0 / 556.0 | 26.0 / 726.0 | 5.0 / 51.0 | 69.0 / 565.0 | 17.0 / 304.0 |
| per-second max: median (baseline) (ms) | 2.00 | 2.00 | 2.00 | 2.00 | 2.00 | 2.00 |
| per-second max: p99.5 / max (ms) | 81.4 / 365.0 | 199.0 / 556.0 | 118.3 / 726.0 | 24.1 / 51.0 | 229.2 / 565.0 | 56.5 / 304.0 |
| spike threshold (ms) | 20.0 | 20.0 | 20.0 | 20.0 | 20.0 | 20.0 |
| **spike events** | **14** | **13** | **13** | **2** | **10** | **19** |
| spike peak, median (ms) | 36.5 | 76.0 | 58.0 | 41.5 | 160.5 | 44.0 |
| threads hit per spike, median | 14 | 14 | 36 | 8 | 100 | 22 |
| **interval median [IQR] (s)** | **40.0** [36.5–50.0] | **24.7** [16.0–45.8] | **40.1** [32.9–42.8] | **445.0** [445.0–445.0] | **49.9** [18.2–68.5] | **32.3** [17.8–66.8] |
| intervals within ±5 s of prediction | 0.38 | 0.08 | 0.42 | 0.00 | 0.33 | 0.33 |
| autocorrelation peak (lag s, r) | 35, 0.169 | 11, 0.234 | 40, 0.237 | 35, 0.365 | 70, 0.285 | 70, 0.275 |
| server mean write latency/s: median / max (ms) | 0.191 / 46.86 | 0.190 / 49.69 | 0.192 / 78.38 | 0.181 / 0.69 | 0.195 / 137.15 | 0.204 / 37.62 |
| WT open sessions min / median / max | 19 / 21 / 113 | 17 / 19 / 115 | 19 / 22 / 75 | 17 / 19 / 29 | 19 / 24 / 115 | 20 / 27 / 55 |
| WT cached cursors median / max | 96,066 / 164,323 | 83,960 / 325,715 | 106,011 / 180,959 | 76,424 / 142,874 | 120,209 / 290,441 | 138,238 / 237,241 |
| session-close sweeps seen | 14 | 11 | 14 | 6 | 6 | 11 |
| spikes coinciding with a sweep | 11/14 | 2/13 | 10/13 | 0/2 | 4/10 | 10/19 |
| sweeps coinciding with a spike | 10/14 | 2/11 | 10/14 | 0/6 | 4/6 | 10/11 |
| D2 server-side spike events (mean/s ≥10× median) | 3 | 8 | 5 | 0 | 7 | 4 |
| D2 interval median (s) | 36.0 | 17.0 | 40.0 | – | 62.0 | 240.0 |
| D2 peak server mean latency/s, median (ms) | 4.25 | 4.11 | 6.95 | – | 20.63 | 6.25 |
| spike events by coincidence | checkpoint start 1, other 2, sweep 8, sweep+checkpoint 3 | checkpoint start 3, other 8, sweep 2 | other 3, sweep 10 | other 2 | checkpoint start 4, other 2, sweep 4 | other 9, sweep 10 |
| *expl.* sweeps seen / max latency in sweep intervals, median (ms) | 14 / 29.0 | 11 / 2.0 | 14 / 31.0 | 6 / 2.0 | 6 / 65.0 | 11 / 48.0 |
| *expl.* max latency in non-sweep intervals, median (ms) | 2.0 | 2.0 | 2.0 | 2.0 | 2.0 | 2.0 |
| *expl.* sweep intervals with max ≥ 10 ms | 1.00 | 0.00 | 1.00 | 0.00 | 1.00 | 1.00 |
| *expl.* interval between sweeps, median (s) | 40.0 | 45.0 | 40.0 | 60.0 | 70.9 | 70.0 |
| *expl.* cursors closed per sweep, median | 15738 | 24345 | 28830 | 11990 | 36022 | 46234 |
| slow-query log inserts > 100 ms | 101 | 125 | 70 | 0 | 572 | 126 |
| mongod peak memory (MiB) | 1444 | 1717 | 1320 | 1329 | 1630 | 1364 |
| other containers' CPU %, median / peak (noise) | 5 / 325 | 5 / 327 | 5 / 301 | 5 / 299 | 4 / 348 | 5 / 235 |
| client peak memory (MiB) | 1382 | 1402 | 1374 | 1393 | 1382 | 1382 |

S3 check (B 4.4.4 vs A 4.4.3): B 4.4.4 spike events = 13 (≤2 required); p99.5 of per-second max ratio A 4.4.3/B 4.4.4 = 0.4x (≥5x required) → **False**
