# gdb all-thread snapshot (WT-7264)

```
pid: 7
mode: at:9
busy_s: 2.0
result: captured
frozen_with_sigstop: True
trigger_epoch_s: 1793158088.5462925
trigger_s_after_script_start: 9.0
trigger: {"mode": "at:9"}
freeze_latency_ms: 0.2
attach_done_ms_after_trigger: 98.6
process_paused_ms: 168.1
```

55 threads.

| state | threads | thread names |
|---|---|---|
| condition-variable wait (background thread) | 23 | Authori.nager-0, Backgro.kSource, Certifi.Monitor, Checkpointer, DeadlineMonitor, FlowCon.fresher, JournalFlusher, Logical.Refresh |
| conn thread elsewhere in an insert command (locks, flow control, reply) | 12 | conn11, conn12, conn13, conn16, conn17, conn20, conn21, conn25 |
| conn thread in WiredTigerIndexUnique::_insert (other step) | 5 | conn10, conn15, conn18, conn22, conn24 |
| idle connection: waiting for next request | 5 | conn14, conn4, conn5, conn6, conn7 |
| eviction | 4 | mongod |
| other | 2 | SignalHandler, conn23 |
| waiting in recv/poll | 2 | Service.Fixed-0, listener |
| conn thread in the unique-index duplicate check (_keyExists -> search_near/next/prev) | 1 | conn19 |
| sleeping | 1 | clientcursormon |

Example, conn thread in the unique-index duplicate check (_keyExists -> search_near/next/prev): thread `conn19` (LWP 222), frames #0..:

```
#0  __wt_hazard_set_func
#1  __wt_page_in_func
#2  __wt_row_search
#3  __wt_btcur_search_near
#4  __curfile_search_near
#5  int mongo::wiredTigerPrepareConflictRetry<mongo::WiredTigerIndexUnique::_keyExists
#6  mongo::WiredTigerIndexUnique::_keyExists
#7  mongo::WiredTigerIndexUnique::_insert
#8  mongo::WiredTigerIndex::insert
#9  mongo::AbstractIndexAccessMethod::insertKeys
#10 mongo::AbstractIndexAccessMethod::insertKeysAndUpdateMultikeyPaths
#11 mongo::IndexCatalogImpl::_indexKeys
#12 mongo::IndexCatalogImpl::_indexFilteredRecords
#13 mongo::IndexCatalogImpl::_indexRecords
#14 mongo::IndexCatalogImpl::indexRecords
#15 mongo::CollectionImpl::_insertDocuments
#16 mongo::CollectionImpl::insertDocuments
#17 mongo::write_ops_exec::
#18 mongo::write_ops_exec::performInserts
#19 mongo::
#20 mongo::TypedCommand<mongo::
#21 mongo::CommandHelpers::runCommandInvocation
#22 mongo::CommandHelpers::runCommandInvocation
#23 mongo::
#24 mongo::
#25 mongo::
#26 mongo::
#27 mongo::
#28 mongo::
#29 mongo::
#30 mongo::unique_function<void
#31 mongo::future_details::SharedStateBase::transitionToFinished
#32 auto mongo::future_details::FutureImpl<mongo::future_details::FakeVoid>::generalImpl<mongo::future_details::FutureImpl<mongo::future_details::FakeVoid>::propagateResultTo
#33 mongo::unique_function<void
#34 mongo::future_details::SharedStateBase::transitionToFinished
#35 mongo::
#36 mongo::
#37 mongo::
#38 mongo::ServiceEntryPointCommon::handleRequest
#39 mongo::ServiceEntryPointMongod::handleRequest
#40 mongo::transport::ServiceStateMachine::Impl::processMessage
#41 mongo::future_details::FutureImpl<mongo::future_details::FakeVoid>::then<mongo::transport::ServiceStateMachine::Impl::startNewLoop
#42 mongo::transport::ServiceStateMachine::Impl::startNewLoop
#43 mongo::unique_function<void
#44 mongo::unique_function<void
```

Example, conn thread in WiredTigerIndexUnique::_insert (other step): thread `conn24` (LWP 227), frames #0..:

