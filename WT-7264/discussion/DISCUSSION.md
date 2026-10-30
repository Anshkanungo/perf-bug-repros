# WT-7264 / SERVER-67350: developer discussion, root cause, fixes

Full Jira JSON (description, every comment, attachment list) for each ticket is in this directory
(`<KEY>.json`, fetched anonymously from `https://jira.mongodb.org/rest/api/2/issue/<KEY>`). Attachments
are in [`attachments/`](attachments/), fix/cause diffs and source snapshots in [`source/`](source/).

## The tickets at a glance

| ticket | title | type / resolution | dates | people | fix versions |
|---|---|---|---|---|---|
| [WT-7264](https://jira.mongodb.org/browse/WT-7264) | Creating a new configuration for search near that allows it to exit quickly when searching for prefixes | Bug / Fixed | 2021-03-04 → 2021-05-03 | reporter Sulabh Mahajan, fixed by Luke Pearson; repro by Bruce Lucas | WT10.0.1, 4.4.7, 5.0.0-rc0 |
| [SERVER-67350](https://jira.mongodb.org/browse/SERVER-67350) | stalling during concurrent insertMany operations when unique index exists | Bug / Duplicate | 2022-06-17 → 2022-10-03 | reporter Richard Martin (external), triage Chris Kelly, Sulabh Mahajan, Louis Williams | – (affects 5.0.9, 4.4.15) |
| [WT-5461](https://jira.mongodb.org/browse/WT-5461) | Search should not return onpage value if nothing is found by transaction read | Task / Fixed | 2020-01-20 → 2020-02-10 | Vamsi Boyapati, Chenhao Qu | WT10.0.0, 4.4.0-rc0 (**the cause**) |
| [SERVER-56509](https://jira.mongodb.org/browse/SERVER-56509) | Wrap unique index insertion _keyExists call in a WT cursor reconfigure | Improvement / Fixed, then reverted | 2021-04-30 → 2021-06-07 | Luke Pearson, Louis Williams | 4.4.7, 5.0.0-rc2 (reverted in 4.4.8, 5.0.2) |
| [SERVER-58936](https://jira.mongodb.org/browse/SERVER-58936) | Unique index constraints may not be enforced | Task / Fixed (by revert) | 2021-07-28 | Jonathan Streets, Henrik Edin | 4.4.8, 5.0.2 (affects **4.4.7, 5.0.0, 5.0.1**) |
| [SERVER-61185](https://jira.mongodb.org/browse/SERVER-61185) | Use prefix_search for unique index lookup | Improvement / Fixed | 2021-11-02 → 2022-01-18 | Louis Williams | 5.3.0, 5.0.14, 4.4.18 (**the shipped fix**) |
| [SERVER-85371](https://jira.mongodb.org/browse/SERVER-85371) | [4.4] Enable wiredTigerPrefixSearchForUniqueIndexes by default | Improvement / Won't Do | 2024-01-18 → 2024-01-25 | Louis Williams | – |
| [WT-7912](https://jira.mongodb.org/browse/WT-7912) | Fix prefix search near optimisation to handle scenarios where the key range is split across pages | Bug / Fixed | 2021-07-30 → 2021-11-01 | Luke Pearson, Monica Ng | WT10.0.1, 5.2.0, 5.0.5, 4.4.18 |
| [WT-8150](https://jira.mongodb.org/browse/WT-8150) | Poor search near performance if a lot of data are invisible | Bug / Gone away | 2021-09-22 → 2021-12-02 | Chenhao Qu | – |
| [SERVER-65527](https://jira.mongodb.org/browse/SERVER-65527) | Use range bounded cursors in place of prefix search_near on unique indexes | Improvement / Fixed | 2022-04-13 → 2022-10-26 | Deepti Hasija, Gregory Wlodarek | 6.2.0-rc0 |
| [SERVER-57500](https://jira.mongodb.org/browse/SERVER-57500) | Inconsistent update performance on unique indexes | Bug / Gone away | 2021-06-07 → 2024-04-17 | Louis Williams | – |
| [WT-6664](https://jira.mongodb.org/browse/WT-6664) | Cache eviction causes high latency during py-tpcc. | Bug / Duplicate of WT-7264 | 2020-09-10 → 2021-11-15 | Keith Smith, Sulabh Mahajan | – |

## WT-7264: how it was found and diagnosed

- **Origin (description, Sulabh Mahajan, 2021-03-04):** an unusually long py-tpcc *load* phase; a few
  inserts got stuck "for more than a few hours", intermittently. Inserting into a **unique index** could
  get stuck repeatedly searching the history store (`__wt_hs_find_upd`), with a very high
  `history store table reads missed` statistic, i.e. the searches return nothing. Call graph:
  [`attachments/hs.png`](attachments/hs.png) (identical bytes re-attached later as `image.png`).
- **Bruce Lucas's repro** ([`attachments/repro.sh`](attachments/repro.sh), copy in
  [`../workload/original/repro.sh`](../workload/original/repro.sh)): a standalone mongod "which eliminates
  considerations of timestamp management, lag, flow control"; 20 threads each insert 100k tiny documents
  `{_id, a, b}` in insertMany batches of 2000, with unique indexes on `a` and `b`. Expected (4.2): steady
  insert rate, all threads finish together. Observed (4.4): erratic insert rate, "a couple of the threads
  typically seem to get stuck apparently indefinitely" with a high rate of missed history-store reads.
- **Version behaviour (Bruce):** "The problem exists in 4.4.0", but it changed between 4.4.1 and 4.4.2: in
  4.4.2 "reads missed" starts immediately and a couple of writers are stuck seemingly indefinitely
  ([`442.png`](attachments/442.png): inserts drop from ~250k/s to ~0 while reads missed run at ~0.8–1.0 M/s);
  in 4.4.1 one writer is stuck but "reads missed" only starts later ([`441.png`](attachments/441.png)), "so
  it looks like we were stuck for some reason that didn't initially trigger reads missed".
- **Sulabh (2021-03-05):** for a unique index MongoDB inserts and immediately removes a prefix key to make
  concurrent inserts of the same key conflict, then searches for the real key; "that search after
  insertion/removal is somehow getting stuck in the history store".
- **Luke Pearson (2021-03-29 → 04-07):** cut-down repro (10 threads, 5000 docs each, batches of 200, one
  unique index) "repro's once every 3 runs" (later "~60% of the time"). FTDC
  ([`image-2021-03-31-17-11-35-375.png`](attachments/image-2021-03-31-17-11-35-375.png)) shows pages written
  from cache rising together with reads missed. Theory: all threads do `search_near` in `_keyExists`; the
  page is force-evicted by an application thread; the thread that then searches "is calling next and prev a
  LOT because nothing is visible to it due to transaction id visibility checks". In memory those steps are
  cheap insert-list walks; once the page is evicted every step is `__wt_txn_read` → read the cell → nothing
  visible → `__wt_hs_find_upd` → nothing. Returning `false` from `__evict_force_check` stopped the repro.
  "Our search near however has to traverse 10000 invisible prefix updates", and the history-store lookup
  happens only "if the thread that is searching for the prefix started prior to the thread that inserted
  and removed the prefix". Two workarounds tried: rewriting the time window of insert+remove (resolved 90%,
  but not a real fix) and prefixing the prefixes with junk bytes (did not work as well as expected).
- **Root cause (Luke, 2021-04-08):** "it was a change introduced by WT-5461. Which instead of returning a
  value to the caller simply nexted or preved as nothing was visible. This is a deviation from 4.2 which
  would return the value back to the caller even if nothing was visible on the update chain as the
  assumption is that the on disk value is visible." Removing the `WT_UPDATE_INVALID` → `continue` lines in
  `bt_curnext.c` / `bt_curprev.c` made Bruce's full repro run "at the same speed or even quicker than 4.2".
  "There aren't any history store specific issues here. The search into the history store is still valid."
- **Full explanation (Luke, 2021-04-09)**, condensed:
  1. A unique-index key is `(value, RecordId)`. Insertion is 4 steps in one transaction: insert the prefix
     `value`, remove it, `search_near(value)` in `_keyExists` to look for an existing `(value, *)`, insert
     `(value, RecordId)`. The insert+remove makes concurrent inserters of the same value conflict; the
     removed prefix must stay in the table until older transactions finish, so it cannot simply be
     `reserve()`d.
  2. `search_near` must return the exact key or a logically adjacent *visible* key. If the landing key is
     invisible, WiredTiger walks `next` to the end of the table, then `prev` to the other end. Example: keys
     a–z, only `a` visible → `search_near("l")` walks the whole table and returns `a`.
  3. **4.2 is fast** because the on-disk value must be globally visible, so pages with updates an older
     reader still needs cannot be evicted; all the walking stays in memory.
     **4.4 is slow** because with durable history "the page can be evicted as long as there exists some
     committed updates on it", and every on-disk value found requires a history-store lookup, on pages
     that are now read back from disk.
  4. Fix: a `search_near` config `prefix_search=true` that stops as soon as the walk leaves the keys that
     start with the searched prefix.
- **Louis Williams** noted the same option could help SERVER-41977 (search_near blocking on an unrelated
  key's prepared update). **Alex Podelko** reported the TPC-C benchmark itself (BF-20413) also shows
  "reads missed" jumps. Luke asked for call stacks of those reads ("reads missed being a symptom, not the
  cause").
- **Fix result (Luke, 2021-04-15):** full repro with the prefix-search patch **8.707 s** vs **7.919 s on 4.2**.
- **Caveat (Luke, 2021-04-27/30):** the optimisation is only correct if the initial `__cursor_row_search`
  lands inside the prefix's key range; "if used improperly it may result in not seeing key/value pairs
  that should've been returned"; unique-index inserts guarantee a key with the prefix exists (their own
  removed prefix). Alexander Gorrod: the search_near loop re-checks the found key against the
  greater-than/less-than condition.
- **Commit:** WiredTiger [`652def8a`](https://github.com/wiredtiger/wiredtiger/commit/652def8ae433a2001145d34baec9ef9f5610a97e)
  (#6473, 2021-05-03), imported into mongo master as
  [`c712d5dd`](https://github.com/mongodb/mongo/commit/c712d5ddbd852b03331284ab9e08bae3addb4aa0) (5.0.0) and
  v4.4 as [`94b923a9`](https://github.com/mongodb/mongo/commit/94b923a9900f81e750e3d69dc9e27ae573fd16e6)
  (4.4.7). Diff: [`source/WT-7264-wt-652def8a.diff`](source/WT-7264-wt-652def8a.diff). The WiredTiger change
  alone does nothing for MongoDB until the server sets `prefix_search=true` (SERVER-56509 / SERVER-61185).

The core of the WiredTiger change (`src/btree/bt_curnext.c`, mirrored in `bt_curprev.c`; `bt_cursor.c`
passes the searched key as `prefix`):

```diff
         rip = &page->pg_row[cbt->slot];
         WT_RET(__cursor_row_slot_key_return(cbt, rip, &kpack, &kpack_used));
+        /*
+         * If the cursor has prefix search configured we can early exit here if the key that we are
+         * visiting is after our prefix.
+         */
+        if (F_ISSET(&cbt->iface, WT_CURSTD_PREFIX_SEARCH) && prefix != NULL &&
+          __wt_prefix_match(prefix, &cbt->iface.key) < 0) {
+            WT_ASSERT(session, CUR2BT(cbt)->collator == NULL);
+            WT_STAT_CONN_DATA_INCR(session, cursor_search_near_prefix_fast_paths);
+            return (WT_NOTFOUND);
+        }
         WT_RET(__wt_txn_read(
           session, cbt, &cbt->iface.key, WT_RECNO_OOB, WT_ROW_UPDATE(page, rip), NULL));
```

`cursor_search_near_prefix_fast_paths` is the statistic "Total number of times a search near has exited
due to prefix config" that our runs report for the fix arm.

## WT-5461: the change that introduced the behaviour (4.4.0-rc0)

Durable history (4.4) writes the *newest committed* value to the data page and older values to the
history store. Before, the on-page value was the stable one, and the search code assumed that if the
transaction read found nothing on the update chain, the on-page value was visible. WT-5461 (Vamsi Boyapati,
fixed by Chenhao Qu, WiredTiger [`59d499af`](https://github.com/wiredtiger/wiredtiger/commit/59d499af86f2def42a35e7d06f4bc037d8c6ec87),
imported for 4.4.0-rc0 by [`00502b11`](https://github.com/mongodb/mongo/commit/00502b11804516673266087d8d10292edb94a70a))
removed that assumption ("How do we know that the on page value is visible?" "We don't." – Alexander
Gorrod / Chenhao Qu). Cursor next/prev now *skip* a row whose transaction read finds nothing visible
([`source/WT-5461-wt-59d499af.diff`](source/WT-5461-wt-59d499af.diff)):

```diff
@@ __cursor_row_next(WT_CURSOR_BTREE *cbt, bool newpage, bool restart)
         WT_RET(__cursor_row_slot_key_return(cbt, rip, &kpack, &kpack_used));
-        WT_RET(__wt_txn_read(session, cbt, WT_ROW_UPDATE(page, rip), &upd));
+        WT_RET(__wt_txn_read(session, cbt, WT_ROW_UPDATE(page, rip), NULL, &upd));
+        if (upd == NULL)
+            continue;
```

That is correct (an invisible value must not be returned), and it is exactly what turns one
`search_near` into an unbounded walk when many keys are invisible. In later code the check reads
`if (cbt->upd_value->type == WT_UPDATE_INVALID) { ++*skippedp; continue; }`, which is what Luke's
experiment removed.

## SERVER-67350: the same bug, reported by a user a year later

- **Report (Richard Martin, 2022-06-17):** several concurrent `insertMany` calls on a collection with a
  unique index stall: the socket hangs, mongod uses "one or two cores at 100% CPU", nothing in the logs,
  mongotop, currentOp or mongostat; the inserts eventually finish without error after 2–10 minutes (up to
  40 minutes on slower MacBooks). "On version v4.2 the test program will complete in 1.7 seconds where on
  the last v5 run I did it took 9m19sec." A single connection inserting 1M documents is fine; "the
  problems start when concurrency is added". Another connection can insert 1M rows meanwhile, so the
  collection is not locked.
- **Logs and FTDC** (Chris Kelly asked; uploaded 2022-06-24 as `requested_files.tar.gz` with 4.2.20,
  4.4.14 and 5.0.9, two runs each). What the logs show (parsed in
  [`server67350_logs.md`](server67350_logs.md)): a Java driver 4.5.0 program, collection
  `test_data_mongo_issue.mainthings` with unique index `someId_1`, **5 connections** each sending two insert
  commands of 100,000 documents (ordered), all started within ~2 ms. In every 4.4.14 and 5.0.9 run, the
  slow commands are each connection's **first** command: 34 s and 156 s (5.0.9 run 1), 3.9 s, 6.2 s,
  13.5 s and **472 s** (5.0.9 run 2), 134 s, 290 s, **548 s** (4.4.14 run 1), 68 s, 161 s, 182 s (4.4.14
  run 2). Every second command takes ~0.4–0.6 s. 4.2.20: every command ~0.5 s.
- **The reporter's FTDC, decoded here** ([`ftdc_decode.py`](ftdc_decode.py), plot
  [`attachments/server67350_ftdc.png`](attachments/server67350_ftdc.png)): 4.4.14 **1.74 billion**
  "history store table reads missed" over its two runs (peak 3.6 M/s), 5.0.9 **0.99 billion** (peak
  1.9 M/s), with 4.9 / 2.4 billion cursor entries skipped by next/prev; inserts/s drop to ~0 within a second
  of each run's start while "active writers" step down 3 → 2 → 1 as the stuck connections finish one at a
  time. 4.2.20 has no history store and finishes each run in about a second. The same signature as
  Bruce's `442.png` and as our runs.
- **Chris Kelly (2022-06-27 → 07-25):** reproduced the slow queries from the FTDC; could *not* reproduce with
  a jstests FSM workload (200 connections, `insertMany` of 1M docs each) but could with the user's driver
  program: stalls on 4.4.15 and 5.0.9, none on 4.2.21, 5.3.1, 6.0.0. **Bisected** to mongo commit
  [`30e753ec`](https://github.com/mongodb/mongo/commit/30e753ec9ebd7804bc1bab62fb892aec33563e69), a
  WiredTiger import between 4.4.1 and 4.4.2 ("4.4.1 does not have any issues"). Its WT tickets are listed in
  [`source/SERVER-67350-bisect-commit-30e753ec.txt`](source/SERVER-67350-bisect-commit-30e753ec.txt); they
  include **WT-6490 "Acquire snapshot for eviction threads"** and **WT-6624 "Use transaction snapshot for
  applications performing eviction"** (WT-6664, later closed as a duplicate of WT-7264, "depends on"
  WT-6624). *Inference, not stated in the tickets:* letting eviction use a snapshot makes pages with
  not-yet-globally-visible updates evictable, which is the precondition Luke identified for the expensive
  history-store path, and would explain Bruce's "reads missed starts immediately in 4.4.2".
- **Sulabh Mahajan (2022-08-02):** the sudden jump in "history store table reads missed", starting in 4.4
  and gone in 5.3, points to WT-7264, resolved in the server by SERVER-61185.
- **Louis Williams (2022-10-03):** closed as a duplicate: "we're not being very efficient when checking for
  the existence of duplicate keys when inserting documents, something that changed in 4.4." Fixed by
  SERVER-61185 in 5.3.0 and 5.0.14; the 4.4 backport is **off by default**.

## The server-side fix, its revert, and the re-implementation

1. **SERVER-56509** (Luke Pearson's patch, committed by Louis Williams; master
   [`c5ac2eb1`](https://github.com/mongodb/mongo/commit/c5ac2eb1ea145693e1c6b974e88a2cfc18780134), v5.0
   [`297e2977`](https://github.com/mongodb/mongo/commit/297e2977ef3e394e02d61aedc954c9aaadc37e73), v4.4
   [`ae2da276`](https://github.com/mongodb/mongo/commit/ae2da27652e552f101559466d165b82a3c122d71); diff
   [`source/SERVER-56509-master-c5ac2eb1.diff`](source/SERVER-56509-master-c5ac2eb1.diff)) wrapped the
   `_keyExists` call in `c->reconfigure(c, "prefix_key=true")`. Commit message: "This improves, but does not
   entirely fix a performance regression with inserts and updates on unique indexes." Louis found a second
   regression (multi-update of a unique field to a value that sorts *before* the old one: 15 s, 8 s with the
   patch, vs 250 ms for a non-unique index), split off as SERVER-57500 (closed "Gone away" in 2024).
2. **SERVER-58936, "Unique index constraints may not be enforced"** (2021-07-28): SERVER-56509 could let
   documents that violate a secondary unique index be inserted and replicated (and then deletes through
   that index touch only half of the duplicates). Affected **4.4.7, 5.0.0, 5.0.1**; fixed in 4.4.8 / 5.0.2 by
   reverting SERVER-56509 on all branches (Henrik Edin: master
   [`ecba2344`](https://github.com/mongodb/mongo/commit/ecba23449a26f3d266ffacda7eb98d8386267606), v5.0
   [`6d9ec525`](https://github.com/mongodb/mongo/commit/6d9ec525e78465dcecadcff99cce953d380fedc8), v4.4
   [`83b8bb8b`](https://github.com/mongodb/mongo/commit/83b8bb8b6b325d8d8d3dfd2ad9f744bdad7d6ca0)). The
   ticket ships a `findUniquenessViolations.js` script. **These versions must not be used for experiments.**
3. **WT-7912** (filed by Luke Pearson two days after the revert): the prefix early exit treated
   "end of page" (`__cursor_row_next` returns `WT_NOTFOUND` at the end of a page) as "end of prefix range",
   so a prefix range split across pages could return `WT_NOTFOUND` although a matching key exists, which is
   precisely a missed duplicate in `_keyExists`. Fixed with a separate return path (WiredTiger
   [`bc1c3dc0`](https://github.com/wiredtiger/wiredtiger/commit/bc1c3dc0d46ea79127697aae7b50e8b6c5afb14d);
   in 5.0.5 and 4.4.18; diff [`source/WT-7912-wt-bc1c3dc0.diff`](source/WT-7912-wt-bc1c3dc0.diff)).
   *The tickets do not spell out "WT-7912 is the cause of SERVER-58936"; the timing and the described flaw
   match.*
4. **SERVER-61185** "re-implement SERVER-56509" (Louis Williams). Master
   [`f18bb1e1`](https://github.com/mongodb/mongo/commit/f18bb1e1c2d7bedeb3c08964e6a65bcc794e2a2a) used
   `prefix_key=true`; Etienne Petrel spotted that the option is called `prefix_search`, fixed in
   [`5923aa87`](https://github.com/mongodb/mongo/commit/5923aa87d869a12d40ce605f3aee69d47314aabf) (so
   SERVER-56509's `prefix_key` probably had no effect at all; *inference*). Backports: v5.0
   [`61c97688`](https://github.com/mongodb/mongo/commit/61c9768820795fd164a8749c090e702eb632329b) (5.0.14,
   **on by default**), v4.4 [`17f21f74`](https://github.com/mongodb/mongo/commit/17f21f74c517b8434ae72cf159918ef413eadf72)
   (4.4.18, "when enabled by a server parameter", **off by default**). Louis (2022-10-13): 4.4 off by default
   "to prevent making significant behavioral changes on a more stable branch"; 5.0 on by default but can be
   disabled; newer versions always on. Diffs in `source/SERVER-61185-*.diff`. The v4.4 change:

```diff
         // Second phase looks up for existence of key to avoid insertion of duplicate key
-        if (_keyExists(opCtx, c, keyString.getBuffer(), sizeWithoutRecordId)) {
+        // The usage of 'prefix_search=true' enables an optimization that allows this search to
+        // return more quickly. See SERVER-56509.
+        // Does not work on prefixed indexes.
+        auto prefixSearch =
+            gWiredTigerPrefixSearchForUniqueIndexes.load() && _prefix == KVPrefix::kNotPrefixed;
+        if (prefixSearch) {
+            c->reconfigure(c, "prefix_search=true");
+        }
+        ON_BLOCK_EXIT([&] {
+            if (prefixSearch) {
+                c->reconfigure(c, "prefix_search=false");
+            }
+        });
+        auto keyExists = _keyExists(opCtx, c, keyString.getBuffer(), sizeWithoutRecordId);
+        if (keyExists) {
```

   ```yaml
   # wiredtiger_parameters.idl (r4.4.30: default false; r5.0.33: default true)
   wiredTigerPrefixSearchForUniqueIndexes:
     description: Uses the prefix_search feature when checking for duplicate keys on unique indexes
     set_at: [ startup, runtime ]
     cpp_vartype: 'AtomicWord<bool>'
   ```

   Source snapshots at the tags used here: [`source/r5.0.33-wiredtiger_index.cpp`](source/r5.0.33-wiredtiger_index.cpp),
   [`source/r5.0.33-wiredtiger_parameters.idl`](source/r5.0.33-wiredtiger_parameters.idl),
   [`source/r4.4.30-wiredtiger_index.cpp`](source/r4.4.30-wiredtiger_index.cpp),
   [`source/r4.4.30-wiredtiger_parameters.idl`](source/r4.4.30-wiredtiger_parameters.idl).
   Alex Podelko (2022-01-12): the fix "was supposed to fix multiple regressions: BF-22130 BF-23346
   BF-22529. Doesn't look like it did."
5. **SERVER-85371** (2024-01, Won't Do): enable the parameter by default in 4.4 ("the consequences are
   pretty severe perf degradation"); not done, so **4.4.18–4.4.30 still ship with the slow path by
   default**.
6. **WT-8150** (Chenhao Qu, 2021-09): generalises the problem ("for each invisible key it inspects, it needs
   to do a history store search ... most of the time, it will find nothing there"); closed "Gone away"
   once prefix search was in. **SERVER-65527** (6.2.0): replaces prefix `search_near` with range-bounded
   cursors (WT-9324), the current mechanism.

## Version map used by this reproduction

| version | WT-5461 behaviour | eviction change of 30e753ec | duplicate-key check | used here as |
|---|---|---|---|---|
| 4.2.24 | no (pre-durable history) | no | `search_near` (cheap: pages stay in memory) | baseline |
| 4.4.1 | yes | no | `search_near`, no prefix exit | before the bisected commit |
| 4.4.2 | yes | yes | same | first release after the bisected commit |
| 4.4.7, 5.0.0, 5.0.1 | – | – | SERVER-56509 (buggy) | **not used** (SERVER-58936) |
| 4.4.30 | yes | yes | prefix exit only if `wiredTigerPrefixSearchForUniqueIndexes=true` (default **false**) | single-binary A/B (secondary) |
| 5.0.33 | yes | yes | prefix exit unless the parameter is `false` (default **true**) | **single-binary primary A/B** |
