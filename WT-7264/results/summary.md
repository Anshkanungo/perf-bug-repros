# WT-7264 / SERVER-67350: results across runs

Stalled call = insertMany ≥ 3 s or still running at the cap. HS misses = increase of `history store table reads missed` over the insert phase.

| condition | runs | stalled runs | insert phase s: median [min–max] | longest call s: median (max) | stall durations (s) | stalled calls on batch 0 | latest stalled-call start (s) | HS reads missed: median (max) | noisy runs | runs fully on AC | stall type of stalled runs (exploratory) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5.0.33 prefix_search=off bruce sync-start | 5 | **4** | 239.0 [5.2–562.3] | 238.02 (561.3) | 561.3, 329.5, 246.7, 238.0, 207.0, 197.8, 171.5, 152.7 … | 9/9 | 0.01 | 388,598,870 (1,083,053,646) | 4 | 4/5 | history-store walk 4 |
| 5.0.33 prefix_search=on bruce sync-start | 5 | **0** | 5.2 [5.0–5.8] | 0.20 (0.3) | – | 0/0 | – | 0.0 (0.0) | 2 | 5/5 | – |
| 4.2.24 prefix_search=absent 67350 | 1 | **0** | 4.3 [4.3–4.3] | 2.42 (2.4) | – | 0/0 | – | – (–) | 0 | 0/1 | – |
| 4.2.24 prefix_search=absent bruce | 3 | **1** | 4.8 [4.7–10.5] | 0.31 (6.0) | 6.0, 6.0, 5.1, 5.1, 5.1, 5.1, 5.1, 5.1 … | 1/20 | 1.04 | – (–) | 1 | 2/3 | eviction 1 |
| 4.2.24 prefix_search=absent bruce sync-start | 3 | **2** | 9.7 [5.4–11.6] | 5.10 (7.2) | 7.2, 7.2, 6.5, 6.5, 6.5, 6.5, 6.5, 6.5 … | 4/40 | 0.84 | – (–) | 1 | 0/3 | eviction 2 |
| 4.4.1 prefix_search=absent bruce | 3 | **2** | 11.3 [10.7–12.3] | 4.47 (4.7) | 4.7, 4.5, 4.4, 4.4, 4.3, 4.3, 4.3, 4.3 … | 21/30 | 1.16 | 106,170 (241,315) | 2 | 2/3 | in-memory walk 2 |
| 4.4.1 prefix_search=absent bruce sync-start | 3 | **2** | 12.4 [10.3–12.8] | 5.28 (5.3) | 5.3, 5.3, 3.0 | 3/3 | 0.01 | 0.0 (364,360) | 1 | 0/3 | in-memory walk 2 |
| 4.4.2 prefix_search=absent bruce | 3 | **3** (3 capped) | 300.0 [300.0–300.0] | 299.93 (299.9) | 299.9, 299.9, 299.9, 299.9, 299.9, 299.9, 299.9, 299.9 … | 27/32 | 0.17 | 543,399,586 (545,804,355) | 3 | 2/3 | history-store walk 3 |
| 4.4.2 prefix_search=absent bruce sync-start | 3 | **3** (3 capped) | 300.0 [300.0–300.0] | 300.00 (300.0) | 300.0, 300.0, 300.0, 300.0, 300.0, 300.0, 300.0, 300.0 … | 15/15 | 0.01 | 628,636,384 (751,376,571) | 3 | 0/3 | history-store walk 3 |
| 4.4.30 prefix_search=off bruce | 3 | **3** (3 capped) | 300.0 [300.0–300.0] | 299.93 (299.9) | 299.9, 299.9, 299.9, 299.9, 299.9, 299.9, 299.9, 299.9 … | 32/40 | 0.19 | 472,184,302 (472,393,693) | 3 | 3/3 | history-store walk 3 |
| 4.4.30 prefix_search=on bruce | 3 | **0** | 5.3 [5.2–5.3] | 0.20 (0.2) | – | 0/0 | – | 0.0 (0.0) | 0 | 3/3 | – |
| 5.0.33 prefix_search=off 67350 | 2 | **0** | 4.4 [4.3–4.4] | 2.65 (2.8) | – | 0/0 | – | 0.0 (0.0) | 1 | 0/2 | – |
| 5.0.33 prefix_search=off bruce | 10 | **2** | 5.4 [5.2–69.0] | 0.35 (68.0) | 68.0, 3.1 | 2/2 | 0.09 | 0.0 (102,669,894) | 3 | 10/10 | history-store walk 1, other 1 |
| 5.0.33 prefix_search=off bruce sync-start (profiled) | 1 | **1** (1 capped) | 300.0 [300.0–300.0] | 300.00 (300.0) | 300.0, 290.1 | 2/2 | 0.00 | 645,846,154 (645,846,154) | 1 | 1/1 | history-store walk 1 |
| 5.0.33 prefix_search=off bruce sync-start NON-UNIQUE | 2 | **0** | 3.4 [3.1–3.6] | 0.17 (0.2) | – | 0/0 | – | 0.0 (0.0) | 1 | 0/2 | – |
| 5.0.33 prefix_search=on 67350 | 2 | **0** | 4.2 [4.2–4.3] | 2.81 (2.8) | – | 0/0 | – | 0.0 (0.0) | 0 | 0/2 | – |
| 5.0.33 prefix_search=on bruce | 10 | **0** | 5.3 [5.2–5.9] | 0.19 (0.3) | – | 0/0 | – | 0.0 (0.0) | 3 | 10/10 | – |
| 5.0.33 prefix_search=on bruce sync-start (profiled) | 1 | **0** | 5.4 [5.4–5.4] | 0.32 (0.3) | – | 0/0 | – | 0.0 (0.0) | 1 | 1/1 | – |

