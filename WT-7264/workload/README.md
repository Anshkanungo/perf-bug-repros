# Workload

| file | what |
|---|---|
| `original/repro.sh` | Bruce Lucas's script, **byte-for-byte** as attached to WT-7264 (`secure/attachment/302948/repro.sh`, 1034 bytes, sha256 `5e791eff…07fc7`). Never edited. |
| `original/parallelTester.js` | `jstests/libs/parallelTester.js` from the `r5.0.33` tag (sha256 `7075447a…0414d`); the original `load()`s it from Bruce's checkout. Provides `Thread`. |
| `repro-adapted.js` | The `mongo --eval` part of `repro.sh`, minimally adapted (changes below). `run.sh --workload bruce` (default) runs it with the legacy shell. |
| `insertmany_67350.py` | **Labelled variant** (`run.sh --workload 67350`): the SERVER-67350 shape rebuilt from the reporter's logs (the reporter's Java program was never attached): 5 threads, 1,000,000 `{someId: ObjectId}` documents in contiguous ascending ranges, one unique index, 100,000 documents per `insert_many`, started on a barrier. |
| `sampler.py` | 1 Hz `serverStatus` sampler (FTDC stand-in: whole WT cache/cursor/transaction sections) plus 1 Hz per-thread CPU of mongod read from `/proc` (needs mongod's PID namespace). |
| `ready.py` | Waits for mongod, applies runtime `setParameter`s (for `--target`), records `buildInfo`, the WT-7264-relevant parameters (`wiredTigerPrefixSearchForUniqueIndexes`, or `absent`), and host facts. |
| `Dockerfile` | `w7264-tools` image: Python 3.12 + pymongo 4.10.1 + numpy/pandas/matplotlib (dependencies only; scripts are bind-mounted). Same layers as `s52879-tools`. |

## What `repro.sh` does, and what `run.sh` does instead

`repro.sh` kills every `mongod`/`mongo` on the machine, wipes `/ssd/db`, starts a standalone `mongod
--fork` with defaults, and runs the shell script. `run.sh` replaces that part with a fresh Docker volume and
a standalone `mongod --wiredTigerCacheSizeGB 1` in a 3 GB container (default cache sizing would use half of
the VM's RAM; see `../PLAN.md`). Nothing outside `w7264-*` containers is touched.

## Changes from the original (`original/repro.sh` → `repro-adapted.js`)

1. **`load()` path:** `/home/bdlucas/mongodb/git/mongo/jstests/libs/parallelTester.js` →
   `/workload/original/parallelTester.js` (the r5.0.33 copy, mounted into the client container).
2. **Parameters** (`--eval 'var CFG={...}'`): `nthreads` (20), `count` (100*1000 per thread), `every`
   (2000 per insertMany) default to the original values. `size = 100` in the original is unused and dropped.
3. **Timing (the only behavioural addition):** each `insertMany` is wrapped in `Date.now()` calls; the
   thread prints `S,<t>,<batch>,<start_ms>` before and `B,<t>,<batch>,<start_ms>,<latency_ms>` after it.
   The documents (`{_id: inx, a: inx, b: inx}`, `inx = t*count + i + j`), the batch size and the order are
   unchanged. The original's progress lines (`print(t, i)` every 10,000 and `thread t finished`) are kept.
4. **Phase markers** `P,setup_start|setup_end|insert_start|insert_end,<ms>` and `T,<t>,<batches>,<end_ms>`.
5. **Optional, off by default:** `syncStart` (W1, "barrier" variant): every thread waits for a common
   start time (~3 s after the script starts) before its first `insertMany`; the insert phase is then timed
   from that moment. `unique:false` (control: same indexes, not unique). `skipSetup`, `coll`.
6. Implicit globals (`size`, `count`, `many`, `inx`, `thread`) became `var` declarations. No effect: each
   `Thread` runs in its own JS scope.

**Verified:** with the 5.0.33 legacy shell the global `db` works inside `Thread` bodies as in the original
(each thread gets its own connection), and every run's log has one `S` and one `B` line per call (1000
calls = 20 threads × 50 batches). The legacy shell sends each 2000-document `insertMany` as **two insert
commands of 1000 documents** (`bulk_api.js`: `maxNumberOfDocsInBatch = 1000`), and mongod runs each command
as WiredTiger transactions of up to 64 documents (`internalInsertMaxBatchSize`, default 64), so one
`insertMany` call is ~32 transactions, each doing 2 `_keyExists` checks per document.

**Timer resolution:** the legacy shell's `Date.now()` has 1 ms resolution. Normal calls take ~0.1–0.3 s;
stalls take seconds to minutes.

## Running the workload against any mongod by hand

```bash
# legacy shell (any machine with Docker; the mongo:5.0.33 image only supplies the client)
docker run --rm --network host -v "$PWD/workload:/workload:ro" --tmpfs /data/db --tmpfs /data/configdb \
  --entrypoint mongo mongo:5.0.33 --host <host:port> --quiet \
  --eval 'var CFG={syncStart:true}' /workload/repro-adapted.js > client.log

# SERVER-67350-like variant
docker run --rm --network host -v "$PWD/workload:/workload:ro" w7264-tools:1 \
  python /workload/insertmany_67350.py --uri "mongodb://<host:port>/?directConnection=true" > client.log
```

The workload writes to `test.c` (or `test_data_mongo_issue.mainthings`) and expects it to be empty.
`../run.sh --target <host:port>` does this plus the sampler, runtime `setParameter`, log collection, and analysis.
