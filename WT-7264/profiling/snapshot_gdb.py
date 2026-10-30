# gdb Python script: take ONE all-thread backtrace of mongod while a WT-7264 stall is in progress.
# Adapted from SERVER-52879/profiling/snapshot_gdb.py (same freeze/attach/frame-pointer mechanics).
#
# Run (inside the sidecar):  gdb -q -batch -nx -ex "set sysroot /proc/PID/root" -ex "file /proc/PID/exe" \
#                                -x snapshot_gdb.py         (env: SNAP_PID, SNAP_OUT, SNAP_MODE, ...)
# Trigger, SNAP_MODE=stall (default): some connection thread ("conn*") has been >= 85% on-CPU for the last
#   SNAP_BUSY_S seconds while at most SNAP_MAX_BUSY (6) connection threads are using >= 30% CPU, i.e. the
#   other client threads have finished and a few threads are still spinning inside their insert (the
#   symptom; a healthy run has ~20 busy connection threads until they all finish within ~0.2 s).
#   CPU is read from /proc/<pid>/task/<tid>/stat every 0.25 s.
# Trigger, SNAP_MODE=at:<secs>: unconditionally, <secs> after the script starts (control snapshot).
# Freeze: the process is SIGSTOPped at the trigger, so the snapshot shows the stall itself rather than
# whatever runs after gdb finished attaching. This needs mongod NOT to be PID 1 of its PID namespace
# (run.sh --profile starts mongod with docker --init). Otherwise it falls back to a plain attach.
# Unwinding: gdb may stop at glibc lock routines on aarch64, so those threads also get a manual
# frame-pointer walk. No breakpoints are used, so a crash of this script never leaves traps in mongod.
import json
import os
import re
import signal
import time

import gdb

PID = int(os.environ["SNAP_PID"])
OUT = os.environ.get("SNAP_OUT", "/out")
TIMEOUT = float(os.environ.get("SNAP_TIMEOUT", "40"))
MODE = os.environ.get("SNAP_MODE", "stall")
BUSY_S = float(os.environ.get("SNAP_BUSY_S", "2"))
MAX_BUSY = int(os.environ.get("SNAP_MAX_BUSY", "6"))
HZ = os.sysconf("SC_CLK_TCK")
POLL = 0.25


def conn_ticks():
    out = {}
    base = f"/proc/{PID}/task"
    for tid in os.listdir(base):
        try:
            with open(f"{base}/{tid}/stat") as f:
                s = f.read()
        except OSError:
            continue
        lp, rp = s.find("("), s.rfind(")")
        comm = s[lp + 1:rp]
        if not comm.startswith("conn"):
            continue
        rest = s[rp + 2:].split()
        out[tid] = (comm, int(rest[11]) + int(rest[12]))
    return out


def fp_walk(max_frames=60):
    """Walk the frame-record chain of the selected thread (AArch64 x29 / x86-64 rbp)."""
    arch = gdb.selected_frame().architecture().name()
    fp_reg = "x29" if "aarch64" in arch else "rbp"
    out = []
    try:
        fp = int(gdb.parse_and_eval(f"${fp_reg}")) & 0xFFFFFFFFFFFFFFFF
    except gdb.error:
        return out
    inf = gdb.selected_inferior()
    for _ in range(max_frames):
        if fp == 0 or fp % 8:
            break
        try:
            mem = inf.read_memory(fp, 16).tobytes()
        except gdb.MemoryError:
            break
        nxt = int.from_bytes(mem[0:8], "little")
        ret = int.from_bytes(mem[8:16], "little")
        if ret == 0:
            break
        try:
            sym = gdb.execute(f"info symbol {ret - 4:#x}", to_string=True).strip()
        except gdb.error:
            sym = "??"
        sym = re.sub(r" in section \S+( of \S+)?$", "", sym)
        out.append(f"{ret:#x} {sym}")
        if nxt <= fp:
            break
        fp = nxt
    return out


t_start = time.time()
fired = None
trigger_info = {}
hist = []          # [(t, {tid: (comm, ticks)})]
busy_since = {}
if MODE.startswith("at:"):
    delay = float(MODE.split(":", 1)[1])
    time.sleep(max(0.0, delay - (time.time() - t_start)))
    fired = time.time()
    trigger_info = {"mode": MODE}
else:
    while time.time() - t_start < TIMEOUT:
        now = time.monotonic()
        try:
            cur = conn_ticks()
        except OSError:
            break
        hist.append((now, cur))
        while hist and now - hist[0][0] > 1.0 + POLL / 2:
            hist.pop(0)
        t0, old = hist[0]
        dt = now - t0
        if dt >= 0.9:
            frac = {tid: (cur[tid][1] - old[tid][1]) / HZ / dt for tid in cur if tid in old}
            busy = [tid for tid, f in frac.items() if f >= 0.30]
            for tid, f in frac.items():
                if f >= 0.85:
                    busy_since.setdefault(tid, now)
                else:
                    busy_since.pop(tid, None)
            long_busy = [tid for tid, s in busy_since.items() if now - s >= BUSY_S]
            if long_busy and len(busy) <= MAX_BUSY:
                fired = time.time()
                trigger_info = {"mode": "stall", "spinning_threads": {tid: cur[tid][0] for tid in long_busy},
                                "conn_threads_using_30pct_cpu": len(busy),
                                "cpu_fraction_last_1s": {tid: round(frac[tid], 2) for tid in busy}}
                break
        time.sleep(POLL)

meta = {"pid": PID, "mode": MODE, "busy_s": BUSY_S}
if fired is None:
    meta["result"] = f"no trigger within {TIMEOUT}s"
else:
    stopped = False
    if PID != 1:
        os.kill(PID, signal.SIGSTOP)
        stopped = True
    t_frozen = time.time()
    gdb.execute(f"attach {PID}", to_string=True)
    t_att = time.time()
    bt = gdb.execute("thread apply all bt", to_string=True)
    extra = []
    for th in gdb.selected_inferior().threads():
        th.switch()
        try:
            f0 = gdb.newest_frame()
            names, f = [], f0
            for _ in range(4):
                if f is None:
                    break
                names.append(f.name() or "")
                f = f.older()
        except gdb.error:
            continue
        if any(n in ("__lll_lock_wait", "pthread_mutex_lock", "__pthread_mutex_lock") for n in names):
            extra.append(f'Thread LWP {th.ptid[1]} "{th.name}" frame-pointer walk:')
            extra += [f"  fp#{i} {s}" for i, s in enumerate(fp_walk())]
    gdb.execute("detach", to_string=True)
    if stopped:
        os.kill(PID, signal.SIGCONT)
    t_cont = time.time()
    with open(os.path.join(OUT, "snapshot.txt"), "w") as f:
        f.write(bt)
        f.write("\n\n=== frame-pointer walks for threads stopped in pthread lock routines ===\n")
        f.write("\n".join(extra) + "\n")
    meta.update({"result": "captured", "frozen_with_sigstop": stopped, "trigger_epoch_s": fired,
                 "trigger_s_after_script_start": round(fired - t_start, 2), "trigger": trigger_info,
                 "freeze_latency_ms": round((t_frozen - fired) * 1000, 2),
                 "attach_done_ms_after_trigger": round((t_att - fired) * 1000, 1),
                 "process_paused_ms": round((t_cont - fired) * 1000, 1)})
with open(os.path.join(OUT, "snapshot_meta.txt"), "w") as f:
    for k, v in meta.items():
        f.write(f"{k}: {json.dumps(v) if isinstance(v, dict) else v}\n")
print("snapshot:", meta)
