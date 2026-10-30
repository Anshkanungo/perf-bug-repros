#!/usr/bin/env python3
"""Summarise SERVER-52879 perf data (pure stdlib; runs inside the s52879-prof sidecar).

Inputs in --dir: oncpu.perf.script, offcpu.perf.script (optional), threads.txt, environment.txt.
Outputs: profile_summary.md, profile_summary.json, offcpu_sweeps.folded, offcpu_long.folded.

On-CPU: samples of the WTIdleSessionSweeper thread ("WTIdleS.Sweeper") whose stack contains
closeExpiredIdleSessions are "sweep samples"; clustering them in time (gap <= 100 ms) gives the
sweep windows, i.e. the periods during which the session-cache mutex was held.
Off-CPU: each sched_switch of a mongod thread (state != R) opens a wait whose stack is the blocking
call chain; the matching sched_wakeup (emitted by the waking mongod thread, e.g. the sweeper
unlocking the mutex) closes it. Waits that start inside a sweep window are the waiting threads.
"""
import argparse
import bisect
import collections
import json
import re
import statistics
from pathlib import Path

HDR_ON = re.compile(r"^\s*(.*?\S)\s+(\d+)\s+(\d+\.\d+):")
HDR_OFF = re.compile(r"^\s*(.*?\S)\s+(\d+)/(\d+)\s+(\d+\.\d+):\s+(\S+):\s*(.*)$")
FRAME = re.compile(r"^\s+([0-9a-f]+)\s+(.*?)\s*$")

FOCUS = [
    "mongo::WiredTigerSessionCache::closeExpiredIdleSessions",
    "mongo::WiredTigerSession::~WiredTigerSession",
    "__session_close",
    "__session_close_cached_cursors",
    "__session_close_cursors",
    "__wt_session_close_cache",
    "__session_discard_dhandle",
    "__wt_cursor_close",
    "__curfile_close",
    "__wt_free_int",
    "free",
]


# Waits that are just idleness (a connection waiting for the client's next request, a background thread's
# timed sleep): kept in the tables, left out of the sweep-window flame graph so it shows contention only.
IDLE_WAITS = {"network recv (idle connection)", "condition variable wait", "sleep", "poll/epoll"}


def frame_name(sym):
    sym = sym.split(" (")[0] if sym.endswith(")") and " (" in sym else sym
    return sym.replace("+0x", "@").split("@")[0].strip() or "[unknown]"


def _open(path):
    """Open a perf script output, transparently using the .gz copy collect.sh leaves behind."""
    import gzip
    path = Path(path)
    if path.exists():
        return open(path, errors="replace")
    gz = Path(str(path) + ".gz")
    return gzip.open(gz, "rt", errors="replace")


def read_samples(path, off=False):
    """Yield (header-match, frames leaf->root)."""
    hdr, frames = None, []
    rx = HDR_OFF if off else HDR_ON
    with _open(path) as f:
        for line in f:
            if not line.strip():
                if hdr:
                    yield hdr, frames
                hdr, frames = None, []
                continue
            fm = FRAME.match(line) if line[0] in " \t" else None
            if fm and hdr:
                frames.append(frame_name(fm.group(2)))
                continue
            m = rx.match(line.rstrip("\n"))
            if m:
                if hdr:
                    yield hdr, frames
                hdr, frames = m, []
    if hdr:
        yield hdr, frames


def has(frames, needle):
    return any(needle in fr for fr in frames)


def classify_wait(frames):
    if has(frames, "WiredTigerSessionCache::getSession"):
        site = "WiredTigerSessionCache::getSession"
    elif has(frames, "WiredTigerSessionCache::releaseSession"):
        site = "WiredTigerSessionCache::releaseSession"
    elif has(frames, "closeExpiredIdleSessions"):
        site = "closeExpiredIdleSessions (sweeper)"
    else:
        site = None
    lockish = any(k in fr for fr in frames for k in ("__lll_lock_wait", "pthread_mutex_lock", "futex", "_lockSlowPath"))
    if site and lockish:
        return f"mutex wait in {site}"
    if site:
        return f"other wait in {site}"
    for k, label in (("recv", "network recv (idle connection)"), ("poll", "poll/epoll"),
                     ("condition_variable", "condition variable wait"), ("pthread_cond", "condition variable wait"),
                     ("nanosleep", "sleep"), ("__lll_lock_wait", "other mutex wait"),
                     ("pthread_mutex_lock", "other mutex wait"), ("fdatasync", "fsync/IO"), ("pwrite", "IO")):
        if has(frames, k):
            return label
    return "other"


