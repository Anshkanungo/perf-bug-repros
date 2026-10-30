# Profile summary (SERVER-52879)

```
date_utc: 2026-10-28T01:35:02Z
kernel: 7.0.14-linuxkit aarch64
perf: perf version 6.1.190
gdb: GNU gdb (Debian 13.1-3) 13.1
perf_event_paranoid: 2 (bypassed: privileged container)
mongod pid (in this pid namespace): 8
mongod exe: /usr/bin/mongod
mongod build-id: b24bfa44ad39ef4efe533343362d549fdbb5cf36
mongod sections: .eh_frame .gnu_debuglink .symtab 
threads: 136
event: cpu-clock  freq: 999  callgraph: fp  secs: 100
sweeper tid: 34
```

## On-CPU (perf, call graphs)

- samples: 60,304 total; WTIdleSessionSweeper thread: 51; of those inside `closeExpiredIdleSessions`: **51**
- busiest threads: mongod 33,254, conn* 21,865, WTCheck.tThread 4,728, WTJourn.Flusher 153, ftdc 151, Backgro.kSource 92, WTIdleS.Sweeper 51, TTLMonitor 3

Share of sweep samples whose stack contains each function (inclusive):

| function | % of sweep samples |
|---|---|
| `mongo::WiredTigerSessionCache::closeExpiredIdleSessions` | 100.0 |
| `mongo::WiredTigerSession::~WiredTigerSession` | 100.0 |
| `__session_close` | 100.0 |
| `__session_close_cached_cursors` | 90.2 |
| `__wt_session_close_cache` | 9.8 |
| `__session_discard_dhandle` | 9.8 |
| `__wt_cursor_close` | 15.7 |
| `__curfile_close` | 27.5 |
| `__wt_free_int` | 7.8 |

Top leaf (self) functions in sweep samples:

| leaf function | % |
|---|---|
| `__wt_cursor_reopen` | 27.5 |
| `__curfile_reopen` | 19.6 |
| `__wt_readlock` | 13.7 |
| `__wt_readunlock` | 9.8 |
| `tcmalloc::CentralFreeList::ReleaseToSpans` | 7.8 |
| `__wt_free_int` | 7.8 |
| `tc_deletearray_aligned_nothrow` | 3.9 |
| `__session_discard_dhandle` | 3.9 |
| `__curfile_close` | 2.0 |
| `__session_close_cursors.isra.6` | 2.0 |

Most common sweeper stacks (leaf first, down to `closeExpiredIdleSessions`):

- 14 samples: `__wt_cursor_reopen <- __curfile_reopen <- __session_close_cursors.isra.6 <- __session_close_cached_cursors <- __wt_session_close_internal <- __session_close <- mongo::WiredTigerSession::~WiredTigerSession <- mongo::WiredTigerSessionCache::closeExpiredIdleSessions`
- 10 samples: `__curfile_reopen <- __session_close_cursors.isra.6 <- __session_close_cached_cursors <- __wt_session_close_internal <- __session_close <- mongo::WiredTigerSession::~WiredTigerSession <- mongo::WiredTigerSessionCache::closeExpiredIdleSessions`
- 7 samples: `__wt_readlock <- __wt_session_lock_dhandle <- __curfile_reopen <- __session_close_cursors.isra.6 <- __session_close_cached_cursors <- __wt_session_close_internal <- __session_close <- mongo::WiredTigerSession::~WiredTigerSession <- mongo::WiredTigerSessionCache::closeExpiredIdleSessions`

## Sweep windows (sweeper on-CPU inside closeExpiredIdleSessions, samples ≤100 ms apart)

| # | start (epoch s) | duration (ms) | samples | threads that blocked on the session-cache mutex | longest such wait (ms) | client inserts ≥10 ms overlapping | max client latency (ms) |
|---|---|---|---|---|---|---|---|
| 1 | 1793151328.336 | 44.0 | 44 | 0 | 0.0 | 0 | 1.0 |
| 2 | 1793151378.381 | 7.0 | 7 | 0 | 0.0 | 0 | 1.0 |

## Off-CPU (sched_switch → sched_wakeup, call graphs)

- 252,091 switch-outs, 20,787 wakeup events, 248,565 blocking waits (75 closed by a recorded wakeup; the rest are bounded by the thread's next switch-out, i.e. blocked time plus a short run: an upper bound)

Waits that **started inside a sweep window**:

| blocking site | waits | distinct threads | total blocked (ms) | longest (ms) |
|---|---|---|---|---|
| condition variable wait | 24 | 3 | 20276.3 | 10000.2 |
| network recv (idle connection) | 75 | 64 | 7881.4 | 109.8 |

(durations without a recorded wakeup are upper bounds; see above)

All waits in the recording, for comparison:

| blocking site | waits | distinct threads | total blocked (ms) | longest (ms) |
|---|---|---|---|---|
| network recv (idle connection) | 94880 | 102 | 10181081.3 | 10010.9 |
| condition variable wait | 81301 | 81 | 1679524.0 | 60000.2 |
| sleep | 24 | 1 | 96005.5 | 4000.7 |
| poll/epoll | 941 | 12 | 91510.5 | 9910.8 |
| fsync/IO | 57140 | 2 | 18452.7 | 139.0 |
| other mutex wait | 12845 | 100 | 3345.5 | 65.3 |
| IO | 814 | 3 | 1452.6 | 34.8 |
| other | 608 | 53 | 419.8 | 16.1 |
| mutex wait in WiredTigerSessionCache::getSession | 11 | 11 | 2.2 | 0.4 |
| mutex wait in WiredTigerSessionCache::releaseSession | 1 | 1 | 0.1 | 0.1 |

Flame graphs: `oncpu_all.svg`, `oncpu_sweeper.svg`, `offcpu_sweeps.svg`, `offcpu_long.svg`.
