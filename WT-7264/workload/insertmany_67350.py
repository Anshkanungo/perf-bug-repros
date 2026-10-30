#!/usr/bin/env python3
"""SERVER-67350-like variant (labelled; NOT the ticket author's program, which was never attached).

What the SERVER-67350 logs show (discussion/DISCUSSION.md): a Java driver 4.5 program creates a collection
with a unique index on `someId` (an ObjectId), then 5 connections each run insertMany over their share of
1,000,000 documents `{someId: ObjectId(...)}`, which the driver splits into insert commands of 100,000
documents (ordered). The 5 connections start within a few ms of each other.

This script reproduces that shape with pymongo:
  * all ObjectIds are generated up front, in order, so each connection gets a contiguous ascending key
    range (as when a list of generated documents is partitioned between threads);
  * N threads (default 5) wait on a barrier, then each calls insert_many on 100,000-document slices.

Output (stdout) uses the same record format as repro-adapted.js:
  P,<phase>,<epoch_ms> / S,<thread>,<batch>,<start_ms> / B,<thread>,<batch>,<start_ms>,<lat_ms> /
  T,<thread>,<batches>,<end_ms>
"""
import argparse
import sys
import threading
import time

from bson import ObjectId
from pymongo import MongoClient


def now_ms():
    return int(time.time() * 1000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uri", required=True)
    ap.add_argument("--db", default="test_data_mongo_issue")
    ap.add_argument("--coll", default="mainthings")
    ap.add_argument("--docs", type=int, default=1_000_000)
    ap.add_argument("--threads", type=int, default=5)
    ap.add_argument("--per-call", type=int, default=100_000, help="documents per insert_many call")
    ap.add_argument("--non-unique", action="store_true", help="control: plain (non-unique) index")
    ap.add_argument("--skip-setup", action="store_true")
    args = ap.parse_args()

    lock = threading.Lock()

    def emit(s):
        with lock:
            sys.stdout.write(s + "\n")
            sys.stdout.flush()

    client = MongoClient(args.uri, directConnection=True, maxPoolSize=args.threads + 4,
                         appname="w7264-67350")
    coll = client[args.db][args.coll]
    if not args.skip_setup:
        emit(f"P,setup_start,{now_ms()}")
        coll.create_index([("someId", 1)], unique=not args.non_unique)
        emit(f"P,setup_end,{now_ms()}")

    ids = [ObjectId() for _ in range(args.docs)]   # ascending
    per = (args.docs + args.threads - 1) // args.threads
    chunks = [ids[i * per:(i + 1) * per] for i in range(args.threads)]
    barrier = threading.Barrier(args.threads + 1)
    errors = []

    def worker(t):
        docs = [{"someId": x} for x in chunks[t]]
        barrier.wait()
        b = 0
        try:
            for i in range(0, len(docs), args.per_call):
                t0 = now_ms()
                emit(f"S,{t},{b},{t0}")
                coll.insert_many(docs[i:i + args.per_call], ordered=True)
                emit(f"B,{t},{b},{t0},{now_ms() - t0}")
                b += 1
        except Exception as e:  # report and let the run fail
            errors.append(repr(e))
        emit(f"T,{t},{b},{now_ms()}")

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(args.threads)]
    for th in threads:
        th.start()
    barrier.wait()
    emit(f"P,insert_start,{now_ms()}")
    for th in threads:
        th.join()
    emit(f"P,insert_end,{now_ms()}")
    if errors:
        print("errors: " + "; ".join(errors), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
