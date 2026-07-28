"""Configuration loader for deterministic communication waveforms."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from dpd.project_paths import PROJECT_ROOT


DEFAULT_WAVEFORM_CONFIG_PATH = PROJECT_ROOT / "config" / "waveform_config.yaml"


@dataclass(frozen=True)
class QamConfig:
    """QAM generation settings."""

    order: int

    def __post_init__(self) -> None:
        if self.order not in (4, 16, 64):
            raise ValueError("Supported QAM orders are 4, 16, and 64.")


@dataclass(frozen=True)
class OfdmConfig:
    """OFDM generation settings."""

    symbol_count: int
    base_fft_size: int
    active_subcarriers: int
    cyclic_prefix_length: int
    oversampling: int

    def __post_init__(self) -> None:
        if self.symbol_count <= 0:
            raise ValueError("OFDM symbol count must be positive.")
        if self.base_fft_size <= 0:
            raise ValueError("Base FFT size must be positive.")
        if self.base_fft_size & (self.base_fft_size - 1):
            raise ValueError("Base FFT size must be a power of two.")
        if self.active_subcarriers <= 0:
            raise ValueError("Active-subcarrier count must be positive.")
        if self.active_subcarriers % 2 != 0:
            raise ValueError("Active-subcarrier count must be even.")
        if self.active_subcarriers >= self.base_fft_size:
            raise ValueError(
                "Active-subcarrier count must be smaller than the base FFT size."
            )
        if self.cyclic_prefix_length < 0:
            raise ValueError("Cyclic-prefix length cannot be negative.")
        if self.cyclic_prefix_length >= self.base_fft_size:
            raise ValueError(
                "Cyclic-prefix length must be smaller than the base FFT size."
            )
        if self.oversampling <= 0:
            raise ValueError("Oversampling factor must be positive.")

    @property
    def ifft_size(self) -> int:
        """Return the oversampled IFFT size."""

        return self.base_fft_size * self.oversampling

    @property
    def cyclic_prefix_samples(self) -> int:
        """Return the oversampled cyclic-prefix length."""

        return self.cyclic_prefix_length * self.oversampling

    @property
    def samples_per_symbol(self) -> int:
        """Return output samples per complete OFDM symbol."""

        return self.ifft_size + self.cyclic_prefix_samples

    @property
    def total_samples(self) -> int:
        """Return the total generated complex-sample count."""

        return self.symbol_count * self.samples_per_symbol


@dataclass(frozen=True)
class NormalizationConfig:
    """Waveform scaling settings."""

    mode: str
    target: float

    def __post_init__(self) -> None:
        if self.mode not in ("none", "peak", "rms"):
            raise ValueError("Normalization mode must be none, peak, or rms.")
        if self.target <= 0.0:
            raise ValueError("Normalization target must be positive.")


@dataclass(frozen=True)
class ReportConfig:
    """Waveform reporting settings."""

    sample_rate_hz: float

    def __post_init__(self) -> None:
        if self.sample_rate_hz <= 0.0:
            raise ValueError("Sample rate must be positive.")


@dataclass(frozen=True)
class WaveformConfig:
    """Complete waveform-generation configuration."""

    seed: int
    qam: QamConfig
    ofdm: OfdmConfig
    normalization: NormalizationConfig
    report: ReportConfig


def _mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Configuration section {key!r} must be a mapping.")
    return value


def load_waveform_config(
    path: Path | str = DEFAULT_WAVEFORM_CONFIG_PATH,
) -> WaveformConfig:
    """Load and validate the waveform YAML file."""

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Waveform configuration not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Waveform configuration root must be a mapping.")

    qam = _mapping(raw, "qam")
    ofdm = _mapping(raw, "ofdm")
    normalization = _mapping(raw, "normalization")
    report = _mapping(raw, "report")

    return WaveformConfig(
        seed=int(raw["seed"]),
        qam=QamConfig(order=int(qam["order"])),
        ofdm=OfdmConfig(
            symbol_count=int(ofdm["symbol_count"]),
            base_fft_size=int(ofdm["base_fft_size"]),
            active_subcarriers=int(ofdm["active_subcarriers"]),
            cyclic_prefix_length=int(ofdm["cyclic_prefix_length"]),
            oversampling=int(ofdm["oversampling"]),
        ),
        normalization=NormalizationConfig(
            mode=str(normalization["mode"]),
            target=float(normalization["target"]),
        ),
        report=ReportConfig(sample_rate_hz=float(report["sample_rate_hz"])),
    )
