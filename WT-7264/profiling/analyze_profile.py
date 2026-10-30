#!/usr/bin/env python3
"""Summarise WT-7264 perf data (pure stdlib; runs inside the w7264-prof sidecar or image).

Inputs in --dir: oncpu.perf.script[.gz], offcpu.perf.script[.gz] (optional), clock_offset.txt,
environment.txt. Optional --client-log: the run's client.log (S/B/T records, epoch ms).
Outputs: profile_summary.md, profile_summary.json, oncpu_stuck.folded.

Which threads are "stuck" is decided from timing alone, never from their stacks (so the stack result is
not force-fitted):
  * with --client-log: a stalled call is an insertMany call that took >= --stall-s seconds (or never
    returned). Its "alone window" is the part of the call after every other client thread had finished.
    The connection threads that are on-CPU for >= 30% of that window are the stuck threads; their samples
    over the whole stalled call are then summarised.
  * without it: connection threads that are >= 80% on-CPU in seconds where at most 3 connection threads
    are active.
The same function list is also reported for *all* connection-thread samples of the recording, which is
the like-for-like comparison between the bug arm and the fix arm.
Adapted from SERVER-52879/profiling/analyze_profile.py (same perf-script parsing).
"""
import argparse
import bisect
import collections
import gzip
import json
import re
import sys
from pathlib import Path

HDR_ON = re.compile(r"^\s*(.*?\S)\s+(\d+)\s+(\d+\.\d+):")
HDR_OFF = re.compile(r"^\s*(.*?\S)\s+(\d+)/(\d+)\s+(\d+\.\d+):\s+(\S+):\s*(.*)$")
FRAME = re.compile(r"^\s+([0-9a-f]+)\s+(.*?)\s*$")

# (label, matcher) in expected call order, outermost first. Matchers compare against the short name
# (argument list and "(anonymous namespace)::" removed).
FOCUS = [
    ("mongo::CollectionImpl::insertDocuments", lambda s: s.endswith("CollectionImpl::insertDocuments")),
    ("mongo::WiredTigerIndex::insert", lambda s: s.endswith("WiredTigerIndex::insert")),
    ("mongo::WiredTigerIndexUnique::_insert", lambda s: s.endswith("WiredTigerIndexUnique::_insert")),
    ("mongo::WiredTigerIndexUnique::_keyExists", lambda s: s.endswith("WiredTigerIndexUnique::_keyExists")),
    ("mongo::wiredTigerPrepareConflictRetry<...>", lambda s: "wiredTigerPrepareConflictRetry" in s),
    ("__curfile_search_near", lambda s: s == "__curfile_search_near"),
    ("__wt_btcur_search_near", lambda s: s == "__wt_btcur_search_near"),
    ("__curfile_next", lambda s: s == "__curfile_next"),
    ("__curfile_prev", lambda s: s == "__curfile_prev"),
    ("__wt_btcur_next[_prefix]", lambda s: s in ("__wt_btcur_next", "__wt_btcur_next_prefix")),
    ("__wt_btcur_prev[_prefix]", lambda s: s in ("__wt_btcur_prev", "__wt_btcur_prev_prefix")),
    ("__cursor_row_next", lambda s: s == "__cursor_row_next"),
    ("__cursor_row_prev", lambda s: s == "__cursor_row_prev"),
    ("__wt_txn_read", lambda s: s == "__wt_txn_read"),
    ("__wt_txn_read_upd_list", lambda s: s.startswith("__wt_txn_read_upd_list")),
    ("__wt_hs_find_upd", lambda s: s == "__wt_hs_find_upd"),
    ("any history-store cursor function (__curhs_* / __wt_hs_*)", lambda s: s.startswith("__curhs_") or s.startswith("__wt_hs_")),
    ("__cursor_row_slot_key_return", lambda s: s == "__cursor_row_slot_key_return"),
    ("__wt_lex_compare*", lambda s: s.startswith("__wt_lex_compare")),
    ("__wt_txn_upd_value_visible_all", lambda s: s == "__wt_txn_upd_value_visible_all"),
    ("__wt_row_search", lambda s: s == "__wt_row_search"),
    ("__wt_page_in_func", lambda s: s == "__wt_page_in_func"),
    ("__evict_force_check", lambda s: s == "__evict_force_check"),
    ("__wt_cache_eviction_worker", lambda s: s == "__wt_cache_eviction_worker"),
    ("KeyString::sizeWithoutRecordId*AtEnd", lambda s: "sizeWithoutRecordId" in s),
]
ANCHORS = ("WiredTigerIndexUnique::_keyExists", "WiredTigerIndexUnique::_insert")


