"""Configuration loader for the behavioral power-amplifier model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from dpd.project_paths import PROJECT_ROOT


DEFAULT_PA_CONFIG_PATH = PROJECT_ROOT / "config" / "pa_config.yaml"


@dataclass(frozen=True)
class PaMemoryConfig:
    """Causal complex FIR memory preceding the nonlinear PA core."""

    input_taps: tuple[complex, ...]

    def __post_init__(self) -> None:
        if not self.input_taps:
            raise ValueError("At least one PA memory tap is required.")
        taps = np.asarray(self.input_taps, dtype=np.complex128)
        if not np.all(np.isfinite(taps.real)) or not np.all(np.isfinite(taps.imag)):
            raise ValueError("PA memory taps must be finite.")
        if abs(self.input_taps[0]) == 0.0:
            raise ValueError("The first PA memory tap cannot be zero.")


@dataclass(frozen=True)
class PaNonlinearityConfig:
    """Rapp AM/AM and saturating AM/PM parameters."""

    small_signal_gain: float
    saturation_amplitude: float
    rapp_smoothness: float
    ampm_max_degrees: float
    ampm_transition_amplitude: float

    def __post_init__(self) -> None:
        if self.small_signal_gain <= 0.0:
            raise ValueError("Small-signal gain must be positive.")
        if self.saturation_amplitude <= 0.0:
            raise ValueError("Saturation amplitude must be positive.")
        if self.rapp_smoothness <= 0.0:
            raise ValueError("Rapp smoothness must be positive.")
        if self.ampm_max_degrees < 0.0:
            raise ValueError("Maximum AM/PM rotation cannot be negative.")
        if self.ampm_transition_amplitude <= 0.0:
            raise ValueError("AM/PM transition amplitude must be positive.")


@dataclass(frozen=True)
class PaReportConfig:
    """PA reporting settings."""

    characterization_points: int

    def __post_init__(self) -> None:
        if self.characterization_points < 16:
            raise ValueError("At least 16 PA characterization points are required.")


@dataclass(frozen=True)
class PaConfig:
    """Complete behavioral PA configuration."""

    model: str
    memory: PaMemoryConfig
    nonlinearity: PaNonlinearityConfig
    report: PaReportConfig

    def __post_init__(self) -> None:
        if self.model != "wiener_rapp_ampm":
            raise ValueError(f"Unsupported PA model: {self.model!r}")


def _mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"PA configuration section {key!r} must be a mapping.")
    return value


def _complex_taps(raw_taps: Any) -> tuple[complex, ...]:
    if not isinstance(raw_taps, list):
        raise ValueError("PA memory input_taps must be a list.")

    taps: list[complex] = []
    for tap_index, raw_tap in enumerate(raw_taps):
        if not isinstance(raw_tap, dict):
            raise ValueError(f"PA tap {tap_index} must be a mapping.")
        taps.append(complex(float(raw_tap["real"]), float(raw_tap["imag"])))
    return tuple(taps)


def load_pa_config(path: Path | str = DEFAULT_PA_CONFIG_PATH) -> PaConfig:
    """Load and validate the behavioral PA YAML configuration."""

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"PA configuration not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("PA configuration root must be a mapping.")

    memory = _mapping(raw, "memory")
    nonlinearity = _mapping(raw, "nonlinearity")
    report = _mapping(raw, "report")

    return PaConfig(
        model=str(raw["model"]),
        memory=PaMemoryConfig(input_taps=_complex_taps(memory["input_taps"])),
        nonlinearity=PaNonlinearityConfig(
            small_signal_gain=float(nonlinearity["small_signal_gain"]),
            saturation_amplitude=float(nonlinearity["saturation_amplitude"]),
            rapp_smoothness=float(nonlinearity["rapp_smoothness"]),
            ampm_max_degrees=float(nonlinearity["ampm_max_degrees"]),
            ampm_transition_amplitude=float(
                nonlinearity["ampm_transition_amplitude"]
            ),
        ),
        report=PaReportConfig(
            characterization_points=int(report["characterization_points"])
        ),
    )
