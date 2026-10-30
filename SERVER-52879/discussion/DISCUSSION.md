# SERVER-52879: developer discussion, root cause, fix

**Ticket:** https://jira.mongodb.org/browse/SERVER-52879. Full JSON (description, all 7 comments, attachment
list) is in [`SERVER-52879.json`](SERVER-52879.json).

| field | value |
|---|---|
| Title | Periodic operation latency spikes every 5 minutes due to closing idle cached WT sessions |
| Reporter | Bruce Lucas (MongoDB) |
| Created | 2020-11-16 |
| Resolved | 2021-01-07 (Fixed, Closed) |
| Fix author | Gregory Wlodarek |
| Affects versions | 4.4.1, 4.2.10, 4.0.21, 3.6.21 |
| Fix versions | 4.9.0, 4.4.4, 4.2.12, 4.0.23 (no 3.6 backport) |
| Component | storage / WiredTiger integration (`src/mongo/db/storage/wiredtiger/wiredtiger_session_cache.cpp`) |

## What Bruce reported (2020-11-16)

- **Test:** 1000 collections × 10 secondary indexes (≈12k WiredTiger tables), then inserts at ~1000/s from
  100 threads (≈10/s each) into random collections. `repro.js` is attached
  (copy: [`../workload/original/repro.js`](../workload/original/repro.js)).
- **Symptom:** latency is normally <1 ms, but FTDC shows periodic spikes of tens of ms
  ([`attachments/spikes.png`](attachments/spikes.png); per-second *average* write latency peaks at 29 ms).
- **Mechanism (his diagnosis):**
  1. `WiredTigerSessionCache::closeExpiredIdleSessions` holds the session-cache mutex while it closes idle
     sessions, which delays all operations.
  2. Up to 100 operations (one per client thread) queue on the mutex, then run concurrently once it's
     released. That needs up to 100 sessions at once, and all of them are cached afterwards.
  3. Between sweeps concurrency is low, so only a few cached sessions are reused.
  4. At the next expiry, most cached sessions are idle and get closed under the mutex, which restarts the cycle.
- **Evidence:** FTDC open-session count and cached-cursor count oscillate in step with the spikes. perf shows
  `closeExpiredIdleSessions` spending ~65% of its time in `close_cached_cursors` and ~25% in
  `__session_discard_dhandle`, both proportional to the number of tables.
- The test set `wiredTigerSessionCloseIdleTimeSecs=30`. The default is 300, so in production the spikes come
  roughly every 5 minutes.

> **Teacher's note: reading `spikes.png`.** These are FTDC charts: mongod's own once-per-second
> `serverStatus` capture, plotted with MongoDB's internal viewer. "ss average latency writes" is
> Δ`opLatencies.writes.latency` / Δ`ops` per second, so a 29 ms *average* over ~1000 inserts means many
> inserts waited far longer. "ss wt cursor cached cursor count" is WiredTiger's count of cursors parked
> in per-session caches. Each sawtooth drop is a sweep closing sessions that held thousands of them.

### Spike period: the charts show 40 s, not 30 s

The description says the spike interval "is `wiredTigerSessionCloseIdleTimeSecs`" (30 s). Measured from the
attached charts with [`measure_ticket_charts.py`](measure_ticket_charts.py)
(output: [`measure_ticket_charts.out.txt`](measure_ticket_charts.out.txt)):

- `spikes.png` (Bruce): 17 spikes, intervals 40.0–41.1 s, median **40.0 s**
- `before.png` (Gregory, pre-fix): 9 spikes, intervals 39.6–40.7 s, median **40.0 s**

The source explains this. The sweeper thread wakes every **10 s** (`WiredTigerSessionSweeper::run`,
`wait_for(... kDebugBuild ? 1 : 10 seconds)`). The burst sessions become idle a few ms *after* a sweep, so
at the sweep 30 s later they are 29.99x s idle, not yet ">30 s", and they are closed one tick later. The
period is therefore (⌊T/10⌋+1)·10 s, which is 40 s for T=30 and ~310 s for the default T=300.

## Comments (chronological)

| date | who | content |
|---|---|---|
| 2020-11-16 | Bruce Lucas | Suggests identifying idle sessions under the mutex but **closing them outside it**. |
| 2020-11-16 | Bruce Lucas | Asks for a **metric counting sessions closed from the session cache**; it would have made the original customer issue much easier to diagnose. |
| 2021-01-07 | Githook | master: `d517928d5b34` "Close expired idle sessions outside of the cache mutex" |
| 2021-01-08 | Bruce Lucas | Retitled the ticket to include "every 5 minutes" (the default timeout) so the visible symptom is discoverable. |
| 2021-01-08 | Githook | v4.4 cherry-pick `d6a3d7b707df` |
| 2021-01-08 | Githook | v4.0 cherry-pick `b01d1f1c14f1` |
| 2021-01-08 | Githook | v4.2 cherry-pick `455bdbb8bcc2` |

Gregory attached [`before.png`](attachments/before.png) and [`after.png`](attachments/after.png)
(2021-01-07) to validate the fix on the same workload. Max per-second average write latency went from
8.06 ms to 0.27 ms, max open sessions from 48 to 18, and the cached-cursor sawtooth flattened.
The metric Bruce asked for was **not** part of this fix: the commit only changes `closeExpiredIdleSessions`.

## Root cause in the code (4.4.3)

`src/mongo/db/storage/wiredtiger/wiredtiger_session_cache.cpp` at `r4.4.3`
(copy: [`source/r4.4.3-wiredtiger_session_cache.cpp`](source/r4.4.3-wiredtiger_session_cache.cpp)):

