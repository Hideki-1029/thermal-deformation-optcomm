from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from pat_acquisition_simulator import (
    CoarseAcquisitionConfig,
    evaluate_coarse_acquisition,
    summarize_acquisition,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_GLOB = "results/femap_deformation/*/los_angles.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "pat_acquisition" / "femap_los_truth"

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


def write_result_csv(
    path: Path,
    times_s: np.ndarray,
    theta_thermal_true_urad: np.ndarray,
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
            ]
            for result in results_by_model.values():
                row.extend(result[i])
            writer.writerow(row)


def write_summary_csv(path: Path, summary_rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id",
        "model",
        "success_rate",
        "mean_acquisition_time_s",
        "median_acquisition_time_s",
        "p95_acquisition_time_s",
        "mean_initial_error_urad",
        "p95_initial_error_urad",
        "mean_thermal_residual_urad",
        "p95_thermal_residual_urad",
    ]

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)


def plot_case(
    output_png: Path,
    times_s: np.ndarray,
    theta_thermal_true_urad: np.ndarray,
    results_by_model: dict[str, np.ndarray],
) -> None:
    output_png.parent.mkdir(parents=True, exist_ok=True)
    time_min = times_s / 60.0

    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)

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

    for model_name, result in results_by_model.items():
        axes[1].plot(time_min, result[:, 1], "o-", markersize=3, label=model_name)
    axes[1].set_ylabel("Acq time [s]")
    axes[1].grid(True)
    axes[1].legend()

    for model_name, result in results_by_model.items():
        axes[2].plot(time_min, result[:, 7], "o-", markersize=3, label=model_name)
    axes[2].set_xlabel("Time [min]")
    axes[2].set_ylabel("Scan-center error [urad]")
    axes[2].grid(True)
    axes[2].legend()

    fig.suptitle("PAT coarse acquisition with Femap thermal LOS truth")
    fig.tight_layout()
    fig.savefig(output_png, dpi=200)
    plt.close(fig)


def run_one_case(
    los_csv: Path,
    output_dir: Path,
    los_prefix: str,
    config: CoarseAcquisitionConfig,
) -> list[dict[str, object]]:
    case_id = los_csv.parent.name
    times_s, theta_thermal_true = read_femap_los_csv(los_csv, los_prefix)

    correction_models = {
        "no_correction": np.zeros_like(theta_thermal_true),
        "thermal_truth_correction": theta_thermal_true.copy(),
    }

    results_by_model = {
        model_name: evaluate_coarse_acquisition(
            theta_thermal_true_urad=theta_thermal_true,
            theta_correction_hat_urad=theta_hat,
            config=config,
        )
        for model_name, theta_hat in correction_models.items()
    }

    case_output_dir = output_dir / case_id
    write_result_csv(
        case_output_dir / "pat_acquisition_results.csv",
        times_s,
        theta_thermal_true,
        results_by_model,
    )
    plot_case(
        case_output_dir / "pat_acquisition_comparison.png",
        times_s,
        theta_thermal_true,
        results_by_model,
    )

    rows = []
    for model_name, result in results_by_model.items():
        row = {"case_id": case_id, "model": model_name}
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
    parser.add_argument("--input-glob", default=DEFAULT_INPUT_GLOB)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--los-prefix", default="far_field_los")
    parser.add_argument("--max-range-urad", type=float, default=1600.0)
    parser.add_argument("--step-urad", type=float, default=40.0)
    parser.add_argument("--detect-radius-urad", type=float, default=25.0)
    parser.add_argument("--dwell-time-s", type=float, default=0.1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_paths = sorted(REPO_ROOT.glob(args.input_glob))
    if not input_paths:
        raise FileNotFoundError(f"No LOS CSV files matched: {args.input_glob}")

    config = CoarseAcquisitionConfig(
        max_range_urad=args.max_range_urad,
        step_urad=args.step_urad,
        detect_radius_urad=args.detect_radius_urad,
        dwell_time_s=args.dwell_time_s,
    )

    summary_rows = []
    for los_csv in input_paths:
        summary_rows.extend(
            run_one_case(
                los_csv=los_csv,
                output_dir=args.output_dir,
                los_prefix=args.los_prefix,
                config=config,
            )
        )

    write_summary_csv(args.output_dir / "summary.csv", summary_rows)

    print(f"Processed {len(input_paths)} LOS CSV files")
    print(f"Output: {args.output_dir}")
    for row in summary_rows:
        print(
            f"{row['case_id']} / {row['model']}: "
            f"success={row['success_rate'] * 100:.1f}%, "
            f"mean_tacq={row['mean_acquisition_time_s']:.2f}s, "
            f"p95_tacq={row['p95_acquisition_time_s']:.2f}s"
        )


if __name__ == "__main__":
    main()
