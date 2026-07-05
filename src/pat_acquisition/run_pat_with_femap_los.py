from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

try:
    import yaml
except ImportError as exc:
    raise ImportError(
        "PyYAML is required to read PAT YAML config. "
        "Install it with: python -m pip install pyyaml"
    ) from exc

from pat_acquisition_simulator import (
    CoarseAcquisitionConfig,
    evaluate_coarse_acquisition,
    summarize_acquisition,
)

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from orbit.pat_orbit_error import (
    load_orbit_error_timeseries_csv,
    resample_orbit_error_to_times,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_GLOB = "results/femap_deformation/*/los_angles.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "pat_acquisition" / "femap_los_truth"
DEFAULT_CONFIG_PATH = Path(__file__).with_name("pat_femap_los_config.yaml")

RESULT_COLUMNS = [
    "success",
    "acquisition_time_s",
    "residual_x_urad",
    "residual_y_urad",
    "residual_norm_urad",
    "pointing_error_x_urad",
    "pointing_error_y_urad",
    "pointing_error_norm_urad",
    "thermal_residual_norm_urad",
    "scan_index",
]


@dataclass(frozen=True)
class OrbitErrorConfig:
    source: str = "sentinel1_tle_vs_pod"
    timeseries_csv: Path | None = None
    resample_mode: str = "cyclic"


@dataclass(frozen=True)
class NonthermalErrorConfig:
    seed: int = 42
    orbit_prediction_bias_1sigma_urad: float = 150.0
    attitude_random_1sigma_urad: float = 50.0
    alignment_bias_1sigma_urad: float = 50.0
    drift_amplitude_urad: float = 30.0
    drift_period_s: float = 900.0
    orbit_error: OrbitErrorConfig = OrbitErrorConfig()


def read_femap_los_csv(path: Path, los_prefix: str) -> tuple[np.ndarray, np.ndarray]:
    x_column = f"{los_prefix}_angle_x_urad"
    y_column = f"{los_prefix}_angle_y_urad"

    times = []
    theta = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"time_s", x_column, y_column}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} is missing required columns: {sorted(missing)}")

        for row in reader:
            times.append(float(row["time_s"]))
            theta.append([float(row[x_column]), float(row[y_column])])

    return np.asarray(times, dtype=float), np.asarray(theta, dtype=float)


def load_yaml_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML config must be a mapping: {path}")
    return data


def config_value(
    config: dict[str, Any],
    section: str,
    key: str,
    cli_value: Any,
    default: Any,
) -> Any:
    if cli_value is not None:
        return cli_value

    section_values = config.get(section, {})
    if section_values is None:
        return default
    if not isinstance(section_values, dict):
        raise ValueError(f"YAML section '{section}' must be a mapping")
    return section_values.get(key, default)


def config_path_value(
    config: dict[str, Any],
    section: str,
    key: str,
    cli_value: Path | None,
    default: Path,
) -> Path:
    value = config_value(config, section, key, cli_value, default)
    path = value if isinstance(value, Path) else Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _seed_for_case(base_seed: int, case_id: str) -> int:
    digest = hashlib.sha256(case_id.encode("utf-8")).digest()
    case_offset = int.from_bytes(digest[:4], byteorder="little", signed=False)
    return (base_seed + case_offset) % (2**32)


def _build_orbit_error_config(
    yaml_config: dict[str, Any],
    args: argparse.Namespace,
) -> OrbitErrorConfig:
    section = yaml_config.get("orbit_error", {})
    if section is None:
        section = {}
    if not isinstance(section, dict):
        raise ValueError("YAML section 'orbit_error' must be a mapping")

    source = config_value(
        yaml_config,
        "orbit_error",
        "source",
        args.orbit_error_source,
        "sentinel1_tle_vs_pod",
    )
    default_csv = REPO_ROOT / "results/orbit/sentinel1_tle_vs_pod/orbit_prediction_error_timeseries.csv"
    csv_path = config_path_value(
        yaml_config,
        "orbit_error",
        "timeseries_csv",
        args.orbit_error_csv,
        default_csv,
    )
    resample_mode = str(
        config_value(
            yaml_config,
            "orbit_error",
            "resample_mode",
            args.orbit_error_resample_mode,
            "cyclic",
        )
    )
    return OrbitErrorConfig(
        source=str(source),
        timeseries_csv=csv_path,
        resample_mode=resample_mode,
    )


