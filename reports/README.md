# Reports

Reproduction reports for the online performance-bug detection project. Each report covers the bug, its
effects, how it was reproduced and the results, the symptom function and call stack, a step-by-step
reproduction pipeline, and the developer discussion.

| bug | system | effect | status |
|---|---|---|---|
| [WT-7264 / SERVER-67350](WT-7264.md) | MongoDB 4.4 / 5.0 | unique-index inserts stuck for minutes at 100% CPU in `search_near` | **reproduced** (bug 4/5 runs stuck 73–561 s, fix 0/5, same binary) |
| [SERVER-52879](SERVER-52879.md) | MongoDB ≤ 4.4.3 | periodic all-operation stalls when idle sessions are closed under a mutex | **partially reproduced** (every sweep stalls on 4.4.3, none on 4.4.4; two pre-registered checks missed) |

`figures/` holds copies of the plots and flame graphs used in the reports. The scripts, raw results and
full Jira exports live in each bug's folder (`../WT-7264/`, `../SERVER-52879/`).