def gen_comm(c):
    return re.sub(r"\d+$", "*", c) if c.startswith("conn") else c


def clean_frames(frames):
    """leaf->root list; drop leading kernel frames after the first futex/schedule marker for readability."""
    return [f for f in frames if f and f != "[unknown]"]


def analyze_oncpu(path):
    total = 0
    by_comm = collections.Counter()
    sweep_times = []
    focus = collections.Counter()
    leaf = collections.Counter()
    stacks = collections.Counter()
    sweeper_total = 0
    for m, frames in read_samples(path):
        comm, t = m.group(1).strip(), float(m.group(3))
        total += 1
        by_comm[gen_comm(comm)] += 1
        if not comm.startswith("WTIdleS"):
            continue
        sweeper_total += 1
        if not has(frames, "closeExpiredIdleSessions"):
            continue
        sweep_times.append(t)
        for fn in FOCUS:
            if any(fr == fn or fr.startswith(fn + "(") for fr in frames):
                focus[fn] += 1
        if frames:
            leaf[frames[0]] += 1
        # stack from closeExpiredIdleSessions down to the leaf
        idx = next(i for i, fr in enumerate(frames) if "closeExpiredIdleSessions" in fr)
        stacks[" <- ".join(frames[: idx + 1])] += 1
    n = len(sweep_times)
    sweep_times.sort()
    windows = []
    for t in sweep_times:
        if windows and t - windows[-1][1] <= 0.1:
            windows[-1][1] = t
            windows[-1][2] += 1
        else:
            windows.append([t, t, 1])
    return {
        "samples_total": total,
        "samples_by_thread": by_comm.most_common(12),
        "sweeper_samples": sweeper_total,
        "sweep_samples": n,
        "focus_inclusive_pct": {k: round(100.0 * v / n, 1) for k, v in focus.items()} if n else {},
        "leaf_top": [(k, round(100.0 * v / n, 1)) for k, v in leaf.most_common(15)] if n else [],
        "stacks_top": [(k, v) for k, v in stacks.most_common(5)],
        "windows": [{"start": w[0], "end": w[1], "dur_ms": round((w[1] - w[0]) * 1000 + 1, 1), "samples": w[2]}
                    for w in windows],
    }