def generate_orbit_prediction_error(
    times_s: np.ndarray,
    case_id: str,
    config: NonthermalErrorConfig,
) -> np.ndarray:
    times_s = np.asarray(times_s, dtype=float)
    orbit_config = config.orbit_error

    if orbit_config.source == "sentinel1_tle_vs_pod":
        if orbit_config.timeseries_csv is None:
            raise ValueError(
                "orbit_error.timeseries_csv is required when source=sentinel1_tle_vs_pod"
            )
        if not orbit_config.timeseries_csv.exists():
            raise FileNotFoundError(
                "Orbit error timeseries not found: "
                f"{orbit_config.timeseries_csv}. "
                "Run src/orbit/run_orbit_prediction_error.py first."
            )
        orbit_times_s, orbit_error_urad, _ = load_orbit_error_timeseries_csv(
            orbit_config.timeseries_csv
        )
        return resample_orbit_error_to_times(
            orbit_times_s,
            orbit_error_urad,
            times_s,
            mode=orbit_config.resample_mode,
        )

    rng = np.random.default_rng(_seed_for_case(config.seed, case_id))
    return np.repeat(
        rng.normal(0.0, config.orbit_prediction_bias_1sigma_urad, size=(1, 2)),
        len(times_s),
        axis=0,
    )


def generate_nonthermal_error(
    times_s: np.ndarray,
    case_id: str,
    config: NonthermalErrorConfig,
) -> np.ndarray:
    """
    Generate a simple non-thermal pointing error time series.

    Components represent orbit prediction error, attitude random error,
    alignment residual, and low-frequency drift in the PAT frame.
    """
    times_s = np.asarray(times_s, dtype=float)
    if config.drift_period_s <= 0.0:
        raise ValueError("drift_period_s must be positive")

    rng = np.random.default_rng(_seed_for_case(config.seed, case_id))
    orbit_prediction_error = generate_orbit_prediction_error(times_s, case_id, config)
    alignment_bias = rng.normal(
        0.0,
        config.alignment_bias_1sigma_urad,
        size=2,
    )
    attitude_random = rng.normal(
        0.0,
        config.attitude_random_1sigma_urad,
        size=(len(times_s), 2),
    )

    drift_phase = rng.uniform(0.0, 2.0 * np.pi, size=2)
    drift_argument = 2.0 * np.pi * times_s[:, None] / config.drift_period_s
    low_frequency_drift = config.drift_amplitude_urad * np.sin(
        drift_argument + drift_phase
    )

    return (
        orbit_prediction_error
        + alignment_bias[None, :]
        + attitude_random
        + low_frequency_drift
    )


def write_result_csv(
    path: Path,
    times_s: np.ndarray,
    theta_thermal_true_urad: np.ndarray,
    nonthermal_error_urad: np.ndarray,
    results_by_model: dict[str, np.ndarray],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)

        header = [
            "case_name",
            "time_s",
            "thermal_los_x_urad",
            "thermal_los_y_urad",
            "thermal_los_norm_urad",
            "nonthermal_error_x_urad",
            "nonthermal_error_y_urad",
            "nonthermal_error_norm_urad",
            "thermal_plus_nonthermal_error_x_urad",
            "thermal_plus_nonthermal_error_y_urad",
            "thermal_plus_nonthermal_error_norm_urad",
        ]
        for model_name in results_by_model:
            header.extend(f"{model_name}_{column}" for column in RESULT_COLUMNS)
        writer.writerow(header)

        for i, time_s in enumerate(times_s):
            row = [
                path.parent.name,
                time_s,
                theta_thermal_true_urad[i, 0],
                theta_thermal_true_urad[i, 1],
                np.linalg.norm(theta_thermal_true_urad[i]),
                nonthermal_error_urad[i, 0],
                nonthermal_error_urad[i, 1],
                np.linalg.norm(nonthermal_error_urad[i]),
                theta_thermal_true_urad[i, 0] + nonthermal_error_urad[i, 0],
                theta_thermal_true_urad[i, 1] + nonthermal_error_urad[i, 1],
                np.linalg.norm(theta_thermal_true_urad[i] + nonthermal_error_urad[i]),
            ]
            for result in results_by_model.values():
                row.extend(result[i])
            writer.writerow(row)


def write_summary_csv(path: Path, summary_rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id",
        "model",
        "uses_nonthermal_error",
        "success_rate",
        "mean_acquisition_time_s",
        "median_acquisition_time_s",
        "p95_acquisition_time_s",
        "mean_initial_error_urad",
        "p95_initial_error_urad",
        "mean_thermal_residual_urad",
        "p95_thermal_residual_urad",
        "mean_nonthermal_error_urad",
        "p95_nonthermal_error_urad",
        "mean_uncorrected_total_error_urad",
        "p95_uncorrected_total_error_urad",
    ]

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)


