#!/usr/bin/env python3
"""pymongo version of the SERVER-52879 workload (same shape as workload/original/repro.js).

Setup: for each of N collections c0..c{N-1}, create indexes {f0:1} .. {f{K-1}:1} (serially, one client).
Run:   T threads; each loops: doc = {f0: i, ..., f{K-1}: i}; insert into a random collection;
       sleep(100 + rand*10) ms. Threads are spread over P processes so the Python GIL does not
       distort the measured latency (10 threads per process by default).

Output on stdout, same format as repro-adapted.js but with sub-millisecond latency:
  P,<phase>,<epoch_ms>
  O,<thread>,<start_epoch_ms>,<lat_ms>       (lat_ms has 3 decimals, measured with perf_counter)
  T,<thread>,<inserts>
"""
import argparse
import multiprocessing as mp
import os
import random
import sys
import threading
import time

from pymongo import MongoClient


def phase(name):
    os.write(1, f"P,{name},{int(time.time() * 1000)}\n".encode())


def setup(uri, ncolls, nindexes):
    client = MongoClient(uri, directConnection=True, appname="s52879-setup")
    db = client.test
    print("creating indexes", flush=True)
    phase("setup_start")
    for i in range(ncolls):
        for j in range(nindexes):
            db[f"c{i}"].create_index([(f"f{j}", 1)])
    phase("setup_end")
    client.close()


def worker_proc(uri, thread_ids, ncolls, nindexes, end_ts, sleep_ms, jitter_ms):
    client = MongoClient(uri, directConnection=True, maxPoolSize=len(thread_ids) + 2,
                         appname="s52879-driver")
    db = client.test
    colls = [db[f"c{i}"] for i in range(ncolls)]
    out_lock = threading.Lock()
    totals = {}

    def run(tid):
        rnd = random.Random()
        buf = []
        last_flush = time.time()
        i = 0
        while time.time() < end_ts:
            doc = {f"f{j}": i for j in range(nindexes)}
            c = colls[int(rnd.random() * ncolls)]
            t0_wall = time.time()
            t0 = time.perf_counter()
            c.insert_one(doc)
            lat_ms = (time.perf_counter() - t0) * 1000.0
            buf.append(f"O,{tid},{int(t0_wall * 1000)},{lat_ms:.3f}")
            now = time.time()
            if now - last_flush >= 1.0:
                with out_lock:
                    os.write(1, ("\n".join(buf) + "\n").encode())
                buf = []
                last_flush = now
            i += 1
            time.sleep((sleep_ms + rnd.random() * jitter_ms) / 1000.0)
        if buf:
            with out_lock:
                os.write(1, ("\n".join(buf) + "\n").encode())
        totals[tid] = i

    threads = [threading.Thread(target=run, args=(tid,), daemon=True) for tid in thread_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    with out_lock:
        os.write(1, "".join(f"T,{tid},{totals.get(tid, 0)}\n" for tid in thread_ids).encode())
    client.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uri", required=True)
    ap.add_argument("--colls", type=int, default=1000)
    ap.add_argument("--indexes", type=int, default=10)
    ap.add_argument("--threads", type=int, default=100)
    ap.add_argument("--threads-per-proc", type=int, default=10)
    ap.add_argument("--duration", type=float, default=720)
    ap.add_argument("--sleep-ms", type=float, default=100)
    ap.add_argument("--jitter-ms", type=float, default=10)
    ap.add_argument("--skip-setup", action="store_true")
    args = ap.parse_args()

    if not args.skip_setup:
        setup(args.uri, args.colls, args.indexes)

    print("inserting", flush=True)
    end_ts = time.time() + args.duration
    phase("insert_start")
    ids = list(range(args.threads))
    groups = [ids[k:k + args.threads_per_proc] for k in range(0, len(ids), args.threads_per_proc)]
    ctx = mp.get_context("fork")
    procs = [ctx.Process(target=worker_proc,
                         args=(args.uri, g, args.colls, args.indexes, end_ts, args.sleep_ms,
                               args.jitter_ms))
             for g in groups]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    phase("insert_end")
    bad = [p.exitcode for p in procs if p.exitcode != 0]
    if bad:
        print(f"driver: {len(bad)} worker processes failed: {bad}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
