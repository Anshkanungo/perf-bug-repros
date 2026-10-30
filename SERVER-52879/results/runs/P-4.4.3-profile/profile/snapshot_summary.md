# gdb all-thread snapshot during a sweep (SERVER-52879)

```
pid: 6
sweeper_tid: 30
busy_ms_threshold: 5.0
result: captured
frozen_with_sigstop: True
trigger_epoch_s: 1793148408.6872537
sweeper_cpu_ms_in_last_10ms: 5.41
freeze_latency_ms: 0.06
attach_done_ms_after_trigger: 97.7
process_paused_ms: 229.4
```

136 threads.

| state | threads | example thread names |
|---|---|---|
| waiting in recv/poll | 94 | conn10, conn100, conn101, conn102, conn103, conn104 |
| condition-variable wait (background thread) | 25 | Backgro.kSource, DeadlineMonitor, FlowCon.fresher, FreeMon.ocessor, FreeMonHTTP-0, FreeMonNet |
| BLOCKED on session-cache mutex in getSession() | 8 | conn14, conn17, conn54, conn74, conn82, conn84 |
| other | 6 | SignalHandler, conn4, conn57, listener, mongod, waitForMajority |
| sleeping | 2 | TTLMonitor, clientcursormon |
| sweeper: closing idle sessions in closeExpiredIdleSessions (4.4.3: under the session-cache mutex; 4.4.4: after releasing it) | 1 | WTIdleS.Sweeper |

Example, sweeper: closing idle sessions in closeExpiredIdleSessions (4.4.3: under the session-cache mutex; 4.4.4: after releasing it): thread `WTIdleS.Sweeper` (LWP 30), frames #0..:

```
#0  tc_free
#1  __wt_cursor_close
#2  __curfile_close
#3  __session_close_cursors.isra.7
#4  __session_close_cached_cursors
#5  __wt_session_close_internal
#6  __session_close
#7  mongo::WiredTigerSession::~WiredTigerSession
#8  mongo::WiredTigerSessionCache::closeExpiredIdleSessions
#9  mongo::WiredTigerKVEngine::WiredTigerSessionSweeper::run
#10 mongo::BackgroundJob::jobBody
#11 std::thread::_State_impl<std::thread::_Invoker<std::tuple<mongo::stdx::thread::thread<mongo::BackgroundJob::go
#12 execute_native_thread_routine
#13 start_thread
#14 ??
```

Example, BLOCKED on session-cache mutex in getSession(): thread `conn98` (LWP 148), frames #0..:

