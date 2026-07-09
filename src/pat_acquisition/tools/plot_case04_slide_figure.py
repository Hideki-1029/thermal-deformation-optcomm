"""
One-off slide figures for PAT coarse acquisition comparison.

Reads pat_acquisition_results.csv from femap_los_truth and fourier_los_model,
then plots acquisition time and scan-center error with a reduced legend (3 curves).

This script is intentionally separate from run_pat_with_femap_los.py.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
PAT_RESULTS_ROOT = REPO_ROOT / "results" / "pat_acquisition"
TRUTH_RESULTS_ROOT = PAT_RESULTS_ROOT / "femap_los_truth"
FOURIER_RESULTS_ROOT = PAT_RESULTS_ROOT / "fourier_los_model"
SLIDE_OUTPUT_ROOT = PAT_RESULTS_ROOT / "slide_figures"

CASE_PRESETS: dict[str, dict[str, str]] = {
    "03": {
        "case_dir": "03_LTAN06_800km_1213COLD_MZ_ALL_HEAT_MZ_0p5",
        "title": "Case 03: PAT coarse acquisition (MZ, ALL HEAT 0.5)",
        "output_name": "pat_acquisition_slide_case03.png",
    },
    "04": {
        "case_dir": "04_LTAN06_800km_1213COLD_MY_ALL_HEAT_MY_0p5",
        "title": "Case 04: PAT coarse acquisition (MY, ALL HEAT 0.5)",
        "output_name": "pat_acquisition_slide_case04.png",
    },
}

# (model_key, label, which results folder provides the column)
SLIDE_MODELS: tuple[tuple[str, str, str], ...] = (
    (
        "thermal_plus_nonthermal_no_correction",
        "No correction",
        "truth",
    ),
    (
        "fourier_ff_correction_with_nonthermal",
        "Fourier lightweight model",
        "fourier",
    ),
    (
        "thermal_truth_correction_with_nonthermal",
        "Truth correction (ideal)",
        "truth",
    ),
)


def resolve_case_paths(case_id: str) -> tuple[Path, Path, Path, str]:
    if case_id not in CASE_PRESETS:
        known = ", ".join(sorted(CASE_PRESETS))
        raise ValueError(f"Unknown case id '{case_id}'. Choose from: {known}")

    preset = CASE_PRESETS[case_id]
    case_dir_name = preset["case_dir"]
    truth_csv = TRUTH_RESULTS_ROOT / case_dir_name / "pat_acquisition_results.csv"
    fourier_csv = FOURIER_RESULTS_ROOT / case_dir_name / "pat_acquisition_results.csv"
    output_png = SLIDE_OUTPUT_ROOT / case_dir_name / preset["output_name"]
    return truth_csv, fourier_csv, output_png, preset["title"]


def _load_model_series(
    path: Path,
    model_key: str,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"No rows found in {path}")

    required = {
        "time_s",
        f"{model_key}_acquisition_time_s",
        f"{model_key}_pointing_error_norm_urad",
    }
    missing = required.difference(reader.fieldnames or [])
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")

    times_s = np.array([float(row["time_s"]) for row in rows], dtype=float)
    series = {
        "acquisition_time_s": np.array(
            [float(row[f"{model_key}_acquisition_time_s"]) for row in rows],
            dtype=float,
        ),
        "scan_center_error_urad": np.array(
            [float(row[f"{model_key}_pointing_error_norm_urad"]) for row in rows],
            dtype=float,
        ),
    }
    return times_s, series


def load_slide_series(
    truth_csv: Path,
    fourier_csv: Path,
) -> tuple[np.ndarray, dict[str, dict[str, np.ndarray]]]:
    series: dict[str, dict[str, np.ndarray]] = {}
    times_s: np.ndarray | None = None

    for model_key, _, source in SLIDE_MODELS:
        csv_path = truth_csv if source == "truth" else fourier_csv
        model_times, model_series = _load_model_series(csv_path, model_key)
        if times_s is None:
            times_s = model_times
        elif len(model_times) != len(times_s) or not np.allclose(model_times, times_s):
            raise ValueError(
                f"time_s mismatch for model '{model_key}' between "
                f"{csv_path} and previously loaded series"
            )
        series[model_key] = model_series

    if times_s is None:
        raise ValueError("No slide models were loaded")
    return times_s, series


def plot_slide_figure(
    output_png: Path,
    times_s: np.ndarray,
    series: dict[str, dict[str, np.ndarray]],
    title: str,
) -> None:
    output_png.parent.mkdir(parents=True, exist_ok=True)
    time_min = times_s / 60.0

    plt.rcParams.update(
        {
            "font.size": 13,
            "axes.titlesize": 14,
            "axes.labelsize": 13,
            "legend.fontsize": 12,
            "lines.linewidth": 2.0,
            "lines.markersize": 4.0,
        }
    )

    colors = ["#1f77b4", "#d62728", "#2ca02c"]
    fig, axes = plt.subplots(2, 1, figsize=(12, 6.5), sharex=True)

    for ax, metric_key, ylabel in (
        (axes[0], "acquisition_time_s", "Acquisition time [s]"),
        (axes[1], "scan_center_error_urad", "Scan-center error [urad]"),
    ):
        for (model_key, label, _), color in zip(SLIDE_MODELS, colors, strict=True):
            ax.plot(
                time_min,
                series[model_key][metric_key],
                "o-",
                color=color,
                label=label,
                alpha=0.95,
            )
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.35)
        ax.set_title(ylabel, loc="left", fontsize=14, pad=8)

    axes[1].set_xlabel("Time [min]")
    axes[0].legend(loc="upper right", framealpha=0.95)
    fig.suptitle(title, fontsize=15, y=0.98)
    fig.tight_layout()
    fig.savefig(output_png, dpi=220, bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create slide-friendly PAT figures for selected cases."
    )
    parser.add_argument(
        "--case-id",
        action="append",
        choices=sorted(CASE_PRESETS),
        help="Case preset to plot. Repeat for multiple cases. Default: 04.",
    )
    parser.add_argument("--truth-csv", type=Path, default=None)
    parser.add_argument("--fourier-csv", type=Path, default=None)
    parser.add_argument("--output-png", type=Path, default=None)
    parser.add_argument("--title", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    case_ids = args.case_id or ["04"]

    jobs: list[tuple[Path, Path, Path, str, str]] = []
    custom = (
        args.truth_csv is not None
        or args.fourier_csv is not None
        or args.output_png is not None
        or args.title is not None
    )
    if custom:
        if len(case_ids) != 1:
            raise ValueError("Custom paths/title require exactly one --case-id")
        default_truth, default_fourier, default_output, default_title = resolve_case_paths(
            case_ids[0]
        )
        jobs.append(
            (
                args.truth_csv or default_truth,
                args.fourier_csv or default_fourier,
                args.output_png or default_output,
                args.title or default_title,
                case_ids[0],
            )
        )
    else:
        for case_id in case_ids:
            truth_csv, fourier_csv, output_png, title = resolve_case_paths(case_id)
            jobs.append((truth_csv, fourier_csv, output_png, title, case_id))

    for truth_csv, fourier_csv, output_png, title, case_id in jobs:
        for path in (truth_csv, fourier_csv):
            if not path.exists():
                raise FileNotFoundError(
                    f"Input CSV not found: {path}. "
                    "Run run_pat_with_femap_los.py first."
                )

        times_s, series = load_slide_series(truth_csv, fourier_csv)
        plot_slide_figure(output_png, times_s, series, title)

        print(f"Case {case_id}")
        print(f"  Truth  : {truth_csv}")
        print(f"  Fourier: {fourier_csv}")
        print(f"  Output : {output_png}")


if __name__ == "__main__":
    main()