def plot_case(
    output_png: Path,
    times_s: np.ndarray,
    theta_thermal_true_urad: np.ndarray,
    nonthermal_error_urad: np.ndarray,
    results_by_model: dict[str, np.ndarray],
) -> None:
    output_png.parent.mkdir(parents=True, exist_ok=True)
    time_min = times_s / 60.0

    fig, axes = plt.subplots(4, 1, figsize=(11, 11), sharex=True)

    axes[0].plot(time_min, theta_thermal_true_urad[:, 0], label="thermal LOS x")
    axes[0].plot(time_min, theta_thermal_true_urad[:, 1], label="thermal LOS y")
    axes[0].plot(
        time_min,
        np.linalg.norm(theta_thermal_true_urad, axis=1),
        label="thermal LOS magnitude",
        linewidth=2,
    )
    axes[0].set_ylabel("Thermal LOS [urad]")
    axes[0].grid(True)
    axes[0].legend()

    axes[1].plot(
        time_min,
        np.linalg.norm(nonthermal_error_urad, axis=1),
        "o-",
        markersize=3,
        label="nonthermal error magnitude",
    )
    axes[1].plot(
        time_min,
        np.linalg.norm(theta_thermal_true_urad + nonthermal_error_urad, axis=1),
        "o-",
        markersize=3,
        label="thermal + nonthermal magnitude",
    )
    axes[1].set_ylabel("Error [urad]")
    axes[1].grid(True)
    axes[1].legend()

    for model_name, result in results_by_model.items():
        axes[2].plot(time_min, result[:, 1], "o-", markersize=3, label=model_name)
    axes[2].set_ylabel("Acq time [s]")
    axes[2].grid(True)
    axes[2].legend()

    for model_name, result in results_by_model.items():
        axes[3].plot(time_min, result[:, 7], "o-", markersize=3, label=model_name)
    axes[3].set_xlabel("Time [min]")
    axes[3].set_ylabel("Scan-center error [urad]")
    axes[3].grid(True)
    axes[3].legend()

    fig.suptitle("PAT coarse acquisition with Femap thermal LOS truth")
    fig.tight_layout()
    fig.savefig(output_png, dpi=200)
    plt.close(fig)


