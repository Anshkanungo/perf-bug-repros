# gdb all-thread snapshot (WT-7264)

```
pid: 7
mode: stall
busy_s: 2.0
result: captured
frozen_with_sigstop: True
trigger_epoch_s: 1793157733.420138
trigger_s_after_script_start: 17.22
trigger: {"mode": "stall", "spinning_threads": {"216": "conn13"}, "conn_threads_using_30pct_cpu": 2, "cpu_fraction_last_1s": {"215": 1.0, "216": 1.0}}
freeze_latency_ms: 0.16
attach_done_ms_after_trigger: 112.7
process_paused_ms: 147.9
```

37 threads.

| state | threads | thread names |
|---|---|---|
| condition-variable wait (background thread) | 24 | Authori.nager-0, Backgro.kSource, Certifi.Monitor, Checkpointer, DeadlineMonitor, FlowCon.fresher, JournalFlusher, Logical.Refresh |
| idle connection: waiting for next request | 4 | conn4, conn5, conn6, conn7 |
| eviction | 3 | mongod |
| conn thread in the unique-index duplicate check (_keyExists -> search_near/next/prev), inside a history-store lookup (__wt_hs_find_upd) | 2 | conn12, conn13 |
| waiting in recv/poll | 2 | Service.Fixed-0, listener |
| sleeping | 1 | clientcursormon |
| other | 1 | SignalHandler |

Example, conn thread in the unique-index duplicate check (_keyExists -> search_near/next/prev), inside a history-store lookup (__wt_hs_find_upd): thread `conn13` (LWP 216), frames #0..:

```
#0  __wt_struct_packv
#1  __wt_cursor_set_keyv
#2  __wt_cursor_set_key
#3  __curhs_set_key
#4  __wt_hs_find_upd
#5  __wt_txn_read
#6  __wt_btcur_prev
#7  __wt_btcur_search_near
#8  __curfile_search_near
#9  int mongo::wiredTigerPrepareConflictRetry<mongo::WiredTigerIndexUnique::_keyExists
#10 mongo::WiredTigerIndexUnique::_keyExists
#11 mongo::WiredTigerIndexUnique::_insert
#12 mongo::WiredTigerIndex::insert
#13 mongo::AbstractIndexAccessMethod::insertKeys
#14 mongo::AbstractIndexAccessMethod::insertKeysAndUpdateMultikeyPaths
#15 mongo::IndexCatalogImpl::_indexKeys
#16 mongo::IndexCatalogImpl::_indexFilteredRecords
#17 mongo::IndexCatalogImpl::_indexRecords
#18 mongo::IndexCatalogImpl::indexRecords
#19 mongo::CollectionImpl::_insertDocuments
#20 mongo::CollectionImpl::insertDocuments
#21 mongo::write_ops_exec::
#22 mongo::write_ops_exec::performInserts
#23 mongo::
#24 mongo::TypedCommand<mongo::
#25 mongo::CommandHelpers::runCommandInvocation
#26 mongo::CommandHelpers::runCommandInvocation
#27 mongo::
#28 mongo::
#29 mongo::
#30 mongo::
#31 mongo::
#32 mongo::
#33 mongo::
#34 mongo::unique_function<void
#35 mongo::future_details::SharedStateBase::transitionToFinished
#36 auto mongo::future_details::FutureImpl<mongo::future_details::FakeVoid>::generalImpl<mongo::future_details::FutureImpl<mongo::future_details::FakeVoid>::propagateResultTo
#37 mongo::unique_function<void
#38 mongo::future_details::SharedStateBase::transitionToFinished
#39 mongo::
#40 mongo::
#41 mongo::
#42 mongo::ServiceEntryPointCommon::handleRequest
#43 mongo::ServiceEntryPointMongod::handleRequest
#44 mongo::transport::ServiceStateMachine::Impl::processMessage
```

Example, conn thread in the unique-index duplicate check (_keyExists -> search_near/next/prev), inside a history-store lookup (__wt_hs_find_upd): thread `conn12` (LWP 215), frames #0..:

```
#0  __curhs_close
#1  __wt_hs_find_upd
#2  __wt_txn_read
#3  __wt_btcur_next_prefix
#4  __curfile_next
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
