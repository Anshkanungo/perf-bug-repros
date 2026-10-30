# SERVER-52879 comparison

| metric | 4.4.3 (no checkpoints) | 4.4.4 (no checkpoints) |
|---|---|---|
| mongod version | 4.4.3 | 4.4.4 |
| driver / topology | shell / standalone | shell / standalone |
| idle timeout (s) → predicted period (s) | 30 → 40 | 30 → 40 |
| inserts/s | 945.5 | 947.8 |
| per-op p50 / p99 (ms) | 1.00 / 2.00 | 1.00 / 1.00 |
| per-op p99.9 / max (ms) | 26.0 / 726.0 | 5.0 / 51.0 |
| per-second max: median (baseline) (ms) | 2.00 | 2.00 |
| per-second max: p99.5 / max (ms) | 118.3 / 726.0 | 24.1 / 51.0 |
| spike threshold (ms) | 20.0 | 20.0 |
| **spike events** | **13** | **2** |
| spike peak, median (ms) | 58.0 | 41.5 |
| threads hit per spike, median | 36 | 8 |
| **interval median [IQR] (s)** | **40.1** [32.9–42.8] | **445.0** [445.0–445.0] |
| intervals within ±5 s of prediction | 0.42 | 0.00 |
| autocorrelation peak (lag s, r) | 40, 0.237 | 35, 0.365 |
| server mean write latency/s: median / max (ms) | 0.192 / 78.38 | 0.181 / 0.69 |
| WT open sessions min / median / max | 19 / 22 / 75 | 17 / 19 / 29 |
| WT cached cursors median / max | 106,011 / 180,959 | 76,424 / 142,874 |
| session-close sweeps seen | 14 | 6 |
| spikes coinciding with a sweep | 10/13 | 0/2 |
| sweeps coinciding with a spike | 10/14 | 0/6 |
| D2 server-side spike events (mean/s ≥10× median) | 5 | 0 |
| D2 interval median (s) | 40.0 | – |
| D2 peak server mean latency/s, median (ms) | 6.95 | – |
| spike events by coincidence | other 3, sweep 10 | other 2 |
| *expl.* sweeps seen / max latency in sweep intervals, median (ms) | 14 / 31.0 | 6 / 2.0 |
| *expl.* max latency in non-sweep intervals, median (ms) | 2.0 | 2.0 |
| *expl.* sweep intervals with max ≥ 10 ms | 1.00 | 0.00 |
| *expl.* interval between sweeps, median (s) | 40.0 | 60.0 |
| *expl.* cursors closed per sweep, median | 28830 | 11990 |
| slow-query log inserts > 100 ms | 70 | 0 |
| mongod peak memory (MiB) | 1320 | 1329 |
| other containers' CPU %, median / peak (noise) | 5 / 301 | 5 / 299 |
| client peak memory (MiB) | 1374 | 1393 |

S3 check (4.4.4 (no checkpoints) vs 4.4.3 (no checkpoints)): 4.4.4 (no checkpoints) spike events = 2 (≤2 required); p99.5 of per-second max ratio 4.4.3 (no checkpoints)/4.4.4 (no checkpoints) = 4.9x (≥5x required) → **False**
