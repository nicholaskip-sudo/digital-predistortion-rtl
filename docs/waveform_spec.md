# Waveform Specification

## Purpose

The waveform generator supplies deterministic signals for:

- Power-amplifier characterization
- DPD coefficient training
- Fixed-point analysis
- RTL golden-vector generation
- Directed verification tests

## Default OFDM waveform

| Parameter | Value |
|---|---:|
| Modulation | 64-QAM |
| OFDM symbols | 32 |
| Base FFT size | 256 |
| Oversampling | 4 |
| Actual IFFT size | 1024 |
| Active subcarriers | 192 |
| Base cyclic prefix | 32 |
| Oversampled cyclic prefix | 128 |
| Output samples per symbol | 1152 |
| Total sample count | 36864 |
| Random seed | 12345 |
| RMS target | 0.20 |

## Active-subcarrier allocation

DC is unused. Half of the active carriers are placed above DC and half below DC.
With 192 active carriers:

- Positive-frequency carriers: 96
- Negative-frequency carriers: 96
- DC carrier: unused

Oversampling is obtained by increasing the IFFT size while keeping the number of occupied
carriers constant. This creates spectral images farther away and provides enough sample
rate for later PA and DPD nonlinear analysis.

## QAM normalization

Square QAM uses ideal constellation levels and normalization:

\[
scale = \sqrt{\frac{2}{3}(M-1)}
\]

The complete ideal constellation has unit average symbol power.

## Directed waveforms

The Python module also generates:

- Complex impulse
- Complex tone
- Complex amplitude ramp
- Two-tone signal

These signals will later be exported as small RTL-debug vectors.
