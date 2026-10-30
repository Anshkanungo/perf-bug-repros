# gdb Python script: take ONE all-thread backtrace of mongod while the idle-session sweeper is busy.
#
# Run (inside the sidecar):  gdb -q -batch -nx -ex "set sysroot /proc/PID/root" -ex "file /proc/PID/exe" \
#                                -x snapshot_gdb.py         (env: SNAP_PID, SNAP_TID, SNAP_OUT, ...)
# Trigger: the sweeper thread (SNAP_TID) accumulated >= SNAP_BUSY_MS of CPU within the last 10 ms
# (from /proc/<pid>/task/<tid>/schedstat), i.e. it is in the middle of a heavy closeExpiredIdleSessions.
# Freeze: the process is SIGSTOPped at the trigger (microseconds), so the snapshot shows the stall itself
# rather than whatever is running ~100 ms later when gdb has finished attaching. This needs mongod to
# NOT be PID 1 of its PID namespace (the kernel ignores SIGSTOP sent to a namespace's init from inside
# it); run.sh --profile starts mongod with docker --init for that reason. Without it, the script falls
# back to a plain (slower) attach and says so.
# Unwinding: gdb stops at glibc's pthread_mutex_lock on aarch64 ("previous frame identical"), so for
# those threads the frame-pointer chain (x29/rbp) is also walked by hand and symbolized.
# No breakpoints are used, so a timeout or crash of this script can never leave traps in mongod.
import collections
import os
import re
import signal
import time

import gdb

PID = int(os.environ["SNAP_PID"])
TID = int(os.environ["SNAP_TID"])
OUT = os.environ.get("SNAP_OUT", "/out")
TIMEOUT = float(os.environ.get("SNAP_TIMEOUT", "150"))
BUSY_MS = float(os.environ.get("SNAP_BUSY_MS", "5"))
WINDOW = 0.010
STAT = f"/proc/{PID}/task/{TID}/schedstat"


def oncpu_ns():
    with open(STAT) as f:
        return int(f.read().split()[0])


def fp_walk(max_frames=40):
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


hist = collections.deque()
t_end = time.time() + TIMEOUT
fired = None
while time.time() < t_end:
    now = time.monotonic()
    v = oncpu_ns()
    hist.append((now, v))
    while hist and now - hist[0][0] > WINDOW:
        hist.popleft()
    if (v - hist[0][1]) / 1e6 >= BUSY_MS:
        fired = (time.time(), (v - hist[0][1]) / 1e6)
        break
    time.sleep(0.0005)

meta = {"pid": PID, "sweeper_tid": TID, "busy_ms_threshold": BUSY_MS}
if fired is None:
    meta["result"] = f"no heavy sweep within {TIMEOUT}s"
else:
    t_trig, busy = fired
    stopped = False
    if PID != 1:
        os.kill(PID, signal.SIGSTOP)
        stopped = True
    t_frozen = time.time()
    gdb.execute(f"attach {PID}", to_string=True)
    t_att = time.time()
    bt = gdb.execute("thread apply all bt", to_string=True)
    # Manual frame-pointer walk for every thread whose CFI unwind ended inside a pthread lock routine.
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
    t_bt = time.time()
    gdb.execute("detach", to_string=True)
    if stopped:
        os.kill(PID, signal.SIGCONT)
    t_cont = time.time()
    with open(os.path.join(OUT, "snapshot.txt"), "w") as f:
        f.write(bt)
        f.write("\n\n=== frame-pointer walks for threads stopped in pthread lock routines ===\n")
        f.write("\n".join(extra) + "\n")
    meta.update({"result": "captured", "frozen_with_sigstop": stopped,
                 "trigger_epoch_s": t_trig, "sweeper_cpu_ms_in_last_10ms": round(busy, 2),
                 "freeze_latency_ms": round((t_frozen - t_trig) * 1000, 2),
                 "attach_done_ms_after_trigger": round((t_att - t_trig) * 1000, 1),
                 "process_paused_ms": round((t_cont - t_trig) * 1000, 1)})
with open(os.path.join(OUT, "snapshot_meta.txt"), "w") as f:
    for k, v in meta.items():
        f.write(f"{k}: {v}\n")
print("snapshot:", meta)
