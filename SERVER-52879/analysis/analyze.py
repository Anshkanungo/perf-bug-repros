#!/usr/bin/env python3
"""SERVER-52879 analysis.

  analyze.py RUN_DIR [RUN_DIR ...] [--compare-out DIR] [--names A,B,...] [--warmup 120]

For every run directory (results/runs/<label>) it writes:
  per_second.csv   client per-second latency stats joined with 1 Hz serverStatus counters
  summary.json     all numbers below
  summary.md       human-readable summary
  timeline.png     latency / open sessions / cached cursors over time

With two or more runs and --compare-out, it also writes DIR/summary.md (side-by-side table) and
DIR/plots/ab_timeline.png + ab_zoom.png (first two runs), and period_vs_timeout.png when the runs
use different idle timeouts.

Spike rule (fixed in PLAN.md before the main runs): a second is a spike second when its maximum
client-side insert latency is >= max(10 x the run's median per-second max, 10 ms). Consecutive spike
seconds (gaps <= 2 s) form one spike event. Event time = start time of its slowest insert.
"""
import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# opLatencies histogram lower bounds in microseconds (src/mongo/db/stats/operation_latency_histogram.cpp, r4.4.3)
LOWER_BOUNDS = [0, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 3072, 4096, 6144, 8192, 12288, 16384,
                24576, 32768, 49152, 65536, 98304, 131072, 196608, 262144, 393216, 524288, 786432, 1048576,
                1572864, 2097152, 4194304, 8388608, 16777216, 33554432, 67108864, 134217728, 268435456,
                536870912]

SPIKE_FACTOR = 10.0
SPIKE_FLOOR_MS = 10.0
MERGE_GAP_S = 2
PERIOD_TOL_S = 5.0
SWEEP_DROP_REL = 0.05     # cached-cursor drop between two 1 s samples that marks a session-close sweep
SWEEP_DROP_ABS = 500

# Validated categorical slots (dataviz reference palette, light surface): slot 1 blue, slot 2 orange, ...
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"]
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8984"
GRID = "#e4e3df"


def predicted_period(idle_s):
    """Sweeper wakes every 10 s; burst sessions go idle just after a sweep, so they are closed at the
    first sweep strictly more than idle_s later: (floor(T/10)+1)*10 s."""
    if not idle_s or idle_s <= 0:
        return None
    return (math.floor(idle_s / 10) + 1) * 10


# ----------------------------------------------------------------------------- loading
def load_client(run):
    phases, totals, rows = {}, {}, []
    with open(run / "raw" / "client.log", errors="replace") as f:
        for line in f:
            if line.startswith("O,"):
                p = line.rstrip("\n").split(",")
                if len(p) == 4:
                    try:
                        rows.append((int(p[1]), int(p[2]), float(p[3])))
                    except ValueError:
                        pass
            elif line.startswith("P,"):
                p = line.strip().split(",")
                phases[p[1]] = int(p[2])
            elif line.startswith("T,"):
                p = line.strip().split(",")
                totals[int(p[1])] = int(p[2])
    ops = pd.DataFrame(rows, columns=["tid", "start_ms", "lat_ms"])
    ops["end_ms"] = ops["start_ms"] + ops["lat_ms"]
    return ops, phases, totals


HIST_MAX_US = 60_000_000  # buckets above 60 s are artifacts (e.g. the 2^40 us overflow bucket after a clock step)


def hist_dict(h):
    return {int(e["micros"]): int(e["count"]) for e in (h or []) if int(e["micros"]) <= HIST_MAX_US}


def upper_of(lo):
    for b in LOWER_BOUNDS:
        if b > lo:
            return b
    return lo * 2


def load_server(run):
    path = run / "raw" / "serverstatus.jsonl"
    recs = []
    with open(path) as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "error" in r:
                continue
            w = r["opLatencies"]["writes"]
            wt = r["wt"]
            recs.append({
                "t_req_ms": r["t_req_ms"], "t_ms": r["t_resp_ms"], "local_ms": r["local_ms"],
                "w_ops": w["ops"], "w_lat_us": w["latency"], "hist": hist_dict(w.get("histogram")),
                "open_sessions": wt["session"].get("open session count"),
                "cached_cursors": wt["cursor"].get("cached cursor count"),
                "open_cursors": wt["cursor"].get("open cursor count"),
                "files_open": wt.get("files_open"),
                "dhandles": wt["dhandle"].get("connection data handles currently active"),
                "ckpt_running": wt.get("ckpt_running"),
                "ckpts": wt.get("ckpts"),
                "conns": r["connections"].get("current"),
            })
    s = pd.DataFrame(recs)
    if s.empty:
        return s
    s["d_ops"] = s["w_ops"].diff()
    s["d_lat_us"] = s["w_lat_us"].diff()
    s["srv_mean_ms"] = (s["d_lat_us"] / s["d_ops"]).where(s["d_ops"] > 0) / 1000.0
    p99, mx = [np.nan], [np.nan]
    for prev, cur in zip(s["hist"].iloc[:-1], s["hist"].iloc[1:]):
        d = {k: cur.get(k, 0) - prev.get(k, 0) for k in cur}
        d = {k: v for k, v in d.items() if v > 0}
        if not d:
            p99.append(np.nan); mx.append(np.nan); continue
        keys = sorted(d)
        tot = sum(d.values())
        acc, p = 0, keys[-1]
        for k in keys:
            acc += d[k]
            if acc >= 0.99 * tot:
                p = k
                break
        p99.append(upper_of(p) / 1000.0)
        mx.append(upper_of(keys[-1]) / 1000.0)
    s["srv_p99_le_ms"] = p99      # upper bound of the bucket holding the p99
    s["srv_max_le_ms"] = mx       # upper bound of the highest non-empty bucket
    return s.drop(columns=["hist"])


