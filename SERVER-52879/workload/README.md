# Workload

| file | what |
|---|---|
| `original/repro.js` | Bruce Lucas's script, **byte-for-byte** as attached to the ticket (`secure/attachment/287290/repro.js`, 1064 bytes, sha256 `f78a32e5…be3c`). Never edited. |
| `original/parallelTester.js` | `jstests/libs/parallelTester.js` from the `r4.4.3` tag (the original `load()`s it from Bruce's checkout). Provides `Thread`. |
| `repro-adapted.js` | The script `run.sh --driver shell` runs (default). Same workload, changes listed below. |
| `driver.py` | pymongo implementation of the same workload shape (`run.sh --driver py`): µs timing, threads spread over processes. Cross-check only. |
| `sampler.py` | 1 Hz `serverStatus` sampler (FTDC stand-in): opLatencies histograms, WT session/cursor/dhandle counters, checkpoints. |
| `ready.py` | Waits for mongod, optionally initiates a 1-node replica set or sets the idle timeout at runtime, records build facts. |
| `Dockerfile` | `s52879-tools` image: Python 3.12 + pymongo 4.10.1 + numpy/pandas/matplotlib (dependencies only; scripts are bind-mounted). |

## Changes from the original (`original/repro.js` → `repro-adapted.js`)

1. **`load()` path:** `/home/bdlucas/mongodb/git/mongo/jstests/libs/parallelTester.js` →
   `/workload/original/parallelTester.js` (the r4.4.3 copy, mounted into the client container).
2. **Parameters:** `ncollections`, `nindexes`, `nthreads` can be overridden through `--eval 'var CFG={...}'`.
   The defaults are the original values (1000, 10, 100).
3. **Finite run:** the original inserts forever. The adapted threads stop after `CFG.durationSecs`
   (default 720 s).
4. **Timing (the only behavioural addition):** each `insert` is wrapped in `Date.now()` calls, and the
   thread prints `O,<thread>,<start_ms>,<latency_ms>`, buffered and flushed about once per second in one
   `print()`. The insert itself, the document shape `{f0: i, …, f9: i}`, the random collection choice, and
   `sleep(100 + Math.random() * 10)` are unchanged.
5. **Phase markers** (`P,setup_start|setup_end|insert_start|insert_end,<ms>`) and per-thread insert totals
   (`T,<thread>,<n>`) are printed so the analysis can find the insert phase.
6. **`skipSetup`** option to reuse an existing dataset (off by default).
7. Implicit globals (`o = {}`, `thread = …`) became `var` declarations. This has no effect: each `Thread`
   runs in its own JS scope.

**Verified:** with the 4.4.3 legacy shell, the global `db` works inside `Thread` bodies exactly as in the
original. Each thread gets its own connection (`connections.current` = 101 with 100 threads), so the original
"use `db` inside threads" pattern is kept rather than replaced with `new Mongo(host)`. A smoke run printed
16,705 per-op lines from 20 concurrent threads with 0 malformed lines.

**Timer resolution:** the legacy shell's `Date.now()` has 1 ms resolution, so per-op latencies are
integers in ms. That is plenty for spikes of tens or hundreds of ms. The server-side histogram (µs buckets)
and `driver.py` (µs) cover the sub-ms baseline.

**Resource use (measured):** 100 shell threads ≈ 1.0–1.2 GiB RSS and ~25–35% of one core for the client
container. The shell is light enough, so the pymongo driver isn't needed for the main runs.

## Running the workload against any mongod by hand

```bash
# legacy shell (any machine with Docker; the 4.4.3 image only supplies the client)
docker run --rm --network host -v "$PWD/workload:/workload:ro" --tmpfs /data/db --tmpfs /data/configdb \
  --entrypoint mongo mongo:4.4.3 --host <host:port> --quiet \
  --eval 'var CFG={durationSecs:720}' /workload/repro-adapted.js > client.log

# pymongo equivalent
docker run --rm --network host -v "$PWD/workload:/workload:ro" s52879-tools:1 \
  python /workload/driver.py --uri "mongodb://<host:port>/?directConnection=true" --duration 720 > client.log
```

`../run.sh --target <host:port>` does this plus the sampler, runtime `setParameter`, log collection, and analysis.
