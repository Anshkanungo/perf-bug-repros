# PROGRESS

**Current status:** SERVER-52879 done and waiting for review. Verdict: *partially reproduced* by the
pre-registered criteria, while the mechanism reproduced cleanly and was profiled on 4.4.3, with 4.4.4 as the
control. Nothing is committed (git initialized only).

**Todo:**
- [ ] Review SERVER-52879 (`SERVER-52879/REPORT.md`, `results/summary.md`, plots, profiles), then commit manually.
- [ ] Optional: rerun on an x86-64 Linux server with many cores, ideally as a source-built pair
      r4.4.3 vs r4.4.3+`d6a3d7b` (fix only), where the spikes should be larger and more regular.
- [ ] Optional: replicate A/B (n=1 per condition so far) to measure run-to-run variance.
- [ ] Optional: diagnose the version-independent stalls (checkpoint start / new-session cursor-open storms),
      which look like WT-5479.
- [ ] Next bug for the collection.

**Done:**
- 2026-10-27: SERVER-52879 reproduction. Repo created and the ticket, attachments, fix diffs, and source
  snapshots collected. PLAN.md written before the runs, with every change logged. Docker-only pipeline:
  `run.sh` (official image, custom image, custom binary, or external `--target`), 1 Hz serverStatus sampler,
  per-insert client log, analysis with plots, and a perf/gdb profiling sidecar. Runs: smoke, A 4.4.3,
  B 4.4.4, P-4.4.3 and P-4.4.4 profiles, C (T=60), V1 A/B with checkpoints pushed out, C2 (T=60, no
  checkpoints). Containers and volumes cleaned up; images kept.

**Decisions:**
- Legacy 4.4 shell runs Bruce's original `repro.js` (minimally adapted, every change documented). It measured
  ~1 GiB for 100 threads, so the pymongo driver (`workload/driver.py`) is kept only as a cross-check option.
  The same 4.4.3 shell image is the client for every server version.
- Official images pulled from `public.ecr.aws/docker/library/*` when Docker Hub returned HTTP 429 (identical digests).
- The release `mongod` is not stripped (`.symtab`), so perf and gdb name WiredTiger statics without the 2.3 GB
  debug-symbol tarball (`mongodb-linux-aarch64-ubuntu2004-debugsymbols-4.4.3.tgz`; not downloaded).
- Profiling: perf `cpu-clock` (no PMU in the VM) with frame-pointer call graphs, plus off-CPU via
  `sched_switch`/`sched_waking`. The gdb snapshot freezes mongod with SIGSTOP (mongod runs under `docker
  --init` in profiling runs).
- An exploratory, clearly labeled sweep-locked analysis was added after Run A. Variation V1
  (`--syncdelay=3600`) and run C2 were added after the data showed checkpoint-start stalls in both versions.
- REPORT.md could not be written by the agent (the harness blocks report files from subagents); its content was
  returned in the agent's final message to be saved by the caller.

**Open questions:**
- Is "partially reproduced" (mechanism yes; pre-registered periodicity/fix thresholds no on this 10-vCPU laptop
  VM) good enough for Quvi's first pass, or should the next step be the x86-64 many-core rerun?
- Should the team's instrumentation target the default config (realistic, with checkpoint stalls as a
  confounder) or `--syncdelay=3600` (single-bug trace)?

---

## WT-7264 / SERVER-67350 (unique-index inserts stuck walking invisible keys)

**Current status:** done and waiting for review (2026-10-28 11:40). Verdict by the pre-registered rule:
**reproduced** (S1–S5 met on one binary, `mongo:5.0.33`, `wiredTigerPrefixSearchForUniqueIndexes` off vs on;
unchanged on AC-only runs). One pre-registered secondary check fails: 4.2.24 had multi-second stalls, but only
in battery runs (Low Power Mode), and of a different kind (eviction, all threads at once). Nothing committed;
`WT-7264/REPORT.md` still has to be saved from the agent's final message.

**Todo:**
- [ ] Save `WT-7264/REPORT.md` from the agent's final message, then review `WT-7264/REPORT.md`,
      `results/summary.md`, `results/plots/`, and `results/runs/P1-5.0.33-W1-off-profile/profile/`.