While only stalled calls were left (every other client thread finished), connection threads at ≥ 90% CPU (median over that window) vs stalled client threads, per run:

- 5.0.33 prefix_search=off bruce sync-start: 2 vs 4, 3 vs 3, 1 vs 1, 1 vs 1
- 4.4.2 prefix_search=absent bruce: 6 vs 12, 10 vs 10, 9 vs 10
- 4.4.2 prefix_search=absent bruce sync-start: 2 vs 3, 5 vs 5, 7 vs 7
- 4.4.30 prefix_search=off bruce: 4 vs 13, 2 vs 15, 5 vs 12
- 5.0.33 prefix_search=off bruce: 1 vs 1
- 5.0.33 prefix_search=off bruce sync-start (profiled): 2 vs 2

## Pre-registered criteria (bug arm = `5.0.33 prefix_search=off bruce sync-start`, fix arm = `5.0.33 prefix_search=on bruce sync-start`)

| criterion | value | result |
|---|---|---|
| **S1** ≥3 of the bug-arm runs have a stalled call | 4/5 | **met** |
| **S2** 0 fix-arm runs have a stalled call | 0/5 | **met** |
| **S3** one-sided Fisher exact test on stalled runs, bug vs fix, p < 0.05 | p = 0.0238 | **met** |
| **S4a** every stalled bug-arm run has ≥ 1,000,000 HS reads missed | 1,083,053,646, 689,428,808, 388,598,870, 272,498,848 | **met** |
| **S4b** fix-arm max HS reads missed < 1% of the smallest stalled bug-arm value | fix max 0 vs bug min 272,498,848 | **met** |
| **S4c** in every stalled bug-arm run ≥ 80% of HS misses accrue while a call has run ≥ 3 s | 100%, 99%, 99%, 99% | **met** |
| **S5** profile: stuck threads ≥50% in _keyExists and ≥50% in __wt_hs_find_upd, snapshot in _keyExists; fix arm __wt_hs_find_upd < 1% | `P1-5.0.33-W1-off-profile`: 59,978 stuck samples, _keyExists 99.9%, __wt_hs_find_upd 81.9%, gdb snapshot in _keyExists: True. Fix: `P1-5.0.33-W1-on-profile`: __wt_hs_find_upd 0.0% of 35,600 conn samples | **met** |

## Pre-registered secondary checks (descriptive, not part of the verdict)

| check | value | result |
|---|---|---|
| **U1** W0 5.0.33: stalled runs off > on | 2/10 vs 0/10 | holds |
| **U2** W0 5.0.33: HS misses > 0 in ≥ 1 off run and = 0 in every on run | off max 102,669,894, on max 0 | holds |
| **V1** W0 4.4.30: ≥ 2/3 off runs stalled and 0 on runs | 3/3 vs 0/3 | holds |
| **R1** 4.4.2: ≥ 2/3 runs stalled | 3/3 | holds |
| **R2** 4.4.1: fewer stalled runs or lower median HS misses than 4.4.2 | stalled 2/3 vs 3/3; median HS misses 106,170 vs 543,399,586 | holds |
| **R'1** 4.4.2 sync-start: ≥ 2/3 runs stalled | 3/3 | holds |
| **R'2** 4.4.1 sync-start: fewer stalled runs or lower median HS misses than 4.4.2 | stalled 2/3 vs 3/3; median HS misses 0.0 vs 628,636,384 | holds |
| **B1 (W0)** 4.2.24: 0 stalled runs | 1/3 | **does not hold** |
| **B1 (W1)** 4.2.24 sync-start: 0 stalled runs | 2/3 | **does not hold** |
| **C1** non-unique indexes, 5.0.33 off W1: 0 stalled runs | 0/2 | holds |

