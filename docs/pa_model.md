# Behavioral Power-Amplifier Model

## Architecture

The selected PA is a Wiener model:

Complex input -> causal complex FIR memory -> Rapp AM/AM + AM/PM -> output


The FIR introduces dependence on current and previous samples. The nonlinear core then
compresses large envelopes and rotates phase as envelope magnitude increases.

## AM/AM model

For memory-filter output magnitude 'r':

linear = gain * r
output = linear / (1 + (linear / saturation)^(2p))^(1/(2p))

'p' is the Rapp smoothness parameter. Larger values produce a sharper transition into
compression.

## AM/PM model

phase = phase_max * (r / transition)^2 / (1 + (r / transition)^2)


The phase rotation starts near zero and approaches the configured maximum smoothly.

## Default parameters

| Parameter | Value |
|---|---:|
| Small-signal gain | 2.0 |
| Saturation amplitude | 0.60 |
| Rapp smoothness | 2.5 |
| Maximum AM/PM | 18 degrees |
| AM/PM transition amplitude | 0.34 |
| Memory taps | 1.0, 0.10-j0.04, -0.035+j0.020 |

## Why this model is suitable

It is deterministic, differentiates linear memory from nonlinear distortion, causes
visible spectral regrowth, and is representable by the selected Memory Polynomial DPD.