def analyze_offcpu(path, windows, margin=0.005):
    """Pair each blocking switch-out of a mongod thread with its wakeup (sched_waking, or sched_wakeup in
    older recordings). If no wakeup was recorded, bound the blocked time by the thread's next switch-out
    (blocked + a short run), and say so ("upper bound")."""
    stacks = {}
    outs = collections.defaultdict(list)    # global tid -> [(t, comm, stack_id, state)]
    wakes = collections.defaultdict(list)   # global tid -> [t]
    n_switch = n_wake = 0
    for m, frames in read_samples(path, off=True):
        comm, t, ev, trace = m.group(1).strip(), float(m.group(4)), m.group(5), m.group(6)
        if ev.endswith("sched_switch"):
            n_switch += 1
            kv = dict(re.findall(r"(\w+)=(\S+)", trace))
            sid = stacks.setdefault(tuple(frames), len(stacks))
            outs[kv.get("prev_pid")].append((t, kv.get("prev_comm", comm), sid, kv.get("prev_state", "R")))
        elif ev.endswith("sched_wakeup") or ev.endswith("sched_waking"):
            n_wake += 1
            kv = dict(re.findall(r"(\w+)=(\S+)", trace))
            wakes[kv.get("pid")].append(t)
    frames_of = {v: list(k) for k, v in stacks.items()}
    waits = []
    for tid, lst in outs.items():
        wl = sorted(wakes.get(tid, []))
        for i, (t0, c, sid, state) in enumerate(lst):
            if state.startswith("R"):
                continue  # preempted, still runnable: not a wait
            t_next = lst[i + 1][0] if i + 1 < len(lst) else None
            j = bisect.bisect_right(wl, t0)
            if j < len(wl) and (t_next is None or wl[j] <= t_next):
                waits.append({"t0": t0, "dur": wl[j] - t0, "comm": c, "sid": sid, "exact": True})
            elif t_next is not None:
                waits.append({"t0": t0, "dur": t_next - t0, "comm": c, "sid": sid, "exact": False})
    wins = [(w["start"] - margin, w["end"] + margin) for w in windows]

    def win_of(t):
        for i, (a, b) in enumerate(wins):
            if a <= t <= b:
                return i
        return None

    def blank():
        return {"waits": 0, "threads": set(), "total_ms": 0.0, "max_ms": 0.0, "exact": 0}

    cat_sweep, cat_all = collections.defaultdict(blank), collections.defaultdict(blank)
    folded_sweep, folded_long = collections.Counter(), collections.Counter()
    per_window = [{"threads": set(), "max_ms": 0.0, "exact": 0} for _ in wins]
    example = None
    cat_cache = {}
    for w in waits:
        sid = w["sid"]
        if sid not in cat_cache:
            cat_cache[sid] = classify_wait(frames_of[sid])
        cat = cat_cache[sid]
        d_ms = w["dur"] * 1000.0
        wi = win_of(w["t0"])
        for tbl in ([cat_all] + ([cat_sweep] if wi is not None else [])):
            e = tbl[cat]
            e["waits"] += 1
            e["threads"].add(w["comm"])
            e["total_ms"] += d_ms
            e["max_ms"] = max(e["max_ms"], d_ms)
            e["exact"] += int(w["exact"])
        key = ";".join([gen_comm(w["comm"])] + list(reversed(clean_frames(frames_of[sid]))))
        if wi is not None and cat not in IDLE_WAITS:   # idle waits that merely started in the window
            folded_sweep[key] += int(w["dur"] * 1e6)
            if cat.startswith("mutex wait in WiredTigerSessionCache"):
                p = per_window[wi]
                p["threads"].add(w["comm"])
                p["max_ms"] = max(p["max_ms"], d_ms)
                p["exact"] += int(w["exact"])
                if example is None or d_ms > example[0]:
                    example = (d_ms, w["comm"], clean_frames(frames_of[sid]), w["exact"])
        if d_ms >= 10 and not cat.startswith("network recv"):
            folded_long[key] += int(w["dur"] * 1e6)

    def table(tbl):
        return sorted(({"category": k, "waits": v["waits"], "threads": len(v["threads"]),
                        "total_ms": round(v["total_ms"], 1), "max_ms": round(v["max_ms"], 1),
                        "exact": v["exact"]} for k, v in tbl.items()), key=lambda r: -r["total_ms"])

    return {
        "switch_events": n_switch, "wakeup_events": n_wake, "waits": len(waits),
        "waits_exact": sum(1 for w in waits if w["exact"]),
        "during_sweeps": table(cat_sweep), "all": table(cat_all),
        "per_window": [{"threads_blocked_on_session_cache": len(p["threads"]), "max_wait_ms": round(p["max_ms"], 1),
                        "exact_wakeups": p["exact"]} for p in per_window],
        "example_blocked": {"wait_ms": round(example[0], 1), "thread": example[1], "stack_leaf_first": example[2],
                            "exact": example[3]} if example else None,
    }, folded_sweep, folded_long