```cpp
void WiredTigerSessionCache::closeExpiredIdleSessions(int64_t idleTimeMillis) {
    ...
    auto cutoffTime = _clockSource->now() - Milliseconds(idleTimeMillis);
    {
        stdx::lock_guard<Latch> lock(_cacheLock);          // <-- held for the whole loop
        for (auto it = _sessions.begin(); it != _sessions.end();) {
            auto session = *it;
            if (session->getIdleExpireTime() < cutoffTime) {
                it = _sessions.erase(it);
                delete (session);                            // <-- WT_SESSION::close() under the latch
            } else { ++it; }
        }
    }
}
```

- `getSession()` (pop the most recently used session, LIFO) and `releaseSession()` (push it back with
  `setIdleExpireTime(now)`) both take `_cacheLock`. Every operation does both, so while the loop above runs,
  every operation that needs a session waits.
- `delete session` → `WiredTigerSession::~WiredTigerSession` → `WT_SESSION::close` → WiredTiger
  `__session_close`, which closes every cursor cached in the session (`__session_close_cached_cursors`) and
  drops its cached data-handle references (`__wt_session_close_cache` → `__session_discard_dhandle`).
- Why sessions hold so many cursors: with the default `wiredTigerCursorCacheSize=-100`, `releaseSession()`
  closes the session's cursors *into WiredTiger's per-session cursor cache*. A session that served inserts
  into random collections caches a cursor for each table it touched, and each insert touches 12 tables
  (record store + `_id` + 10 indexes). With 12k tables a session can collect thousands of them, so the
  closing cost scales with the table count.
- The sweeper: `WiredTigerKVEngine::WiredTigerSessionSweeper::run` (copy:
  [`source/r4.4.3-wiredtiger_kv_engine.cpp`](source/r4.4.3-wiredtiger_kv_engine.cpp), line ~200) loops
  `wait_for(10 s)` → `closeExpiredIdleSessions(wiredTigerSessionCloseIdleTimeSecs * 1000)`.

> **Teacher's note: why the cycle sustains itself.** The cache is a LIFO stack. When ~100 stalled operations
> are released at once, the cache can't cover them, so ~100 brand-new sessions are opened and then pushed
> back. Normal traffic (low concurrency) only keeps reusing the top few, so the rest go idle *together*
> and expire *together* at a later sweep. That mass close stalls everyone again and creates the next
> burst. A one-time disturbance turns into a stable oscillation.

## The fix

Identical 9-line change on all branches
([`source/fix-d6a3d7b707df26dfdc64b1ffd7264fae2886ec50.diff`](source/fix-d6a3d7b707df26dfdc64b1ffd7264fae2886ec50.diff)):
expired sessions are moved into a local `sessionsToClose` list under the latch, and
`delete session` runs after the latch is released.

```diff
     auto cutoffTime = _clockSource->now() - Milliseconds(idleTimeMillis);
+    SessionCache sessionsToClose;
     {
         stdx::lock_guard<Latch> lock(_cacheLock);
 ...
                 it = _sessions.erase(it);
-                delete (session);
+                sessionsToClose.push_back(session);
 ...
     }
+    // Closing expired idle sessions is expensive, so do it outside of the cache mutex. This helps
+    // to avoid periodic operation latency spikes as seen in SERVER-52879.
+    for (auto session : sessionsToClose) {
+        delete session;
+    }
```

| branch | commit | committed | link |
|---|---|---|---|
| master (4.9.0) | `d517928d5b34e5988eea9fc15e1c2db4c3ff8d77` | 2021-01-07 | https://github.com/mongodb/mongo/commit/d517928d5b34e5988eea9fc15e1c2db4c3ff8d77 |
| v4.4 (4.4.4) | `d6a3d7b707df26dfdc64b1ffd7264fae2886ec50` | 2021-01-08 | https://github.com/mongodb/mongo/commit/d6a3d7b707df26dfdc64b1ffd7264fae2886ec50 |
| v4.2 (4.2.12) | `455bdbb8bcc2166a14fe009d28e71ee6bf4de59e` | 2021-01-08 | https://github.com/mongodb/mongo/commit/455bdbb8bcc2166a14fe009d28e71ee6bf4de59e |
| v4.0 (4.0.23) | `b01d1f1c14f1270e36adf06c78b6de9f63308936` | 2021-01-08 | https://github.com/mongodb/mongo/commit/b01d1f1c14f1270e36adf06c78b6de9f63308936 |

All four were authored 2021-01-06 by Gregory Wlodarek and touch one file (+9/−1). `diff` of
`wiredtiger_session_cache.cpp` between the `r4.4.3` and `r4.4.4` tags shows exactly this change and nothing else.

**Caveat for A/B tests with release builds:** `r4.4.3...r4.4.4` has 64 commits (300 files), including 7
WiredTiger imports that touch WT `cursor/`, `conn/`, and `schema/`. Comparing the two releases therefore
isn't a single-commit experiment. See `../PLAN.md` (change 2) for the control we added.

## Affected / fixed versions (from the ticket)

| line | affected (listed) | first fixed |
|---|---|---|
| 3.6 | 3.6.21 | not fixed |
| 4.0 | 4.0.21 | 4.0.23 |
| 4.2 | 4.2.10 | 4.2.12 |
| 4.4 | 4.4.1 (and, by code, 4.4.0–4.4.3) | 4.4.4 |
| master | – | 4.9.0 (→ 5.0) |

This repro uses **4.4.3** (the last 4.4 release before the fix) vs **4.4.4** (the first with it).