def run_one_case(
    los_csv: Path,
    output_dir: Path,
    los_prefix: str,
    config: CoarseAcquisitionConfig,
    nonthermal_config: NonthermalErrorConfig,
) -> list[dict[str, object]]:
    case_id = los_csv.parent.name
    times_s, theta_thermal_true = read_femap_los_csv(los_csv, los_prefix)
    nonthermal_error = generate_nonthermal_error(times_s, case_id, nonthermal_config)

    model_specs = {
        "no_correction": {
            "theta_hat": np.zeros_like(theta_thermal_true),
            "nonthermal": np.zeros_like(theta_thermal_true),
        },
        "thermal_truth_correction": {
            "theta_hat": theta_thermal_true.copy(),
            "nonthermal": np.zeros_like(theta_thermal_true),
        },
        "thermal_plus_nonthermal_no_correction": {
            "theta_hat": np.zeros_like(theta_thermal_true),
            "nonthermal": nonthermal_error,
        },
        "thermal_truth_correction_with_nonthermal": {
            "theta_hat": theta_thermal_true.copy(),
            "nonthermal": nonthermal_error,
        },
    }

    results_by_model = {
        model_name: evaluate_coarse_acquisition(
            theta_thermal_true_urad=theta_thermal_true,
            theta_correction_hat_urad=model_spec["theta_hat"],
            config=config,
            nonthermal_error_urad=model_spec["nonthermal"],
        )
        for model_name, model_spec in model_specs.items()
    }

    case_output_dir = output_dir / case_id
    write_result_csv(
        case_output_dir / "pat_acquisition_results.csv",
        times_s,
        theta_thermal_true,
        nonthermal_error,
        results_by_model,
    )
    plot_case(
        case_output_dir / "pat_acquisition_comparison.png",
        times_s,
        theta_thermal_true,
        nonthermal_error,
        results_by_model,
    )

    rows = []
    zero_error = np.zeros_like(theta_thermal_true)
    for model_name, result in results_by_model.items():
        model_nonthermal = model_specs[model_name]["nonthermal"]
        uses_nonthermal_error = not np.allclose(model_nonthermal, zero_error)
        uncorrected_total_error = theta_thermal_true + model_nonthermal
        row = {
            "case_id": case_id,
            "model": model_name,
            "uses_nonthermal_error": uses_nonthermal_error,
            "mean_nonthermal_error_urad": float(
                np.nanmean(np.linalg.norm(model_nonthermal, axis=1))
            ),
            "p95_nonthermal_error_urad": float(
                np.nanpercentile(np.linalg.norm(model_nonthermal, axis=1), 95)
            ),
            "mean_uncorrected_total_error_urad": float(
                np.nanmean(np.linalg.norm(uncorrected_total_error, axis=1))
            ),
            "p95_uncorrected_total_error_urad": float(
                np.nanpercentile(np.linalg.norm(uncorrected_total_error, axis=1), 95)
            ),
        }
        row.update(summarize_acquisition(result))
        rows.append(row)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Connect Femap-derived far-field LOS truth to a coarse PAT "
            "acquisition simulator."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--input-glob", default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--los-prefix", default=None)
    parser.add_argument("--max-range-urad", type=float, default=None)
    parser.add_argument("--step-urad", type=float, default=None)
    parser.add_argument("--detect-radius-urad", type=float, default=None)
    parser.add_argument("--dwell-time-s", type=float, default=None)
    parser.add_argument("--nonthermal-seed", type=int, default=None)
    parser.add_argument("--orbit-prediction-bias-1sigma-urad", type=float, default=None)
    parser.add_argument("--attitude-random-1sigma-urad", type=float, default=None)
    parser.add_argument("--alignment-bias-1sigma-urad", type=float, default=None)
    parser.add_argument("--drift-amplitude-urad", type=float, default=None)
    parser.add_argument("--drift-period-s", type=float, default=None)
    parser.add_argument("--orbit-error-source", default=None)
    parser.add_argument("--orbit-error-csv", type=Path, default=None)
    parser.add_argument("--orbit-error-resample-mode", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    yaml_config = load_yaml_config(args.config)

    input_glob = config_value(
        yaml_config, "input", "input_glob", args.input_glob, DEFAULT_INPUT_GLOB
    )
    output_dir = config_path_value(
        yaml_config, "input", "output_dir", args.output_dir, DEFAULT_OUTPUT_DIR
    )
    los_prefix = config_value(
        yaml_config, "input", "los_prefix", args.los_prefix, "far_field_los"
    )

    input_paths = sorted(REPO_ROOT.glob(input_glob))
    if not input_paths:
        raise FileNotFoundError(f"No LOS CSV files matched: {input_glob}")

    config = CoarseAcquisitionConfig(
        max_range_urad=config_value(
            yaml_config, "scan", "max_range_urad", args.max_range_urad, 1600.0
        ),
        step_urad=config_value(yaml_config, "scan", "step_urad", args.step_urad, 40.0),
        detect_radius_urad=config_value(
            yaml_config, "scan", "detect_radius_urad", args.detect_radius_urad, 25.0
        ),
        dwell_time_s=config_value(
            yaml_config, "scan", "dwell_time_s", args.dwell_time_s, 0.1
        ),
    )
    nonthermal_config = NonthermalErrorConfig(
        seed=config_value(
            yaml_config, "nonthermal_error", "seed", args.nonthermal_seed, 42
        ),
        orbit_prediction_bias_1sigma_urad=config_value(
            yaml_config,
            "nonthermal_error",
            "orbit_prediction_bias_1sigma_urad",
            args.orbit_prediction_bias_1sigma_urad,
            150.0,
        ),
        attitude_random_1sigma_urad=config_value(
            yaml_config,
            "nonthermal_error",
            "attitude_random_1sigma_urad",
            args.attitude_random_1sigma_urad,
            50.0,
        ),
        alignment_bias_1sigma_urad=config_value(
            yaml_config,
            "nonthermal_error",
            "alignment_bias_1sigma_urad",
            args.alignment_bias_1sigma_urad,
            50.0,
        ),
        drift_amplitude_urad=config_value(
            yaml_config,
            "nonthermal_error",
            "drift_amplitude_urad",
            args.drift_amplitude_urad,
            30.0,
        ),
        drift_period_s=config_value(
            yaml_config,
            "nonthermal_error",
            "drift_period_s",
            args.drift_period_s,
            900.0,
        ),
        orbit_error=_build_orbit_error_config(yaml_config, args),
    )

    summary_rows = []
    for los_csv in input_paths:
        summary_rows.extend(
            run_one_case(
                los_csv=los_csv,
                output_dir=output_dir,
                los_prefix=los_prefix,
                config=config,
                nonthermal_config=nonthermal_config,
            )
        )

    write_summary_csv(output_dir / "summary.csv", summary_rows)

    print(f"Processed {len(input_paths)} LOS CSV files")
    print(f"Config: {args.config}")
    print(f"Output: {output_dir}")
    for row in summary_rows:
        print(
            f"{row['case_id']} / {row['model']}: "
            f"success={row['success_rate'] * 100:.1f}%, "
            f"mean_tacq={row['mean_acquisition_time_s']:.2f}s, "
            f"p95_tacq={row['p95_acquisition_time_s']:.2f}s"
        )


if __name__ == "__main__":
    main()
