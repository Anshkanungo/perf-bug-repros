# gdb all-thread snapshot (WT-7264)

```
pid: 7
mode: at:7
busy_s: 2.0
result: captured
frozen_with_sigstop: True
trigger_epoch_s: 1793157606.70604
trigger_s_after_script_start: 7.0
trigger: {"mode": "at:7"}
freeze_latency_ms: 0.09
attach_done_ms_after_trigger: 119.4
process_paused_ms: 160.7
```

55 threads.

| state | threads | thread names |
|---|---|---|
| condition-variable wait (background thread) | 27 | Authori.nager-0, Backgro.kSource, Certifi.Monitor, Checkpointer, DeadlineMonitor, FlowCon.fresher, JournalFlusher, Logical.Refresh |
| idle connection: waiting for next request | 24 | conn10, conn11, conn12, conn13, conn14, conn15, conn16, conn17 |
| waiting in recv/poll | 2 | Service.Fixed-0, listener |
| sleeping | 1 | clientcursormon |
| other | 1 | SignalHandler |