DSO = re.compile(r" \((?:/|\[)[^()]*\)$")   # trailing " (/usr/bin/mongod)" or " ([kernel.kallsyms])"


def frame_name(sym):
    sym = DSO.sub("", sym)
    return sym.replace("+0x", "@").split("@")[0].strip() or "[unknown]"


def short(fr):
    s = fr.replace("(anonymous namespace)::", "")
    i = s.find("(")
    return s[:i] if i > 0 else s


def _open(path):
    path = Path(path)
    if path.exists():
        return open(path, errors="replace")
    return gzip.open(str(path) + ".gz", "rt", errors="replace")


def exists(path):
    return Path(path).exists() or Path(str(path) + ".gz").exists()


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


def gen_comm(c):
    return re.sub(r"\d+$", "*", c) if c.startswith("conn") else c


def load_oncpu(path, off_s):
    """Samples as (t_epoch, tid, comm, short-name stack leaf->root, full-name stack). Stacks are interned
    tuples (a 40 s recording of a busy mongod has ~10^5 samples but few distinct stacks)."""
    samples = []
    stacks, short_of = {}, {}
    for m, frames in read_samples(path):
        comm, tid, t = sys.intern(m.group(1).strip()), int(m.group(2)), float(m.group(3)) + off_s
        fr = tuple(f for f in frames if f and f != "[unknown]")
        fr = stacks.setdefault(fr, fr)
        sh = short_of.get(fr)
        if sh is None:
            sh = short_of[fr] = tuple(sys.intern(short(f)) for f in fr)
        samples.append((t, tid, comm, sh, fr))
    samples.sort(key=lambda s: s[0])
    return samples


def load_client(path):
    S, B, T = {}, {}, {}
    with open(path, errors="replace") as f:
        for line in f:
            p = line.strip().split(",")
            try:
                if p[0] == "S" and len(p) == 4:
                    S[(int(p[1]), int(p[2]))] = int(p[3]) / 1000.0
                elif p[0] == "B" and len(p) == 5:
                    B[(int(p[1]), int(p[2]))] = (int(p[3]) / 1000.0, int(p[4]) / 1000.0)
                elif p[0] == "T" and len(p) == 4:
                    T[int(p[1])] = int(p[3]) / 1000.0
            except ValueError:
                continue
    return S, B, T


_LABELS_CACHE = {}


def labels_of(names):
    """FOCUS labels present in one (interned) short-name stack; cached per distinct stack."""
    r = _LABELS_CACHE.get(names)
    if r is None:
        r = _LABELS_CACHE[names] = tuple(label for label, match in FOCUS if any(match(x) for x in names))
    return r


def focus_table(sample_list):
    n = len(sample_list)
    cnt = collections.Counter()
    for s in sample_list:
        for label in labels_of(s[3]):
            cnt[label] += 1
    return n, [(label, cnt.get(label, 0), round(100.0 * cnt.get(label, 0) / n, 1) if n else 0.0) for label, _ in FOCUS]


def top_leaves(sample_list, k=12):
    c = collections.Counter(s[3][0] if s[3] else "[unknown]" for s in sample_list)
    n = len(sample_list)
    return [(f, v, round(100.0 * v / n, 1)) for f, v in c.most_common(k)] if n else []


