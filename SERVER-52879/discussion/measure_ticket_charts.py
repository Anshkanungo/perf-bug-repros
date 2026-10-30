#!/usr/bin/env python3
"""Measure the spike spacing in the ticket's FTDC screenshots (attachments/spikes.png, before.png).

Red marks in the "ss average latency" row are located column-wise inside the plot area. The
pixels-per-second scale comes from the light-gray time gridlines, which are 150 s (2.5 min) apart.
Run:  ./analyze.sh is not needed; any Python with numpy + Pillow works, e.g.
  docker run --rm --name s52879-pix -v "$PWD/discussion:/d:ro" s52879-tools:1 python /d/measure_ticket_charts.py
"""
import numpy as np
from PIL import Image

# (file, latency-row y-range, gridline y-range, plot-area x-range, gridline spacing in seconds)
CHARTS = [
    ("/d/attachments/spikes.png", (205, 250), (300, 330), (530, 1275), 150),
    ("/d/attachments/before.png", (290, 332), (380, 400), (410, 972), 150),
]


def groups(cols, gap):
    out = []
    for c in cols:
        if out and c - out[-1][-1] <= gap:
            out[-1].append(c)
        else:
            out.append([c])
    return [float(np.mean(g)) for g in out]


for path, (y0, y1), (g0, g1), (x0, x1), grid_s in CHARTS:
    im = np.asarray(Image.open(path).convert("RGB")).astype(int)
    band = im[y0:y1, x0:x1]
    red = (band[..., 0] > 180) & (band[..., 1] < 120) & (band[..., 2] < 110)
    spikes = [x0 + x for x in groups(np.where(red.sum(axis=0) >= 6)[0], 3)]
    gb = im[g0:g1, x0:x1]
    gray = (abs(gb[..., 0] - gb[..., 1]) < 6) & (gb[..., 0] > 200) & (gb[..., 0] < 240)
    grid = groups(np.where(gray.sum(axis=0) >= (g1 - g0) * 0.6)[0], 2)
    px_per_s = np.median(np.diff(grid)) / grid_s
    iv = np.diff(spikes) / px_per_s
    print(f"{path.split('/')[-1]}: {len(spikes)} spikes, {px_per_s:.3f} px/s, intervals (s): "
          f"{', '.join(f'{v:.1f}' for v in iv)}; median {np.median(iv):.1f}, min {iv.min():.1f}, max {iv.max():.1f}")
