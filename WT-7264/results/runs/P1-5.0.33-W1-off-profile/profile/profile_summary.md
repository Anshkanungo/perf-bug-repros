# Profile summary (WT-7264)

```
date_utc: 2026-10-28T03:21:55Z
kernel: 7.0.14-linuxkit aarch64
perf: perf version 6.1.190
gdb: GNU gdb (Debian 13.1-3) 13.1
perf_event_paranoid: 2 (bypassed: privileged container)
mongod pid (in this pid namespace): 7
mongod exe: /usr/bin/mongod
mongod build-id: 8c5312cc4de9153d83270c84d5ec310989d67c93
mongod sections: .eh_frame .gnu_debuglink .symtab 
threads: 34
event: cpu-clock  freq: 999  callgraph: fp  secs: 40  snapshot: 1 (stall)
```

- on-CPU samples: 98,103; connection threads: 92,190
- busiest threads: conn* 92,190, mongod 5,782, ftdc 61, JournalFlusher 43, listener 9, Service.Fixed-0 9, Backgro.kSource 6, FlowCon.fresher 2
- stuck-thread detection: client log: insertMany calls >= 3.0 s; threads >= 30% on-CPU while alone

## Stalled insertMany calls (client log)

| client thread | batch | start (epoch s) | duration (s) | alone window (s) | stuck server tid(s) |
|---|---|---|---|---|---|
| 8 | 0 | 1793157723.707 | 290.1 | 24.8 | 216, 215 |
| 7 | 0 | 1793157723.708 | still running at end of log | 24.8 | 216, 215 |

## Stuck connection thread(s): 59,978 samples over their stalled calls

Share of the stuck threads' samples whose stack contains each function (inclusive), next to the same share over **all** connection-thread samples of the recording:

| function (outermost first) | stuck: samples | stuck: % | all conn threads: % |
|---|---|---|---|
| `mongo::CollectionImpl::insertDocuments` | 59,978 | 100.0 | 97.3 |
| `mongo::WiredTigerIndex::insert` | 59,974 | 100.0 | 91.8 |
| `mongo::WiredTigerIndexUnique::_insert` | 59,973 | 100.0 | 87.9 |
| `mongo::WiredTigerIndexUnique::_keyExists` | 59,948 | 99.9 | 69.0 |
| `mongo::wiredTigerPrepareConflictRetry<...>` | 59,948 | 99.9 | 68.8 |
| `__curfile_search_near` | 44,491 | 74.2 | 50.3 |
| `__wt_btcur_search_near` | 44,377 | 74.0 | 50.2 |
| `__curfile_next` | 19,354 | 32.3 | 21.0 |
| `__curfile_prev` | 0 | 0.0 | 1.6 |
| `__wt_btcur_next[_prefix]` | 40,686 | 67.8 | 44.6 |
| `__wt_btcur_prev[_prefix]` | 23,475 | 39.1 | 27.1 |
| `__cursor_row_next` | 0 | 0.0 | 0.0 |
| `__cursor_row_prev` | 0 | 0.0 | 0.0 |
| `__wt_txn_read` | 53,648 | 89.4 | 58.6 |
| `__wt_txn_read_upd_list` | 835 | 1.4 | 1.2 |
| `__wt_hs_find_upd` | 49,129 | 81.9 | 53.3 |
| `any history-store cursor function (__curhs_* / __wt_hs_*)` | 49,129 | 81.9 | 53.3 |
| `__cursor_row_slot_key_return` | 0 | 0.0 | 0.0 |
| `__wt_lex_compare*` | 0 | 0.0 | 0.0 |
| `__wt_txn_upd_value_visible_all` | 0 | 0.0 | 0.2 |
| `__wt_row_search` | 2,500 | 4.2 | 8.0 |
| `__wt_page_in_func` | 4,110 | 6.9 | 5.6 |
| `__evict_force_check` | 0 | 0.0 | 0.0 |
| `__wt_cache_eviction_worker` | 85 | 0.1 | 1.2 |
| `KeyString::sizeWithoutRecordId*AtEnd` | 0 | 0.0 | 0.0 |

Top leaf (self) functions, stuck threads:

| leaf | samples | % |
|---|---|---|
| `__wt_session_gen_leave` | 3,847 | 6.4 |
| `__wt_readlock` | 3,323 | 5.5 |
| `__wt_hazard_set_func` | 3,173 | 5.3 |
| `__wt_struct_packv` | 2,913 | 4.9 |
| `__wt_btcur_next_prefix` | 2,877 | 4.8 |
| `__wt_config_gets_def` | 2,725 | 4.5 |
| `__wt_scr_alloc_func` | 2,720 | 4.5 |
| `__wt_btcur_prev` | 2,532 | 4.2 |
| `__wt_value_return_buf` | 2,357 | 3.9 |
| `__wt_txn_read` | 2,151 | 3.6 |
| `__ctype_b_loc` | 2,036 | 3.4 |
| `__wt_cursor_cache` | 2,029 | 3.4 |

Most common stacks of the stuck threads, from `WiredTigerIndexUnique::_keyExists` (or `_insert`) down to the leaf:

