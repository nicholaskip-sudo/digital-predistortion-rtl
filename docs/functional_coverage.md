# DPD Functional Coverage Model

## Sampling point

Coverage is sampled from 'dpd_stream_if.monitor_cb' on the DUT clock's rising edge.
This is the same edge used for ready/valid transfers.

## Data coverage

Accepted input and output samples are classified by:

- Complex quadrant
- Maximum absolute I/Q magnitude
- Output saturation status

Magnitude classes use Q1.15 integer magnitudes:

| Class | Maximum absolute I/Q value |
|---|---:|
| Low | 0-2047 |
| Medium | 2048-8191 |
| High | 8192-16383 |
| Peak | 16384-32768 |

The coverage model also crosses quadrant with magnitude for both the input and output.

## Protocol coverage

Each active cycle is classified for the input and output interfaces:

| State | Meaning |
|---|---|
| Idle | 'valid == 0' |
| Stalled | 'valid == 1 && ready == 0' |
| Transferred | 'valid == 1 && ready == 1' |

Additional bins cover:

- 'out_ready' asserted and deasserted
- Output stall lengths
- Saturated and non-saturated output transfers

## Mandatory full-run closure

The 36,864-sample test requires:

- Four input quadrants
- Four output quadrants
- Four input magnitude classes
- Four output magnitude classes
- All six input/output protocol states
- Both output-ready states
- Both saturation states
- At least one output stall
- Exactly 36,864 accepted inputs and outputs

The cross coverage and stall-length covergroup percentages are reported but are not
used as hard pass/fail thresholds.
