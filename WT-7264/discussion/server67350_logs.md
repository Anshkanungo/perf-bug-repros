# SERVER-67350 reporter's logs and FTDC (parsed)

Source: `requested_files.tar.gz` attached to SERVER-67350 by the reporter (mongod logs + `diagnostic.data` for 4.2.20, 4.4.14, 5.0.9, two runs each). The archive was extracted into its own directory and only parsed as data (`server67350_analyze.py`, FTDC decoded by `ftdc_decode.py`). It is not committed here; download it from the ticket (attachment `requested_files.tar.gz`).

## 4.2.20

Insert commands in the slow-query log (all of them are logged: ≥ 100 ms):

| connection | started (UTC) | duration (s) | documents |
|---|---|---|---|
| conn3 | 13:17:05.066 | 0.5 | 100000 |
| conn4 | 13:17:05.068 | 0.5 | 100000 |
| conn6 | 13:17:05.069 | 0.5 | 100000 |
| conn7 | 13:17:05.069 | 0.5 | 100000 |
| conn5 | 13:17:05.072 | 0.5 | 100000 |
| conn4 | 13:17:05.736 | 0.5 | 100000 |
| conn3 | 13:17:05.801 | 0.6 | 100000 |
| conn7 | 13:17:05.804 | 0.5 | 99996 |
| conn6 | 13:17:05.815 | 0.5 | 100000 |
| conn5 | 13:17:05.818 | 0.5 | 100000 |
| conn13 | 13:17:09.763 | 0.5 | 100000 |
| conn12 | 13:17:09.765 | 0.5 | 100000 |
| conn14 | 13:17:09.774 | 0.6 | 100000 |
| conn16 | 13:17:09.776 | 0.5 | 100000 |
| conn15 | 13:17:09.779 | 0.6 | 100000 |
| conn13 | 13:17:10.435 | 0.5 | 99996 |
| conn16 | 13:17:10.452 | 0.6 | 100000 |
| conn12 | 13:17:10.523 | 0.5 | 100000 |
| conn15 | 13:17:10.546 | 0.5 | 100000 |
| conn14 | 13:17:10.549 | 0.5 | 100000 |

FTDC (32 samples): no history store in 4.2.20 (pre-durable-history).

## 4.4.14

Insert commands in the slow-query log (all of them are logged: ≥ 100 ms):

| connection | started (UTC) | duration (s) | documents |
|---|---|---|---|
| conn6 | 12:59:10.830 | 548.1 | 100000 |
| conn9 | 12:59:10.842 | 134.4 | 100000 |
| conn7 | 12:59:10.843 | 0.4 | 100000 |
| conn10 | 12:59:10.843 | 289.6 | 100000 |
| conn8 | 12:59:10.847 | 0.5 | 100000 |
| conn7 | 12:59:11.367 | 0.4 | 99996 |
| conn8 | 12:59:11.505 | 0.5 | 100000 |
| conn9 | 13:01:25.370 | 5.7 | 100000 |
| conn10 | 13:04:00.536 | 0.5 | 100000 |
| conn6 | 13:08:19.030 | 0.4 | 100000 |
| conn14 | 13:11:37.462 | 0.4 | 100000 |
| conn13 | 13:11:37.464 | 182.0 | 100000 |
| conn15 | 13:11:37.465 | 68.0 | 100000 |
| conn16 | 13:11:37.468 | 160.5 | 100000 |
| conn17 | 13:11:37.470 | 0.6 | 100000 |
| conn14 | 13:11:38.019 | 0.4 | 99996 |
| conn17 | 13:11:38.127 | 0.5 | 100000 |
| conn15 | 13:12:45.533 | 4.3 | 100000 |
| conn16 | 13:14:18.071 | 0.5 | 100000 |
| conn13 | 13:14:39.587 | 0.4 | 100000 |

FTDC (1021 samples, 1020 s): history store reads missed over the file: **1,741,599,252**; cursor entries skipped by next+prev: 4,921,532,228; peak reads-missed rate 3,579,591/s; max active writers 5.

## 5.0.9

Insert commands in the slow-query log (all of them are logged: ≥ 100 ms):

| connection | started (UTC) | duration (s) | documents |
|---|---|---|---|
| conn6 | 12:43:21.991 | 34.0 | 100000 |
| conn8 | 12:43:21.995 | 0.5 | 100000 |
| conn7 | 12:43:22.006 | 155.6 | 100000 |
| conn5 | 12:43:22.022 | 0.6 | 100000 |
| conn9 | 12:43:22.027 | 0.6 | 100000 |
| conn8 | 12:43:22.626 | 0.5 | 99996 |
| conn5 | 12:43:22.783 | 0.6 | 100000 |
| conn9 | 12:43:22.791 | 0.6 | 100000 |
| conn6 | 12:43:56.127 | 0.5 | 100000 |
| conn7 | 12:45:57.667 | 0.5 | 100000 |
| conn16 | 12:47:33.592 | 0.4 | 100000 |
| conn17 | 12:47:33.594 | 0.6 | 100000 |
| conn13 | 12:47:33.597 | 13.5 | 100000 |
| conn14 | 12:47:33.598 | 471.7 | 100000 |
| conn15 | 12:47:33.600 | 3.9 | 100000 |
| conn16 | 12:47:34.191 | 0.4 | 99996 |
| conn17 | 12:47:34.324 | 0.6 | 100000 |
| conn15 | 12:47:37.552 | 6.2 | 100000 |
| conn13 | 12:47:47.164 | 0.5 | 100000 |
| conn14 | 12:55:25.414 | 0.4 | 100000 |

FTDC (798 samples, 797 s): history store reads missed over the file: **986,293,371**; cursor entries skipped by next+prev: 2,400,138,966; peak reads-missed rate 1,914,623/s; max active writers 5.