def top_stacks(sample_list, k=6):
    c = collections.Counter()
    for s in sample_list:
        names = s[3]
        idx = None
        for a in ANCHORS:
            idx = next((i for i, x in enumerate(names) if x.endswith(a)), None)
            if idx is not None:
                break
        if idx is None:
            continue
        # collapse consecutive duplicates (recursion / inlined wrappers) for readability
        seq = []
        for x in reversed(names[: idx + 1]):
            if not seq or seq[-1] != x:
                seq.append(x)
        c[" -> ".join(seq)] += 1
    n = len(sample_list)
    return [(st, v, round(100.0 * v / n, 1)) for st, v in c.most_common(k)] if n else []


TREE_KEEP = ("__curfile_search_near", "__wt_btcur_search_near", "__curfile_next", "__curfile_prev",
             "__wt_btcur_next", "__wt_btcur_prev", "__wt_btcur_next_prefix", "__wt_btcur_prev_prefix",
             "__cursor_row_next", "__cursor_row_prev", "__wt_txn_read", "__wt_hs_find_upd")


def tree_view(sample_list, root="WiredTigerIndexUnique::_keyExists", max_depth=6):
    """hs.png-style call tree under `root`: only the cursor/transaction frames named in TREE_KEEP, cut after
    __wt_hs_find_upd. Returns [(depth, name, samples)] in tree order and the number of samples under root."""
    tree = {}
    n_root = 0
    for s in sample_list:
        names = s[3]
        idx = next((i for i, x in enumerate(names) if x.endswith(root)), None)
        if idx is None:
            continue
        n_root += 1
        path = []
        for x in reversed(names[:idx]):          # root side first
            if x in TREE_KEEP and (not path or path[-1] != x):
                path.append(x)
            if x == "__wt_hs_find_upd":
                break
        node = tree
        for x in path[:max_depth]:
            ent = node.setdefault(x, [0, {}])
            ent[0] += 1
            node = ent[1]
    out = []

    def walk(node, depth):
        for name, (cnt, kids) in sorted(node.items(), key=lambda kv: -kv[1][0]):
            out.append((depth, name, cnt))
            walk(kids, depth + 1)
    walk(tree, 0)
    return out, n_root


def children_of(sample_list, fn="__wt_hs_find_upd"):
    """Where time goes inside `fn`: its direct callee in each sample that contains it (or `(self)`)."""
    c = collections.Counter()
    n = 0
    for s in sample_list:
        names = s[3]
        idx = next((i for i, x in enumerate(names) if x == fn), None)
        if idx is None:
            continue
        n += 1
        c[names[idx - 1] if idx > 0 else "(self)"] += 1
    return n, [(k, v, round(100.0 * v / n, 1)) for k, v in c.most_common(8)] if n else []


def find_stuck(samples, client, stall_s, freq):
    S, B, T = client
    end_rec = samples[-1][0] if samples else 0
    calls = []
    for key, t0 in S.items():
        if key in B:
            lat = B[key][1]
            if lat >= stall_s:
                calls.append({"thread": key[0], "batch": key[1], "start": t0, "end": t0 + lat, "lat_s": lat,
                              "returned": True})
        else:
            calls.append({"thread": key[0], "batch": key[1], "start": t0, "end": None, "lat_s": None,
                          "returned": False})
    calls = [c for c in calls if c["returned"] or (end_rec - c["start"]) >= stall_s]
    if not calls:
        return [], []
    stalled_threads = {c["thread"] for c in calls}
    others_done = max([t for th, t in T.items() if th not in stalled_threads] or [0])
    times = [s[0] for s in samples]
    stuck = {}
    for c in calls:
        # clip to the recording: a stall usually outlasts the perf window
        end = min(c["end"] if c["end"] is not None else end_rec, end_rec)
        a = max(c["start"], others_done)
        c["alone_window"] = [round(a, 3), round(end, 3)]
        if end - a < 0.5:
            c["note"] = "no alone window (other threads still running until the call ended)"
            continue
        i, j = bisect.bisect_left(times, a), bisect.bisect_right(times, end)
        per_tid = collections.Counter(s[1] for s in samples[i:j] if s[2].startswith("conn"))
        need = 0.30 * (end - a) * freq
        tids = [tid for tid, n in per_tid.items() if n >= need]
        c["stuck_tids"] = tids
        c["alone_window_samples_by_tid"] = dict(per_tid.most_common(5))
        for tid in tids:
            w = stuck.setdefault(tid, [c["start"], end])
            w[0], w[1] = min(w[0], c["start"]), max(w[1], end)
    return calls, [(tid, w[0], w[1]) for tid, w in stuck.items()]


