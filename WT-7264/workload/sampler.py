#!/usr/bin/env python3
"""1 Hz serverStatus sampler (our plain-text stand-in for FTDC) plus optional per-thread CPU of mongod.

serverStatus → --out (JSON lines). Each line has:
  t_req_ms / t_resp_ms   client wall clock (epoch ms) when the request was sent / answered
  local_ms, uptime_ms, version
  opcounters, opLatencies (reads/writes/commands, no histograms), globalLock (active readers/writers),
  connections, mem, metrics.document
  wt.cache, wt.cursor, wt.transaction, wt.concurrentTransactions   (whole WiredTiger sections, so every
                                                                   version's stat names are kept as-is)

Per-thread CPU → --threads-out (JSON lines), only when this container shares mongod's PID namespace
(docker run --pid=container:<mongod>): every second, utime+stime clock ticks of every mongod thread
(/proc/<pid>/task/<tid>/stat), so a connection thread spinning at 100% CPU is visible (SERVER-67350:
"mongod will be using one or two cores at 100% CPU").

Samples are aligned to wall-clock second boundaries. A slow serverStatus keeps its real timestamps and
missed ticks are skipped (a stall shows up as a gap, not as a hidden delay).
"""
import argparse
import json
import os
import signal
import sys
import threading
import time

from pymongo import MongoClient

STOP = threading.Event()


def _stop(*_):
    STOP.set()


def pick(ss):
    wt = ss.get("wiredTiger", {})
    return {
        "local_ms": int(ss["localTime"].timestamp() * 1000),
        "uptime_ms": ss.get("uptimeMillis"),
        "version": ss.get("version"),
        "opcounters": ss.get("opcounters", {}),
        "opLatencies": ss.get("opLatencies", {}),
        "globalLock": {"activeClients": ss.get("globalLock", {}).get("activeClients", {}),
                       "currentQueue": ss.get("globalLock", {}).get("currentQueue", {})},
        "connections": ss.get("connections", {}),
        "mem": ss.get("mem", {}),
        "document": ss.get("metrics", {}).get("document", {}),
        "wt": {
            "cache": wt.get("cache", {}),
            "cursor": wt.get("cursor", {}),
            "transaction": wt.get("transaction", {}),
            "concurrentTransactions": wt.get("concurrentTransactions", {}),
        },
    }


def find_mongod_pid():
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            with open(f"/proc/{d}/comm") as f:
                if f.read().strip() == "mongod":
                    return int(d)
        except OSError:
            continue
    return None


def thread_ticks(pid):
    out = {}
    base = f"/proc/{pid}/task"
    for tid in os.listdir(base):
        try:
            with open(f"{base}/{tid}/stat") as f:
                s = f.read()
        except OSError:
            continue
        # comm is in parentheses and may contain spaces; fields after it are space separated
        lp, rp = s.find("("), s.rfind(")")
        comm = s[lp + 1:rp]
        rest = s[rp + 2:].split()
        utime, stime = int(rest[11]), int(rest[12])  # fields 14 and 15 of stat
        out[tid] = [comm, utime + stime]
    return out


def thread_loop(path, interval):
    pid = None
    deadline = time.time() + 60
    while pid is None and not STOP.is_set() and time.time() < deadline:
        pid = find_mongod_pid()
        if pid is None:
            time.sleep(0.5)
    if pid is None:
        print("sampler: no mongod process visible; per-thread CPU disabled", file=sys.stderr)
        return
    hz = os.sysconf("SC_CLK_TCK")
    with open(path, "a", buffering=1) as out:
        out.write(json.dumps({"pid": pid, "clk_tck": hz}) + "\n")
        while not STOP.is_set():
            now = time.time()
            nxt = (int(now / interval) + 1) * interval
            if STOP.wait(max(0.0, nxt - now)):
                break
            try:
                ticks = thread_ticks(pid)
            except OSError:
                break  # mongod went away
            out.write(json.dumps({"t_ms": int(time.time() * 1000), "threads": ticks}) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uri", required=True)
    ap.add_argument("--out", required=True, help="serverStatus JSON-lines output")
    ap.add_argument("--threads-out", help="per-thread CPU JSON-lines output (needs mongod's PID namespace)")
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--dump-full", help="also write one full serverStatus document here and continue")
    args = ap.parse_args()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    if args.threads_out:
        threading.Thread(target=thread_loop, args=(args.threads_out, args.interval), daemon=True).start()

    client = MongoClient(args.uri, directConnection=True, serverSelectionTimeoutMS=60000,
                         appname="w7264-sampler")
    admin = client.admin
    admin.command("ping")
    if args.dump_full:
        ss = admin.command({"serverStatus": 1})
        with open(args.dump_full, "w") as f:
            json.dump(ss, f, default=str, indent=1)

    n = 0
    with open(args.out, "a", buffering=1) as out:
        while not STOP.is_set():
            now = time.time()
            nxt = (int(now / args.interval) + 1) * args.interval
            if STOP.wait(max(0.0, nxt - now)):
                break
            t_req = time.time()
            try:
                ss = admin.command({"serverStatus": 1})
            except Exception as e:  # keep sampling through transient errors
                out.write(json.dumps({"t_req_ms": int(t_req * 1000), "error": str(e)}) + "\n")
                continue
            rec = {"t_req_ms": int(t_req * 1000), "t_resp_ms": int(time.time() * 1000)}
            rec.update(pick(ss))
            out.write(json.dumps(rec, default=str) + "\n")
            n += 1
    print(f"sampler: wrote {n} samples to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