## Power-source sensitivity check (disclosed, PLAN.md change 7; not used for the verdict)

The laptop ran some counted runs on battery, where Low Power Mode slows the CPU. Below, every criterion and secondary check recomputed on the 43 of 63 counted runs whose whole insert phase was on AC power (per-run `power` in each `summary.json`).

| check | all counted runs | AC-only runs | same result? |
|---|---|---|---|
| S1 | 4/5 → met | 3/4 → met | yes |
| S2 | 0/5 → met | 0/5 → met | yes |
| S3 | p = 0.0238 → met | p = 0.0476 → met | yes |
| S4a | 1,083,053,646, 689,428,808, 388,598,870, 272,498,848 → met | 689,428,808, 388,598,870, 272,498,848 → met | yes |
| S4b | fix max 0 vs bug min 272,498,848 → met | fix max 0 vs bug min 272,498,848 → met | yes |
| S4c | 100%, 99%, 99%, 99% → met | 99%, 99%, 99% → met | yes |
| S5 | `P1-5.0.33-W1-off-profile`: 59,978 stuck samples, _keyExists 99.9%, __wt_hs_find_upd 81.9%, gdb snapshot in _keyExists: True / `P1-5.0.33-W1-on-profile`: __wt_hs_find_upd 0.0% of 35,600 conn samples → met | profiled runs: P1-5.0.33-W1-off-profile, P1-5.0.33-W1-on-profile → met | yes |
| U1 | 2/10 vs 0/10 → holds | 2/10 vs 0/10 → holds | yes |
| U2 | off max 102,669,894, on max 0 → holds | off max 102,669,894, on max 0 → holds | yes |
| V1 | 3/3 vs 0/3 → holds | 3/3 vs 0/3 → holds | yes |
| R1 | 3/3 → holds | 2/2 → holds | yes |
| R2 | stalled 2/3 vs 3/3; median HS misses 106,170 vs 543,399,586 → holds | stalled 2/2 vs 2/2; median HS misses 173,742 vs 544,601,970 → holds | yes |
| R'1 | 3/3 → holds | no AC-only runs | – |
| R'2 | stalled 2/3 vs 3/3; median HS misses 0.0 vs 628,636,384 → holds | no AC-only runs | – |
| B1 (W0) | 1/3 → does not hold | 0/2 → holds | **no** |
| B1 (W1) | 2/3 → does not hold | no AC-only runs | – |
| C1 | 0/2 → holds | no AC-only runs | – |

Sensitivity check (pre-registered, not used for the verdict): non-noisy runs only, stalled runs bug 0/1, fix 0/3, one-sided Fisher p = 1.0000. This check is uninformative: every stalled run lasts minutes, and other containers burst to ≥ 2 cores about every 30 s, so every long run is flagged.

Exploratory replacement (added after block A): noise only in the first 10 s, where every stall starts. Runs without a burst there: stalled bug 2/3, fix 0/3, one-sided Fisher p = 0.2000; stalled bug-arm runs that did have a burst in their first 10 s: 2.

## Exploratory: which threads stall (not a criterion)

Thread t inserts keys [t·100000, (t+1)·100000), so a low t has more of the other threads' keys "next" of its insert point. Rank correlation between thread index and stall duration:

- 5.0.33 prefix_search=off bruce sync-start: 9 stalled calls (uncapped runs); Spearman rho(thread index, stall duration) = -0.30; stalled thread indexes: [1, 1, 6, 7, 8, 9, 9, 10, 13]
- 4.2.24 prefix_search=absent bruce: 20 stalled calls (uncapped runs); Spearman rho(thread index, stall duration) = -0.41; stalled thread indexes: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
- 4.2.24 prefix_search=absent bruce sync-start: 40 stalled calls (uncapped runs); Spearman rho(thread index, stall duration) = -0.04; stalled thread indexes: [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 17, 17, 18, 18, 19, 19]
- 4.4.1 prefix_search=absent bruce: 30 stalled calls (uncapped runs); Spearman rho(thread index, stall duration) = +0.00; stalled thread indexes: [0, 1, 2, 2, 3, 3, 4, 5, 6, 7, 7, 8, 8, 9, 10, 10, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 17, 17, 18, 19]