def load_docker_stats(run):
    # docker_stats.jsonl (run.sh) plus docker_stats_all.jsonl (an all-container log added by hand to Run A,
    # which predates run.sh sampling every container)
    paths = [p for p in (run / "raw" / "docker_stats.jsonl", run / "raw" / "docker_stats_all.jsonl") if p.exists()]
    out = {}
    if not paths:
        return out
    units = {"B": 1, "KiB": 2**10, "MiB": 2**20, "GiB": 2**30, "kB": 1e3, "MB": 1e6, "GB": 1e9}
    others = {}  # timestamp -> summed CPU% of containers that are not ours (noise source)
    seen = set()
    lines = [ln for p in paths for ln in open(p)]
    for line in lines:
        try:
            rec = json.loads(line)
            r, ts = rec["s"], rec["t"]
        except (json.JSONDecodeError, KeyError):
            continue
        m = re.match(r"([\d.]+)\s*([A-Za-z]+)", r.get("MemUsage", ""))
        if not m:
            continue
        b = float(m.group(1)) * units.get(m.group(2), 1)
        cpu = float(r.get("CPUPerc", "0%").rstrip("%") or 0)
        if (ts, r.get("Name")) in seen:
            continue
        seen.add((ts, r.get("Name")))
        if not r.get("Name", "").startswith("s52879-"):
            others[ts] = others.get(ts, 0.0) + cpu
            continue
        o = out.setdefault(r["Name"], {"mem_max_mib": 0.0, "cpu_max_pct": 0.0})
        o["mem_max_mib"] = max(o["mem_max_mib"], b / 2**20)
        o["cpu_max_pct"] = max(o["cpu_max_pct"], cpu)
    if others:
        v = sorted(others.values())
        out["(other containers, summed)"] = {"mem_max_mib": float("nan"), "cpu_max_pct": v[-1],
                                             "cpu_median_pct": v[len(v) // 2]}
    return out


def load_slow_ops(run):
    """Count 'Slow query' (id 51803, default slowms=100) insert lines in the mongod JSON log."""
    path = run / "raw" / "mongod.log"
    n, mx = 0, 0
    if not path.exists():
        return None
    for line in open(path, errors="replace"):
        if '"id":51803' not in line or '"insert"' not in line:
            continue
        m = re.search(r'"durationMillis":(\d+)', line)
        if m:
            n += 1
            mx = max(mx, int(m.group(1)))
    return {"slow_inserts_over_100ms": n, "slowest_ms": mx}


# ----------------------------------------------------------------------------- analysis
def per_second(ops, t0):
    sec = ((ops["end_ms"] - t0) // 1000).astype(int)
    g = ops.assign(sec=sec).groupby("sec")["lat_ms"]
    ps = pd.DataFrame({"count": g.size(), "p50_ms": g.median(), "p99_ms": g.quantile(0.99),
                       "max_ms": g.max()})
    return ps


def detect_spikes(ps, ops, t0, win_lo, win_hi):
    w = ps.loc[(ps.index >= win_lo) & (ps.index < win_hi)]
    baseline = float(w["max_ms"].median())
    thr = max(SPIKE_FACTOR * baseline, SPIKE_FLOOR_MS)
    spike_secs = list(w.index[w["max_ms"] >= thr])
    clusters = []
    for s in spike_secs:
        if clusters and s - clusters[-1][-1] <= MERGE_GAP_S:
            clusters[-1].append(s)
        else:
            clusters.append([s])
    events = []
    for c in clusters:
        lo_ms, hi_ms = t0 + c[0] * 1000, t0 + (c[-1] + 1) * 1000
        sel = ops[(ops["end_ms"] >= lo_ms) & (ops["end_ms"] < hi_ms)]
        slow = sel[sel["lat_ms"] >= thr]
        top = sel.loc[sel["lat_ms"].idxmax()]
        events.append({
            "t_s": round((top["start_ms"] - t0) / 1000.0, 3),     # start of the slowest insert
            "first_slow_start_s": round((slow["start_ms"].min() - t0) / 1000.0, 3),
            "last_slow_end_s": round((slow["end_ms"].max() - t0) / 1000.0, 3),
            "peak_ms": float(top["lat_ms"]),
            "n_slow_ops": int(len(slow)),
            "n_threads_slow": int(slow["tid"].nunique()),
        })
    return baseline, thr, events


def detect_spikes_server(srv, t0, win_lo, win_hi):
    """D2 (secondary, FTDC-equivalent): per-sample server mean write latency >= max(10 x median, 1 ms)."""
    s = srv.assign(t_s=(srv["t_ms"] - t0) / 1000.0)
    s = s[(s["t_s"] >= win_lo) & (s["t_s"] < win_hi)].dropna(subset=["srv_mean_ms"])
    if s.empty:
        return None
    baseline = float(s["srv_mean_ms"].median())
    thr = max(SPIKE_FACTOR * baseline, 1.0)
    hits = s[s["srv_mean_ms"] >= thr]
    clusters = []
    for _, r in hits.iterrows():
        if clusters and r["t_s"] - clusters[-1][-1]["t_s"] <= MERGE_GAP_S + 0.5:
            clusters[-1].append(r)
        else:
            clusters.append([r])
    events = []
    for c in clusters:
        top = max(c, key=lambda r: r["srv_mean_ms"])
        events.append({"t_s": round(float(top["t_s"]), 3), "peak_mean_ms": float(top["srv_mean_ms"]),
                       "max_le_ms": float(top["srv_max_le_ms"]) if not math.isnan(top["srv_max_le_ms"]) else None})
    return {"baseline_mean_ms": baseline, "threshold_ms": thr, "events": events}


def interval_stats(events, predicted):
    t = [e["t_s"] for e in events]
    iv = np.diff(t)
    if len(iv) == 0:
        return {"n_intervals": 0}
    out = {"n_intervals": int(len(iv)), "median_s": float(np.median(iv)),
           "iqr_s": [float(np.percentile(iv, 25)), float(np.percentile(iv, 75))],
           "min_s": float(iv.min()), "max_s": float(iv.max()),
           "intervals_s": [round(float(x), 2) for x in iv]}
    if predicted:
        out["predicted_s"] = predicted
        out["frac_within_tol"] = float(np.mean(np.abs(iv - predicted) <= PERIOD_TOL_S))
    return out


def acf_period(ps, win_lo, win_hi, max_lag=200):
    w = ps.loc[(ps.index >= win_lo) & (ps.index < win_hi), "max_ms"]
    w = w.reindex(range(int(win_lo), int(win_hi))).ffill().bfill()
    x = np.log10(np.maximum(w.values, 0.1))
    x = x - x.mean()
    n = len(x)
    if n < 60 or np.allclose(x, 0):
        return None
    den = float(np.dot(x, x))
    lags = range(5, min(max_lag, n // 2))
    ac = [float(np.dot(x[:-k], x[k:]) / den) for k in lags]
    i = int(np.argmax(ac))
    return {"lag_s": int(list(lags)[i]), "acf": round(ac[i], 3)}


def sweep_events(srv, t0):
    """Session-close sweeps seen as cached-cursor drops between consecutive 1 s samples."""
    c = srv["cached_cursors"].astype(float)
    d = c.diff()
    rel = d / c.shift(1)
    m = (d <= -SWEEP_DROP_ABS) & (rel <= -SWEEP_DROP_REL)
    ev = srv.loc[m, ["t_req_ms", "t_ms"]].copy()
    ev["drop"] = -d[m]
    ev["t_s"] = (ev["t_ms"] - t0) / 1000.0
    ev["prev_t_s"] = (srv["t_ms"].shift(1)[m] - t0) / 1000.0
    return ev


def match_events(spikes, sweeps, slack=2.0):
    if not spikes or sweeps.empty:
        return 0, 0
    sp_hit = 0
    for e in spikes:
        lo, hi = e["first_slow_start_s"] - slack, e["last_slow_end_s"] + slack
        if ((sweeps["t_s"] >= lo) & (sweeps["prev_t_s"] <= hi)).any():
            sp_hit += 1
    sw_hit = 0
    for _, r in sweeps.iterrows():
        if any(e["first_slow_start_s"] - slack <= r["t_s"] and r["prev_t_s"] <= e["last_slow_end_s"] + slack
               for e in spikes):
            sw_hit += 1
    return sp_hit, sw_hit


def sweep_locked(srv, ops, t0, win_lo, win_hi):
    """EXPLORATORY (added after Run A, applied identically to every run): latency inside each 1 s
    sampling interval that contains a session-close sweep (cached-cursor drop) vs. all other intervals."""
    s = srv[["t_ms", "cached_cursors", "open_sessions"]].copy()
    s["prev_t_ms"] = s["t_ms"].shift(1)
    s["d_cur"] = s["cached_cursors"].diff()
    s["d_ses"] = s["open_sessions"].diff()
    s["rel"] = s["d_cur"] / s["cached_cursors"].shift(1)
    s = s.dropna()
    s = s[(s["prev_t_ms"] >= t0 + win_lo * 1000) & (s["t_ms"] < t0 + win_hi * 1000)]
    is_sweep = (s["d_cur"] <= -SWEEP_DROP_ABS) & (s["rel"] <= -SWEEP_DROP_REL)
    end = ops["end_ms"].values
    lat = ops["lat_ms"].values
    order = np.argsort(end)
    end, lat = end[order], lat[order]
    rows = []
    for _, r in s.iterrows():
        a, b = np.searchsorted(end, [r["prev_t_ms"], r["t_ms"]])
        seg = lat[a:b]
        rows.append({"sweep": bool(is_sweep.loc[_]), "max_ms": float(seg.max()) if len(seg) else np.nan,
                     "n_ge10": int((seg >= 10).sum()), "d_cur": float(r["d_cur"]), "d_ses": float(r["d_ses"]),
                     "t_s": (r["t_ms"] - t0) / 1000.0})
    df = pd.DataFrame(rows)
    if df.empty or not df["sweep"].any():
        return {"sweeps": 0}
    sw, ot = df[df["sweep"]], df[~df["sweep"]]
    return {
        "sweeps": int(len(sw)), "other_intervals": int(len(ot)),
        "sweep_max_ms_median": float(sw["max_ms"].median()), "other_max_ms_median": float(ot["max_ms"].median()),
        "sweep_max_ms_list": [round(x, 1) for x in sw["max_ms"].tolist()],
        "sweep_cursors_closed_median": float(-sw["d_cur"].median()),
        "sweep_frac_max_ge_10ms": float((sw["max_ms"] >= 10).mean()),
        "other_frac_max_ge_10ms": float((ot["max_ms"] >= 10).mean()),
        "sweep_frac_max_ge_thr": None,
        "sweep_times_s": [round(x, 1) for x in sw["t_s"].tolist()],
        "sweep_interval_median_s": float(np.median(np.diff(sw["t_s"].values))) if len(sw) > 1 else None,
        "_df": df,
    }


def tag_events(events, srv, t0, sweeps):
    """Label each spike event: coincides with a session-close sweep, a checkpoint start, both, or neither."""
    ck = srv[["t_ms", "ckpt_running"]].copy()
    ck["start"] = (ck["ckpt_running"].fillna(0).astype(float) > 0) & (ck["ckpt_running"].shift(1).fillna(0).astype(float) == 0)
    ck_starts = ((ck.loc[ck["start"], "t_ms"] - t0) / 1000.0).tolist()
    for e in events:
        lo, hi = e["first_slow_start_s"] - 2.0, e["last_slow_end_s"] + 2.0
        is_sw = any((r["prev_t_s"] <= hi) and (r["t_s"] >= lo) for _, r in sweeps.iterrows()) if len(sweeps) else False
        is_ck = any(lo - 1.0 <= c <= hi + 1.0 for c in ck_starts)
        e["tag"] = "sweep+checkpoint" if (is_sw and is_ck) else "sweep" if is_sw else "checkpoint start" if is_ck else "other"
    return ck_starts


def analyze_run(run, warmup):
    meta = json.load(open(run / "meta.json"))
    server = json.load(open(run / "server.json")) if (run / "server.json").exists() else {}
    ops, phases, totals = load_client(run)
    t0 = phases.get("insert_start", int(ops["start_ms"].min()))
    t_end = phases.get("insert_end", int(ops["end_ms"].max()))
    dur = (t_end - t0) / 1000.0
    win_lo, win_hi = warmup, int(math.floor(dur)) - 1
    ps = per_second(ops, t0)
    srv = load_server(run)
    baseline, thr, events = detect_spikes(ps, ops, t0, win_lo, win_hi)
    idle = server.get("wiredTigerSessionCloseIdleTimeSecs", meta.get("idle_timeout_s"))
    pred = predicted_period(idle)
    ivs = interval_stats(events, pred)
    acf = acf_period(ps, win_lo, win_hi)

    wops = ops[(ops["end_ms"] >= t0 + win_lo * 1000) & (ops["end_ms"] < t0 + win_hi * 1000)]
    wps = ps.loc[(ps.index >= win_lo) & (ps.index < win_hi)]

    summary = {
        "label": meta["label"], "version": server.get("version"), "gitVersion": server.get("gitVersion"),
        "driver": meta["driver"], "topology": meta.get("topology"),
        "idle_timeout_s": idle, "predicted_period_s": pred,
        "collections": meta["collections"], "indexes": meta["indexes_per_collection"],
        "threads": meta["threads"], "insert_phase_s": round(dur, 1),
        "setup_s": round((phases["setup_end"] - phases["setup_start"]) / 1000.0, 1)
        if "setup_end" in phases and "setup_start" in phases else None,
        "window_s": [win_lo, win_hi],
        "ops_total": int(len(ops)), "ops_per_s_window": round(len(wops) / max(1, win_hi - win_lo), 1),
        "op_latency_ms_window": {q: float(np.percentile(wops["lat_ms"], p)) for q, p in
                                 (("p50", 50), ("p99", 99), ("p99_9", 99.9), ("max", 100))},
        "per_second_max_ms": {"median": baseline, "p99_5": float(np.percentile(wps["max_ms"], 99.5)),
                              "max": float(wps["max_ms"].max())},
        "per_second_p99_ms_median": float(wps["p99_ms"].median()),
        "spike_threshold_ms": thr,
        "spike_events": len(events),
        "spike_peak_ms_median": float(np.median([e["peak_ms"] for e in events])) if events else None,
        "spike_slow_ops_median": float(np.median([e["n_slow_ops"] for e in events])) if events else None,
        "spike_threads_median": float(np.median([e["n_threads_slow"] for e in events])) if events else None,
        "intervals": ivs, "acf": acf, "events": events,
    }
    if not srv.empty:
        sw = srv[(srv["t_ms"] >= t0 + win_lo * 1000) & (srv["t_ms"] < t0 + win_hi * 1000)]
        sweeps = sweep_events(srv, t0)
        sweeps_w = sweeps[(sweeps["t_s"] >= win_lo) & (sweeps["t_s"] < win_hi)]
        sp_hit, sw_hit = match_events(events, sweeps_w)
        gaps = srv["t_ms"].diff() / 1000.0
        summary["server"] = {
            "samples": int(len(srv)),
            "srv_mean_ms_median": float(sw["srv_mean_ms"].median()),
            "srv_mean_ms_max": float(sw["srv_mean_ms"].max()),
            "srv_max_le_ms_median": float(sw["srv_max_le_ms"].median()),
            "srv_max_le_ms_max": float(sw["srv_max_le_ms"].max()),
            "open_sessions": [int(sw["open_sessions"].min()), float(sw["open_sessions"].median()),
                              int(sw["open_sessions"].max())],
            "cached_cursors": [int(sw["cached_cursors"].min()), float(sw["cached_cursors"].median()),
                               int(sw["cached_cursors"].max())],
            "files_open_max": int(srv["files_open"].max()),
            "dhandles_max": int(srv["dhandles"].max()),
            "checkpoints": int(srv["ckpts"].max() - srv["ckpts"].min()),
            "sweep_close_events": int(len(sweeps_w)),
            "sweep_close_drop_median": float(sweeps_w["drop"].median()) if len(sweeps_w) else None,
            "spikes_with_sweep_close": sp_hit,
            "sweep_closes_with_spike": sw_hit,
            "sample_gap_max_s": float(gaps.max()),
        }
        sweep_t = sweeps_w["t_s"].tolist()
        ck_starts = tag_events(events, srv, t0, sweeps_w)
        sl = sweep_locked(srv, ops, t0, win_lo, win_hi)
        if sl.get("sweeps"):
            df = sl.pop("_df")
            sl["sweep_frac_max_ge_thr"] = float((df.loc[df["sweep"], "max_ms"] >= thr).mean())
            sl["other_frac_max_ge_thr"] = float((df.loc[~df["sweep"], "max_ms"] >= thr).mean())
        summary["exploratory_sweep_locked"] = sl
        summary["checkpoint_starts_s"] = [round(c, 1) for c in ck_starts]
        summary["spike_tags"] = dict(collections.Counter(e["tag"] for e in events))
        d2 = detect_spikes_server(srv, t0, win_lo, win_hi)
        if d2:
            d2["n_events"] = len(d2["events"])
            d2["intervals"] = interval_stats(d2["events"], pred)
            d2["peak_mean_ms_median"] = (float(np.median([e["peak_mean_ms"] for e in d2["events"]]))
                                         if d2["events"] else None)
            d2["coincide_with_D1"] = sum(1 for e in d2["events"]
                                         if any(abs(e["t_s"] - c["t_s"]) <= 2.5 for c in events))
        summary["server_detector_D2"] = d2
    else:
        sweep_t = []
    summary["docker_stats"] = load_docker_stats(run)
    summary["slow_query_log"] = load_slow_ops(run)
    pi = summary["intervals"]
    summary["criteria"] = {
        "S1_ge8_spike_events": len(events) >= 8,
        "S2_period": bool(pi.get("n_intervals", 0) >= 3 and pred is not None
                          and abs(pi["median_s"] - pred) <= PERIOD_TOL_S
                          and pi.get("frac_within_tol", 0) >= 0.75),
    }

    # per_second.csv: client stats + server sample landing in that second
    out = ps.copy()
    out.index.name = "sec"
    if not srv.empty:
        s2 = srv.copy()
        s2["sec"] = ((s2["t_ms"] - t0) // 1000).astype(int)
        s2 = s2.drop_duplicates("sec", keep="last").set_index("sec")
        out = out.join(s2[["srv_mean_ms", "srv_p99_le_ms", "srv_max_le_ms", "open_sessions",
                           "cached_cursors", "open_cursors", "files_open", "dhandles", "ckpt_running",
                           "conns"]], how="outer")
    out.to_csv(run / "per_second.csv", float_format="%.3f")
    return {"run": run, "meta": meta, "summary": summary, "ops": ops, "ps": ps, "srv": srv, "t0": t0,
            "sweep_t": sweep_t}


# ----------------------------------------------------------------------------- reporting
def fmt(x, nd=1):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def summary_md(s):
    iv = s["intervals"]
    sv = s.get("server", {})
    lines = [
        f"# Run `{s['label']}`", "",
        f"- mongod **{s['version']}** (`{(s['gitVersion'] or '')[:12]}`), {s['topology']}, driver `{s['driver']}`",
        f"- workload: {s['collections']} colls × {s['indexes']} indexes, {s['threads']} threads; "
        f"setup {fmt(s['setup_s'])} s; inserts {fmt(s['insert_phase_s'])} s; analysis window "
        f"{s['window_s'][0]}–{s['window_s'][1]} s after insert start",
        f"- idle timeout {s['idle_timeout_s']} s → predicted spike period {s['predicted_period_s']} s", "",
        "| metric | value |", "|---|---|",
        f"| inserts/s (window) | {fmt(s['ops_per_s_window'])} |",
        f"| per-op latency p50 / p99 / p99.9 / max (ms) | {fmt(s['op_latency_ms_window']['p50'], 2)} / "
        f"{fmt(s['op_latency_ms_window']['p99'], 2)} / {fmt(s['op_latency_ms_window']['p99_9'], 2)} / "
        f"{fmt(s['op_latency_ms_window']['max'], 1)} |",
        f"| per-second max latency: median (baseline) / p99.5 / max (ms) | {fmt(s['per_second_max_ms']['median'], 2)} / "
        f"{fmt(s['per_second_max_ms']['p99_5'], 1)} / {fmt(s['per_second_max_ms']['max'], 1)} |",
        f"| spike threshold (ms) | {fmt(s['spike_threshold_ms'], 1)} |",
        f"| spike events | {s['spike_events']} |",
        f"| spike peak latency, median (ms) | {fmt(s['spike_peak_ms_median'])} |",
        f"| slow inserts per spike / threads hit, median | {fmt(s['spike_slow_ops_median'], 0)} / {fmt(s['spike_threads_median'], 0)} |",
        f"| inter-spike interval median [IQR] (s) | {fmt(iv.get('median_s'))} "
        f"[{fmt(iv.get('iqr_s', [None, None])[0])}–{fmt(iv.get('iqr_s', [None, None])[1])}] |",
        f"| intervals within ±{PERIOD_TOL_S:.0f} s of prediction | {fmt(iv.get('frac_within_tol', None), 2)} |",
        f"| autocorrelation peak (lag s, r) | {s['acf']['lag_s'] if s['acf'] else '–'}, {s['acf']['acf'] if s['acf'] else '–'} |",
    ]
    if sv:
        lines += [
            f"| server mean write latency per second: median / max (ms) | {fmt(sv['srv_mean_ms_median'], 3)} / {fmt(sv['srv_mean_ms_max'], 2)} |",
            f"| server histogram max per second: median / max (≤ ms) | {fmt(sv['srv_max_le_ms_median'], 1)} / {fmt(sv['srv_max_le_ms_max'], 1)} |",
            f"| WT open sessions min / median / max | {sv['open_sessions'][0]} / {fmt(sv['open_sessions'][1], 0)} / {sv['open_sessions'][2]} |",
            f"| WT cached cursors min / median / max | {sv['cached_cursors'][0]:,} / {sv['cached_cursors'][1]:,.0f} / {sv['cached_cursors'][2]:,} |",
            f"| WT files open (max) / dhandles (max) | {sv['files_open_max']:,} / {sv['dhandles_max']:,} |",
            f"| session-close sweeps seen (cached-cursor drops) | {sv['sweep_close_events']} (median drop {fmt(sv['sweep_close_drop_median'], 0)}) |",
            f"| spikes coinciding with a sweep / sweeps coinciding with a spike | {sv['spikes_with_sweep_close']}/{s['spike_events']} / {sv['sweep_closes_with_spike']}/{sv['sweep_close_events']} |",
            f"| checkpoints during run | {sv['checkpoints']} |",
            f"| longest gap between serverStatus samples (s) | {fmt(sv['sample_gap_max_s'], 2)} |",
        ]
    d2 = s.get("server_detector_D2")
    if d2:
        iv2 = d2["intervals"]
        lines += [
            f"| D2 (server mean/s ≥ 10× median {d2['baseline_mean_ms']:.3f} ms, floor 1 ms): threshold (ms) | {d2['threshold_ms']:.2f} |",
            f"| D2 spike events / coinciding with D1 events | {d2['n_events']} / {d2['coincide_with_D1']} |",
            f"| D2 peak server mean latency, median (ms) | {fmt(d2['peak_mean_ms_median'], 2)} |",
            f"| D2 interval median [IQR] (s) | {fmt(iv2.get('median_s'))} [{fmt(iv2.get('iqr_s', [None, None])[0])}–{fmt(iv2.get('iqr_s', [None, None])[1])}] |",
        ]
    sl = s.get("exploratory_sweep_locked")
    if sl and sl.get("sweeps"):
        lines += [
            f"| *exploratory:* sweeps / max client latency in sweep intervals, median (ms) | {sl['sweeps']} / {fmt(sl['sweep_max_ms_median'])} |",
            f"| *exploratory:* max client latency in non-sweep intervals, median (ms) | {fmt(sl['other_max_ms_median'])} |",
            f"| *exploratory:* share of intervals with max ≥ spike threshold: sweep / non-sweep | {fmt(sl['sweep_frac_max_ge_thr'], 2)} / {fmt(sl['other_frac_max_ge_thr'], 3)} |",
            f"| *exploratory:* share with max ≥ 10 ms: sweep / non-sweep | {fmt(sl['sweep_frac_max_ge_10ms'], 2)} / {fmt(sl['other_frac_max_ge_10ms'], 3)} |",
            f"| *exploratory:* cursors closed per sweep, median | {fmt(sl['sweep_cursors_closed_median'], 0)} |",
            f"| *exploratory:* interval between session-close sweeps, median (s) | {fmt(sl.get('sweep_interval_median_s'))} |",
        ]
    if s.get("spike_tags"):
        lines.append("| spike events by coincidence (sweep / checkpoint start / other) | "
                     + ", ".join(f"{k}: {v}" for k, v in sorted(s["spike_tags"].items())) + " |")
    sq = s.get("slow_query_log")
    if sq:
        lines.append(f"| mongod slow-query log: inserts > 100 ms / slowest (ms) | {sq['slow_inserts_over_100ms']} / {sq['slowest_ms']} |")
    for name, d in sorted(s.get("docker_stats", {}).items()):
        if name.startswith("("):
            lines.append(f"| {name}: CPU % median / peak | {d['cpu_median_pct']:.0f} / {d['cpu_max_pct']:.0f} |")
        else:
            lines.append(f"| {name}: peak memory (MiB) / peak CPU (%) | {d['mem_max_mib']:.0f} / {d['cpu_max_pct']:.0f} |")
    lines += ["", f"Criteria: S1 (≥8 spike events) **{s['criteria']['S1_ge8_spike_events']}**, "
                  f"S2 (period {s['predicted_period_s']}±{PERIOD_TOL_S:.0f} s) **{s['criteria']['S2_period']}**", ""]
    if s["events"]:
        lines += ["Spike events (s after insert start / peak ms / slow inserts / threads / coincides with):", "",
                  ", ".join(f"{e['t_s']:.1f}s/{e['peak_ms']:.0f}ms/{e['n_slow_ops']}/{e['n_threads_slow']}/{e.get('tag', '?')}"
                            for e in s["events"]), ""]
    if sl and sl.get("sweeps"):
        lines += ["Session-close sweeps (s) and max client latency in that 1 s interval (ms): " +
                  ", ".join(f"{t:.0f}s:{m:.0f}" for t, m in zip(sl["sweep_times_s"], sl["sweep_max_ms_list"])), ""]
    if iv.get("intervals_s"):
        lines += ["Intervals (s): " + ", ".join(f"{x:.1f}" for x in iv["intervals_s"]), ""]
    return "\n".join(lines)


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(True, axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def plot_timeline(results, names, out_path, title, zoom=None):
    """Columns = runs; rows = insert latency (log), WT open sessions, WT cached cursors.
    Small multiples share x within a column and y within a row (no dual axes)."""
    import matplotlib.transforms as mtransforms
    from matplotlib.lines import Line2D
    n = len(results)
    fig, axes = plt.subplots(3, n, figsize=(6.2 * n, 7.2), sharey="row", squeeze=False,
                             gridspec_kw={"height_ratios": [2.2, 1, 1]})
    fig.patch.set_facecolor(SURFACE)
    ses_max = cur_max = lat_max = 1.0
    for j, (r, name) in enumerate(zip(results, names)):
        s, ps, srv, t0 = r["summary"], r["ps"], r["srv"], r["t0"]
        color = SERIES[j % len(SERIES)]
        x_ps = ps.index.values + 0.5
        x_srv = (srv["t_ms"].values - t0) / 1000.0 if not srv.empty else np.array([])
        scale = 1.0 if zoom else 60.0
        lo, hi = zoom if zoom else (0, s["insert_phase_s"])
        a0, a1, a2 = axes[0][j], axes[1][j], axes[2][j]
        for a in (a0, a1, a2):
            style_axes(a)
            if not zoom:
                a.axvspan(0, s["window_s"][0] / scale, color=GRID, alpha=0.5, linewidth=0)
            a.set_xlim(lo / scale, hi / scale)
        trans = mtransforms.blended_transform_factory(a0.transData, a0.transAxes)
        if zoom:
            o = r["ops"]
            sel = o[(o["start_ms"] >= t0 + lo * 1000) & (o["start_ms"] < t0 + hi * 1000)]
            a0.scatter((sel["start_ms"] - t0) / 1000.0, np.maximum(sel["lat_ms"], 0.5), s=3, color=color,
                       alpha=0.35, linewidths=0, rasterized=True)
            a0.set_ylabel("each insert: latency (ms)", color=INK2, fontsize=9)
            lat_max = max(lat_max, float(sel["lat_ms"].max()) if len(sel) else 1.0)
            if j == 0:
                a0.text(0.01, 0.97, "inserts under 1 ms (legacy-shell timer resolution) are drawn at 0.5 ms",
                        transform=a0.transAxes, color=INK2, fontsize=7.5, va="top")
        else:
            a0.plot(x_ps / scale, np.maximum(ps["max_ms"].values, 0.5), color=color, linewidth=1.0)
            a0.plot(x_ps / scale, np.maximum(ps["p99_ms"].values, 0.5), color=MUTED, linewidth=0.8)
            a0.set_ylabel("insert latency per second (ms)", color=INK2, fontsize=9)
            lat_max = max(lat_max, float(ps["max_ms"].max()))
            a0.text(s["window_s"][0] / scale / 2, 0.97, "warm-up", transform=trans, color=INK2, fontsize=8,
                    ha="center", va="top")
            a0.legend(handles=[Line2D([], [], color=color, linewidth=1.5, label="per-second max"),
                               Line2D([], [], color=MUTED, linewidth=1.5, label="per-second p99")],
                      loc="upper right", fontsize=7.5, frameon=False, labelcolor=INK2)
        # checkpoint starts (a separate stall source, see REPORT) as small ticks on the time axis
        ck = r["summary"].get("checkpoint_starts_s") or []
        ck = [c for c in ck if lo <= c <= hi]
        if ck:
            a0.plot([c / scale for c in ck], [0.0] * len(ck), transform=trans, linestyle="none", marker="^",
                    markersize=6, color=INK2, clip_on=False)
            a0.text(0.0, -0.13, "▲ = WT checkpoint start", transform=a0.transAxes, color=INK2, fontsize=7.5)
        a0.axhline(s["spike_threshold_ms"], color=INK2, linewidth=0.8, linestyle=(0, (4, 3)))
        a0.text(lo / scale + (hi - lo) / scale * 0.01, s["spike_threshold_ms"] * 1.1,
                f"spike threshold {s['spike_threshold_ms']:.0f} ms", color=INK2, fontsize=7.5, va="bottom")
        a0.set_yscale("log")
        ev = s["intervals"]
        sl = s.get("exploratory_sweep_locked") or {}
        sub = (f"{s['spike_events']} spike events"
               + (f", median interval {ev['median_s']:.1f} s" if ev.get("n_intervals") else "")
               + (f"; {sl['sweeps']} sweeps, {sl['sweep_frac_max_ge_10ms'] * 100:.0f}% with a ≥10 ms insert"
                  if sl.get("sweeps") else ""))
        a0.set_title(f"{name}\n{sub}", color=INK, fontsize=10, loc="left")
        if not srv.empty:
            a1.plot(x_srv / scale, srv["open_sessions"].values, color=color, linewidth=1.0, drawstyle="steps-post")
            a2.plot(x_srv / scale, srv["cached_cursors"].values / 1000.0, color=color, linewidth=1.0)
            vis = (x_srv >= lo) & (x_srv <= hi)
            if vis.any():
                ses_max = max(ses_max, float(np.nanmax(srv["open_sessions"].values[vis])))
                cur_max = max(cur_max, float(np.nanmax(srv["cached_cursors"].values[vis])) / 1000.0)
        a1.set_ylabel("WT open sessions", color=INK2, fontsize=9)
        a2.set_ylabel("WT cached cursors (k)", color=INK2, fontsize=9)
        a2.set_xlabel("seconds since inserts started" if zoom else "minutes since inserts started",
                      color=INK2, fontsize=9)
    # row limits after all columns are drawn, so no run is clipped
    axes[0][0].set_ylim(0.4, lat_max * 2.0)
    axes[1][0].set_ylim(0, ses_max * 1.08)
    axes[2][0].set_ylim(0, cur_max * 1.08)
    fig.suptitle(title, x=0.01, ha="left", color=INK, fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out_path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def plot_periods(results, names, out_path):
    """Per run: intervals between spike events (filled) and between session-close sweeps (hollow),
    with the predicted (floor(T/10)+1)*10 s period."""
    fig, ax = plt.subplots(figsize=(7.6, 1.0 + 1.25 * len(results)))
    fig.patch.set_facecolor(SURFACE)
    style_axes(ax)
    ax.grid(True, axis="x", color=GRID, linewidth=0.6)
    ticks, labels = [], []
    rng = np.random.default_rng(7)
    for j, (r, name) in enumerate(zip(results, names)):
        s = r["summary"]
        color = SERIES[j % len(SERIES)]
        sp = s["intervals"].get("intervals_s", [])
        sw_t = (s.get("exploratory_sweep_locked") or {}).get("sweep_times_s", [])
        sw = list(np.diff(sw_t)) if len(sw_t) > 1 else []
        y_sp, y_sw = 2 * j + 0.0, 2 * j + 0.8
        ax.scatter(sp, y_sp + rng.uniform(-0.12, 0.12, len(sp)), s=34, color=color, edgecolors=SURFACE,
                   linewidths=1.2, zorder=3)
        ax.scatter(sw, y_sw + rng.uniform(-0.12, 0.12, len(sw)), s=34, facecolors="none", edgecolors=color,
                   linewidths=1.4, zorder=3)
        if s["predicted_period_s"]:
            ax.plot([s["predicted_period_s"]] * 2, [y_sp - 0.35, y_sw + 0.35], color=INK, linewidth=1.5, zorder=4)
            ax.text(s["predicted_period_s"], y_sw + 0.4, f"predicted {s['predicted_period_s']} s", ha="center",
                    va="bottom", fontsize=8, color=INK2)
        ticks += [y_sp, y_sw]
        labels += [f"{name}: spike events", f"{name}: session-close sweeps"]
    ax.set_yticks(ticks)
    ax.set_yticklabels(labels, fontsize=8.5, color=INK)
    ax.set_ylim(-0.7, 2 * len(results) - 0.2 + 0.4)
    ax.set_xlim(0, max(150, ax.get_xlim()[1]))
    ax.set_xlabel("interval to the next event (s)", color=INK2, fontsize=9)
    fig.suptitle("Sweep / spike period follows the idle timeout T (4.4.3)\n"
                 "filled = spike events, hollow = session-close sweeps; line = predicted (⌊T/10⌋+1)·10 s",
                 x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out_path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def compare_md(results, names):
    S = [r["summary"] for r in results]
    rows = [
        ("mongod version", lambda s: s["version"]),
        ("driver / topology", lambda s: f"{s['driver']} / {s['topology']}"),
        ("idle timeout (s) → predicted period (s)", lambda s: f"{s['idle_timeout_s']} → {s['predicted_period_s']}"),
        ("inserts/s", lambda s: fmt(s["ops_per_s_window"])),
        ("per-op p50 / p99 (ms)", lambda s: f"{fmt(s['op_latency_ms_window']['p50'], 2)} / {fmt(s['op_latency_ms_window']['p99'], 2)}"),
        ("per-op p99.9 / max (ms)", lambda s: f"{fmt(s['op_latency_ms_window']['p99_9'], 1)} / {fmt(s['op_latency_ms_window']['max'], 1)}"),
        ("per-second max: median (baseline) (ms)", lambda s: fmt(s["per_second_max_ms"]["median"], 2)),
        ("per-second max: p99.5 / max (ms)", lambda s: f"{fmt(s['per_second_max_ms']['p99_5'], 1)} / {fmt(s['per_second_max_ms']['max'], 1)}"),
        ("spike threshold (ms)", lambda s: fmt(s["spike_threshold_ms"], 1)),
        ("**spike events**", lambda s: f"**{s['spike_events']}**"),
        ("spike peak, median (ms)", lambda s: fmt(s["spike_peak_ms_median"])),
        ("threads hit per spike, median", lambda s: fmt(s["spike_threads_median"], 0)),
        ("**interval median [IQR] (s)**", lambda s: (f"**{fmt(s['intervals'].get('median_s'))}** "
                                                     f"[{fmt(s['intervals'].get('iqr_s', [None, None])[0])}–{fmt(s['intervals'].get('iqr_s', [None, None])[1])}]")),
        ("intervals within ±5 s of prediction", lambda s: fmt(s["intervals"].get("frac_within_tol"), 2)),
        ("autocorrelation peak (lag s, r)", lambda s: f"{s['acf']['lag_s']}, {s['acf']['acf']}" if s["acf"] else "–"),
        ("server mean write latency/s: median / max (ms)", lambda s: f"{fmt(s['server']['srv_mean_ms_median'], 3)} / {fmt(s['server']['srv_mean_ms_max'], 2)}" if "server" in s else "–"),
        ("WT open sessions min / median / max", lambda s: "{} / {:.0f} / {}".format(*s["server"]["open_sessions"]) if "server" in s else "–"),
        ("WT cached cursors median / max", lambda s: "{:,.0f} / {:,}".format(s["server"]["cached_cursors"][1], s["server"]["cached_cursors"][2]) if "server" in s else "–"),
        ("session-close sweeps seen", lambda s: str(s["server"]["sweep_close_events"]) if "server" in s else "–"),
        ("spikes coinciding with a sweep", lambda s: f"{s['server']['spikes_with_sweep_close']}/{s['spike_events']}" if "server" in s else "–"),
        ("sweeps coinciding with a spike", lambda s: f"{s['server']['sweep_closes_with_spike']}/{s['server']['sweep_close_events']}" if "server" in s else "–"),
        ("D2 server-side spike events (mean/s ≥10× median)", lambda s: str(s["server_detector_D2"]["n_events"]) if s.get("server_detector_D2") else "–"),
        ("D2 interval median (s)", lambda s: fmt(s["server_detector_D2"]["intervals"].get("median_s")) if s.get("server_detector_D2") else "–"),
        ("D2 peak server mean latency/s, median (ms)", lambda s: fmt(s["server_detector_D2"]["peak_mean_ms_median"], 2) if s.get("server_detector_D2") else "–"),
        ("spike events by coincidence", lambda s: ", ".join(f"{k} {v}" for k, v in sorted(s.get("spike_tags", {}).items())) or "–"),
        ("*expl.* sweeps seen / max latency in sweep intervals, median (ms)", lambda s: f"{s['exploratory_sweep_locked']['sweeps']} / {fmt(s['exploratory_sweep_locked']['sweep_max_ms_median'])}" if s.get("exploratory_sweep_locked", {}).get("sweeps") else "–"),
        ("*expl.* max latency in non-sweep intervals, median (ms)", lambda s: fmt(s["exploratory_sweep_locked"]["other_max_ms_median"]) if s.get("exploratory_sweep_locked", {}).get("sweeps") else "–"),
        ("*expl.* sweep intervals with max ≥ 10 ms", lambda s: fmt(s["exploratory_sweep_locked"]["sweep_frac_max_ge_10ms"], 2) if s.get("exploratory_sweep_locked", {}).get("sweeps") else "–"),
        ("*expl.* interval between sweeps, median (s)", lambda s: fmt(s["exploratory_sweep_locked"].get("sweep_interval_median_s")) if s.get("exploratory_sweep_locked", {}).get("sweeps") else "–"),
        ("*expl.* cursors closed per sweep, median", lambda s: fmt(s["exploratory_sweep_locked"]["sweep_cursors_closed_median"], 0) if s.get("exploratory_sweep_locked", {}).get("sweeps") else "–"),
        ("slow-query log inserts > 100 ms", lambda s: str(s["slow_query_log"]["slow_inserts_over_100ms"]) if s.get("slow_query_log") else "–"),
        ("mongod peak memory (MiB)", lambda s: next((f"{d['mem_max_mib']:.0f}" for n, d in s["docker_stats"].items() if n.endswith("mongod")), "–")),
        ("other containers' CPU %, median / peak (noise)", lambda s: next((f"{d['cpu_median_pct']:.0f} / {d['cpu_max_pct']:.0f}" for n, d in s["docker_stats"].items() if n.startswith("(")), "–")),
        ("client peak memory (MiB)", lambda s: next((f"{d['mem_max_mib']:.0f}" for n, d in s["docker_stats"].items() if n.endswith("client")), "–")),
    ]
    out = ["| metric | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for label, f in rows:
        out.append(f"| {label} | " + " | ".join(f(s) for s in S) + " |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--warmup", type=int, default=120)
    ap.add_argument("--compare-out")
    ap.add_argument("--names", help="comma-separated display names, in run order")
    ap.add_argument("--zoom", default="", help="start,end seconds for ab_zoom.png (default: auto)")
    ap.add_argument("--title", default="SERVER-52879: identical workload, two mongod builds")
    args = ap.parse_args()

    results = []
    for rd in args.runs:
        run = Path(rd)
        r = analyze_run(run, args.warmup)
        (run / "summary.json").write_text(json.dumps(r["summary"], indent=1, default=float))
        (run / "summary.md").write_text(summary_md(r["summary"]))
        name = f"{r['summary']['version']} ({r['summary']['driver']}, idle {r['summary']['idle_timeout_s']} s)"
        plot_timeline([r], [name], run / "timeline.png", f"Run {r['summary']['label']}")
        s = r["summary"]
        print(f"{s['label']}: version {s['version']}, {s['ops_per_s_window']} ins/s, baseline max "
              f"{s['per_second_max_ms']['median']:.2f} ms, thr {s['spike_threshold_ms']:.1f} ms, "
              f"{s['spike_events']} spike events, interval median "
              f"{s['intervals'].get('median_s', float('nan')):.1f} s, acf {s['acf']}, criteria {s['criteria']}")
        results.append(r)

    if args.compare_out and len(results) >= 2:
        out = Path(args.compare_out)
        (out / "plots").mkdir(parents=True, exist_ok=True)
        names = (args.names.split(",") if args.names else
                 [f"{r['summary']['version']} idle {r['summary']['idle_timeout_s']}s" for r in results])
        md = ["# SERVER-52879 comparison", "", compare_md(results, names), ""]
        a, b = results[0]["summary"], results[1]["summary"]
        if a["per_second_max_ms"]["p99_5"] and b["per_second_max_ms"]["p99_5"]:
            ratio = a["per_second_max_ms"]["p99_5"] / b["per_second_max_ms"]["p99_5"]
            s3 = b["spike_events"] <= 2 and ratio >= 5
            md += [f"S3 check ({names[1]} vs {names[0]}): {names[1]} spike events = {b['spike_events']} (≤2 required); "
                   f"p99.5 of per-second max ratio {names[0]}/{names[1]} = {ratio:.1f}x (≥5x required) → **{s3}**", ""]
        (out / "summary.md").write_text("\n".join(md))
        plot_timeline(results[:2], names[:2], out / "plots" / "ab_timeline.png", args.title)
        if args.zoom:
            z0, z1 = (float(x) for x in args.zoom.split(","))
        else:
            ev = results[0]["summary"]["events"]
            z0 = max(results[0]["summary"]["window_s"][0], (ev[len(ev) // 2]["t_s"] - 50) if ev else 300)
            z1 = z0 + 150
        plot_timeline(results[:2], names[:2], out / "plots" / "ab_zoom.png",
                      args.title + f" (zoom: {z0:.0f}–{z1:.0f} s, every insert)", zoom=(z0, z1))
        v0 = results[0]["summary"]["version"]
        same = [(r, n) for r, n in zip(results, names) if r["summary"]["version"] == v0]
        if len({r["summary"]["idle_timeout_s"] for r, _ in same}) > 1:
            plot_periods([r for r, _ in same], [n for _, n in same], out / "plots" / "period_vs_timeout.png")
        print(f"comparison written to {out}")


if __name__ == "__main__":
    sys.exit(main())
