"""
One-off slide figures for PAT coarse acquisition comparison.

Reads existing pat_acquisition_results.csv and plots only acquisition time
and scan-center error with a reduced legend (3 curves).

This script is intentionally separate from run_pat_with_femap_los.py.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = REPO_ROOT / "results" / "pat_acquisition" / "femap_los_truth"

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

SLIDE_MODELS: tuple[tuple[str, str], ...] = (
    (
        "thermal_plus_nonthermal_no_correction",
        "No correction",
    ),
    (
        "fourier_ff_correction_with_nonthermal",
        "Fourier lightweight model",
    ),
    (
        "thermal_truth_correction_with_nonthermal",
        "Truth correction (ideal)",
    ),
)


def resolve_case_paths(case_id: str) -> tuple[Path, Path, str]:
    if case_id not in CASE_PRESETS:
        known = ", ".join(sorted(CASE_PRESETS))
        raise ValueError(f"Unknown case id '{case_id}'. Choose from: {known}")

    preset = CASE_PRESETS[case_id]
    case_dir = RESULTS_ROOT / preset["case_dir"]
    input_csv = case_dir / "pat_acquisition_results.csv"
    output_png = case_dir / preset["output_name"]
    return input_csv, output_png, preset["title"]


def load_results_csv(path: Path) -> tuple[np.ndarray, dict[str, dict[str, np.ndarray]]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"No rows found in {path}")

    times_s = np.array([float(row["time_s"]) for row in rows], dtype=float)
    series: dict[str, dict[str, np.ndarray]] = {}

    for model_key, _ in SLIDE_MODELS:
        tacq = np.array(
            [float(row[f"{model_key}_acquisition_time_s"]) for row in rows],
            dtype=float,
        )
        scan_error = np.array(
            [float(row[f"{model_key}_pointing_error_norm_urad"]) for row in rows],
            dtype=float,
        )
        series[model_key] = {
            "acquisition_time_s": tacq,
            "scan_center_error_urad": scan_error,
        }

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
        for (model_key, label), color in zip(SLIDE_MODELS, colors, strict=True):
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
    parser.add_argument("--input-csv", type=Path, default=None)
    parser.add_argument("--output-png", type=Path, default=None)
    parser.add_argument("--title", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    case_ids = args.case_id or ["04"]

    jobs: list[tuple[Path, Path, str, str]] = []
    if args.input_csv is not None or args.output_png is not None or args.title is not None:
        if len(case_ids) != 1:
            raise ValueError("Custom paths/title require exactly one --case-id")
        default_input, default_output, default_title = resolve_case_paths(case_ids[0])
        jobs.append(
            (
                args.input_csv or default_input,
                args.output_png or default_output,
                args.title or default_title,
                case_ids[0],
            )
        )
    else:
        for case_id in case_ids:
            input_csv, output_png, title = resolve_case_paths(case_id)
            jobs.append((input_csv, output_png, title, case_id))

    for input_csv, output_png, title, case_id in jobs:
        if not input_csv.exists():
            raise FileNotFoundError(
                f"Input CSV not found: {input_csv}. "
                "Run run_pat_with_femap_los.py first."
            )

        times_s, series = load_results_csv(input_csv)
        plot_slide_figure(output_png, times_s, series, title)

        print(f"Case {case_id}")
        print(f"  Input : {input_csv}")
        print(f"  Output: {output_png}")


if __name__ == "__main__":
    main()