## Runs

| condition | label | insert s | stalled calls (threads) | longest call s | HS misses | noisy | power (start → end) | stall type (exploratory) |
|---|---|---|---|---|---|---|---|---|
| 5.0.33 prefix_search=off bruce sync-start | `A1-5.0.33-W1-off` | 562.3 | 4 (4) | 561.32 | 1,083,053,646 | yes | battery → AC | history-store walk |
| 5.0.33 prefix_search=off bruce sync-start | `A2-5.0.33-W1-off` | 247.6 | 3 (3) | 246.66 | 689,428,808 | yes | AC | history-store walk |
| 5.0.33 prefix_search=off bruce sync-start | `A3-5.0.33-W1-off` | 239.01 | 1 (1) | 238.02 | 388,598,870 | yes | AC | history-store walk |
| 5.0.33 prefix_search=off bruce sync-start | `A4-5.0.33-W1-off` | 172.58 | 1 (1) | 171.54 | 272,498,848 | yes | AC | history-store walk |
| 5.0.33 prefix_search=off bruce sync-start | `A5-5.0.33-W1-off` | 5.24 | 0 (0) | 0.23 | 0.0 |  | AC | none |
| 5.0.33 prefix_search=on bruce sync-start | `A1-5.0.33-W1-on` | 5.59 | 0 (0) | 0.24 | 0.0 | yes | AC | none |
| 5.0.33 prefix_search=on bruce sync-start | `A2-5.0.33-W1-on` | 5.04 | 0 (0) | 0.20 | 0.0 |  | AC | none |
| 5.0.33 prefix_search=on bruce sync-start | `A3-5.0.33-W1-on` | 5.81 | 0 (0) | 0.33 | 0.0 | yes | AC | none |
| 5.0.33 prefix_search=on bruce sync-start | `A4-5.0.33-W1-on` | 5.16 | 0 (0) | 0.20 | 0.0 |  | AC | none |
| 5.0.33 prefix_search=on bruce sync-start | `A5-5.0.33-W1-on` | 5.2 | 0 (0) | 0.18 | 0.0 |  | AC | none |
| 4.2.24 prefix_search=absent 67350 | `X1-4.2.24-W2` | 4.32 | 0 (0) | 2.42 | – |  | battery | none |
| 4.2.24 prefix_search=absent bruce | `B1-4.2.24-W0` | 4.77 | 0 (0) | 0.21 | – | yes | AC | none |
| 4.2.24 prefix_search=absent bruce | `B2-4.2.24-W0` | 4.74 | 0 (0) | 0.31 | – |  | AC | none |
| 4.2.24 prefix_search=absent bruce | `B4-4.2.24-W0` | 10.51 | 20 (20) | 6.02 | – |  | battery | eviction |
| 4.2.24 prefix_search=absent bruce sync-start | `BS1-4.2.24-W1` | 5.44 | 0 (0) | 1.23 | – |  | battery | none |
| 4.2.24 prefix_search=absent bruce sync-start | `BS2-4.2.24-W1` | 9.66 | 20 (20) | 5.10 | – | yes | battery | eviction |
| 4.2.24 prefix_search=absent bruce sync-start | `BS3-4.2.24-W1` | 11.64 | 20 (20) | 7.21 | – |  | battery | eviction |
| 4.4.1 prefix_search=absent bruce | `R1-4.4.1-W0` | 11.26 | 16 (16) | 4.47 | 241,315 |  | AC | in-memory walk |
| 4.4.1 prefix_search=absent bruce | `R2-4.4.1-W0` | 12.33 | 14 (14) | 4.68 | 106,170 | yes | AC | in-memory walk |
| 4.4.1 prefix_search=absent bruce | `R4-4.4.1-W0` | 10.65 | 0 (0) | 2.94 | 0.0 | yes | battery | none |
| 4.4.1 prefix_search=absent bruce sync-start | `RS1-4.4.1-W1` | 12.84 | 1 (1) | 5.33 | 0.0 | yes | battery | in-memory walk |
| 4.4.1 prefix_search=absent bruce sync-start | `RS2-4.4.1-W1` | 12.39 | 2 (2) | 5.28 | 364,360 |  | battery | in-memory walk |
| 4.4.1 prefix_search=absent bruce sync-start | `RS3-4.4.1-W1` | 10.33 | 0 (0) | 2.99 | 0.0 |  | battery | none |
| 4.4.2 prefix_search=absent bruce | `R1-4.4.2-W0` | 300.0 CAP | 12 (12) | 299.93 | 545,804,355 | yes | AC | history-store walk |
| 4.4.2 prefix_search=absent bruce | `R2-4.4.2-W0` | 300.0 CAP | 10 (10) | 299.91 | 543,399,586 | yes | AC | history-store walk |
| 4.4.2 prefix_search=absent bruce | `R4-4.4.2-W0` | 300.0 CAP | 10 (10) | 299.94 | 524,062,341 | yes | battery | history-store walk |
| 4.4.2 prefix_search=absent bruce sync-start | `RS3-4.4.2-W1` | 300.0 CAP | 3 (3) | 300.00 | 751,376,571 | yes | battery | history-store walk |
| 4.4.2 prefix_search=absent bruce sync-start | `RS4-4.4.2-W1` | 300.0 CAP | 5 (5) | 300.00 | 628,636,384 | yes | battery | history-store walk |
| 4.4.2 prefix_search=absent bruce sync-start | `RS5-4.4.2-W1` | 300.0 CAP | 7 (7) | 300.00 | 585,469,205 | yes | battery | history-store walk |
| 4.4.30 prefix_search=off bruce | `V1-4.4.30-W0-off` | 300.0 CAP | 13 (13) | 299.92 | 472,184,302 | yes | AC | history-store walk |
| 4.4.30 prefix_search=off bruce | `V2-4.4.30-W0-off` | 300.0 CAP | 15 (15) | 299.94 | 468,949,081 | yes | AC | history-store walk |
| 4.4.30 prefix_search=off bruce | `V3-4.4.30-W0-off` | 300.0 CAP | 12 (12) | 299.93 | 472,393,693 | yes | AC | history-store walk |
| 4.4.30 prefix_search=on bruce | `V1-4.4.30-W0-on` | 5.23 | 0 (0) | 0.19 | 0.0 |  | AC | none |
| 4.4.30 prefix_search=on bruce | `V2-4.4.30-W0-on` | 5.26 | 0 (0) | 0.21 | 0.0 |  | AC | none |
| 4.4.30 prefix_search=on bruce | `V3-4.4.30-W0-on` | 5.34 | 0 (0) | 0.20 | 0.0 |  | AC | none |
| 5.0.33 prefix_search=off 67350 | `X1-5.0.33-W2-off` | 4.34 | 0 (0) | 2.80 | 0.0 | yes | battery | none |
| 5.0.33 prefix_search=off 67350 | `X2-5.0.33-W2-off` | 4.4 | 0 (0) | 2.50 | 0.0 |  | battery | none |
| 5.0.33 prefix_search=off bruce | `U01-5.0.33-W0-off` | 5.38 | 0 (0) | 0.19 | 0.0 |  | AC | none |
| 5.0.33 prefix_search=off bruce | `U02-5.0.33-W0-off` | 5.24 | 0 (0) | 0.20 | 0.0 |  | AC | none |
| 5.0.33 prefix_search=off bruce | `U03-5.0.33-W0-off` | 69.02 | 1 (1) | 67.99 | 102,669,894 | yes | AC | history-store walk |
| 5.0.33 prefix_search=off bruce | `U04-5.0.33-W0-off` | 5.75 | 0 (0) | 0.56 | 0.0 | yes | AC | none |
| 5.0.33 prefix_search=off bruce | `U05-5.0.33-W0-off` | 5.19 | 0 (0) | 0.17 | 0.0 |  | AC | none |
| 5.0.33 prefix_search=off bruce | `U06-5.0.33-W0-off` | 5.47 | 0 (0) | 0.96 | 36,675 |  | AC | none |
| 5.0.33 prefix_search=off bruce | `U07-5.0.33-W0-off` | 6.64 | 1 (1) | 3.11 | 1,916,224 |  | AC | other |
| 5.0.33 prefix_search=off bruce | `U08-5.0.33-W0-off` | 5.28 | 0 (0) | 0.32 | 0.0 |  | AC | none |
| 5.0.33 prefix_search=off bruce | `U09-5.0.33-W0-off` | 5.64 | 0 (0) | 0.33 | 0.0 | yes | AC | none |
| 5.0.33 prefix_search=off bruce | `U10-5.0.33-W0-off` | 5.35 | 0 (0) | 0.38 | 0.0 |  | AC | none |
| 5.0.33 prefix_search=off bruce sync-start (profiled) | `P1-5.0.33-W1-off-profile` | 300.0 CAP | 2 (2) | 300.00 | 645,846,154 | yes | AC | history-store walk |
| 5.0.33 prefix_search=off bruce sync-start NON-UNIQUE | `C1-5.0.33-W1-off-nonunique` | 3.65 | 0 (0) | 0.19 | 0.0 | yes | battery | none |
| 5.0.33 prefix_search=off bruce sync-start NON-UNIQUE | `C2-5.0.33-W1-off-nonunique` | 3.08 | 0 (0) | 0.16 | 0.0 |  | battery | none |
| 5.0.33 prefix_search=on 67350 | `X1-5.0.33-W2-on` | 4.28 | 0 (0) | 2.84 | 0.0 |  | battery | none |
| 5.0.33 prefix_search=on 67350 | `X2-5.0.33-W2-on` | 4.22 | 0 (0) | 2.77 | 0.0 |  | battery | none |
| 5.0.33 prefix_search=on bruce | `U01-5.0.33-W0-on` | 5.76 | 0 (0) | 0.28 | 0.0 | yes | AC | none |
| 5.0.33 prefix_search=on bruce | `U02-5.0.33-W0-on` | 5.23 | 0 (0) | 0.17 | 0.0 |  | AC | none |
| 5.0.33 prefix_search=on bruce | `U03-5.0.33-W0-on` | 5.33 | 0 (0) | 0.18 | 0.0 |  | AC | none |
| 5.0.33 prefix_search=on bruce | `U04-5.0.33-W0-on` | 5.27 | 0 (0) | 0.19 | 0.0 |  | AC | none |
| 5.0.33 prefix_search=on bruce | `U05-5.0.33-W0-on` | 5.28 | 0 (0) | 0.18 | 0.0 |  | AC | none |
| 5.0.33 prefix_search=on bruce | `U06-5.0.33-W0-on` | 5.88 | 0 (0) | 0.28 | 0.0 | yes | AC | none |
| 5.0.33 prefix_search=on bruce | `U07-5.0.33-W0-on` | 5.29 | 0 (0) | 0.18 | 0.0 | yes | AC | none |
| 5.0.33 prefix_search=on bruce | `U08-5.0.33-W0-on` | 5.31 | 0 (0) | 0.26 | 0.0 |  | AC | none |
| 5.0.33 prefix_search=on bruce | `U09-5.0.33-W0-on` | 5.23 | 0 (0) | 0.24 | 0.0 |  | AC | none |
| 5.0.33 prefix_search=on bruce | `U10-5.0.33-W0-on` | 5.2 | 0 (0) | 0.18 | 0.0 |  | AC | none |
| 5.0.33 prefix_search=on bruce sync-start (profiled) | `P1-5.0.33-W1-on-profile` | 5.36 | 0 (0) | 0.32 | 0.0 | yes | AC | none |