def find_stuck_fallback(samples, freq):
    per_sec = collections.defaultdict(collections.Counter)
    for s in samples:
        if s[2].startswith("conn"):
            per_sec[int(s[0])][s[1]] += 1
    stuck = {}
    for sec, c in per_sec.items():
        active = [tid for tid, n in c.items() if n >= 0.3 * freq]
        if 1 <= len(active) <= 3:
            for tid in active:
                if c[tid] >= 0.8 * freq:
                    w = stuck.setdefault(tid, [sec, sec + 1])
                    w[0], w[1] = min(w[0], sec), max(w[1], sec + 1)
    return [(tid, a, b) for tid, (a, b) in stuck.items()]


def offcpu_for(path, off_s, tids, windows):
    """Blocked time of the stuck threads inside their stall windows, by blocking site.
    perf script prints the thread id in the profiled PID namespace in its header (`comm pid/tid`), which is
    what the on-CPU samples use, but the tracepoint fields (`prev_pid=`, `pid=`) carry the *global* pid.
    The header tid of a sched_switch is its prev task, which gives the global -> local mapping."""
    outs = collections.defaultdict(list)
    wakes_global = collections.defaultdict(list)
    g2l = {}
    counts = collections.Counter()
    for m, frames in read_samples(path, off=True):
        t, ev, trace = float(m.group(4)) + off_s, m.group(5), m.group(6)
        kv = dict(re.findall(r"(\w+)=(\S+)", trace))
        if ev.endswith("sched_switch"):
            local = int(m.group(3))
            try:
                g2l[int(kv.get("prev_pid", -1))] = local
            except ValueError:
                pass
            if local in tids:
                state = kv.get("prev_state", "R")
                counts[(local, state)] += 1
                outs[local].append((t, state, [short(f) for f in frames]))
        elif ev.endswith("sched_waking") or ev.endswith("sched_wakeup"):
            try:
                wakes_global[int(kv.get("pid", -1))].append(t)
            except ValueError:
                pass
    wakes = collections.defaultdict(list)
    for g, lst in wakes_global.items():
        if g in g2l:
            wakes[g2l[g]].extend(lst)
    res = collections.Counter()
    unmatched, unmatched_ms = 0, 0.0
    for tid, lst in outs.items():
        a, b = windows[tid]
        wl = sorted(wakes.get(tid, []))
        for i, (t0, state, fr) in enumerate(lst):
            if state.startswith("R") or state.lower().startswith("t") or not (a <= t0 <= b):
                continue  # preempted while runnable, or stopped by the gdb snapshot: not a wait
            t_next = lst[i + 1][0] if i + 1 < len(lst) else None
            j = bisect.bisect_right(wl, t0)
            if j < len(wl) and (t_next is None or wl[j] <= t_next):
                t1 = wl[j]
            else:
                # no recorded wakeup (e.g. woken from interrupt context): only an upper bound, which also
                # contains the time the thread then ran until its next switch-out -> reported separately
                unmatched += 1
                unmatched_ms += ((t_next or t0) - t0) * 1000.0
                continue
            j = " ".join(fr)
            site = ("cache eviction wait (__wt_cache_eviction_worker)" if "__wt_cache_eviction_worker" in j else
                    "page read / IO" if any(k in j for k in ("pread", "__wt_block_read", "__wt_bt_read")) else
                    "mutex/spinlock" if any(k in j for k in ("futex", "__lll_lock", "pthread_mutex")) else
                    "network (client)" if any(k in j for k in ("recv", "send", "poll")) else "other")
            res[site] += (t1 - t0) * 1000.0
    out = {k: round(v, 1) for k, v in res.most_common()}
    out["_waits_without_recorded_wakeup"] = {"count": unmatched, "upper_bound_ms": round(unmatched_ms, 1)}
    out["_switch_outs_by_state"] = {f"{tid}:{st}": n for (tid, st), n in sorted(counts.items())}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--client-log")
    ap.add_argument("--stall-s", type=float, default=3.0)
    ap.add_argument("--freq", type=float, default=999.0)
    args = ap.parse_args()
    d = Path(args.dir)
    off_s = float((d / "clock_offset.txt").read_text()) if (d / "clock_offset.txt").exists() else 0.0
    samples = load_oncpu(d / "oncpu.perf.script", off_s)
    by_comm = collections.Counter(gen_comm(s[2]) for s in samples)
    conn = [s for s in samples if s[2].startswith("conn")]
    res = {"samples_total": len(samples), "samples_by_thread": by_comm.most_common(12),
           "recording_epoch": [samples[0][0], samples[-1][0]] if samples else None}

    calls, stuck = [], []
    if args.client_log and Path(args.client_log).exists():
        calls, stuck = find_stuck(samples, load_client(args.client_log), args.stall_s, args.freq)
        method = (f"client log: insertMany calls >= {args.stall_s} s; threads >= 30% on-CPU while alone"
                  if calls else f"client log: no insertMany call >= {args.stall_s} s, so no stuck thread")
    else:
        stuck = find_stuck_fallback(samples, args.freq)
        method = "no client log: per-second heuristic (conn threads >= 80% on-CPU while <= 3 are active)"
    res["stall_calls"] = calls
    res["stuck_method"] = method
    res["stuck_threads"] = [{"tid": tid, "window_epoch": [round(a, 3), round(b, 3)]} for tid, a, b in stuck]

    win = {tid: (a, b) for tid, a, b in stuck}
    stuck_samples = [s for s in samples if s[1] in win and win[s[1]][0] <= s[0] <= win[s[1]][1]]
    n_st, ft_st = focus_table(stuck_samples)
    n_all, ft_all = focus_table(conn)
    tv, n_ke = tree_view(stuck_samples)
    n_hs, hs_children = children_of(stuck_samples)
    res["stuck"] = {"samples": n_st, "focus": ft_st, "leaves": top_leaves(stuck_samples),
                    "stacks": top_stacks(stuck_samples), "tree_keyExists": tv, "samples_in_keyExists": n_ke,
                    "inside_hs_find_upd": {"samples": n_hs, "children": hs_children}}
    res["all_conn"] = {"samples": n_all, "focus": ft_all, "leaves": top_leaves(conn)}
    # time series of the stuck threads' CPU (samples per second) for the summary
    if stuck_samples:
        t0 = min(a for a, b in win.values())
        per = collections.Counter(int(s[0] - t0) for s in stuck_samples)
        res["stuck"]["samples_per_second"] = [per.get(i, 0) for i in range(max(per) + 1)]
    with open(d / "oncpu_stuck.folded", "w") as f:
        folded = collections.Counter(";".join([gen_comm(s[2])] + list(reversed(s[4]))) for s in stuck_samples)
        for k, v in folded.items():
            f.write(f"{k} {v}\n")
    if stuck and exists(d / "offcpu.perf.script"):
        res["stuck_offcpu_ms"] = offcpu_for(d / "offcpu.perf.script", off_s, set(win), win)
    (d / "profile_summary.json").write_text(json.dumps(res, indent=1, default=list))

    env = (d / "environment.txt").read_text() if (d / "environment.txt").exists() else ""
    L = ["# Profile summary (WT-7264)", "", "```", env.strip(), "```", "",
         f"- on-CPU samples: {len(samples):,}; connection threads: {n_all:,}",
         "- busiest threads: " + ", ".join(f"{c} {n:,}" for c, n in by_comm.most_common(8)),
         f"- stuck-thread detection: {method or 'n/a'}", ""]
    if calls:
        L += ["## Stalled insertMany calls (client log)", "",
              "| client thread | batch | start (epoch s) | duration (s) | alone window (s) | stuck server tid(s) |",
              "|---|---|---|---|---|---|"]
        for c in calls:
            dur = f"{c['lat_s']:.1f}" if c["returned"] else "still running at end of log"
            aw = c.get("alone_window")
            aws = f"{aw[1] - aw[0]:.1f}" if aw else "-"
            L.append(f"| {c['thread']} | {c['batch']} | {c['start']:.3f} | {dur} | {aws} | "
                     f"{', '.join(str(x) for x in c.get('stuck_tids', [])) or c.get('note', '-')} |")
        L.append("")
    if stuck_samples:
        L += [f"## Stuck connection thread(s): {n_st:,} samples over their stalled calls", "",
              "Share of the stuck threads' samples whose stack contains each function (inclusive), next to the "
              "same share over **all** connection-thread samples of the recording:", "",
              "| function (outermost first) | stuck: samples | stuck: % | all conn threads: % |", "|---|---|---|---|"]
        for (label, n1, p1), (_, n2, p2) in zip(ft_st, ft_all):
            L.append(f"| `{label}` | {n1:,} | {p1} | {p2} |")
        L += ["", "Top leaf (self) functions, stuck threads:", "", "| leaf | samples | % |", "|---|---|---|"]
        L += [f"| `{f}` | {v:,} | {p} |" for f, v, p in res["stuck"]["leaves"]]
        L += ["", "Most common stacks of the stuck threads, from `WiredTigerIndexUnique::_keyExists` "
              "(or `_insert`) down to the leaf:", ""]
        L += [f"- {v:,} samples ({p}%): `{st}`" for st, v, p in res["stuck"]["stacks"]]
        if tv:
            L += ["", f"Call tree under `WiredTigerIndexUnique::_keyExists` ({n_ke:,} samples = 100%), cursor and "
                  "transaction frames only, cut at `__wt_hs_find_upd` (same view as the ticket's `hs.png`):", "", "```"]
            L += [f"{cnt:>9,} {100.0 * cnt / n_ke:5.1f}%  " + "  " * dep + name for dep, name, cnt in tv[:40]]
            L += ["```"]
        if n_hs:
            L += ["", f"Inside `__wt_hs_find_upd` ({n_hs:,} samples): its direct callees. Every lookup opens a "
                  "history-store cursor, positions it, and closes it again:", "", "| callee | samples | % |", "|---|---|---|"]
            L += [f"| `{k}` | {v:,} | {p} |" for k, v, p in hs_children]
        if "stuck_offcpu_ms" in res:
            oc = dict(res["stuck_offcpu_ms"])
            sw = oc.pop("_switch_outs_by_state", {})
            um = oc.pop("_waits_without_recorded_wakeup", {"count": 0, "upper_bound_ms": 0})
            L += ["", "Off-CPU time of the stuck threads inside their stalled calls (ms, by blocking site, waits "
                  "closed by a recorded wakeup only; preemptions while runnable are not waits): "
                  + (", ".join(f"{k} {v}" for k, v in oc.items()) or "none")
                  + f". Waits without a recorded wakeup: {um['count']} (upper bound {um['upper_bound_ms']} ms, which "
                  "includes the following run time, so it is not added in).",
                  "Switch-outs by thread:state (R = preempted while runnable, S = sleeping, D = uninterruptible "
                  "sleep, t/T = stopped by the gdb snapshot): " + ", ".join(f"{k} {v}" for k, v in sw.items())]
    else:
        L += ["## No stuck thread in this recording", "",
              "Function shares over all connection-thread samples:", "",
              "| function (outermost first) | samples | % |", "|---|---|---|"]
        L += [f"| `{label}` | {n:,} | {p} |" for label, n, p in ft_all]
    L += ["", "Top leaf (self) functions, all connection threads:", "", "| leaf | samples | % |", "|---|---|---|"]
    L += [f"| `{f}` | {v:,} | {p} |" for f, v, p in res["all_conn"]["leaves"]]
    L += ["", "Flame graphs: `oncpu_all.svg` (every mongod thread), `oncpu_stuck.svg` (stuck threads only).", ""]
    (d / "profile_summary.md").write_text("\n".join(L))
    print("analyze_profile: wrote", d / "profile_summary.md", f"(stuck samples {n_st}, conn samples {n_all})")


if __name__ == "__main__":
    main()
