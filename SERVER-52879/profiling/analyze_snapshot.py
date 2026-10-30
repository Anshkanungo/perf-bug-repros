#!/usr/bin/env python3
"""Classify the threads in a gdb 'thread apply all bt' snapshot (snapshot.txt) -> snapshot_summary.md."""
import argparse
import collections
import re
from pathlib import Path

THREAD = re.compile(r'^Thread (\d+) \(.*?LWP (\d+)')       # gdb 13: Thread 76 (LWP 98 "conn47"):
NAME = re.compile(r'"([^"]*)"')
FPWALK = re.compile(r'^Thread LWP (\d+) "([^"]*)" frame-pointer walk:')
FPFRAME = re.compile(r'^\s+fp#\d+ 0x[0-9a-f]+ (.+?)(?: \+ \d+)?$')
FRAME = re.compile(r"^#(\d+)\s+(?:0x[0-9a-f]+ in )?(.+?)(?: \(.*\))?(?: from .*| at .*)?$")


def func(line):
    m = FRAME.match(line)
    if not m:
        return None
    f = m.group(2)
    f = re.sub(r"\s*\(.*$", "", f)
    return f.strip()


def classify(frames):
    j = " | ".join(frames)
    if "closeExpiredIdleSessions" in j:
        return "sweeper: closing idle sessions in closeExpiredIdleSessions (4.4.3: under the session-cache mutex; 4.4.4: after releasing it)"
    lock = any(k in j for k in ("__lll_lock_wait", "pthread_mutex_lock", "_lockSlowPath", "futex"))
    if "WiredTigerSessionCache::getSession" in j and lock:
        return "BLOCKED on session-cache mutex in getSession()"
    if "WiredTigerSessionCache::releaseSession" in j and lock:
        return "BLOCKED on session-cache mutex in releaseSession()"
    if "WiredTigerSessionCache" in j:
        return "in WiredTigerSessionCache (other)"
    if any(k in j for k in ("recvmsg", "recv", "__libc_recv", "poll", "epoll_wait")) and "conn" in j:
        return "idle connection: waiting for next request"
    if any(k in j for k in ("recvmsg", "__libc_recv", "recv")):
        return "waiting in recv/poll"
    if "pthread_cond" in j or "condition_variable" in j:
        return "condition-variable wait (background thread)"
    if any(k in j for k in ("nanosleep", "sleep_for", "sleepmillis")):
        return "sleeping"
    if lock:
        return "other mutex wait"
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
    for t in threads:  # CFI frames first; append the frame-pointer walk when the CFI unwind stopped early
        if t["fp_frames"]:
            t["frames"] = t["frames"] + ["(frame-pointer walk:)"] + t["fp_frames"]
    cats = collections.Counter()
    by_cat = collections.defaultdict(list)
    for t in threads:
        c = classify(t["frames"])
        t["cat"] = c
        cats[c] += 1
        by_cat[c].append(t)
    L = ["# gdb all-thread snapshot during a sweep (SERVER-52879)", "", "```", meta.strip(), "```", "",
         f"{len(threads)} threads.", "", "| state | threads | example thread names |", "|---|---|---|"]
    for c, n in cats.most_common():
        names = ", ".join(sorted({t["name"] for t in by_cat[c]})[:6])
        L.append(f"| {c} | {n} | {names} |")
    for c in ("sweeper: closing idle sessions in closeExpiredIdleSessions (4.4.3: under the session-cache mutex; 4.4.4: after releasing it)",
              "BLOCKED on session-cache mutex in getSession()",
              "BLOCKED on session-cache mutex in releaseSession()"):
        if by_cat.get(c):
            t = by_cat[c][0]
            L += ["", f"Example, {c}: thread `{t['name']}` (LWP {t['lwp']}), frames #0..:", "", "```"]
            L += [f"#{i:<2} {f}" for i, f in enumerate(t["frames"][:30])] + ["```"]
    (d / "snapshot_summary.md").write_text("\n".join(L) + "\n")
    print("analyze_snapshot:", dict(cats))


if __name__ == "__main__":
    main()