## Excluded runs (listed in `excluded_runs.txt`; kept in `runs/`, not counted anywhere above)

| label | condition | reason | what it showed |
|---|---|---|---|
| `B3-4.2.24-W0` | 4.2.24 prefix_search=absent bruce | started 6 s after the host woke from 10 min of sleep | 8.34 s, 1 stalled calls, longest 3.2 s |
| `R3-4.4.1-W0` | 4.4.1 prefix_search=absent bruce | host slept 3 s into the insert phase (10 min) | 13.24 s, 5 stalled calls, longest 4.8 s |
| `R3-4.4.2-W0` | 4.4.2 prefix_search=absent bruce | host slept 148 s into the insert phase (VM frozen 5 min; the cap fired at 459 s instead of 300 s) | 300.0 s (capped), 12 stalled calls, longest 299.9 s |
| `RS1-4.4.2-W1` | 4.4.2 prefix_search=absent bruce sync-start | started 23 s after the host woke from 10 min of sleep | 300.0 s (capped), 1 stalled calls, longest 300.0 s |
| `RS2-4.4.2-W1` | 4.4.2 prefix_search=absent bruce sync-start | aborted at 00:22 EDT (about 1 min in) when the work was paused for the night; partial data kept | 17.87 s, 2 stalled calls, longest 17.9 s |

Plots: `plots/conditions.png` (every run as a dot).
