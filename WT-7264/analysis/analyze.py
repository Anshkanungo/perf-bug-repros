#!/usr/bin/env python3
"""WT-7264 / SERVER-67350 analysis.

  analyze.py RUN_DIR [RUN_DIR ...]                      per-run summaries (each RUN_DIR = results/runs/<label>)
  analyze.py RUN_DIR ... --compare-out results          + cross-run results/summary.md, plots, criteria

Per run it writes: summary.json, summary.md, calls.csv (one row per insertMany call), per_second.csv
(1 Hz server counters joined with client progress), timeline.png.

Definitions (fixed in PLAN.md before the main runs):
  stalled call  = an insertMany call that took >= STALL_S (3 s), or was still running when the run ended
                  (cap or end of log); its duration is then a lower bound.
  stalled run   = a run with >= 1 stalled call.
  HS misses     = increase of wiredTiger.cache "history store table reads missed" over the insert phase.
  stall share   = fraction of the run's HS-miss increase that happened while some call had already been
                  running for >= STALL_S.
  noisy run     = other (non-w7264) containers used >= 200% CPU in any docker-stats sample of the insert phase.
"""
import argparse
import collections
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

STALL_S = 3.0
NOISE_CPU_PCT = 200.0
# Validated categorical slots (dataviz reference palette, light surface)
BLUE, ORANGE, GREEN, PURPLE, RED = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6", "#d03b3b"
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"

CACHE_KEYS = {
    "hs_reads": "history store table reads",
    "hs_misses": "history store table reads missed",
    "hs_inserts": "history store table insert calls",
    "app_evicted": "pages evicted by application threads",
    "forced_evict": "forced eviction - pages selected count",
    "pages_read": "pages read into cache",
    "cache_bytes": "bytes currently in the cache",
    "dirty_bytes": "tracked dirty bytes in the cache",
}
CURSOR_KEYS = {
    "search_near": "cursor search near calls",
    "next": "cursor next calls",
    "prev": "cursor prev calls",
    "skip_next": "Total number of entries skipped by cursor next calls",
    "skip_prev": "Total number of entries skipped by cursor prev calls",
    "prefix_exits": "Total number of times a search near has exited due to prefix config",
}
TXN_KEYS = {
    "ckpt_running": "transaction checkpoint currently running",
    "ckpts": "transaction checkpoints",
    "ckpt_last_ms": "transaction checkpoint most recent time (msecs)",
    "pinned_range": "transaction range of IDs currently pinned",
}


def style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


# ----------------------------------------------------------------------------- loading
def load_client(run):
    P, S, B, T = {}, {}, {}, {}
    path = run / "raw" / "client.log"
    for line in open(path, errors="replace"):
        p = line.strip().split(",")
        try:
            if p[0] == "P" and len(p) == 3:
                P[p[1]] = int(p[2])
            elif p[0] == "S" and len(p) == 4:
                S[(int(p[1]), int(p[2]))] = int(p[3])
            elif p[0] == "B" and len(p) == 5:
                B[(int(p[1]), int(p[2]))] = (int(p[3]), int(p[4]))
            elif p[0] == "T" and len(p) == 4:
                T[int(p[1])] = int(p[3])
        except ValueError:
            continue
    rows = []
    for (th, b), st in S.items():
        if (th, b) in B:
            rows.append((th, b, st, B[(th, b)][1] / 1000.0, True))
        else:
            rows.append((th, b, st, np.nan, False))
    calls = pd.DataFrame(rows, columns=["thread", "batch", "start_ms", "lat_s", "returned"])
    calls = calls.sort_values(["thread", "batch"]).reset_index(drop=True)
    return P, calls, T


def load_server(run):
    path = run / "raw" / "serverstatus.jsonl"
    recs = []
    if not path.exists():
        return pd.DataFrame()
    for line in open(path):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "error" in r:
            continue
        wt = r.get("wt", {})
        cache, cur, txn = wt.get("cache", {}), wt.get("cursor", {}), wt.get("transaction", {})
        rec = {"t_ms": r["t_resp_ms"], "t_req_ms": r["t_req_ms"],
               "inserts": r.get("opcounters", {}).get("insert"),
               "w_ops": r.get("opLatencies", {}).get("writes", {}).get("ops"),
               "w_lat_us": r.get("opLatencies", {}).get("writes", {}).get("latency"),
               "active_writers": r.get("globalLock", {}).get("activeClients", {}).get("writers")}
        for k, name in CACHE_KEYS.items():
            rec[k] = cache.get(name)
        for k, name in CURSOR_KEYS.items():
            rec[k] = cur.get(name)
        for k, name in TXN_KEYS.items():
            rec[k] = txn.get(name)
        recs.append(rec)
    s = pd.DataFrame(recs)
    for c in s.columns:
        s[c] = pd.to_numeric(s[c], errors="coerce")
    return s


def load_threads(run, t0_ms):
    """Per-second CPU fraction of each mongod connection thread (from the sampler's /proc reads)."""
    path = run / "raw" / "threads.jsonl"
    if not path.exists():
        return None
    hz, prev, out = 100, None, []
    for line in open(path):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "clk_tck" in r:
            hz = r["clk_tck"]
            continue
        if prev is not None:
            dt = (r["t_ms"] - prev["t_ms"]) / 1000.0
            if dt > 0:
                busy, conn_cpu, total = 0, 0.0, 0.0
                for tid, (comm, ticks) in r["threads"].items():
                    if tid in prev["threads"]:
                        f = (ticks - prev["threads"][tid][1]) / hz / dt
                        total += f
                        if comm.startswith("conn"):
                            conn_cpu += f
                            busy += f >= 0.9
                out.append({"t_s": (r["t_ms"] - t0_ms) / 1000.0, "conn_threads_ge90": busy,
                            "conn_cpu_cores": round(conn_cpu, 2), "mongod_cpu_cores": round(total, 2)})
        prev = r
    return pd.DataFrame(out)


