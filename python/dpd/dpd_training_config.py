"""Configuration loader for floating-point DPD training."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from dpd.project_paths import PROJECT_ROOT


DEFAULT_DPD_TRAINING_CONFIG_PATH = (
    PROJECT_ROOT / "config" / "dpd_training_config.yaml"
)


@dataclass(frozen=True)
class DpdTargetConfig:
    """Desired linear PA-plus-DPD response."""

    linear_gain: float

    def __post_init__(self) -> None:
        if self.linear_gain <= 0.0:
            raise ValueError("Target linear gain must be positive.")


@dataclass(frozen=True)
class LeastSquaresConfig:
    """Numerically stabilized least-squares settings."""

    ridge_regularization: float
    ignore_initial_samples: int
    training_fraction: float

    def __post_init__(self) -> None:
        if self.ridge_regularization < 0.0:
            raise ValueError("Ridge regularization cannot be negative.")
        if self.ignore_initial_samples < 0:
            raise ValueError("Ignored initial-sample count cannot be negative.")
        if not 0.0 < self.training_fraction < 1.0:
            raise ValueError("Training fraction must lie strictly between zero and one.")


@dataclass(frozen=True)
class IterationConfig:
    """Safeguarded indirect-learning iteration settings."""

    maximum_iterations: int
    minimum_validation_improvement_db: float

    def __post_init__(self) -> None:
        if self.maximum_iterations <= 0:
            raise ValueError("Maximum iteration count must be positive.")
        if self.minimum_validation_improvement_db < 0.0:
            raise ValueError("Minimum validation improvement cannot be negative.")


@dataclass(frozen=True)
class OutputLimitConfig:
    """Component-wise predistorter output limits."""

    mode: str
    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        if self.mode != "component_saturation":
            raise ValueError("The MVP output-limit mode must be component_saturation.")
        if self.minimum >= self.maximum:
            raise ValueError("Output-limit minimum must be smaller than maximum.")
        if self.minimum > 0.0 or self.maximum < 0.0:
            raise ValueError("Output limits must include zero.")


@dataclass(frozen=True)
class DpdReportConfig:
    """Floating-point DPD report settings."""

    maximum_constellation_points: int

    def __post_init__(self) -> None:
        if self.maximum_constellation_points <= 0:
            raise ValueError("Maximum constellation-point count must be positive.")


@dataclass(frozen=True)
class DpdTrainingConfig:
    """Complete floating-point DPD training configuration."""

    method: str
    target: DpdTargetConfig
    least_squares: LeastSquaresConfig
    iteration: IterationConfig
    output_limit: OutputLimitConfig
    report: DpdReportConfig

    def __post_init__(self) -> None:
        if self.method != "indirect_learning_architecture":
            raise ValueError(f"Unsupported DPD training method: {self.method!r}")


def _mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"DPD training section {key!r} must be a mapping.")
    return value


def load_dpd_training_config(
    path: Path | str = DEFAULT_DPD_TRAINING_CONFIG_PATH,
) -> DpdTrainingConfig:
    """Load and validate the floating-point DPD training YAML file."""

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"DPD training configuration not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("DPD training configuration root must be a mapping.")

    target = _mapping(raw, "target")
    least_squares = _mapping(raw, "least_squares")
    iteration = _mapping(raw, "iteration")
    output_limit = _mapping(raw, "output_limit")
    report = _mapping(raw, "report")

    return DpdTrainingConfig(
        method=str(raw["method"]),
        target=DpdTargetConfig(linear_gain=float(target["linear_gain"])),
        least_squares=LeastSquaresConfig(
            ridge_regularization=float(least_squares["ridge_regularization"]),
            ignore_initial_samples=int(least_squares["ignore_initial_samples"]),
            training_fraction=float(least_squares["training_fraction"]),
        ),
        iteration=IterationConfig(
            maximum_iterations=int(iteration["maximum_iterations"]),
            minimum_validation_improvement_db=float(
                iteration["minimum_validation_improvement_db"]
            ),
        ),
        output_limit=OutputLimitConfig(
            mode=str(output_limit["mode"]),
            minimum=float(output_limit["minimum"]),
            maximum=float(output_limit["maximum"]),
        ),
        report=DpdReportConfig(
            maximum_constellation_points=int(report["maximum_constellation_points"])
        ),
    )