- 1,335 samples (2.2%): `mongo::wiredTigerPrepareConflictRetry<mongo::WiredTigerIndexUnique::_keyExists -> __curfile_search_near -> __wt_btcur_search_near -> __wt_btcur_prev`
- 1,319 samples (2.2%): `mongo::wiredTigerPrepareConflictRetry<mongo::WiredTigerIndexUnique::_keyExists -> __curfile_search_near -> __wt_btcur_search_near -> __wt_btcur_next_prefix`
- 1,257 samples (2.1%): `mongo::wiredTigerPrepareConflictRetry<mongo::WiredTigerIndexUnique::_keyExists -> __curfile_next -> __wt_btcur_next_prefix`
- 1,118 samples (1.9%): `mongo::wiredTigerPrepareConflictRetry<mongo::WiredTigerIndexUnique::_keyExists -> __curfile_search_near -> __wt_btcur_search_near -> __wt_btcur_prev -> __wt_txn_read -> __wt_hs_find_upd -> __wt_curhs_open -> __curhs_file_cursor_open -> __wt_open_cursor -> __wt_cursor_cache_get -> __curfile_reopen -> __wt_session_lock_dhandle -> __wt_readlock`
- 1,118 samples (1.9%): `mongo::wiredTigerPrepareConflictRetry<mongo::WiredTigerIndexUnique::_keyExists -> __curfile_search_near -> __wt_btcur_search_near -> __wt_btcur_next_prefix -> __wt_txn_read -> __wt_hs_find_upd -> __wt_curhs_open -> __curhs_file_cursor_open -> __wt_open_cursor -> __wt_cursor_cache_get -> __curfile_reopen -> __wt_session_lock_dhandle -> __wt_readlock`
- 1,086 samples (1.8%): `mongo::wiredTigerPrepareConflictRetry<mongo::WiredTigerIndexUnique::_keyExists -> __curfile_next -> __wt_btcur_next_prefix -> __wt_txn_read -> __wt_hs_find_upd -> __wt_curhs_open -> __curhs_file_cursor_open -> __wt_open_cursor -> __wt_cursor_cache_get -> __curfile_reopen -> __wt_session_lock_dhandle -> __wt_readlock`

Call tree under `WiredTigerIndexUnique::_keyExists` (59,948 samples = 100%), cursor and transaction frames only, cut at `__wt_hs_find_upd` (same view as the ticket's `hs.png`):

```
   40,594  67.7%  __curfile_search_near
   40,594  67.7%    __wt_btcur_search_near
   20,769  34.6%      __wt_btcur_next_prefix
   18,665  31.1%        __wt_txn_read
   16,988  28.3%          __wt_hs_find_upd
   19,825  33.1%      __wt_btcur_prev
   17,502  29.2%        __wt_txn_read
   16,206  27.0%          __wt_hs_find_upd
   19,354  32.3%  __curfile_next
   19,354  32.3%    __wt_btcur_next_prefix
   17,481  29.2%      __wt_txn_read
   15,935  26.6%        __wt_hs_find_upd
```

Inside `__wt_hs_find_upd` (49,129 samples): its direct callees. Every lookup opens a history-store cursor, positions it, and closes it again:

| callee | samples | % |
|---|---|---|
| `__wt_curhs_open` | 16,120 | 32.8 |
| `__curhs_search_near_helper` | 15,815 | 32.2 |
| `__curhs_set_key` | 9,095 | 18.5 |
| `__curhs_close` | 7,360 | 15.0 |
| `(self)` | 521 | 1.1 |
| `__wt_free_update_list` | 87 | 0.2 |
| `__wt_update_vector_free` | 71 | 0.1 |
| `__wt_update_vector_init` | 58 | 0.1 |

Off-CPU time of the stuck threads inside their stalled calls (ms, by blocking site, waits closed by a recorded wakeup only; preemptions while runnable are not waits): cache eviction wait (__wt_cache_eviction_worker) 67.3, mutex/spinlock 0.0. Waits without a recorded wakeup: 224 (upper bound 1936.6 ms, which includes the following run time, so it is not added in).
Switch-outs by thread:state (R = preempted while runnable, S = sleeping, D = uninterruptible sleep, t/T = stopped by the gdb snapshot): 215:R 2431, 215:R+ 10, 215:S 140, 215:T 2, 215:t 1, 216:D 1, 216:R 5285, 216:R+ 62, 216:S 125, 216:T 2, 216:t 1

Top leaf (self) functions, all connection threads:

| leaf | samples | % |
|---|---|---|
| `__wt_row_modify` | 8,913 | 9.7 |
| `__wt_session_gen_leave` | 4,026 | 4.4 |
| `__wt_hazard_set_func` | 3,825 | 4.1 |
| `__wt_readlock` | 3,338 | 3.6 |
| `__wt_row_search` | 3,076 | 3.3 |
| `__wt_btcur_next_prefix` | 2,955 | 3.2 |
| `__wt_struct_packv` | 2,928 | 3.2 |
| `__wt_config_gets_def` | 2,729 | 3.0 |
| `__wt_scr_alloc_func` | 2,727 | 3.0 |
| `__wt_btcur_prev` | 2,633 | 2.9 |
| `__ctype_b_loc` | 2,619 | 2.8 |
| `__wt_value_return_buf` | 2,545 | 2.8 |

Flame graphs: `oncpu_all.svg` (every mongod thread), `oncpu_stuck.svg` (stuck threads only).
