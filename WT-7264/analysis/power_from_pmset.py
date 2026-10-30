#!/usr/bin/env python3
"""Reconstruct the host's power source (AC vs battery) for runs that predate run.sh recording it.

  pmset -g log > /tmp/pmset.log            # macOS
  python3 -I analysis/power_from_pmset.py /tmp/pmset.log results/runs --timeline results/power_timeline.csv

macOS logs a "Using AC(Charge: N)" / "Using Batt(Charge: N)" tag on power-management events (assertion
summaries, sleep, wake). The power source at time t is taken from the last tag at or before t. A run is
"AC" only if its whole insert phase is covered: the last tag before its start says AC and no tag inside it
says battery. On this laptop battery power also means Low Power Mode (`pmset -g custom`: Battery Power
lowpowermode 1), which slows the CPU. Writes results/runs/<label>/power.json (source: "pmset -g log") for
every run (for runs that also have run.sh's live power fields, the analysis prefers those and uses
power.json only for battery tags inside the run), and the tagged events to --timeline.
Only stdlib; reads the log as text.
"""
import argparse
import csv
import datetime
import json
import re
from pathlib import Path

TAG = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d [+-]\d{4}) .*?Using (AC|Batt|BATT)\s*\(?\s*[Cc]harge:\s*(\d+)")


def parse_log(path):
    ev = []
    for line in open(path, errors="replace"):
        m = TAG.match(line)
        if m:
            t = datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S %z").timestamp()
            ev.append((t, "AC Power" if m.group(2) == "AC" else "Battery Power", int(m.group(3)), m.group(1)))
    ev.sort()
    return ev


def source_at(ev, t):
    prev = None
    for e in ev:
        if e[0] <= t:
            prev = e
        else:
            break
    return prev


def run_window(run):
    """(start, end) epoch seconds of the insert phase from the client log, else from meta/outcome."""
    start = end = None
    cl = run / "raw" / "client.log"
    if cl.exists():
        last = None
        for line in open(cl, errors="replace"):
            p = line.strip().split(",")
            try:
                if p[0] == "P" and p[1] == "insert_start":
                    start = int(p[2]) / 1000.0
                elif p[0] == "P" and p[1] == "insert_end":
                    end = int(p[2]) / 1000.0
                elif p[0] == "B":
                    last = max(last or 0, (int(p[3]) + int(p[4])) / 1000.0)
                elif p[0] == "S":
                    last = max(last or 0, int(p[3]) / 1000.0)
            except (IndexError, ValueError):
                continue
        end = end or last
    meta = json.load(open(run / "meta.json")) if (run / "meta.json").exists() else {}
    out = json.load(open(run / "outcome.json")) if (run / "outcome.json").exists() else {}

    def utc(s):
        return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()
    if start is None and meta.get("started_utc"):
        start = utc(meta["started_utc"])
    if out.get("ended_utc"):
        end = max(end or 0, utc(out["ended_utc"]))   # a capped run ends when it is killed
    return start, end


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pmset_log")
    ap.add_argument("runs_dir")
    ap.add_argument("--timeline")
    args = ap.parse_args()
    ev = parse_log(args.pmset_log)
    if args.timeline:
        # only the transitions (plus the tag just before each, and the last tag) of the last 3 days
        recent = [e for e in ev if e[0] >= ev[-1][0] - 3 * 86400]
        with open(args.timeline, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["local_time", "source", "charge_pct", "note"])
            for i, (t, src, ch, s) in enumerate(recent):
                changed = i > 0 and src != recent[i - 1][1]
                before_change = i + 1 < len(recent) and recent[i + 1][1] != src
                if i == 0 or changed or before_change or i == len(recent) - 1:
                    w.writerow([s, src, ch, "source changed" if changed else
                                "last tag before a change" if before_change else "first/last tag"])
    for run in sorted(Path(args.runs_dir).iterdir()):
        if not run.is_dir() or not (run / "raw" / "client.log").exists():
            continue
        # Runs with live power fields (run.sh since 2026-10-28) still get power.json: the log is the only
        # way to see an unplug/replug *during* a run (battery_tag_inside_run).
        start, end = run_window(run)
        if start is None:
            continue
        a, b = source_at(ev, start), source_at(ev, end or start)
        inside = [e for e in ev if start < e[0] <= (end or start)]
        on_batt_inside = any(e[1] == "Battery Power" for e in inside)
        rec = {
            "how": "reconstructed from `pmset -g log` power tags (last tag at or before the time)",
            "insert_phase_utc": [datetime.datetime.fromtimestamp(x, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                                 if x else None for x in (start, end)],
            "power_start": {"source": a[1] if a else "unknown", "charge_pct": a[2] if a else None,
                            "tag_time": a[3] if a else None},
            "power_end": {"source": b[1] if b else "unknown", "charge_pct": b[2] if b else None,
                          "tag_time": b[3] if b else None},
            "battery_tag_inside_run": on_batt_inside,
            "whole_run_on_ac": bool(a and a[1] == "AC Power" and b and b[1] == "AC Power" and not on_batt_inside),
            "low_power_mode_on_battery": "assumed 1 (pmset -g custom on 2026-10-28: Battery Power lowpowermode 1)",
        }
        (run / "power.json").write_text(json.dumps(rec, indent=1) + "\n")
        print(f"{run.name}: start {rec['power_start']['source']}, end {rec['power_end']['source']}, "
              f"whole run on AC: {rec['whole_run_on_ac']}")


if __name__ == "__main__":
    main()