```
#0  __wt_hazard_set_func
#1  __wt_page_in_func
#2  __wt_row_search
#3  __wt_btcur_insert
#4  __curfile_insert
#5  mongo::wiredTigerCursorInsert
#6  mongo::WiredTigerIndexUnique::_insert
#7  mongo::WiredTigerIndex::insert
#8  mongo::AbstractIndexAccessMethod::insertKeys
#9  mongo::AbstractIndexAccessMethod::insertKeysAndUpdateMultikeyPaths
#10 mongo::IndexCatalogImpl::_indexKeys
#11 mongo::IndexCatalogImpl::_indexFilteredRecords
#12 mongo::IndexCatalogImpl::_indexRecords
#13 mongo::IndexCatalogImpl::indexRecords
#14 mongo::CollectionImpl::_insertDocuments
#15 mongo::CollectionImpl::insertDocuments
#16 mongo::write_ops_exec::
#17 mongo::write_ops_exec::performInserts
#18 mongo::
#19 mongo::TypedCommand<mongo::
#20 mongo::CommandHelpers::runCommandInvocation
#21 mongo::CommandHelpers::runCommandInvocation
#22 mongo::
#23 mongo::
#24 mongo::
#25 mongo::
#26 mongo::
#27 mongo::
#28 mongo::
#29 mongo::unique_function<void
#30 mongo::future_details::SharedStateBase::transitionToFinished
#31 auto mongo::future_details::FutureImpl<mongo::future_details::FakeVoid>::generalImpl<mongo::future_details::FutureImpl<mongo::future_details::FakeVoid>::propagateResultTo
#32 mongo::unique_function<void
#33 mongo::future_details::SharedStateBase::transitionToFinished
#34 mongo::
#35 mongo::
#36 mongo::
#37 mongo::ServiceEntryPointCommon::handleRequest
#38 mongo::ServiceEntryPointMongod::handleRequest
#39 mongo::transport::ServiceStateMachine::Impl::processMessage
#40 mongo::future_details::FutureImpl<mongo::future_details::FakeVoid>::then<mongo::transport::ServiceStateMachine::Impl::startNewLoop
#41 mongo::transport::ServiceStateMachine::Impl::startNewLoop
#42 mongo::unique_function<void
#43 mongo::unique_function<void
#44 mongo::unique_function<void
```

Example, conn thread in WiredTigerIndexUnique::_insert (other step): thread `conn22` (LWP 225), frames #0..:

```
#0  __wt_row_modify
#1  __wt_btcur_insert
#2  __curfile_insert
#3  mongo::wiredTigerCursorInsert
#4  mongo::WiredTigerIndexUnique::_insert
#5  mongo::WiredTigerIndex::insert
#6  mongo::AbstractIndexAccessMethod::insertKeys
#7  mongo::AbstractIndexAccessMethod::insertKeysAndUpdateMultikeyPaths
#8  mongo::IndexCatalogImpl::_indexKeys
#9  mongo::IndexCatalogImpl::_indexFilteredRecords
#10 mongo::IndexCatalogImpl::_indexRecords
#11 mongo::IndexCatalogImpl::indexRecords
#12 mongo::CollectionImpl::_insertDocuments
#13 mongo::CollectionImpl::insertDocuments
#14 mongo::write_ops_exec::
#15 mongo::write_ops_exec::performInserts
#16 mongo::
#17 mongo::TypedCommand<mongo::
#18 mongo::CommandHelpers::runCommandInvocation
#19 mongo::CommandHelpers::runCommandInvocation
#20 mongo::
#21 mongo::
#22 mongo::
#23 mongo::
#24 mongo::
#25 mongo::
#26 mongo::
#27 mongo::unique_function<void
#28 mongo::future_details::SharedStateBase::transitionToFinished
#29 auto mongo::future_details::FutureImpl<mongo::future_details::FakeVoid>::generalImpl<mongo::future_details::FutureImpl<mongo::future_details::FakeVoid>::propagateResultTo
#30 mongo::unique_function<void
#31 mongo::future_details::SharedStateBase::transitionToFinished
#32 mongo::
#33 mongo::
#34 mongo::
#35 mongo::ServiceEntryPointCommon::handleRequest
#36 mongo::ServiceEntryPointMongod::handleRequest
#37 mongo::transport::ServiceStateMachine::Impl::processMessage
#38 mongo::future_details::FutureImpl<mongo::future_details::FakeVoid>::then<mongo::transport::ServiceStateMachine::Impl::startNewLoop
#39 mongo::transport::ServiceStateMachine::Impl::startNewLoop
#40 mongo::unique_function<void
#41 mongo::unique_function<void
#42 mongo::unique_function<void
#43 mongo::unique_function<void
#44 mongo::unique_function<void
```
