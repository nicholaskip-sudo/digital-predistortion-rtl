"""Tests for waveform configuration."""

from dpd.waveform_config import OfdmConfig, load_waveform_config


def test_default_waveform_configuration() -> None:
    config = load_waveform_config()

    assert config.seed == 12345
    assert config.qam.order == 64
    assert config.ofdm.symbol_count == 32
    assert config.ofdm.base_fft_size == 256
    assert config.ofdm.active_subcarriers == 192
    assert config.ofdm.cyclic_prefix_length == 32
    assert config.ofdm.oversampling == 4
    assert config.ofdm.ifft_size == 1024
    assert config.ofdm.cyclic_prefix_samples == 128
    assert config.ofdm.samples_per_symbol == 1152
    assert config.ofdm.total_samples == 36864


def test_odd_active_subcarrier_count_is_rejected() -> None:
    try:
        OfdmConfig(
            symbol_count=1,
            base_fft_size=256,
            active_subcarriers=191,
            cyclic_prefix_length=32,
            oversampling=4,
        )
    except ValueError as error:
        assert "even" in str(error)
    else:
        raise AssertionError("Expected odd active-subcarrier count to be rejected.")
