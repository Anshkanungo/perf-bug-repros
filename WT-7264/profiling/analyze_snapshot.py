#!/usr/bin/env python3
"""Classify the threads in a gdb 'thread apply all bt' snapshot (snapshot.txt) -> snapshot_summary.md.

Adapted from SERVER-52879/profiling/analyze_snapshot.py (same gdb 13 parsing fixes: the "Thread N (LWP M
"name")" header, frames with or without "0x... in", and appended frame-pointer walks).
"""
import argparse
import collections
import re
from pathlib import Path

THREAD = re.compile(r'^Thread (\d+) \(.*?LWP (\d+)')       # gdb 13: Thread 76 (LWP 98 "conn47"):
NAME = re.compile(r'"([^"]*)"')
FPWALK = re.compile(r'^Thread LWP (\d+) "([^"]*)" frame-pointer walk:')
FPFRAME = re.compile(r'^\s+fp#\d+ 0x[0-9a-f]+ (.+?)(?: \+ \d+)?$')
FRAME = re.compile(r"^#(\d+)\s+(?:0x[0-9a-f]+ in )?(.+?)(?: \(.*\))?(?: from .*| at .*)?$")

STUCK = "conn thread in the unique-index duplicate check (_keyExists -> search_near/next/prev)"
STUCK_HS = STUCK + ", inside a history-store lookup (__wt_hs_find_upd)"


def func(line):
    m = FRAME.match(line)
    if not m:
        return None
    f = m.group(2)
    f = re.sub(r"\s*\(.*$", "", f)
    return f.strip()


def classify(name, frames):
    j = " | ".join(frames)
    if "_keyExists" in j or ("WiredTigerIndexUnique::_insert" in j and "search_near" in j):
        return STUCK_HS if "__wt_hs_find_upd" in j else STUCK
    if "WiredTigerIndexUnique::_insert" in j:
        return "conn thread in WiredTigerIndexUnique::_insert (other step)"
    if "CollectionImpl::insertDocuments" in j or "insertDocuments" in j:
        return "conn thread in insertDocuments (record store / other index)"
    if "performInserts" in j or "CmdInsert" in j:
        return "conn thread elsewhere in an insert command (locks, flow control, reply)"
    if name.startswith("conn") and any(k in j for k in ("recvmsg", "recv", "poll", "epoll_wait")):
        return "idle connection: waiting for next request"
    if "__wt_cache_eviction_worker" in j or "__evict" in j:
        return "eviction"
    if "__wt_checkpoint" in j or "__checkpoint" in j or "txn_checkpoint" in j:
        return "checkpoint"
    if "pthread_cond" in j or "condition_variable" in j or "__wt_cond_wait" in j:
        return "condition-variable wait (background thread)"
    if any(k in j for k in ("nanosleep", "sleep_for", "sleepmillis", "__wt_sleep")):
        return "sleeping"
    if any(k in j for k in ("__lll_lock_wait", "pthread_mutex_lock", "futex")):
        return "other mutex wait"
    if any(k in j for k in ("recvmsg", "__libc_recv", "recv", "poll", "epoll_wait")):
        return "waiting in recv/poll"
    return "other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    d = Path(ap.parse_args().dir)
    snap = d / "snapshot.txt"
    meta = (d / "snapshot_meta.txt").read_text() if (d / "snapshot_meta.txt").exists() else ""
    if not snap.exists():
        (d / "snapshot_summary.md").write_text("# gdb snapshot\n\nNo snapshot captured.\n\n```\n" + meta + "```\n")
        return
    threads, cur, by_lwp, fpcur = [], None, {}, None
    for line in snap.read_text(errors="replace").splitlines():
        m = THREAD.match(line)
        if m:
            nm = NAME.search(line)
            cur = {"num": int(m.group(1)), "lwp": int(m.group(2)), "name": nm.group(1) if nm else "?",
                   "frames": [], "fp_frames": []}
            threads.append(cur)
            by_lwp[cur["lwp"]] = cur
            fpcur = None
            continue
        m = FPWALK.match(line)
        if m:
            fpcur = by_lwp.get(int(m.group(1)))
            cur = None
            continue
        if fpcur is not None:
            m = FPFRAME.match(line)
            if m:
                fpcur["fp_frames"].append(m.group(1).strip())
            continue
        if line.startswith("#") and cur is not None:
            f = func(line)
            if f:
                cur["frames"].append(f)
    for t in threads:
        if t["fp_frames"]:
            t["frames"] = t["frames"] + ["(frame-pointer walk:)"] + t["fp_frames"]
    cats = collections.Counter()
    by_cat = collections.defaultdict(list)
    for t in threads:
        c = classify(t["name"], t["frames"])
        t["cat"] = c
        cats[c] += 1
        by_cat[c].append(t)
    L = ["# gdb all-thread snapshot (WT-7264)", "", "```", meta.strip(), "```", "",
         f"{len(threads)} threads.", "", "| state | threads | thread names |", "|---|---|---|"]
    for c, n in cats.most_common():
        names = ", ".join(sorted({t["name"] for t in by_cat[c]})[:8])
        L.append(f"| {c} | {n} | {names} |")
    for c in (STUCK_HS, STUCK, "conn thread in WiredTigerIndexUnique::_insert (other step)",
              "conn thread in insertDocuments (record store / other index)"):
        for t in by_cat.get(c, [])[:2]:
            L += ["", f"Example, {c}: thread `{t['name']}` (LWP {t['lwp']}), frames #0..:", "", "```"]
            L += [f"#{i:<2} {f}" for i, f in enumerate(t["frames"][:45])] + ["```"]
    (d / "snapshot_summary.md").write_text("\n".join(L) + "\n")
    print("analyze_snapshot:", dict(cats))


if __name__ == "__main__":
    main()
