# Milestone 2 - NumPy-only PSD fix

The project now implements Welch PSD using NumPy only:

- Hann window
- 50% overlap
- Segment mean removal
- Two-sided FFT
- Density scaling
- FFT-shifted output
- Peak normalization to 0 dB

## Verification

The tests confirm:

- Correct positive-frequency tone location
- Centered frequency output
- 0 dB peak normalization
- Deterministic repeated results
- Clear handling of empty input
