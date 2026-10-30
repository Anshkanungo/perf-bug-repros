# gdb all-thread snapshot during a sweep (SERVER-52879)

```
pid: 8
sweeper_tid: 34
busy_ms_threshold: 5.0
result: captured
frozen_with_sigstop: True
trigger_epoch_s: 1793151488.4165742
sweeper_cpu_ms_in_last_10ms: 5.38
freeze_latency_ms: 0.1
attach_done_ms_after_trigger: 108.3
process_paused_ms: 226.6
```

136 threads.

| state | threads | example thread names |
|---|---|---|
| waiting in recv/poll | 103 | conn10, conn100, conn101, conn102, conn103, conn104 |
| condition-variable wait (background thread) | 26 | Backgro.kSource, DeadlineMonitor, FlowCon.fresher, FreeMon.ocessor, FreeMonHTTP-0, FreeMonNet |
| other | 4 | SignalHandler, conn4, listener, waitForMajority |
| sleeping | 2 | TTLMonitor, clientcursormon |
| sweeper: closing idle sessions in closeExpiredIdleSessions (4.4.3: under the session-cache mutex; 4.4.4: after releasing it) | 1 | WTIdleS.Sweeper |

Example, sweeper: closing idle sessions in closeExpiredIdleSessions (4.4.3: under the session-cache mutex; 4.4.4: after releasing it): thread `WTIdleS.Sweeper` (LWP 34), frames #0..:

```
#0  __wt_cursor_reopen
#1  __curfile_reopen
#2  __session_close_cursors.isra.6
#3  __session_close_cached_cursors
#4  __wt_session_close_internal
#5  __session_close
#6  mongo::WiredTigerSession::~WiredTigerSession
#7  mongo::WiredTigerSessionCache::closeExpiredIdleSessions
#8  mongo::WiredTigerKVEngine::WiredTigerSessionSweeper::run
#9  mongo::BackgroundJob::jobBody
#10 std::thread::_State_impl<std::thread::_Invoker<std::tuple<mongo::stdx::thread::thread<mongo::BackgroundJob::go
#11 execute_native_thread_routine
#12 start_thread
#13 ??
```