def client_overlap(client_log, windows):
    ops = []
    with open(client_log, errors="replace") as f:
        for line in f:
            if line.startswith("O,"):
                p = line.strip().split(",")
                if len(p) == 4:
                    s = int(p[2]) / 1000.0
                    ops.append((s, s + float(p[3]) / 1000.0, float(p[3])))
    res = []
    for w in windows:
        hit = [o for o in ops if o[0] <= w["end_epoch"] + 0.002 and o[1] >= w["start_epoch"] - 0.002]
        slow = [o for o in hit if o[2] >= 10]
        res.append({"ops_overlapping": len(hit), "ops_ge_10ms": len(slow),
                    "max_latency_ms": max((o[2] for o in hit), default=None)})
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--client-log")
    args = ap.parse_args()
    d = Path(args.dir)
    off_s = float((d / "clock_offset.txt").read_text()) if (d / "clock_offset.txt").exists() else 0.0
    on = analyze_oncpu(d / "oncpu.perf.script")
    for w in on["windows"]:  # perf timestamps are CLOCK_MONOTONIC; add epoch versions for correlation
        w["start_epoch"] = round(w["start"] + off_s, 4)
        w["end_epoch"] = round(w["end"] + off_s, 4)
    res = {"oncpu": on}
    folded_sweep = folded_long = None
    if (d / "offcpu.perf.script").exists() or (d / "offcpu.perf.script.gz").exists():
        off, folded_sweep, folded_long = analyze_offcpu(d / "offcpu.perf.script", on["windows"])
        res["offcpu"] = off
        (d / "offcpu_sweeps.folded").write_text("".join(f"{k} {v}\n" for k, v in folded_sweep.items()))
        (d / "offcpu_long.folded").write_text("".join(f"{k} {v}\n" for k, v in folded_long.items()))
    if args.client_log and Path(args.client_log).exists():
        res["client"] = client_overlap(args.client_log, on["windows"])
    (d / "profile_summary.json").write_text(json.dumps(res, indent=1, default=list))

    env = (d / "environment.txt").read_text() if (d / "environment.txt").exists() else ""
    L = ["# Profile summary (SERVER-52879)", "", "```", env.strip(), "```", "",
         "## On-CPU (perf, call graphs)", "",
         f"- samples: {on['samples_total']:,} total; WTIdleSessionSweeper thread: {on['sweeper_samples']:,}; "
         f"of those inside `closeExpiredIdleSessions`: **{on['sweep_samples']:,}**",
         f"- busiest threads: " + ", ".join(f"{c} {n:,}" for c, n in on["samples_by_thread"][:8]), ""]
    if on["sweep_samples"]:
        L += ["Share of sweep samples whose stack contains each function (inclusive):", "",
              "| function | % of sweep samples |", "|---|---|"]
        for fn in FOCUS:
            if fn in on["focus_inclusive_pct"]:
                L.append(f"| `{fn}` | {on['focus_inclusive_pct'][fn]} |")
        L += ["", "Top leaf (self) functions in sweep samples:", "", "| leaf function | % |", "|---|---|"]
        L += [f"| `{k}` | {v} |" for k, v in on["leaf_top"][:10]]
        L += ["", "Most common sweeper stacks (leaf first, down to `closeExpiredIdleSessions`):", ""]
        L += [f"- {v:,} samples: `{k}`" for k, v in on["stacks_top"][:3]]
    L += ["", "## Sweep windows (sweeper on-CPU inside closeExpiredIdleSessions, samples ≤100 ms apart)", ""]
    hdr = "| # | start (epoch s) | duration (ms) | samples |"
    sep = "|---|---|---|---|"
    if "offcpu" in res:
        hdr += " threads that blocked on the session-cache mutex | longest such wait (ms) |"
        sep += "---|---|"
    if "client" in res:
        hdr += " client inserts ≥10 ms overlapping | max client latency (ms) |"
        sep += "---|---|"
    L += [hdr, sep]
    for i, w in enumerate(on["windows"]):
        row = f"| {i + 1} | {w['start_epoch']:.3f} | {w['dur_ms']} | {w['samples']} |"
        if "offcpu" in res:
            p = res["offcpu"]["per_window"][i]
            row += f" {p['threads_blocked_on_session_cache']} | {p['max_wait_ms']} |"
        if "client" in res:
            c = res["client"][i]
            row += f" {c['ops_ge_10ms']} | {c['max_latency_ms']} |"
        L.append(row)
    if "offcpu" in res:
        off = res["offcpu"]
        L += ["", "## Off-CPU (sched_switch → sched_wakeup, call graphs)", "",
              f"- {off['switch_events']:,} switch-outs, {off['wakeup_events']:,} wakeup events, {off['waits']:,} blocking waits "
              f"({off['waits_exact']:,} closed by a recorded wakeup; the rest are bounded by the thread's next switch-out, "
              "i.e. blocked time plus a short run: an upper bound)",
              "", "Waits that **started inside a sweep window**:", "",
              "| blocking site | waits | distinct threads | total blocked (ms) | longest (ms) |", "|---|---|---|---|---|"]
        L += [f"| {r['category']} | {r['waits']} | {r['threads']} | {r['total_ms']} | {r['max_ms']} |" for r in off["during_sweeps"][:10]]
        L += ["", "(durations without a recorded wakeup are upper bounds; see above)"]
        L += ["", "All waits in the recording, for comparison:", "",
              "| blocking site | waits | distinct threads | total blocked (ms) | longest (ms) |", "|---|---|---|---|---|"]
        L += [f"| {r['category']} | {r['waits']} | {r['threads']} | {r['total_ms']} | {r['max_ms']} |" for r in off["all"][:10]]
        ex = off.get("example_blocked")
        if ex:
            L += ["", f"Longest session-cache wait during a sweep: {ex['wait_ms']} ms on thread `{ex['thread']}`"
                      f"{'' if ex['exact'] else ' (upper bound)'}. Stack (leaf first):", "", "```"] + ex["stack_leaf_first"][:40] + ["```"]
    L += ["", "Flame graphs: `oncpu_all.svg`, `oncpu_sweeper.svg`, `offcpu_sweeps.svg`, `offcpu_long.svg`.", ""]
    (d / "profile_summary.md").write_text("\n".join(L))
    print("analyze_profile: wrote", d / "profile_summary.md")


if __name__ == "__main__":
    main()