```
#0  __lll_lock_wait
#1  pthread_mutex_lock
#2  (frame-pointer walk:)
#3  mongo::latch_detail::Mutex::lock()
#4  mongo::WiredTigerSessionCache::getSession()
#5  mongo::WiredTigerRecoveryUnit::_ensureSession() [clone .part.363]
#6  mongo::WiredTigerRecoveryUnit::_txnOpen()
#7  mongo::WiredTigerRecoveryUnit::getSession()
#8  mongo::WiredTigerCursor::WiredTigerCursor(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&, unsigned long, bool, mongo::OperationContext*)
#9  mongo::WiredTigerRecordStore::_insertRecords(mongo::OperationContext*, mongo::Record*, mongo::Timestamp const*, unsigned long)
#10 mongo::WiredTigerRecordStore::insertRecords(mongo::OperationContext*, std::vector<mongo::Record, std::allocator<mongo::Record> >*, std::vector<mongo::Timestamp, std::allocator<mongo::Timestamp> > const&)
#11 mongo::CollectionImpl::_insertDocuments(mongo::OperationContext*, __gnu_cxx::__normal_iterator<mongo::InsertStatement const*, std::vector<mongo::InsertStatement, std::allocator<mongo::InsertStatement> > >, __gnu_cxx::__normal_iterator<mongo::InsertStatement const*, std::vector<mongo::InsertStatement, std::allocator<mongo::InsertStatement> > >, mongo::OpDebug*)
#12 mongo::CollectionImpl::insertDocuments(mongo::OperationContext*, __gnu_cxx::__normal_iterator<mongo::InsertStatement const*, std::vector<mongo::InsertStatement, std::allocator<mongo::InsertStatement> > >, __gnu_cxx::__normal_iterator<mongo::InsertStatement const*, std::vector<mongo::InsertStatement, std::allocator<mongo::InsertStatement> > >, mongo::OpDebug*, bool)
#13 mongo::(anonymous namespace)::insertDocuments(mongo::OperationContext*, mongo::Collection*, __gnu_cxx::__normal_iterator<mongo::InsertStatement*, std::vector<mongo::InsertStatement, std::allocator<mongo::InsertStatement> > >, __gnu_cxx::__normal_iterator<mongo::InsertStatement*, std::vector<mongo::InsertStatement, std::allocator<mongo::InsertStatement> > >, bool)
#14 mongo::(anonymous namespace)::insertBatchAndHandleErrors(mongo::OperationContext*, mongo::write_ops::Insert const&, std::vector<mongo::InsertStatement, std::allocator<mongo::InsertStatement> >&, mongo::(anonymous namespace)::LastOpFixer*, mongo::WriteResult*, bool)::{lambda()#4}::operator()() const
#15 mongo::performInserts(mongo::OperationContext*, mongo::write_ops::Insert const&, bool)
#16 mongo::(anonymous namespace)::CmdInsert::Invocation::runImpl(mongo::OperationContext*, mongo::BSONObjBuilder&) const
#17 mongo::(anonymous namespace)::WriteCommand::InvocationBase::run(mongo::OperationContext*, mongo::rpc::ReplyBuilderInterface*)
#18 mongo::CommandHelpers::runCommandInvocation(mongo::OperationContext*, mongo::OpMsgRequest const&, mongo::CommandInvocation*, mongo::rpc::ReplyBuilderInterface*)
#19 mongo::(anonymous namespace)::runCommandImpl(mongo::OperationContext*, mongo::CommandInvocation*, mongo::OpMsgRequest const&, mongo::rpc::ReplyBuilderInterface*, mongo::LogicalTime, mongo::ServiceEntryPointCommon::Hooks const&, mongo::BSONObjBuilder*, mongo::OperationSessionInfoFromClient const&)
#20 mongo::(anonymous namespace)::execCommandDatabase(mongo::OperationContext*, mongo::Command*, mongo::OpMsgRequest const&, mongo::rpc::ReplyBuilderInterface*, mongo::ServiceEntryPointCommon::Hooks const&)
#21 mongo::(anonymous namespace)::receivedCommands(mongo::OperationContext*, mongo::Message const&, mongo::ServiceEntryPointCommon::Hooks const&)
#22 mongo::ServiceEntryPointCommon::handleRequest(mongo::OperationContext*, mongo::Message const&, mongo::ServiceEntryPointCommon::Hooks const&)
#23 mongo::ServiceEntryPointMongod::handleRequest(mongo::OperationContext*, mongo::Message const&)
#24 mongo::ServiceStateMachine::_processMessage(mongo::ServiceStateMachine::ThreadGuard)
#25 mongo::ServiceStateMachine::_runNextInGuard(mongo::ServiceStateMachine::ThreadGuard)
#26 std::_Function_handler<void (), mongo::ServiceStateMachine::_scheduleNextWithGuard(mongo::ServiceStateMachine::ThreadGuard, mongo::transport::ServiceExecutor::ScheduleFlags, mongo::transport::ServiceExecutorTaskName, mongo::ServiceStateMachine::Ownership)::{lambda()#1}>::_M_invoke(std::_Any_data const&)
#27 mongo::transport::ServiceExecutorSynchronous::schedule(std::function<void ()>, mongo::transport::ServiceExecutor::ScheduleFlags, mongo::transport::ServiceExecutorTaskName)
#28 mongo::ServiceStateMachine::_scheduleNextWithGuard(mongo::ServiceStateMachine::ThreadGuard, mongo::transport::ServiceExecutor::ScheduleFlags, mongo::transport::ServiceExecutorTaskName, mongo::ServiceStateMachine::Ownership)
#29 mongo::ServiceStateMachine::_sourceCallback(mongo::Status)
```
