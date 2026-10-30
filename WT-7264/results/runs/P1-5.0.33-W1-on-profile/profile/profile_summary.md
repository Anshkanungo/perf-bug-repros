# Profile summary (WT-7264)

```
date_utc: 2026-10-28T03:27:59Z
kernel: 7.0.14-linuxkit aarch64
perf: perf version 6.1.190
gdb: GNU gdb (Debian 13.1-3) 13.1
perf_event_paranoid: 2 (bypassed: privileged container)
mongod pid (in this pid namespace): 7
mongod exe: /usr/bin/mongod
mongod build-id: 8c5312cc4de9153d83270c84d5ec310989d67c93
mongod sections: .eh_frame .gnu_debuglink .symtab 
threads: 34
event: cpu-clock  freq: 999  callgraph: fp  secs: 25  snapshot: 1 (at:9)
```

- on-CPU samples: 39,712; connection threads: 35,600
- busiest threads: conn* 35,600, mongod 3,974, ftdc 54, JournalFlusher 51, Service.Fixed-0 11, listener 10, Backgro.kSource 5, Timesta.Monitor 4
- stuck-thread detection: client log: no insertMany call >= 3.0 s, so no stuck thread

## No stuck thread in this recording

Function shares over all connection-thread samples:

| function (outermost first) | samples | % |
|---|---|---|
| `mongo::CollectionImpl::insertDocuments` | 33,196 | 93.2 |
| `mongo::WiredTigerIndex::insert` | 27,363 | 76.9 |
| `mongo::WiredTigerIndexUnique::_insert` | 23,151 | 65.0 |
| `mongo::WiredTigerIndexUnique::_keyExists` | 1,433 | 4.0 |
| `mongo::wiredTigerPrepareConflictRetry<...>` | 1,374 | 3.9 |
| `__curfile_search_near` | 1,328 | 3.7 |
| `__wt_btcur_search_near` | 1,295 | 3.6 |
| `__curfile_next` | 0 | 0.0 |
| `__curfile_prev` | 3 | 0.0 |
| `__wt_btcur_next[_prefix]` | 59 | 0.2 |
| `__wt_btcur_prev[_prefix]` | 3 | 0.0 |
| `__cursor_row_next` | 0 | 0.0 |
| `__cursor_row_prev` | 0 | 0.0 |
| `__wt_txn_read` | 0 | 0.0 |
| `__wt_txn_read_upd_list` | 0 | 0.0 |
| `__wt_hs_find_upd` | 0 | 0.0 |
| `any history-store cursor function (__curhs_* / __wt_hs_*)` | 0 | 0.0 |
| `__cursor_row_slot_key_return` | 0 | 0.0 |
| `__wt_lex_compare*` | 0 | 0.0 |
| `__wt_txn_upd_value_visible_all` | 1 | 0.0 |
| `__wt_row_search` | 5,166 | 14.5 |
| `__wt_page_in_func` | 1,180 | 3.3 |
| `__evict_force_check` | 0 | 0.0 |
| `__wt_cache_eviction_worker` | 9 | 0.0 |
| `KeyString::sizeWithoutRecordId*AtEnd` | 5 | 0.0 |

Top leaf (self) functions, all connection threads:

| leaf | samples | % |
|---|---|---|
| `__wt_row_modify` | 13,133 | 36.9 |
| `__wt_row_search` | 2,825 | 7.9 |
| `__wt_struct_size` | 1,387 | 3.9 |
| `__wt_search_insert` | 1,127 | 3.2 |
| `__config_next` | 935 | 2.6 |
| `__wt_struct_pack` | 928 | 2.6 |
| `__wt_hazard_set_func` | 780 | 2.2 |
| `__wt_hazard_clear` | 558 | 1.6 |
| `__ctype_b_loc` | 518 | 1.5 |
| `mongo::WiredTigerSession::releaseCursor` | 481 | 1.4 |
| `__wt_update_obsolete_check` | 443 | 1.2 |
| `tcmalloc::CentralFreeList::FetchFromOneSpans` | 432 | 1.2 |

Flame graphs: `oncpu_all.svg` (every mongod thread), `oncpu_stuck.svg` (stuck threads only).
