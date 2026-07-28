# Milestone 13 Stress Verification Plan

| Feature | Stimulus | Checker |
|---|---|---|
| Random complex samples | Deterministic LFSR plus directed edges | Dynamic exact predictor |
| Input bubbles | 0-3 cycles between items | Idle-cycle counter |
| Output backpressure | LFSR-controlled 'out_ready' | Stall counters and SVA |
| Reset interruption | Reset while output is stalled | Pending prediction flush and accounting |
| Coefficient update | Identity → zero → identity | Mode-aware predictor |
| Recovery | 512 samples after final update | Exact scoreboard |
| Bad input protocol | Data changes while stalled | Expected SVA fatal |
| Bad output protocol | Data changes while stalled | Expected SVA fatal |

## Stress seed matrix

13
13013
12648430

Each seed runs 2,048 accepted inputs. Matrix closure therefore covers 6,144 accepted
randomized transactions in addition to the existing fixed-vector regressions.

## Generated reports

reports/logs/dpd_uvm_stress_seed_<seed>.log
reports/results/uvm_stress_seed_<seed>.json
reports/results/uvm_stress_matrix.json
reports/logs/negative_input_stability.log
reports/logs/negative_output_stability.log

