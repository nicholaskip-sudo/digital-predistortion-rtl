# Floating-Point Memory Polynomial DPD Training

## Model

The predistorter is:

\[
z[n] = \sum_{m=0}^{2}\sum_{p\in\{1,3,5\}}
a_{p,m}x[n-m]|x[n-m]|^{p-1}
\]

The nine complex coefficients use the canonical memory-major, order-minor ordering.

## Indirect Learning Architecture

For a target linear gain \(G_t=1.5\):

1. Apply the current predistorter to the training waveform.
2. Pass the predistorted waveform through the PA.
3. Normalize the PA output by \(G_t\).
4. Fit a postdistorter mapping normalized PA output back to PA input.
5. Copy the postdistorter coefficients into the predistorter.
6. Accept the candidate only when held-out validation NMSE improves.

The validation guard is important because unconstrained repeated ILA updates can diverge.

## Target gain and headroom

The PA small-signal gain is 2.0, while the selected linearized target gain is 1.5. The
reduced target preserves nonlinear correction headroom. The report includes a same-gain
simple-backoff baseline so the DPD benefit is not confused with output-power reduction.

## Least-squares conditioning

Order-1, order-3, and order-5 basis columns have very different magnitudes. Before solving,
each column is divided by its RMS value. Ridge rows are then added to the normalized system.
The solved coefficients are finally converted back to the original basis scale.

## Output limiting

Real and imaginary components are saturated independently to the Q1.15 external range:

- Minimum: -1.0
- Maximum: 32767/32768

This matches the component-wise saturation behavior planned for the fixed-point model and RTL.
