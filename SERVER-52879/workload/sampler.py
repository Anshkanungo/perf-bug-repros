#!/usr/bin/env python3
"""Sample mongod serverStatus once per second and append selected sections as JSON lines.

This is our plain-text stand-in for FTDC (mongod's own 1 Hz serverStatus capture). Each line has:
  t_req_ms / t_resp_ms  client wall-clock (epoch ms) when the request was sent / answered
  local_ms              server localTime (epoch ms)
  opLatencies           reads/writes/commands/transactions with latency histograms
  wt.session, wt.cursor, wt.dhandle, wt.files_open, wt.ckpt_running, wt.ckpts, ...
  connections, opcounters, mem

Samples are aligned to wall-clock second boundaries. If a serverStatus call blocks (it needs a
WT session from the same session cache the bug stalls), the late sample keeps its real timestamps
and missed ticks are skipped, so stalls show up as gaps instead of being hidden.
"""
import argparse
import json
import signal
import sys
import time

from pymongo import MongoClient

STOP = False


def _stop(*_):
    global STOP
    STOP = True


def pick(ss):
    wt = ss.get("wiredTiger", {})
    txn = wt.get("transaction", {})
    conn = wt.get("connection", {})
    return {
        "local_ms": int(ss["localTime"].timestamp() * 1000),
        "uptime_ms": ss.get("uptimeMillis"),
        "version": ss.get("version"),
        "opLatencies": ss.get("opLatencies", {}),
        "connections": ss.get("connections", {}),
        "opcounters": ss.get("opcounters", {}),
        "mem": ss.get("mem", {}),
        "wt": {
            "session": wt.get("session", {}),
            "cursor": wt.get("cursor", {}),
            "dhandle": wt.get("data-handle", {}),
            "files_open": conn.get("files currently open"),
            "ckpt_running": txn.get("transaction checkpoint currently running"),
            "ckpts": txn.get("transaction checkpoints"),
            "ckpt_most_recent_ms": txn.get("transaction checkpoint most recent time (msecs)"),
            "concurrentTransactions": wt.get("concurrentTransactions", {}),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uri", required=True)
    ap.add_argument("--out", required=True, help="JSON-lines output file")
    ap.add_argument("--duration", type=float, default=0, help="seconds; 0 = until SIGTERM")
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--dump-full", help="also write one full serverStatus document here and continue")
    args = ap.parse_args()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    client = MongoClient(args.uri, directConnection=True, serverSelectionTimeoutMS=60000,
                         appname="s52879-sampler")
    admin = client.admin
    admin.command("ping")

    if args.dump_full:
        ss = admin.command({"serverStatus": 1, "opLatencies": {"histograms": True}})
        with open(args.dump_full, "w") as f:
            json.dump(ss, f, default=str, indent=1)

    t_end = time.time() + args.duration if args.duration > 0 else float("inf")
    n = 0
    with open(args.out, "a", buffering=1) as out:
        while not STOP and time.time() < t_end:
            # Sleep to the next interval boundary.
            now = time.time()
            nxt = (int(now / args.interval) + 1) * args.interval
            time.sleep(max(0.0, nxt - now))
            if STOP:
                break
            t_req = time.time()
            try:
                ss = admin.command({"serverStatus": 1, "opLatencies": {"histograms": True}})
            except Exception as e:  # keep sampling through transient errors
                out.write(json.dumps({"t_req_ms": int(t_req * 1000), "error": str(e)}) + "\n")
                continue
            t_resp = time.time()
            rec = {"t_req_ms": int(t_req * 1000), "t_resp_ms": int(t_resp * 1000)}
            rec.update(pick(ss))
            out.write(json.dumps(rec, default=str) + "\n")
            n += 1
    print(f"sampler: wrote {n} samples to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