def load_docker_stats(run, t0_ms, t1_ms):
    path = run / "raw" / "docker_stats.txt"
    if not path.exists():
        return None
    others, ours = {}, {}
    for line in open(path, errors="replace"):
        ts, _, js = line.partition(" ")
        try:
            r = json.loads(js)
            ts = int(ts)
        except (ValueError, json.JSONDecodeError):
            continue
        if not (t0_ms / 1000.0 - 1 <= ts <= t1_ms / 1000.0 + 1):
            continue
        cpu = float(r.get("CPUPerc", "0%").rstrip("%") or 0)
        name = r.get("Name", "")
        if name.startswith("w7264-"):
            ours.setdefault(name, []).append(cpu)
        else:
            others[ts] = others.get(ts, 0.0) + cpu
    v = sorted(others.values())
    return {"other_cpu_median_pct": v[len(v) // 2] if v else None, "other_cpu_peak_pct": v[-1] if v else None,
            "other_samples": len(v),
            "mongod_cpu_peak_pct": max(ours.get("w7264-mongod", [0]) or [0]),
            "series_other": sorted(others.items())}


def load_slow(run):
    path = run / "raw" / "mongod.log"
    out = []
    if not path.exists():
        return out
    for line in open(path, errors="replace"):
        if '"Slow query"' not in line or '"insert"' not in line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        a = d.get("attr", {})
        st = a.get("storage", {})
        out.append({"ms": a.get("durationMillis"), "ninserted": a.get("ninserted"), "ctx": d.get("ctx"),
                    "bytesRead": st.get("data", {}).get("bytesRead"),
                    "cacheWaitMicros": st.get("timeWaitingMicros", {}).get("cache")})
    return out


# ----------------------------------------------------------------------------- per run
def bracket(s, col, lo_ms, hi_ms):
    """Samples bracketing the insert phase: the last sample taken before it started and the first one
    taken at least 0.5 s after it ended (or the last sample)."""
    w = s.dropna(subset=[col])
    before = w[w["t_req_ms"] <= lo_ms]
    after = w[w["t_req_ms"] >= hi_ms + 500]
    a = before.iloc[-1] if len(before) else (w.iloc[0] if len(w) else None)
    b = after.iloc[0] if len(after) else (w.iloc[-1] if len(w) else None)
    return a, b


def delta(s, col, lo_ms, hi_ms):
    if s.empty or col not in s or s[col].isna().all():
        return None
    a, b = bracket(s, col, lo_ms, hi_ms)
    if a is None or b is None:
        return None
    return float(b[col] - a[col])


def stall_type(stalled, d, share):
    """EXPLORATORY (added 2026-10-28 after battery runs of 4.2.24 stalled; not a criterion): what kind of
    stall a stalled run had, from server counters over the insert phase.
      history-store walk : >= 10^6 history-store reads missed, >= 50% of them while a call was stuck
                           (the WT-7264 mechanism on 4.4.2+ / 5.0)
      in-memory walk     : >= 5x10^7 cursor entries skipped by next/prev, < 10^6 HS misses (4.4.1's form)
      eviction           : >= 5x10^4 pages evicted by application threads and no HS-walk signature
                           (all threads at once; seen on battery / Low Power Mode, including on 4.2.24)
    """
    if not stalled:
        return "none"
    hs = d.get("hs_misses")
    skipped = (d.get("skip_next") or 0) + (d.get("skip_prev") or 0)
    if hs is not None and hs >= 1e6 and (share or 0) >= 0.5:
        return "history-store walk"
    if skipped >= 5e7 and (hs is None or hs < 1e6):
        return "in-memory walk"
    if (d.get("app_evicted") or 0) >= 5e4:
        return "eviction"
    return "other"


def analyze_run(run):
    meta = json.load(open(run / "meta.json"))
    server = json.load(open(run / "server.json")) if (run / "server.json").exists() else {}
    outcome = json.load(open(run / "outcome.json")) if (run / "outcome.json").exists() else {}
    P, calls, T = load_client(run)
    t0 = P.get("insert_start", int(calls["start_ms"].min()) if len(calls) else 0)
    capped = bool(outcome.get("capped"))
    last_evt = max([t0] + [int(x) for x in (calls["start_ms"] + calls["lat_s"].fillna(0) * 1000)] + list(T.values()))
    t_end = P.get("insert_end", last_evt)
    if capped or "insert_end" not in P:
        t_end = max(last_evt, t0 + int(outcome.get("cap_s", 0)) * 1000 if capped else last_evt)
    phase_s = (t_end - t0) / 1000.0

    calls["start_s"] = (calls["start_ms"] - t0) / 1000.0
    calls["dur_s"] = calls["lat_s"].where(calls["returned"], (t_end - calls["start_ms"]) / 1000.0)
    calls["stalled"] = (calls["dur_s"] >= STALL_S) | (~calls["returned"])
    calls.to_csv(run / "calls.csv", index=False)
    done = calls[calls["returned"]]
    stalled = calls[calls["stalled"]]
    thread_end = {th: (t - t0) / 1000.0 for th, t in T.items()}
    ends = sorted(thread_end.values())
    srv = load_server(run)
    thr = load_threads(run, t0)
    dstats = load_docker_stats(run, t0, t_end)
    slow = load_slow(run)

    # counters over the insert phase
    d = {k: delta(srv, k, t0, t_end) for k in list(CACHE_KEYS) + list(CURSOR_KEYS) + ["inserts", "ckpts"]
         if k not in ("cache_bytes", "dirty_bytes")}
    # stall share of HS misses: increments in sample intervals that end inside a window where some call has
    # been running for >= STALL_S
    share = None
    stall_windows = []
    for _, c in stalled.iterrows():
        a = c["start_ms"] + STALL_S * 1000
        b = c["start_ms"] + c["dur_s"] * 1000
        stall_windows.append((a, b))
    if not srv.empty and srv["hs_misses"].notna().any():
        a, b = bracket(srv, "hs_misses", t0, t_end)
        s = srv[(srv["t_ms"] >= a["t_ms"]) & (srv["t_ms"] <= b["t_ms"])].dropna(subset=["hs_misses"])
        inc = s["hs_misses"].diff().fillna(0).clip(lower=0)
        mid = (s["t_ms"] + s["t_ms"].shift(1)) / 2
        inside = mid.apply(lambda m: any(a <= m <= b + 1000 for a, b in stall_windows))
        tot = float(inc.sum())
        share = float(inc[inside].sum() / tot) if tot > 0 else None
    # checkpoints during the run
    ck = {}
    if not srv.empty and srv["ckpt_running"].notna().any():
        s = srv[(srv["t_ms"] >= t0) & (srv["t_ms"] <= t_end)]
        ck = {"checkpoints_completed": d.get("ckpts"),
              "seconds_with_checkpoint_running": int((s["ckpt_running"] > 0).sum()),
              "checkpoint_running_during_stalls": bool(any(
                  ((s["t_ms"] >= a) & (s["t_ms"] <= b) & (s["ckpt_running"] > 0)).any() for a, b in stall_windows)),
              "last_checkpoint_ms_max": float(s["ckpt_last_ms"].max()) if s["ckpt_last_ms"].notna().any() else None}
    alone = None
    if thr is not None and not thr.empty and len(stalled):
        # seconds after every non-stalled thread had finished but while a stalled call was running
        others = [v for th, v in thread_end.items() if th not in set(stalled["thread"])]
        if others:
            a = max(others)
            b = max(float(c["start_s"] + c["dur_s"]) for _, c in stalled.iterrows())
            w = thr[(thr["t_s"] > a + 1) & (thr["t_s"] <= b)]
            if len(w):
                alone = {"window_s": [round(a, 1), round(b, 1)],
                         "conn_threads_ge90_median": float(w["conn_threads_ge90"].median()),
                         "mongod_cpu_cores_median": round(float(w["mongod_cpu_cores"].median()), 2)}
    noisy = bool(dstats and dstats["other_cpu_peak_pct"] is not None and dstats["other_cpu_peak_pct"] >= NOISE_CPU_PCT)
    # Host pause (e.g. the laptop slept): the host-side `docker stats` stream stops while the VM is frozen.
    host_gap = 0.0
    if dstats and dstats.get("series_other"):
        ts = [t for t, _ in dstats["series_other"]]
        host_gap = float(max([b - a for a, b in zip(ts, ts[1:])] or [0]))
    # EXPLORATORY (added after block A): noise during the first 10 s only, where every stall starts. The
    # pre-registered flag above marks almost every long run, because the bursts recur every ~30 s.
    onset = [v for ts, v in (dstats or {}).get("series_other", []) if t0 / 1000.0 - 1 <= ts <= t0 / 1000.0 + 10]
    onset_peak = max(onset) if onset else None
    noisy_onset = bool(onset_peak is not None and onset_peak >= NOISE_CPU_PCT)
    params = server.get("parameters", {})
    # Host power source (PLAN.md change 7): recorded live by run.sh (meta/outcome) or reconstructed from
    # `pmset -g log` into power.json by analysis/power_from_pmset.py (which also flags battery tags inside).
    power = {}
    pj = json.load(open(run / "power.json")) if (run / "power.json").exists() else {}
    if "power_start" in meta:
        power = {"start": meta["power_start"].get("source"), "end": outcome.get("power_end", {}).get("source"),
                 "low_power_mode_start": meta["power_start"].get("low_power_mode"), "how": "recorded by run.sh"}
    elif pj:
        power = {"start": pj["power_start"]["source"], "end": pj["power_end"]["source"], "how": "pmset -g log"}
    if pj:
        power["battery_tag_inside_run"] = pj.get("battery_tag_inside_run")
    whole_ac = bool(power) and power.get("start") == "AC Power" and power.get("end") == "AC Power" \
        and not power.get("battery_tag_inside_run")
    summary = {
        "label": meta["label"], "workload": meta.get("workload"),
        "version": server.get("version"), "gitVersion": server.get("gitVersion"),
        "prefix_search": params.get("wiredTigerPrefixSearchForUniqueIndexes"),
        "sync_start": bool(meta.get("sync_start")), "non_unique": bool(meta.get("non_unique")),
        "profiled": bool(meta.get("profile")),
        "cache_gb": meta.get("cache_gb"), "wt_cache_max_bytes": server.get("wt_cache_max_bytes"),
        "capped": capped, "cap_s": outcome.get("cap_s"), "insert_phase_s": round(phase_s, 2),
        "threads": int(calls["thread"].nunique()) if len(calls) else 0,
        "calls": int(len(calls)), "calls_returned": int(calls["returned"].sum()),
        "docs_inserted_server": d.get("inserts"),
        "call_latency_s": {q: float(np.percentile(done["lat_s"], p)) for q, p in
                           (("p50", 50), ("p90", 90), ("p99", 99), ("max", 100))} if len(done) else {},
        "longest_call_s": float(calls["dur_s"].max()) if len(calls) else None,
        "stalled_calls": int(len(stalled)), "stalled_threads": int(stalled["thread"].nunique()),
        "stalled": bool(len(stalled) > 0),
        "stalls": [{"thread": int(c["thread"]), "batch": int(c["batch"]), "start_s": round(float(c["start_s"]), 3),
                    "dur_s": round(float(c["dur_s"]), 2), "returned": bool(c["returned"])}
                   for _, c in stalled.sort_values("dur_s", ascending=False).iterrows()],
        "thread_end_s": {"median": float(np.median(ends)) if ends else None, "max": ends[-1] if ends else None},
        "straggler_gap_s": round(ends[-1] - float(np.median(ends)), 2) if ends else None,
        "first_call_s": {"median": float(calls[calls["batch"] == 0]["dur_s"].median()) if len(calls) else None,
                         "max": float(calls[calls["batch"] == 0]["dur_s"].max()) if len(calls) else None},
        "counters": d, "hs_misses": d.get("hs_misses"), "hs_misses_stall_share": share,
        "entries_skipped": (d.get("skip_next") or 0) + (d.get("skip_prev") or 0)
        if d.get("skip_next") is not None else None,
        "checkpoints": ck, "alone_window": alone,
        "docker": {k: v for k, v in (dstats or {}).items() if k != "series_other"}, "noisy": noisy,
        "other_cpu_peak_first10s_pct": onset_peak, "noisy_onset": noisy_onset,
        "host_stream_max_gap_s": host_gap,
        "power": power, "whole_run_on_ac": whole_ac,
        "stall_type": stall_type(len(stalled) > 0, d, share),
        "slow_inserts_ge_1s": [x for x in slow if (x["ms"] or 0) >= 1000],
    }
    (run / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    write_per_second(run, srv, thr, calls, t0)
    write_run_md(run, summary)
    plot_run(run, summary, calls, srv, thr, dstats, t0, t_end)
    return summary


def write_per_second(run, srv, thr, calls, t0):
    """1 Hz time series: server counter rates, client calls in flight, mongod per-thread CPU."""
    if srv.empty:
        return
    d = pd.DataFrame({"t_s": ((srv["t_ms"] - t0) / 1000.0).round(3)})
    dt = srv["t_ms"].diff() / 1000.0
    for col, name in (("inserts", "docs_inserted_per_s"), ("hs_misses", "hs_reads_missed_per_s"),
                      ("hs_reads", "hs_reads_per_s"), ("search_near", "search_near_calls_per_s"),
                      ("app_evicted", "pages_evicted_by_app_threads_per_s"), ("pages_read", "pages_read_per_s")):
        d[name] = (srv[col].diff() / dt).round(1) if srv[col].notna().any() else np.nan
    if srv["skip_next"].notna().any():
        d["cursor_entries_skipped_per_s"] = ((srv["skip_next"] + srv["skip_prev"]).diff() / dt).round(1)
    d["active_writers"] = srv["active_writers"]
    d["checkpoint_running"] = srv["ckpt_running"]
    d["cache_bytes"] = srv["cache_bytes"]
    if len(calls):
        st = calls["start_s"].values
        en = (calls["start_s"] + calls["dur_s"]).values
        d["calls_in_flight"] = [int(((st <= t) & (en > t)).sum()) for t in d["t_s"]]
        d["calls_in_flight_ge_3s"] = [int(((st + STALL_S <= t) & (en > t)).sum()) for t in d["t_s"]]
    if thr is not None and not thr.empty:
        m = pd.merge_asof(d.sort_values("t_s"), thr.sort_values("t_s"), on="t_s", direction="nearest",
                          tolerance=1.0)
        d = m
    d.to_csv(run / "per_second.csv", index=False)


def fmt(x, nd=1):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    if isinstance(x, (int, np.integer)) or (isinstance(x, float) and abs(x) >= 1000):
        return f"{x:,.0f}"
    return f"{x:.{nd}f}"


def write_run_md(run, s):
    L = [f"# Run `{s['label']}`", "",
         f"- mongod **{s['version']}** (`{(s['gitVersion'] or '')[:10]}`), workload `{s['workload']}`"
         f"{' (sync start)' if s['sync_start'] else ''}{' (NON-unique control)' if s['non_unique'] else ''}, "
         f"`wiredTigerPrefixSearchForUniqueIndexes` = {s['prefix_search']}, WT cache {s['cache_gb']} GB",
         f"- insert phase: **{s['insert_phase_s']} s**{' (CAPPED: client killed at the cap)' if s['capped'] else ''}; "
         f"{s['calls_returned']}/{s['calls']} insertMany calls returned; {fmt(s['docs_inserted_server'])} docs inserted (server)",
         f"- call latency p50 / p99 / max (returned calls): "
         + " / ".join(fmt(s["call_latency_s"].get(k), 2) for k in ("p50", "p99", "max")) + " s",
         f"- **stalled calls (≥ {STALL_S:.0f} s or never returned): {s['stalled_calls']}** on {s['stalled_threads']} thread(s); "
         f"longest call {fmt(s['longest_call_s'], 2)} s; stall type (exploratory): {s.get('stall_type')}",
         f"- host power: {(s.get('power') or {}).get('start', '?')} → {(s.get('power') or {}).get('end', '?')}"
         f"{' (battery = Low Power Mode on this laptop)' if 'Battery' in str(s.get('power')) else ''}",
         f"- thread finish time median / last: {fmt(s['thread_end_s']['median'], 2)} / {fmt(s['thread_end_s']['max'], 2)} s "
         f"(straggler gap {fmt(s['straggler_gap_s'], 2)} s)",
         f"- history store reads missed: **{fmt(s['hs_misses'])}** "
         f"({'–' if s['hs_misses_stall_share'] is None else f'{100 * s['hs_misses_stall_share']:.0f}%'} while a call had been running ≥ {STALL_S:.0f} s); "
         f"cursor entries skipped (next+prev): {fmt(s['entries_skipped'])}; "
         f"search_near calls: {fmt(s['counters'].get('search_near'))}; prefix-search early exits: {fmt(s['counters'].get('prefix_exits'))}",
         f"- eviction: pages evicted by application threads {fmt(s['counters'].get('app_evicted'))}, "
         f"forced-eviction pages selected {fmt(s['counters'].get('forced_evict'))}, pages read into cache {fmt(s['counters'].get('pages_read'))}",
         f"- checkpoints: {s['checkpoints']}",
         f"- noise: other containers' CPU median / peak {fmt(s['docker'].get('other_cpu_median_pct'))} / "
         f"{fmt(s['docker'].get('other_cpu_peak_pct'))} % ({s['docker'].get('other_samples')} samples) → "
         f"{'**NOISY**' if s['noisy'] else 'not noisy'}; w7264-mongod peak {fmt(s['docker'].get('mongod_cpu_peak_pct'))} %",
         ]
    if s["alone_window"]:
        a = s["alone_window"]
        L.append(f"- while only stalled calls were left ({a['window_s'][0]}–{a['window_s'][1]} s): median "
                 f"{a['conn_threads_ge90_median']:.0f} connection thread(s) at ≥90% CPU, mongod {a['mongod_cpu_cores_median']} cores")
    if s["stalls"]:
        L += ["", "| client thread | batch | start (s) | duration (s) | returned |", "|---|---|---|---|---|"]
        L += [f"| {x['thread']} | {x['batch']} | {x['start_s']} | {x['dur_s']} | {x['returned']} |" for x in s["stalls"][:20]]
    if s["slow_inserts_ge_1s"]:
        L += ["", "mongod slow-query log, insert commands ≥ 1 s:", "",
              "| conn | ms | docs | bytes read | cache wait (ms) |", "|---|---|---|---|---|"]
        L += [f"| {x['ctx']} | {x['ms']} | {x['ninserted']} | {fmt(x['bytesRead'])} | "
              f"{fmt((x['cacheWaitMicros'] or 0) / 1000.0)} |" for x in s["slow_inserts_ge_1s"][:10]]
    L += ["", "Plot: `timeline.png`. Per call: `calls.csv`. Raw data: `raw/` (git-ignored).", ""]
    (run / "summary.md").write_text("\n".join(L))


def plot_run(run, s, calls, srv, thr, dstats, t0, t_end):
    fig, axes = plt.subplots(4, 1, figsize=(11, 9.5), sharex=True, facecolor=SURFACE,
                             gridspec_kw={"height_ratios": [2.2, 1.2, 1.2, 1.2]})
    for ax in axes:
        style(ax)
    ax = axes[0]
    ok = calls[~calls["stalled"]]
    st = calls[calls["stalled"]]
    ax.scatter(ok["start_s"], ok["dur_s"].clip(lower=0.001), s=7, color=BLUE, alpha=0.6, label="insertMany call")
    for _, c in st.iterrows():
        ax.hlines(c["dur_s"], c["start_s"], c["start_s"] + c["dur_s"], color=ORANGE, linewidth=2)
        ax.scatter([c["start_s"]], [c["dur_s"]], s=30, color=ORANGE, zorder=3,
                   marker="o" if c["returned"] else ">")
    if len(st):
        ax.plot([], [], color=ORANGE, linewidth=2, label=f"stalled call (≥{STALL_S:.0f} s), bar = how long it ran")
    ax.axhline(STALL_S, color=MUTED, linestyle="--", linewidth=0.8)
    ax.set_yscale("log")
    ax.set_ylabel("call latency (s)", color=INK2, fontsize=9)
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    title = (f"{s['version']}  prefix_search={s['prefix_search']}  {s['workload']}"
             f"{' sync-start' if s['sync_start'] else ''}{' NON-UNIQUE' if s['non_unique'] else ''}: "
             f"{s['insert_phase_s']} s{' (CAPPED)' if s['capped'] else ''}, "
             f"{s['stalled_calls']} stalled call(s), longest {s['longest_call_s']:.1f} s")
    ax.set_title(title, loc="left", fontsize=10, color=INK)

    ax = axes[1]
    if not srv.empty:
        x = (srv["t_ms"] - t0) / 1000.0
        dt = srv["t_ms"].diff() / 1000.0
        ax.plot(x, (srv["inserts"].diff() / dt).clip(lower=0), color=BLUE, linewidth=1.2, label="docs inserted/s (server)")
    # client threads still running
    if len(calls):
        ends = calls.groupby("thread").apply(lambda g: float((g["start_s"] + g["dur_s"]).max()), include_groups=False)
        tt = np.linspace(0, max(1.0, (t_end - t0) / 1000.0), 400)
        ax2 = ax.twinx()
        ax2.step(tt, [(ends > v).sum() for v in tt], color=ORANGE, linewidth=1.2, where="post")
        ax2.set_ylabel("client threads\nstill inserting", color=ORANGE, fontsize=8)
        ax2.tick_params(colors=ORANGE, labelsize=8)
        ax2.spines["top"].set_visible(False)
    ax.set_ylabel("docs/s", color=INK2, fontsize=9)
    ax.legend(loc="upper right", fontsize=8, frameon=False)

    ax = axes[2]
    if not srv.empty and srv["hs_misses"].notna().any():
        x = (srv["t_ms"] - t0) / 1000.0
        dt = srv["t_ms"].diff() / 1000.0
        ax.plot(x, (srv["hs_misses"].diff() / dt).clip(lower=0), color=RED, linewidth=1.2,
                label="history store reads missed /s")
        if srv["skip_next"].notna().any():
            ax.plot(x, ((srv["skip_next"] + srv["skip_prev"]).diff() / dt).clip(lower=0), color=PURPLE,
                    linewidth=1.0, label="cursor entries skipped (next+prev) /s")
        ax.legend(loc="upper right", fontsize=8, frameon=False)
    else:
        ax.text(0.01, 0.5, "no history store in this version (4.2: lookaside)", transform=ax.transAxes,
                color=INK2, fontsize=9)
    ax.set_ylabel("per second", color=INK2, fontsize=9)

    ax = axes[3]
    if thr is not None and not thr.empty:
        ax.plot(thr["t_s"], thr["mongod_cpu_cores"], color=BLUE, linewidth=1.2, label="mongod CPU (cores)")
        ax.step(thr["t_s"], thr["conn_threads_ge90"], color=ORANGE, linewidth=1.2, where="post",
                label="connection threads at ≥90% CPU")
    if dstats and dstats.get("series_other"):
        xs = [ts - t0 / 1000.0 for ts, _ in dstats["series_other"]]
        ax.plot(xs, [v / 100.0 for _, v in dstats["series_other"]], color=MUTED, linewidth=1.0,
                label="other containers' CPU (cores)")
    if not srv.empty and srv["ckpt_running"].notna().any():
        x = (srv["t_ms"] - t0) / 1000.0
        on = srv["ckpt_running"] > 0
        for xi in x[on]:
            ax.axvspan(xi - 0.5, xi + 0.5, color=GREEN, alpha=0.15, linewidth=0)
        ax.plot([], [], color=GREEN, alpha=0.3, linewidth=6, label="checkpoint running")
    ax.set_ylabel("cores / threads", color=INK2, fontsize=9)
    ax.set_xlabel("seconds since the insert phase started", color=INK2, fontsize=9)
    ax.legend(loc="upper right", fontsize=8, frameon=False, ncol=2)
    axes[0].set_xlim(-0.5, max(2.0, (t_end - t0) / 1000.0 + 1))
    fig.tight_layout()
    fig.savefig(run / "timeline.png", dpi=110, facecolor=SURFACE)
    plt.close(fig)


# ----------------------------------------------------------------------------- comparison
def condition(s):
    ps = s["prefix_search"]
    ps = "absent" if ps in (None, "absent") else ("on" if ps is True or ps == "true" else "off")
    k = f"{s['version']} prefix_search={ps} {s['workload']}"
    if s["sync_start"]:
        k += " sync-start"
    if s["non_unique"]:
        k += " NON-UNIQUE"
    if s["profiled"]:
        k += " (profiled)"
    return k


def fisher_one_sided(a, n1, b, n2):
    """P(X >= a) for X ~ hypergeometric(stalled runs in arm 1 | margins): one-sided Fisher exact test."""
    k = a + b
    N = n1 + n2

    def C(n, r):
        return math.comb(n, r) if 0 <= r <= n else 0
    den = C(N, k)
    return sum(C(n1, x) * C(n2, k - x) for x in range(a, min(n1, k) + 1)) / den if den else float("nan")


def s5_check(runs_dirs, bug_key, fix_key, groups):
    """S5 from the profiled runs: stuck-thread stack shares (bug arm) and HS-lookup share (fix arm)."""
    def prof(label):
        p = Path(runs_dirs[label]) / "profile" / "profile_summary.json"
        return json.load(open(p)) if p.exists() else None

    def share(focus, label):
        for lab, n, pct in focus:
            if lab == label:
                return pct
        return None
    bug_runs = [x for x in groups.get(bug_key + " (profiled)", []) if x["stalled"]]
    fix_runs = groups.get(fix_key + " (profiled)", [])
    res = {"bug": [], "fix": []}
    for x in bug_runs:
        pr = prof(x["label"])
        if not pr or not pr.get("stuck", {}).get("samples"):
            continue
        f = pr["stuck"]["focus"]
        snap = Path(runs_dirs[x["label"]]) / "profile" / "snapshot_summary.md"
        snap_ok = snap.exists() and "unique-index duplicate check" in snap.read_text()
        res["bug"].append({"label": x["label"], "samples": pr["stuck"]["samples"],
                           "keyExists_pct": share(f, "mongo::WiredTigerIndexUnique::_keyExists"),
                           "hs_find_upd_pct": share(f, "__wt_hs_find_upd"), "snapshot_in_keyExists": snap_ok})
    for x in fix_runs:
        pr = prof(x["label"])
        if pr:
            res["fix"].append({"label": x["label"], "samples": pr["all_conn"]["samples"],
                               "hs_find_upd_pct": share(pr["all_conn"]["focus"], "__wt_hs_find_upd")})
    ok_bug = any((b["keyExists_pct"] or 0) >= 50 and (b["hs_find_upd_pct"] or 0) >= 50 and b["snapshot_in_keyExists"]
                 for b in res["bug"])
    ok_fix = bool(res["fix"]) and all((f["hs_find_upd_pct"] or 0) < 1 for f in res["fix"])
    res["pass"] = ok_bug and ok_fix
    return res


def secondary_checks(groups):
    """The pre-registered secondary checks of PLAN.md (descriptive; not part of the verdict)."""
    def g(k):
        return groups.get(k, [])

    def nst(k):
        return sum(x["stalled"] for x in g(k))

    def med_hs(k):
        v = [x["hs_misses"] for x in g(k) if x["hs_misses"] is not None]
        return float(np.median(v)) if v else None
    out = []
    off, on = "5.0.33 prefix_search=off bruce", "5.0.33 prefix_search=on bruce"
    if g(off) and g(on):
        out.append(("U1", f"W0 5.0.33: stalled runs off > on", f"{nst(off)}/{len(g(off))} vs {nst(on)}/{len(g(on))}",
                    nst(off) > nst(on)))
        u2 = any((x["hs_misses"] or 0) > 0 for x in g(off)) and all((x["hs_misses"] or 0) == 0 for x in g(on))
        out.append(("U2", "W0 5.0.33: HS misses > 0 in ≥ 1 off run and = 0 in every on run",
                    f"off max {fmt(max(x['hs_misses'] or 0 for x in g(off)))}, on max {fmt(max(x['hs_misses'] or 0 for x in g(on)))}", u2))
    off, on = "4.4.30 prefix_search=off bruce", "4.4.30 prefix_search=on bruce"
    if g(off) and g(on):
        out.append(("V1", "W0 4.4.30: ≥ 2/3 off runs stalled and 0 on runs", f"{nst(off)}/{len(g(off))} vs {nst(on)}/{len(g(on))}",
                    nst(off) >= 2 and nst(on) == 0))
    for tag, suf in (("R", ""), ("R'", " sync-start")):
        a, b = "4.4.2 prefix_search=absent bruce" + suf, "4.4.1 prefix_search=absent bruce" + suf
        if g(a) and g(b):
            out.append((f"{tag}1", f"4.4.2{suf}: ≥ 2/3 runs stalled", f"{nst(a)}/{len(g(a))}", nst(a) >= 2))
            r2 = nst(b) < nst(a) or (med_hs(b) is not None and med_hs(a) is not None and med_hs(b) < med_hs(a))
            out.append((f"{tag}2", f"4.4.1{suf}: fewer stalled runs or lower median HS misses than 4.4.2",
                        f"stalled {nst(b)}/{len(g(b))} vs {nst(a)}/{len(g(a))}; median HS misses {fmt(med_hs(b))} vs {fmt(med_hs(a))}", r2))
    for suf in ("", " sync-start"):
        k = "4.2.24 prefix_search=absent bruce" + suf
        if g(k):
            out.append(("B1" + (" (W1)" if suf else " (W0)"), f"4.2.24{suf}: 0 stalled runs", f"{nst(k)}/{len(g(k))}", nst(k) == 0))
    k = "5.0.33 prefix_search=off bruce sync-start NON-UNIQUE"
    if g(k):
        out.append(("C1", "non-unique indexes, 5.0.33 off W1: 0 stalled runs", f"{nst(k)}/{len(g(k))}", nst(k) == 0))
    return out


def primary_criteria(groups, bug_key, fix_key):
    """S1-S4 of PLAN.md on the given groups (None if either arm is missing)."""
    if bug_key not in groups or fix_key not in groups:
        return None
    bg, fg = groups[bug_key], groups[fix_key]
    b = {"stalled_runs": sum(x["stalled"] for x in bg), "runs": len(bg)}
    f = {"stalled_runs": sum(x["stalled"] for x in fg), "runs": len(fg)}
    p = fisher_one_sided(b["stalled_runs"], b["runs"], f["stalled_runs"], f["runs"])
    bug_runs = bg

    stalled_bug = [x for x in bug_runs if x["stalled"]]
    fix_max_hs = max([x["hs_misses"] or 0 for x in groups[fix_key]] or [0])
    s4a = all((x["hs_misses"] or 0) >= 1e6 for x in stalled_bug) if stalled_bug else False
    s4b = (fix_max_hs < 0.01 * min(x["hs_misses"] or 0 for x in stalled_bug)) if stalled_bug else False
    s4c = all((x["hs_misses_stall_share"] or 0) >= 0.8 for x in stalled_bug) if stalled_bug else False
    crit = {
        "S1": {"desc": "≥3 of the bug-arm runs have a stalled call", "value": f"{b['stalled_runs']}/{b['runs']}",
               "pass": b["stalled_runs"] >= 3},
        "S2": {"desc": "0 fix-arm runs have a stalled call", "value": f"{f['stalled_runs']}/{f['runs']}",
               "pass": f["stalled_runs"] == 0},
        "S3": {"desc": "one-sided Fisher exact test on stalled runs, bug vs fix, p < 0.05", "value": f"p = {p:.4f}",
               "pass": p < 0.05},
        "S4a": {"desc": "every stalled bug-arm run has ≥ 1,000,000 HS reads missed",
                "value": ", ".join(fmt(x["hs_misses"]) for x in stalled_bug) or "–", "pass": s4a},
        "S4b": {"desc": "fix-arm max HS reads missed < 1% of the smallest stalled bug-arm value",
                "value": f"fix max {fmt(fix_max_hs)} vs bug min {fmt(min([x['hs_misses'] or 0 for x in stalled_bug] or [0]))}",
                "pass": s4b},
        "S4c": {"desc": "in every stalled bug-arm run ≥ 80% of HS misses accrue while a call has run ≥ 3 s",
                "value": ", ".join(f"{100 * (x['hs_misses_stall_share'] or 0):.0f}%" for x in stalled_bug) or "–",
                "pass": s4c},
    }
    return crit


def write_run_index(summaries, path):
    """Every run handed to the comparison, in start order, with its role and the host power source."""
    def role(x):
        if x["label"] in EXCLUDED:
            return "excluded"
        return "counted" if x["label"][:1].isupper() else "pilot / smoke / test"

    def pw(p, k):
        return {"AC Power": "AC", "Battery Power": "battery"}.get((p or {}).get(k), "?")
    rows = []
    for x in summaries:
        meta = {}
        d = RUN_DIRS.get(x["label"])
        if d and (Path(d) / "meta.json").exists():
            meta = json.load(open(Path(d) / "meta.json"))
        rows.append((meta.get("started_utc", ""), x))
    rows.sort(key=lambda r: r[0])
    L = ["# Run index (WT-7264)", "",
         "Every run in `runs/` that has a `meta.json`, in start order (UTC); the first, hand-run pilot "
         "(`pilot0-5.0.33-prefixoff-manual`) has none and is described in `../PLAN.md`. "
         "*Role*: counted runs feed `summary.md`; excluded runs are "
         "listed with their reason in `excluded_runs.txt`; pilot/smoke/test runs came before the plan or tested "
         "the tooling (`../PLAN.md`). *Power*: host power source at the start and end of the insert phase "
         "(AC, or battery = Low Power Mode on this laptop); `+bat` = a battery tag inside the run. Recorded by "
         "run.sh since 2026-10-28, reconstructed from `pmset -g log` before that (`power.json`).", "",
         "| started (UTC) | label | role | condition | insert s | stalled calls (threads) | longest call s | "
         "HS misses | power start → end | note |", "|---|---|---|---|---|---|---|---|---|---|"]
    for started, x in rows:
        p = x.get("power") or {}
        pws = f"{pw(p, 'start')} → {pw(p, 'end')}" + (" +bat" if p.get("battery_tag_inside_run") and
                                                      pw(p, "start") == pw(p, "end") == "AC" else "")
        L.append(f"| {started.replace('T', ' ').replace('Z', '')} | `{x['label']}` | {role(x)} | {condition(x)} | "
                 f"{x['insert_phase_s']}{' CAP' if x['capped'] else ''} | {x['stalled_calls']} ({x['stalled_threads']}) | "
                 f"{x['longest_call_s']:.2f} | {fmt(x['hs_misses'])} | {pws} | {EXCLUDED.get(x['label'], '')} |")
    path.write_text("\n".join(L) + "\n")


RUN_DIRS = {}


def load_excluded(path):
    """results/excluded_runs.txt: `<label>: <reason>` per line (# comments allowed)."""
    ex = {}
    if path and Path(path).exists():
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and ":" in line:
                k, _, v = line.partition(":")
                ex[k.strip()] = v.strip()
    return ex


EXCLUDED = {}


def compare(summaries, out, bug_key, fix_key):
    out.mkdir(parents=True, exist_ok=True)
    (out / "plots").mkdir(exist_ok=True)
    write_run_index(summaries, out / "run_index.md")
    excluded = [s for s in summaries if s["label"] in EXCLUDED]
    # pilot/smoke/test runs (lower-case labels) never count; PLAN.md lists them as pilots
    summaries = [s for s in summaries if s["label"] not in EXCLUDED and s["label"][:1].isupper()]
    groups = {}
    for s in summaries:
        groups.setdefault(condition(s), []).append(s)
    order = sorted(groups, key=lambda k: (k != bug_key, k != fix_key, k))
    rows = []
    for k in order:
        g = groups[k]
        tot = [x["insert_phase_s"] for x in g]
        lc = [x["longest_call_s"] for x in g]
        hs = [x["hs_misses"] for x in g if x["hs_misses"] is not None]
        rows.append({
            "condition": k, "runs": len(g), "stalled_runs": sum(x["stalled"] for x in g),
            "capped_runs": sum(x["capped"] for x in g),
            "insert_s_median": float(np.median(tot)), "insert_s_min": min(tot), "insert_s_max": max(tot),
            "longest_call_s_median": float(np.median(lc)), "longest_call_s_max": max(lc),
            "stall_durations_s": sorted([y["dur_s"] for x in g for y in x["stalls"]], reverse=True),
            "stalled_threads_per_stalled_run": [x["stalled_threads"] for x in g if x["stalled"]],
            "hs_misses_median": float(np.median(hs)) if hs else None, "hs_misses_max": max(hs) if hs else None,
            "hs_misses_min_stalled": min([x["hs_misses"] for x in g if x["stalled"] and x["hs_misses"] is not None] or [None])
            if any(x["stalled"] for x in g) else None,
            "stall_share_min": min([x["hs_misses_stall_share"] for x in g
                                    if x["stalled"] and x["hs_misses_stall_share"] is not None] or [None])
            if any(x["stalled"] for x in g) else None,
            "noisy_runs": sum(x["noisy"] for x in g),
            "ac_runs": sum(bool(x.get("whole_run_on_ac")) for x in g),
            "stall_types": dict(collections.Counter(x.get("stall_type", "?") for x in g if x["stalled"])),
            "stalled_calls_total": sum(x["stalled_calls"] for x in g),
            "stalled_calls_batch0": sum(1 for x in g for y in x["stalls"] if y["batch"] == 0),
            "stall_start_max_s": max([y["start_s"] for x in g for y in x["stalls"]] or [None]) if any(x["stalls"] for x in g) else None,
            "alone_threads_vs_stalled": [(x["alone_window"]["conn_threads_ge90_median"], x["stalled_threads"])
                                         for x in g if x.get("alone_window")],
            "labels": [x["label"] for x in g],
        })
    R = {r["condition"]: r for r in rows}
    crit = primary_criteria(groups, bug_key, fix_key)
    # Disclosed sensitivity check (PLAN.md change 7): the same criteria on runs whose whole insert phase was
    # on AC power (battery power means Low Power Mode on this laptop).
    groups_ac = {k: [x for x in g if x.get("whole_run_on_ac")] for k, g in groups.items()}
    groups_ac = {k: g for k, g in groups_ac.items() if g}
    crit_ac = primary_criteria(groups_ac, bug_key, fix_key)
    sens = None
    if bug_key in R and fix_key in R:
        bq = [x for x in groups[bug_key] if not x["noisy"]]
        fq = [x for x in groups[fix_key] if not x["noisy"]]
        bs, fs = sum(x["stalled"] for x in bq), sum(x["stalled"] for x in fq)
        sens = {"bug": f"{bs}/{len(bq)}", "fix": f"{fs}/{len(fq)}",
                "fisher_p": fisher_one_sided(bs, len(bq), fs, len(fq)) if bq and fq else None}
        bq2 = [x for x in groups[bug_key] if not x.get("noisy_onset")]
        fq2 = [x for x in groups[fix_key] if not x.get("noisy_onset")]
        bs2, fs2 = sum(x["stalled"] for x in bq2), sum(x["stalled"] for x in fq2)
        sens["onset"] = {"bug": f"{bs2}/{len(bq2)}", "fix": f"{fs2}/{len(fq2)}",
                         "fisher_p": fisher_one_sided(bs2, len(bq2), fs2, len(fq2)) if bq2 and fq2 else None,
                         "stalled_runs_with_noisy_onset": sum(1 for x in groups[bug_key] if x["stalled"] and x.get("noisy_onset"))}
    L = ["# WT-7264 / SERVER-67350: results across runs", "",
         f"Stalled call = insertMany ≥ {STALL_S:.0f} s or still running at the cap. "
         "HS misses = increase of `history store table reads missed` over the insert phase.", "",
         "| condition | runs | stalled runs | insert phase s: median [min–max] | longest call s: median (max) | "
         "stall durations (s) | stalled calls on batch 0 | latest stalled-call start (s) | HS reads missed: median (max) | "
         "noisy runs | runs fully on AC | stall type of stalled runs (exploratory) |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['condition']} | {r['runs']} | **{r['stalled_runs']}**{f' ({r['capped_runs']} capped)' if r['capped_runs'] else ''} | "
                 f"{r['insert_s_median']:.1f} [{r['insert_s_min']:.1f}–{r['insert_s_max']:.1f}] | "
                 f"{r['longest_call_s_median']:.2f} ({r['longest_call_s_max']:.1f}) | "
                 f"{', '.join(f'{x:.1f}' for x in r['stall_durations_s'][:8]) or '–'}"
                 f"{' …' if len(r['stall_durations_s']) > 8 else ''} | "
                 f"{r['stalled_calls_batch0']}/{r['stalled_calls_total']} | "
                 f"{'–' if r['stall_start_max_s'] is None else f'{r['stall_start_max_s']:.2f}'} | "
                 f"{fmt(r['hs_misses_median'])} ({fmt(r['hs_misses_max'])}) | {r['noisy_runs']} | {r['ac_runs']}/{r['runs']} | "
                 f"{', '.join(f'{k} {v}' for k, v in r['stall_types'].items()) or '–'} |")
    L += ["", "While only stalled calls were left (every other client thread finished), connection threads at ≥ 90% "
          "CPU (median over that window) vs stalled client threads, per run:", ""]
    for r in rows:
        if r["alone_threads_vs_stalled"]:
            L.append(f"- {r['condition']}: " + ", ".join(f"{a:.0f} vs {b}" for a, b in r["alone_threads_vs_stalled"]))
    if crit:
        L += ["", f"## Pre-registered criteria (bug arm = `{bug_key}`, fix arm = `{fix_key}`)", "",
              "| criterion | value | result |", "|---|---|---|"]
        L += [f"| **{k}** {v['desc']} | {v['value']} | {'**met**' if v['pass'] else '**not met**'} |" for k, v in crit.items()]
        s5 = s5_check(RUN_DIRS, bug_key, fix_key, groups)
        if s5["bug"] or s5["fix"]:
            vb = "; ".join(f"`{b['label']}`: {b['samples']:,} stuck samples, _keyExists {b['keyExists_pct']}%, "
                           f"__wt_hs_find_upd {b['hs_find_upd_pct']}%, gdb snapshot in _keyExists: {b['snapshot_in_keyExists']}"
                           for b in s5["bug"]) or "no profiled bug-arm stall"
            vf = "; ".join(f"`{f['label']}`: __wt_hs_find_upd {f['hs_find_upd_pct']}% of {f['samples']:,} conn samples"
                           for f in s5["fix"]) or "no profiled fix-arm run"
            L.append(f"| **S5** profile: stuck threads ≥50% in _keyExists and ≥50% in __wt_hs_find_upd, snapshot in "
                     f"_keyExists; fix arm __wt_hs_find_upd < 1% | {vb}. Fix: {vf} | {'**met**' if s5['pass'] else '**not met**'} |")
            crit["S5"] = {"desc": "profile", "value": vb + " / " + vf, "pass": s5["pass"]}
        sec = secondary_checks(groups)
        if sec:
            L += ["", "## Pre-registered secondary checks (descriptive, not part of the verdict)", "",
                  "| check | value | result |", "|---|---|---|"]
            L += [f"| **{i}** {d} | {v} | {'holds' if ok else '**does not hold**'} |" for i, d, v, ok in sec]
        sec_ac = {i: (v, ok) for i, d, v, ok in secondary_checks(groups_ac)}
        if crit_ac is not None and "S5" in crit:
            s5a = s5_check(RUN_DIRS, bug_key, fix_key, groups_ac)
            crit_ac["S5"] = {"desc": "profile", "value": "profiled runs: " + ", ".join(
                [b["label"] for b in s5a["bug"]] + [f["label"] for f in s5a["fix"]]) or "none on AC", "pass": s5a["pass"]}
        if crit_ac or sec_ac:
            n_ac = sum(len(g) for g in groups_ac.values())
            n_all = sum(len(g) for g in groups.values())
            L += ["", f"## Power-source sensitivity check (disclosed, PLAN.md change 7; not used for the verdict)", "",
                  f"The laptop ran some counted runs on battery, where Low Power Mode slows the CPU. Below, every "
                  f"criterion and secondary check recomputed on the {n_ac} of {n_all} counted runs whose whole insert "
                  "phase was on AC power (per-run `power` in each `summary.json`).", "",
                  "| check | all counted runs | AC-only runs | same result? |", "|---|---|---|---|"]
            for k, v in (crit or {}).items():
                a = (crit_ac or {}).get(k)
                L.append(f"| {k} | {v['value']} → {'met' if v['pass'] else 'not met'} | "
                         + (f"{a['value']} → {'met' if a['pass'] else 'not met'}" if a else "–")
                         + f" | {'yes' if a and a['pass'] == v['pass'] else ('**no**' if a else '–')} |")
            for i, d, v, ok in sec:
                a = sec_ac.get(i)
                L.append(f"| {i} | {v} → {'holds' if ok else 'does not hold'} | "
                         + (f"{a[0]} → {'holds' if a[1] else 'does not hold'}" if a else "no AC-only runs")
                         + f" | {'yes' if a and a[1] == ok else ('**no**' if a else '–')} |")
        if sens:
            L += ["", f"Sensitivity check (pre-registered, not used for the verdict): non-noisy runs only, stalled runs "
                  f"bug {sens['bug']}, fix {sens['fix']}, one-sided Fisher p = "
                  + ("–" if sens["fisher_p"] is None else f"{sens['fisher_p']:.4f}")
                  + ". This check is uninformative: every stalled run lasts minutes, and other containers burst to "
                  "≥ 2 cores about every 30 s, so every long run is flagged.",
                  "", f"Exploratory replacement (added after block A): noise only in the first 10 s, where every stall "
                  f"starts. Runs without a burst there: stalled bug {sens['onset']['bug']}, fix {sens['onset']['fix']}, "
                  "one-sided Fisher p = " + ("–" if sens["onset"]["fisher_p"] is None else f"{sens['onset']['fisher_p']:.4f}")
                  + f"; stalled bug-arm runs that did have a burst in their first 10 s: {sens['onset']['stalled_runs_with_noisy_onset']}."]
    # EXPLORATORY (added after block A started; not a criterion): does the stuck thread's key range matter?
    # A thread's key range is [t*100000, (t+1)*100000); the keys "next" of its insert point belong to threads > t.
    ex = []
    for k in order:
        pts = [(y["thread"], y["dur_s"]) for x in groups[k] for y in x["stalls"] if not x["capped"]]
        if len(pts) >= 5 and "67350" not in k:
            xs = np.argsort(np.argsort([p[0] for p in pts]))
            ys = np.argsort(np.argsort([p[1] for p in pts]))
            rho = float(np.corrcoef(xs, ys)[0, 1]) if np.std(xs) > 0 and np.std(ys) > 0 else float("nan")
            ex.append(f"- {k}: {len(pts)} stalled calls (uncapped runs); Spearman rho(thread index, stall duration) = "
                      f"{rho:+.2f}; stalled thread indexes: {sorted(p[0] for p in pts)}")
    if ex:
        L += ["", "## Exploratory: which threads stall (not a criterion)", "",
              "Thread t inserts keys [t·100000, (t+1)·100000), so a low t has more of the other threads' keys "
              "\"next\" of its insert point. Rank correlation between thread index and stall duration:", ""] + ex
    def pw(x):
        p = x.get("power") or {}
        a = {"AC Power": "AC", "Battery Power": "battery"}.get(p.get("start"), "?")
        b = {"AC Power": "AC", "Battery Power": "battery"}.get(p.get("end"), "?")
        return a if a == b and not p.get("battery_tag_inside_run") else f"{a} → {b}"
    L += ["", "## Runs", "", "| condition | label | insert s | stalled calls (threads) | longest call s | HS misses | "
          "noisy | power (start → end) | stall type (exploratory) |", "|---|---|---|---|---|---|---|---|---|"]
    for k in order:
        for x in groups[k]:
            L.append(f"| {k} | `{x['label']}` | {x['insert_phase_s']}{' CAP' if x['capped'] else ''} | "
                     f"{x['stalled_calls']} ({x['stalled_threads']}) | {x['longest_call_s']:.2f} | {fmt(x['hs_misses'])} | "
                     f"{'yes' if x['noisy'] else ''} | {pw(x)} | {x.get('stall_type', '')} |")
    if excluded:
        L += ["", "## Excluded runs (listed in `excluded_runs.txt`; kept in `runs/`, not counted anywhere above)", "",
              "| label | condition | reason | what it showed |", "|---|---|---|---|"]
        L += [f"| `{x['label']}` | {condition(x)} | {EXCLUDED[x['label']]} | {x['insert_phase_s']} s"
              f"{' (capped)' if x['capped'] else ''}, {x['stalled_calls']} stalled calls, longest {x['longest_call_s']:.1f} s |"
              for x in excluded]
    L += ["", "Plots: `plots/conditions.png` (every run as a dot)."]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    (out / "comparison.json").write_text(json.dumps({"conditions": rows, "criteria": crit, "sensitivity_non_noisy": sens},
                                                    indent=1, default=str))
    plot_conditions(groups, order, out / "plots" / "conditions.png")
    print((out / "summary.md").read_text())


def plot_conditions(groups, order, path):
    fig, axes = plt.subplots(1, 3, figsize=(15, 0.55 * len(order) + 2.2), facecolor=SURFACE, sharey=True)
    metrics = [("insert_phase_s", "insert phase (s)"), ("longest_call_s", "longest insertMany call (s)"),
               ("hs_misses", "history store reads missed")]
    rng = np.random.default_rng(1)
    for ax, (m, lab) in zip(axes, metrics):
        style(ax)
        for i, k in enumerate(order):
            for x in groups[k]:
                v = x[m]
                if v is None:
                    continue
                y = i + rng.uniform(-0.18, 0.18)
                col = ORANGE if x["stalled"] else BLUE
                on_ac = bool(x.get("whole_run_on_ac"))
                ax.scatter([max(v, 1 if m == "hs_misses" else 0.01)], [y], s=28, alpha=0.9,
                           facecolors=col if on_ac else "none", edgecolors=col, linewidths=1.2,
                           marker=">" if x["capped"] else "o")
        ax.set_xscale("log")
        ax.set_xlabel(lab, color=INK2, fontsize=9)
        if m == "longest_call_s":
            ax.axvline(STALL_S, color=MUTED, linestyle="--", linewidth=0.8)
    def display(k):
        k = k.replace("prefix_search=absent ", "").replace("prefix_search=", "prefix_search ")
        k = k.replace("bruce sync-start", "W1 barrier").replace("bruce", "W0 unmodified").replace("67350", "W2 (67350-like)")
        return k
    axes[0].set_yticks(range(len(order)))
    axes[0].set_yticklabels([display(k) for k in order], fontsize=8)
    axes[0].invert_yaxis()
    axes[0].scatter([], [], color=ORANGE, label="run with a stalled call")
    axes[0].scatter([], [], color=BLUE, label="no stalled call")
    axes[0].scatter([], [], facecolors="none", edgecolors=INK2, label="hollow: (partly) on battery / Low Power Mode")
    axes[0].scatter([], [], marker=">", color=INK2, label="▶: hit the run cap")
    axes[0].legend(loc="lower right", fontsize=8, frameon=False)
    fig.suptitle("WT-7264: every run, by condition (log scales; HS misses shown as ≥1)", x=0.01, ha="left",
                 fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=110, facecolor=SURFACE)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--compare-out")
    ap.add_argument("--bug-key", default="5.0.33 prefix_search=off bruce sync-start")
    ap.add_argument("--fix-key", default="5.0.33 prefix_search=on bruce sync-start")
    ap.add_argument("--reuse", action="store_true", help="reuse existing summary.json files (comparison only)")
    ap.add_argument("--exclude-file", default=None,
                    help="runs to leave out of the comparison, `<label>: <reason>` per line "
                         "(default: <compare-out>/excluded_runs.txt if it exists)")
    args = ap.parse_args()
    if args.compare_out:
        EXCLUDED.update(load_excluded(args.exclude_file or Path(args.compare_out) / "excluded_runs.txt"))
    sums = []
    for r in args.runs:
        run = Path(r)
        if not (run / "meta.json").exists():
            print("skip (no meta.json):", run)
            continue
        if args.reuse and (run / "summary.json").exists():
            sums.append(json.load(open(run / "summary.json")))
            RUN_DIRS[sums[-1]["label"]] = str(run)
            continue
        s = analyze_run(run)
        sums.append(s)
        RUN_DIRS[s["label"]] = str(run)
        print(f"{s['label']}: {s['insert_phase_s']} s, stalled calls {s['stalled_calls']}, "
              f"longest {s['longest_call_s']:.2f} s, HS misses {fmt(s['hs_misses'])}, noisy={s['noisy']}")
    if args.compare_out:
        compare(sums, Path(args.compare_out), args.bug_key, args.fix_key)


if __name__ == "__main__":
    main()
