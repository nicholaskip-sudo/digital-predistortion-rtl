# DPD Algorithm Specification

The MVP uses the complex-baseband Memory Polynomial:

\[
y[n] =
\sum_{m=0}^{M-1}
\sum_{p \in \{1,3,5\}}
a_{p,m} x[n-m] |x[n-m]|^{p-1}
\]

## Fixed MVP parameters

- Memory depth: 3
- Polynomial orders: 1, 3, 5
- Complex coefficients: 9
- Training: offline in Python
- RTL coefficients: static during a sample-processing run

## Canonical coefficient ordering

Ordering is memory-major and order-minor:

| Index | Memory | Order | Basis |
|---:|---:|---:|---|
| 0 | 0 | 1 | x[n] |
| 1 | 0 | 3 | x[n]|x[n]|² |
| 2 | 0 | 5 | x[n]|x[n]|⁴ |
| 3 | 1 | 1 | x[n-1] |
| 4 | 1 | 3 | x[n-1]|x[n-1]|² |
| 5 | 1 | 5 | x[n-1]|x[n-1]|⁴ |
| 6 | 2 | 1 | x[n-2] |
| 7 | 2 | 3 | x[n-2]|x[n-2]|² |
| 8 | 2 | 5 | x[n-2]|x[n-2]|⁴ |

Coefficient index:

index = memory_index * number_of_orders + order_slot

