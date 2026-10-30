#!/usr/bin/env python3
"""Summarise the SERVER-67350 reporter's logs + FTDC (requested_files.tar.gz) -> server67350_logs.md/.png.

  python -I server67350_analyze.py --data <extracted tarball dir> --ftdc <dir with ftdc_<version>.csv> \
         --out-md server67350_logs.md --out-png attachments/server67350_ftdc.png

The tarball is untrusted data: it is extracted into its own directory, nothing in it is executed, and this
script only parses text/CSV. The CSVs come from ftdc_decode.py.
"""
import argparse
import csv
import datetime
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

VERSIONS = ["4.2.20", "4.4.14", "5.0.9"]
BLUE, ORANGE, RED, SURFACE, INK2, MUTED, GRID = "#2a78d6", "#eb6834", "#d03b3b", "#fcfcfb", "#52514e", "#8a8984", "#e4e3df"
TXT = re.compile(r"^(\S+) I\s+COMMAND\s+\[(conn\d+)\] command (\S+) command: insert .*?ninserted:(\d+).* (\d+)ms$")


def ts(s):
    s = s.replace("Z", "+00:00")
    if re.search(r"[+-]\d{4}$", s):
        s = s[:-2] + ":" + s[-2:]
    return datetime.datetime.fromisoformat(s)


def inserts_from_log(path):
    out = []
    for line in open(path, errors="replace"):
        line = line.rstrip("\n")
        if line.startswith("{"):
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            a = d.get("attr", {})
            if d.get("msg") == "Slow query" and "insert" in a.get("command", {}):
                end = ts(d["t"]["$date"])
                out.append((d["ctx"], end, a.get("durationMillis"), a.get("ninserted")))
        else:
            m = TXT.match(line)
            if m:
                out.append((m.group(2), ts(m.group(1)), int(m.group(5)), int(m.group(4))))
    return out


def load_ftdc(path):
    rows = []
    with open(path) as f:
        r = csv.reader(f)
        hdr = next(r)
        for row in r:
            if row[0].startswith("#") or not row[0]:
                continue
            rec = {"t": datetime.datetime.fromisoformat(row[0]).replace(tzinfo=datetime.timezone.utc)}
            for h, v in zip(hdr[2:], row[2:]):
                rec[h.split(".")[-1]] = float(v) if v not in ("", None) else None
            rows.append(rec)
    rows.sort(key=lambda x: x["t"])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--ftdc", required=True)
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--out-png", required=True)
    a = ap.parse_args()
    L = ["# SERVER-67350 reporter's logs and FTDC (parsed)", "",
         "Source: `requested_files.tar.gz` attached to SERVER-67350 by the reporter (mongod logs + `diagnostic.data` "
         "for 4.2.20, 4.4.14, 5.0.9, two runs each). The archive was extracted into its own directory and only "
         "parsed as data (`server67350_analyze.py`, FTDC decoded by `ftdc_decode.py`). It is not committed here; "
         "download it from the ticket (attachment `requested_files.tar.gz`).", ""]
    fig, axes = plt.subplots(len(VERSIONS), 1, figsize=(12, 8.5), facecolor=SURFACE)
    for ax, v in zip(axes, VERSIONS):
        ins = inserts_from_log(Path(a.data) / v / "mongo.log")
        L += [f"## {v}", "", "Insert commands in the slow-query log (all of them are logged: ≥ 100 ms):", "",
              "| connection | started (UTC) | duration (s) | documents |", "|---|---|---|---|"]
        for conn, end, ms, n in sorted(ins, key=lambda x: x[1] - datetime.timedelta(milliseconds=x[2])):
            start = end - datetime.timedelta(milliseconds=ms)
            L.append(f"| {conn} | {start.strftime('%H:%M:%S.%f')[:12]} | {ms / 1000:.1f} | {n} |")
        p = Path(a.ftdc) / f"ftdc_{v}.csv"
        rows = load_ftdc(p) if p.exists() else []
        if rows:
            t0 = rows[0]["t"]
            xs, ins_rate, miss_rate, writers = [], [], [], []
            for r0, r1 in zip(rows, rows[1:]):
                dt = (r1["t"] - r0["t"]).total_seconds()
                if dt <= 0:
                    continue
                xs.append((r1["t"] - t0).total_seconds())
                ins_rate.append(max(0.0, ((r1["insert"] or 0) - (r0["insert"] or 0)) / dt))
                m0, m1 = r0.get("history store table reads missed"), r1.get("history store table reads missed")
                miss_rate.append(max(0.0, (m1 - m0) / dt) if m0 is not None and m1 is not None else 0.0)
                writers.append(r1.get("writers") or 0)
            tot_miss = (rows[-1].get("history store table reads missed") or 0) - (rows[0].get("history store table reads missed") or 0) \
                if rows[0].get("history store table reads missed") is not None else None
            skipped = None
            if rows[0].get("Total number of entries skipped by cursor next calls") is not None:
                skipped = sum((rows[-1].get(k) or 0) - (rows[0].get(k) or 0) for k in
                              ("Total number of entries skipped by cursor next calls",
                               "Total number of entries skipped by cursor prev calls"))
            L += ["", f"FTDC ({len(rows)} samples, {xs[-1] if xs else 0:.0f} s): history store reads missed over the file: "
                  f"**{tot_miss:,.0f}**" if tot_miss is not None else "", ]
            if tot_miss is None:
                L[-1] = f"FTDC ({len(rows)} samples): no history store in {v} (pre-durable-history)."
            if skipped is not None:
                L[-1] += (f"; cursor entries skipped by next+prev: {skipped:,.0f}; peak reads-missed rate "
                          f"{max(miss_rate):,.0f}/s; max active writers {max(writers):.0f}.")
            ax.set_facecolor(SURFACE)
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
            ax.grid(True, color=GRID, linewidth=0.6)
            ax.plot(xs, ins_rate, color=BLUE, linewidth=1.2, label="inserts/s")
            ax.set_ylabel("inserts/s", color=BLUE, fontsize=8)
            ax.tick_params(labelsize=8, colors=INK2)
            ax2 = ax.twinx()
            ax2.plot(xs, miss_rate, color=RED, linewidth=1.2, label="HS reads missed/s")
            ax2.step(xs, [w * max(max(miss_rate), 1) / max(max(writers), 1) for w in writers], color=ORANGE,
                     linewidth=1.0, where="post", alpha=0.8, label="active writers (scaled)")
            ax2.set_ylabel("HS reads missed/s", color=RED, fontsize=8)
            ax2.tick_params(labelsize=8, colors=INK2)
            ax2.spines["top"].set_visible(False)
            ax.set_title(f"SERVER-67350 reporter's FTDC, mongod {v} (two runs; x = seconds since the FTDC file starts)",
                         loc="left", fontsize=9)
            h1, l1 = ax.get_legend_handles_labels()
            h2, l2 = ax2.get_legend_handles_labels()
            ax.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=7, frameon=False)
        L.append("")
    fig.tight_layout()
    fig.savefig(a.out_png, dpi=100, facecolor=SURFACE)
    Path(a.out_md).write_text("\n".join(L) + "\n")
    print("wrote", a.out_md, a.out_png)


if __name__ == "__main__":
    main()
