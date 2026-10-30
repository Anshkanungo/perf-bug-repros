#!/usr/bin/env python3
"""Minimal FTDC (mongod diagnostic.data) decoder: prints selected metrics as CSV.

  python3 -I ftdc_decode.py <diagnostic.data dir> [--metric SUBSTRING ...]

Needs the `bson` package (pymongo); run.sh's w7264-tools image has it:
  docker run --rm -v <dir>:/d:ro -v $PWD/discussion:/s:ro w7264-tools:1 python -I /s/ftdc_decode.py /d

Format (mongo src/mongo/db/ftdc): a file is a sequence of BSON documents {_id, type, ...}. type 1 holds
`data` = uint32 length + zlib(BSON reference sample, uint32 metric count, uint32 sample count, then
metric-major unsigned LEB128 deltas where a 0 is followed by a varint count of further zeros). Metrics are
the numeric leaves of the reference sample in document order (double/int/long/bool/date; a Timestamp is
two metrics). Value of sample k = reference value + sum of the first k deltas (mod 2^64).
Input files are treated as data only.
"""
import argparse
import csv
import datetime
import struct
import sys
import zlib
from pathlib import Path

import bson
from bson.timestamp import Timestamp

DEFAULT = ["serverStatus.opcounters.insert",
           "serverStatus.wiredTiger.cache.history store table reads missed",
           "serverStatus.wiredTiger.cache.history store table reads",
           "serverStatus.wiredTiger.cursor.Total number of entries skipped by cursor next calls",
           "serverStatus.wiredTiger.cursor.Total number of entries skipped by cursor prev calls",
           "serverStatus.wiredTiger.cursor.cursor search near calls",
           "serverStatus.globalLock.activeClients.writers",
           "serverStatus.wiredTiger.cache.pages evicted by application threads",
           "serverStatus.wiredTiger.cache.cache overflow table reads",            # 4.2 (lookaside)
           "serverStatus.wiredTiger.cache.cache overflow cursor application thread wait time (usecs)"]


def leaves(doc, prefix=""):
    """(path, value) for every metric leaf, in FTDC extraction order."""
    items = doc.items() if isinstance(doc, dict) else enumerate(doc)
    for k, v in items:
        p = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, bool):
            yield p, int(v)
        elif isinstance(v, (int, float)):
            yield p, int(v)
        elif isinstance(v, datetime.datetime):
            yield p, int(v.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000) if v.tzinfo is None \
                else int(v.timestamp() * 1000)
        elif isinstance(v, Timestamp):
            yield p + ".t", v.time
            yield p + ".i", v.inc
        elif isinstance(v, (dict, list)):
            yield from leaves(v, p)


def varints(buf, pos):
    while pos < len(buf):
        shift, val = 0, 0
        while True:
            b = buf[pos]
            pos += 1
            val |= (b & 0x7F) << shift
            if not b & 0x80:
                break
            shift += 7
        yield val


def decode_chunk(data):
    raw = zlib.decompress(data[4:])
    ref_len = struct.unpack_from("<i", raw, 0)[0]
    ref = bson.decode(raw[:ref_len])
    nmetrics, nsamples = struct.unpack_from("<II", raw, ref_len)
    paths, base = zip(*leaves(ref)) if ref else ((), ())
    if len(paths) != nmetrics:
        raise ValueError(f"metric count mismatch: parsed {len(paths)} leaves, header says {nmetrics}")
    deltas = [[0] * nsamples for _ in range(nmetrics)]
    it = varints(raw, ref_len + 8)
    i = j = 0
    zeros = 0
    total = nmetrics * nsamples
    n = 0
    while n < total:
        if zeros:
            v = 0
            zeros -= 1
        else:
            v = next(it)
            if v == 0:
                zeros = next(it)
        deltas[i][j] = v
        n += 1
        j += 1
        if j == nsamples:
            i, j = i + 1, 0
    rows = [list(base)]
    cur = list(base)
    for k in range(nsamples):
        cur = [(cur[m] + deltas[m][k]) & 0xFFFFFFFFFFFFFFFF for m in range(nmetrics)]
        rows.append([x - (1 << 64) if x >= 1 << 63 else x for x in cur])
    return list(paths), rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--metric", action="append", help="substring of a metric path (repeatable)")
    args = ap.parse_args()
    wanted = args.metric or DEFAULT
    files = sorted(p for p in Path(args.dir).iterdir() if p.name.startswith("metrics."))
    files.sort(key=lambda p: (p.name == "metrics.interim", p.name))
    w = csv.writer(sys.stdout)
    header_done = False
    seen = set()
    for f in files:
        data = f.read_bytes()
        pos = 0
        while pos + 4 <= len(data):
            ln = struct.unpack_from("<i", data, pos)[0]
            if ln <= 0 or pos + ln > len(data):
                break
            doc = bson.decode(data[pos:pos + ln])
            pos += ln
            if doc.get("type") != 1:
                continue
            try:
                paths, rows = decode_chunk(doc["data"])
            except Exception as e:  # keep going on a damaged chunk
                print(f"# {f.name}: skipped chunk: {e}", file=sys.stderr)
                continue
            tcol = next((i for i, p in enumerate(paths) if p in ("start", "serverStatus.start")), None)
            cols = [(want, next((i for i, p in enumerate(paths) if p.endswith(want)), None)) for want in wanted]
            if not header_done:
                w.writerow(["t_utc", "file"] + [c[0] for c in cols])
                header_done = True
            for r in rows:
                t = r[tcol] if tcol is not None else None
                if t in seen:
                    continue
                seen.add(t)
                ts = datetime.datetime.fromtimestamp(t / 1000, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] if t else ""
                w.writerow([ts, f.name] + [r[i] if i is not None else "" for _, i in cols])


if __name__ == "__main__":
    main()
