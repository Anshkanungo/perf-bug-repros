#!/usr/bin/env python3
"""Wait for mongod, optionally initiate a 1-node replica set / set the idle timeout, record server facts."""
import argparse
import json
import sys
import time

from pymongo import MongoClient
from pymongo.errors import PyMongoError


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uri", required=True)
    ap.add_argument("--hostport", required=True, help="host:port as seen by other containers")
    ap.add_argument("--replset", default="", help="initiate a single-node replica set with this name")
    ap.add_argument("--set-idle-timeout", type=int, default=None,
                    help="setParameter wiredTigerSessionCloseIdleTimeSecs at runtime (external mongod)")
    ap.add_argument("--out", required=True, help="write server facts (JSON) here")
    ap.add_argument("--timeout", type=float, default=180)
    args = ap.parse_args()

    client = MongoClient(args.uri, directConnection=True, serverSelectionTimeoutMS=2000,
                         appname="s52879-ready")
    deadline = time.time() + args.timeout
    while True:
        try:
            client.admin.command("ping")
            break
        except PyMongoError as e:
            if time.time() > deadline:
                print(f"ready: mongod not reachable at {args.uri}: {e}", file=sys.stderr)
                sys.exit(1)
            time.sleep(1)

    if args.replset:
        try:
            client.admin.command({"replSetInitiate": {"_id": args.replset,
                                                      "members": [{"_id": 0, "host": args.hostport}]}})
        except PyMongoError as e:
            if "already initialized" not in str(e):
                raise
        while not client.admin.command("isMaster").get("ismaster"):
            if time.time() > deadline:
                print("ready: replica set did not elect a primary", file=sys.stderr)
                sys.exit(1)
            time.sleep(1)

    if args.set_idle_timeout is not None:
        client.admin.command({"setParameter": 1,
                              "wiredTigerSessionCloseIdleTimeSecs": args.set_idle_timeout})

    bi = client.admin.command("buildInfo")
    params = client.admin.command({"getParameter": 1, "wiredTigerSessionCloseIdleTimeSecs": 1,
                                   "wiredTigerCursorCacheSize": 1})
    hi = client.admin.command("hostInfo")
    opts = client.admin.command("getCmdLineOpts")
    facts = {
        "version": bi.get("version"),
        "gitVersion": bi.get("gitVersion"),
        "allocator": bi.get("allocator"),
        "buildEnvironment": {k: bi.get("buildEnvironment", {}).get(k)
                             for k in ("distarch", "target_arch", "target_os", "cc", "ccflags")},
        "debug": bi.get("debug"),
        "wiredTigerSessionCloseIdleTimeSecs": params.get("wiredTigerSessionCloseIdleTimeSecs"),
        "wiredTigerCursorCacheSize": params.get("wiredTigerCursorCacheSize"),
        "argv": opts.get("argv"),
        "host": {"os": hi.get("os", {}), "numCores": hi.get("system", {}).get("numCores"),
                 "memSizeMB": hi.get("system", {}).get("memSizeMB"),
                 "cpuArch": hi.get("system", {}).get("cpuArch")},
    }
    with open(args.out, "w") as f:
        json.dump(facts, f, indent=1, default=str)
    print(f"ready: mongod {facts['version']} ({facts['gitVersion'][:10]}), "
          f"idle timeout {facts['wiredTigerSessionCloseIdleTimeSecs']} s")


if __name__ == "__main__":
    main()
