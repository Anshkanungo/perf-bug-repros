# Profile summary (WT-7264)

```
date_utc: 2026-10-28T03:19:59Z
kernel: 7.0.14-linuxkit aarch64
perf: perf version 6.1.190
gdb: GNU gdb (Debian 13.1-3) 13.1
perf_event_paranoid: 2 (bypassed: privileged container)
mongod pid (in this pid namespace): 7
mongod exe: /usr/bin/mongod
mongod build-id: 8c5312cc4de9153d83270c84d5ec310989d67c93
mongod sections: .eh_frame .gnu_debuglink .symtab 
threads: 34
event: cpu-clock  freq: 999  callgraph: fp  secs: 20  snapshot: 1 (at:7)
```

- on-CPU samples: 38,906; connection threads: 34,979
- busiest threads: conn* 34,979, mongod 3,813, ftdc 44, JournalFlusher 41, Service.Fixed-0 10, listener 7, Backgro.kSource 4, Timesta.Monitor 4
- stuck-thread detection: client log: no insertMany call >= 3.0 s, so no stuck thread

## No stuck thread in this recording

Function shares over all connection-thread samples:

| function (outermost first) | samples | % |
|---|---|---|
| `mongo::CollectionImpl::insertDocuments` | 32,590 | 93.2 |
| `mongo::WiredTigerIndex::insert` | 26,606 | 76.1 |
| `mongo::WiredTigerIndexUnique::_insert` | 22,584 | 64.6 |
| `mongo::WiredTigerIndexUnique::_keyExists` | 1,352 | 3.9 |
| `mongo::wiredTigerPrepareConflictRetry<...>` | 1,293 | 3.7 |
| `__curfile_search_near` | 1,257 | 3.6 |
| `__wt_btcur_search_near` | 1,204 | 3.4 |
| `__curfile_next` | 0 | 0.0 |
| `__curfile_prev` | 2 | 0.0 |
| `__wt_btcur_next` | 0 | 0.0 |
| `__wt_btcur_prev` | 1 | 0.0 |
| `__cursor_row_next` | 0 | 0.0 |
| `__cursor_row_prev` | 0 | 0.0 |
| `__wt_txn_read` | 0 | 0.0 |
| `__wt_txn_read_upd_list` | 0 | 0.0 |
| `__wt_hs_find_upd` | 0 | 0.0 |
| `any history-store cursor function (__curhs_* / __wt_hs_*)` | 1 | 0.0 |
| `__cursor_row_slot_key_return` | 0 | 0.0 |
| `__wt_lex_compare*` | 0 | 0.0 |
| `__wt_txn_upd_value_visible_all` | 0 | 0.0 |
| `__wt_row_search` | 5,175 | 14.8 |
| `__wt_page_in_func` | 1,235 | 3.5 |
| `__evict_force_check` | 0 | 0.0 |
| `__wt_cache_eviction_worker` | 4 | 0.0 |
| `KeyString::sizeWithoutRecordId*AtEnd` | 3 | 0.0 |

Top leaf (self) functions, all connection threads:

| leaf | samples | % |
|---|---|---|
| `__wt_row_modify` | 12,863 | 36.8 |
| `__wt_row_search` | 2,800 | 8.0 |
| `__wt_struct_size` | 1,465 | 4.2 |
| `__wt_search_insert` | 1,093 | 3.1 |
| `__wt_hazard_set_func` | 817 | 2.3 |
| `__config_next` | 814 | 2.3 |
| `__wt_struct_pack` | 777 | 2.2 |
| `__wt_hazard_clear` | 547 | 1.6 |
| `mongo::WiredTigerSession::releaseCursor` | 518 | 1.5 |
| `__wt_update_obsolete_check` | 505 | 1.4 |
| `tcmalloc::CentralFreeList::FetchFromOneSpans` | 478 | 1.4 |
| `__wt_btcur_insert` | 418 | 1.2 |

Flame graphs: `oncpu_all.svg` (every mongod thread), `oncpu_stuck.svg` (stuck threads only).
