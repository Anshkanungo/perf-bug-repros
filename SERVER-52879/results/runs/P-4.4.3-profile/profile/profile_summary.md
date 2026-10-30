# Profile summary (SERVER-52879)

```
date_utc: 2026-10-28T00:44:17Z
kernel: 7.0.14-linuxkit aarch64
perf: perf version 6.1.190
gdb: GNU gdb (Debian 13.1-3) 13.1
perf_event_paranoid: 2 (bypassed: privileged container)
mongod pid (in this pid namespace): 6
mongod exe: /usr/bin/mongod
mongod build-id: 4a27fe178941a944bf6a81c801e4a33d51dc4a69
mongod sections: .eh_frame .gnu_debuglink .symtab 
threads: 136
event: cpu-clock  freq: 999  callgraph: fp  secs: 100
sweeper tid: 30
```

## On-CPU (perf, call graphs)

- samples: 52,285 total; WTIdleSessionSweeper thread: 57; of those inside `closeExpiredIdleSessions`: **57**
- busiest threads: mongod 26,524, conn* 21,834, WTCheck.tThread 3,451, WTJourn.Flusher 158, ftdc 153, Backgro.kSource 97, WTIdleS.Sweeper 57, Periodi.kRunner 5

Share of sweep samples whose stack contains each function (inclusive):

| function | % of sweep samples |
|---|---|
| `mongo::WiredTigerSessionCache::closeExpiredIdleSessions` | 100.0 |
| `mongo::WiredTigerSession::~WiredTigerSession` | 100.0 |
| `__session_close` | 100.0 |
| `__session_close_cached_cursors` | 91.2 |
| `__wt_session_close_cache` | 8.8 |
| `__session_discard_dhandle` | 8.8 |
| `__wt_cursor_close` | 21.1 |
| `__curfile_close` | 36.8 |

Top leaf (self) functions in sweep samples:

| leaf function | % |
|---|---|
| `__wt_cursor_reopen` | 36.8 |
| `__wt_readlock` | 17.5 |
| `tc_deletearray_aligned_nothrow` | 14.0 |
| `__session_discard_dhandle` | 7.0 |
| `__wt_readunlock` | 5.3 |
| `__wt_session_release_dhandle` | 5.3 |
| `__wt_cursor_close` | 5.3 |
| `__curfile_close` | 3.5 |
| `tcmalloc::CentralFreeList::ReleaseToSpans` | 3.5 |
| `__wt_btcur_close` | 1.8 |

Most common sweeper stacks (leaf first, down to `closeExpiredIdleSessions`):

- 21 samples: `__wt_cursor_reopen <- __curfile_reopen <- __session_close_cursors.isra.7 <- __session_close_cached_cursors <- __wt_session_close_internal <- __session_close <- mongo::WiredTigerSession::~WiredTigerSession <- mongo::WiredTigerSessionCache::closeExpiredIdleSessions`
- 10 samples: `__wt_readlock <- __wt_session_lock_dhandle <- __curfile_reopen <- __session_close_cursors.isra.7 <- __session_close_cached_cursors <- __wt_session_close_internal <- __session_close <- mongo::WiredTigerSession::~WiredTigerSession <- mongo::WiredTigerSessionCache::closeExpiredIdleSessions`
- 8 samples: `tc_deletearray_aligned_nothrow <- __wt_cursor_close <- __curfile_close <- __session_close_cursors.isra.7 <- __session_close_cached_cursors <- __wt_session_close_internal <- __session_close <- mongo::WiredTigerSession::~WiredTigerSession <- mongo::WiredTigerSessionCache::closeExpiredIdleSessions`

## Sweep windows (sweeper on-CPU inside closeExpiredIdleSessions, samples ≤100 ms apart)

| # | start (epoch s) | duration (ms) | samples | threads that blocked on the session-cache mutex | longest such wait (ms) | client inserts ≥10 ms overlapping | max client latency (ms) |
|---|---|---|---|---|---|---|---|
| 1 | 1793148328.613 | 57.1 | 57 | 57 | 57.0 | 53 | 57.0 |