- [ ] Commit manually (nothing is committed; raw data under `results/runs/*/raw/` is git-ignored).
- [ ] Decide whether Quvi should use the barrier workload (W1, stalls in 4/5 runs on 5.0.33) or Bruce's
      unmodified workload (W0: 2/10 on 5.0.33, but every run on 4.4.30 with its default settings).
- [ ] Optional: rerun on an x86-64 Linux server (more cores, real PMU: `profile.sh --event cycles`).
- [ ] Optional: source-build pair around the SERVER-67350 bisect commit `30e753ec` (4.4.1 vs 4.4.2 here are
      release builds, not a single-commit experiment).

**Done:**
- 2026-10-27: WT-7264 reproduction. Jira JSON for 12 tickets, attachments, cause/fix diffs (WT-5461,
  WT-7264, WT-7912, SERVER-56509 + revert, SERVER-61185 on master/v5.0/v4.4) and source snapshots at
  r5.0.33/r4.4.30; the SERVER-67350 reporter's logs and FTDC decoded (own FTDC decoder). PLAN.md with
  pre-registered criteria after 11 disclosed pilot runs. Docker-only pipeline (`run.sh` with `--target`,
  `--image`, `--mongod-binary`, `--set`/`--prefix-search`, hard cap), `campaign.sh`, 1 Hz serverStatus +
  per-thread CPU sampler, analysis + plots, perf/gdb sidecar with a stall-triggered gdb snapshot. Runs
  until the pause: primary A/B (5+5), Bruce's unmodified workload on 5.0.33 (10+10), 4.4.30 off/on (3+3),
  profiles of a stuck run and a fixed run, part of 4.4.2/4.4.1/4.2.24. 5 runs excluded (4 overlapped a host
  sleep at 23:59–00:15, 1 aborted by the pause). Paused 00:22 with nothing running.
- 2026-10-28: resumed. Power source reconstructed for every earlier run from `pmset -g log` and recorded
  live from now on; AC-only sensitivity check added. After 72 min waiting for AC, the user said to run on
  battery: the last 17 runs (4.4.2/4.4.1/4.2.24 repetitions, barrier variants, non-unique control,
  SERVER-67350-like variant) ran 11:13–11:38 on battery. Final analysis, plots, README, PLAN outcome.
  Containers, volumes and the `w7264-net` network removed; images kept.

**Decisions:**
- Primary A/B is a single-binary parameter flip (`mongo:5.0.33`, runtime-settable parameter, checked at
  `r5.0.33` and with `getParameter`), not a version comparison.
- Primary workload is a labelled barrier variant of Bruce's script (all threads start their first
  insertMany together): pilots showed the unmodified script stalls in ~1/6 runs on 5.0.33 here, the
  barrier in 3/3. The unmodified script was run too (10+10) and is reported next to it.
- A stall = an insertMany call ≥ 3 s (healthy calls ≤ ~0.5 s). Hard cap 600 s (primary) / 300 s (others).
- Same client for every server: the legacy `mongo` shell from `mongo:5.0.33`.
- WT cache always 1 GB, mongod container 3 GB without swap; the other containers on the VM are sampled,
  never touched.
- 4.4.7, 5.0.0 and 5.0.1 deliberately not used (SERVER-58936).
- Host power is a recorded condition, not an exclusion reason (user's call, 2026-10-28): every check is
  reported on all counted runs and on AC-only runs. Runs that overlapped a host *sleep* are excluded.

**Open questions:**
- Is the barrier variant acceptable as the lab's default trigger, or should the instrumentation target
  4.4.30 with its default settings (stalls with the unmodified workload, but burns all cores)?
- Keep or drop the raw data (per run up to ~15 MB; profiles ~1 GB before gzip, git-ignored)?
- Rerun the 19 runs that were entirely on battery (the 17 after the resume plus RS1-4.4.1-W1 and
  BS1-4.2.24-W1) on AC, so B1 (W1), R′, C1 and the 67350-like variant also have AC data?
