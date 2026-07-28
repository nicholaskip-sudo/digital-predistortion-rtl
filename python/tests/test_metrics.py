"""Tests for shared PA and DPD quality metrics."""

from __future__ import annotations

import numpy as np
import pytest

from dpd.metrics import best_fit_complex_gain, evm_rms_percent, nmse_db, per_column_complex_gain


def test_best_fit_gain_recovers_exact_complex_gain() -> None:
    reference = np.array([1+1j, -0.5+0.2j, 0.3-0.7j], dtype=np.complex128)
    gain = 1.7 - 0.35j
    observed = gain * reference
    assert best_fit_complex_gain(reference, observed) == pytest.approx(gain)
    assert nmse_db(reference, observed) < -300.0
    assert evm_rms_percent(reference, observed) == pytest.approx(0.0)


def test_per_column_gain_recovers_independent_carrier_gains() -> None:
    reference = np.array([[1+0j, 1+1j], [-1+1j, 0.5-0.5j]], dtype=np.complex128)
    gains = np.array([2.0+0.2j, 0.8-0.1j], dtype=np.complex128)
    observed = reference * gains[np.newaxis, :]
    np.testing.assert_allclose(per_column_complex_gain(reference, observed), gains)
