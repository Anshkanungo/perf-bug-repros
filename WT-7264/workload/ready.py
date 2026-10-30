#!/usr/bin/env python3
"""Wait for mongod, optionally apply runtime setParameter values, and record the server facts.

  ready.py --uri URI --out server.json [--set wiredTigerPrefixSearchForUniqueIndexes=false ...]

--set is applied with the setParameter command (for an external --target mongod; run.sh passes the same
values as --setParameter at startup when it starts mongod itself). Afterwards the values that matter for
WT-7264 are read back with getParameter; a parameter the server does not know (e.g.
wiredTigerPrefixSearchForUniqueIndexes before 4.4.18 / 5.0.14) is recorded as "absent".
"""
import argparse
import json
import sys
import time

from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError

WATCH = ["wiredTigerPrefixSearchForUniqueIndexes", "internalInsertMaxBatchSize",
         "wiredTigerCursorCacheSize", "wiredTigerSessionCloseIdleTimeSecs"]


def parse_value(v):
    lv = v.lower()
    if lv in ("true", "false"):
        return lv == "true"
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uri", required=True)
    ap.add_argument("--out", required=True, help="write server facts (JSON) here")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE",
                    help="setParameter at runtime (repeatable)")
    ap.add_argument("--timeout", type=float, default=180)
    args = ap.parse_args()

    client = MongoClient(args.uri, directConnection=True, serverSelectionTimeoutMS=2000,
                         appname="w7264-ready")
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

    applied = {}
    for kv in args.set:
        k, _, v = kv.partition("=")
        val = parse_value(v)
        try:
            client.admin.command({"setParameter": 1, k: val})
            applied[k] = val
        except OperationFailure as e:
            print(f"ready: setParameter {k}={val!r} failed: {e}", file=sys.stderr)
            sys.exit(1)

    params = {}
    for k in WATCH:
        try:
            params[k] = client.admin.command({"getParameter": 1, k: 1}).get(k)
        except OperationFailure:
            params[k] = "absent"

    bi = client.admin.command("buildInfo")
    hi = client.admin.command("hostInfo")
    opts = client.admin.command("getCmdLineOpts")
    ss = client.admin.command("serverStatus")
    cache = ss.get("wiredTiger", {}).get("cache", {})
    facts = {
        "version": bi.get("version"),
        "gitVersion": bi.get("gitVersion"),
        "wiredTigerVersion": ss.get("wiredTiger", {}).get("version") if isinstance(ss.get("wiredTiger"), dict) else None,
        "allocator": bi.get("allocator"),
        "buildEnvironment": {k: bi.get("buildEnvironment", {}).get(k)
                             for k in ("distarch", "target_arch", "target_os", "cc", "ccflags")},
        "debug": bi.get("debug"),
        "parameters": params,
        "runtime_setParameter": applied,
        "wt_cache_max_bytes": cache.get("maximum bytes configured"),
        "argv": opts.get("argv"),
        "parsed": opts.get("parsed"),
        "host": {"os": hi.get("os", {}), "numCores": hi.get("system", {}).get("numCores"),
                 "memSizeMB": hi.get("system", {}).get("memSizeMB"),
                 "memLimitMB": hi.get("system", {}).get("memLimitMB"),
                 "cpuArch": hi.get("system", {}).get("cpuArch")},
    }
    with open(args.out, "w") as f:
        json.dump(facts, f, indent=1, default=str)
    print(f"ready: mongod {facts['version']} ({(facts['gitVersion'] or '')[:10]}), "
          f"wiredTigerPrefixSearchForUniqueIndexes={params['wiredTigerPrefixSearchForUniqueIndexes']}, "
          f"WT cache {facts['wt_cache_max_bytes']} bytes")


if __name__ == "__main__":
    main()