## Off-CPU (sched_switch → sched_wakeup, call graphs)

- 238,560 switch-outs, 24,652 wakeup events, 231,715 blocking waits (51 closed by a recorded wakeup; the rest are bounded by the thread's next switch-out, i.e. blocked time plus a short run: an upper bound)

Waits that **started inside a sweep window**:

| blocking site | waits | distinct threads | total blocked (ms) | longest (ms) |
|---|---|---|---|---|
| condition variable wait | 67 | 4 | 21285.6 | 10003.2 |
| network recv (idle connection) | 63 | 63 | 6648.7 | 109.7 |
| mutex wait in WiredTigerSessionCache::getSession | 57 | 57 | 1890.9 | 57.0 |

(durations without a recorded wakeup are upper bounds; see above)

All waits in the recording, for comparison:

| blocking site | waits | distinct threads | total blocked (ms) | longest (ms) |
|---|---|---|---|---|
| network recv (idle connection) | 94842 | 102 | 10178055.7 | 10013.6 |
| condition variable wait | 67385 | 13 | 1830130.2 | 60003.0 |
| sleep | 25 | 2 | 156009.1 | 60000.4 |
| poll/epoll | 901 | 15 | 91372.4 | 9910.1 |
| fsync/IO | 65087 | 2 | 16791.4 | 421.2 |
| mutex wait in WiredTigerSessionCache::getSession | 71 | 64 | 1897.6 | 57.0 |
| IO | 751 | 3 | 1194.4 | 13.4 |
| other mutex wait | 2112 | 105 | 940.6 | 75.5 |
| other | 541 | 72 | 563.1 | 50.8 |

Longest session-cache wait during a sweep: 57.0 ms on thread `conn14` (upper bound). Stack (leaf first):

```
__schedule
__schedule
schedule
futex_do_wait
__futex_wait
futex_wait
do_futex
__arm64_sys_futex
invoke_syscall.constprop.0
do_el0_svc
el0_svc
el0t_64_sync_handler
el0t_64_sync
__lll_lock_wait
__pthread_mutex_lock
mongo::latch_detail::Mutex::lock
mongo::WiredTigerSessionCache::getSession
mongo::WiredTigerRecoveryUnit::_ensureSession
mongo::WiredTigerRecoveryUnit::_txnOpen
mongo::WiredTigerRecoveryUnit::getSession
mongo::WiredTigerCursor::WiredTigerCursor
mongo::WiredTigerRecordStore::_insertRecords
mongo::WiredTigerRecordStore::insertRecords
mongo::CollectionImpl::_insertDocuments
mongo::CollectionImpl::insertDocuments
mongo::(anonymous namespace)::insertDocuments
mongo::(anonymous namespace)::insertBatchAndHandleErrors(mongo::OperationContext*, mongo::write_ops::Insert const&, std::vector<mongo::InsertStatement, std::allocator<mongo::InsertStatement> >&, mongo::(anonymous namespace)::LastOpFixer*, mongo::WriteResult*, bool)::{lambda()#4}::operator()
mongo::performInserts
mongo::(anonymous namespace)::CmdInsert::Invocation::runImpl
mongo::(anonymous namespace)::WriteCommand::InvocationBase::run
mongo::CommandHelpers::runCommandInvocation
mongo::(anonymous namespace)::runCommandImpl
mongo::(anonymous namespace)::execCommandDatabase
mongo::(anonymous namespace)::receivedCommands
mongo::ServiceEntryPointCommon::handleRequest
mongo::ServiceEntryPointMongod::handleRequest
mongo::ServiceStateMachine::_processMessage
mongo::ServiceStateMachine::_runNextInGuard
std::_Function_handler<void
mongo::transport::ServiceExecutorSynchronous::schedule
```

Flame graphs: `oncpu_all.svg`, `oncpu_sweeper.svg`, `offcpu_sweeps.svg`, `offcpu_long.svg`.
