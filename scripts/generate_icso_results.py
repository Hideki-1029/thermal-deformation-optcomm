import importlib.util
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
FEMAP_LOS_CSV = (
    REPO_ROOT
    / "results"
    / "femap_deformation"
    / "260629_1505_translation_rotation_stt_lct_los_angles.csv"
)
PAT_SCRIPT = REPO_ROOT / "src" / "pat_acquisition" / "test_thermo_PAT_system_1.py"
OUTPUT_DIR = REPO_ROOT / "results" / "icso"
FIGURE_DIR = REPO_ROOT / "papers" / "ICSO" / "figure"


def load_pat_module():
    spec = importlib.util.spec_from_file_location("thermo_pat", PAT_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_output_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def save_femap_summary():
    df = pd.read_csv(FEMAP_LOS_CSV)
    summary_columns = [
        "centerline_angle_magnitude_urad",
        "stt_rotation_angle_magnitude_urad",
        "lct_rotation_angle_magnitude_urad",
        "relative_rotation_angle_magnitude_urad",
        "global_los_angle_magnitude_urad",
        "stt_relative_los_angle_magnitude_urad",
    ]
    summary = df[summary_columns].describe().loc[["mean", "min", "max", "std"]]
    summary.to_csv(OUTPUT_DIR / "femap_los_summary.csv")

    x = df["case_index"]
    fig, axes = plt.subplots(2, 1, figsize=(8.0, 6.0), sharex=True)
    axes[0].plot(x, df["stt_relative_los_angle_x_urad"], label="x")
    axes[0].plot(x, df["stt_relative_los_angle_y_urad"], label="y")
    axes[0].set_ylabel("STT-relative LOS [urad]")
    axes[0].set_title("Femap-derived STT-relative LOS bias")
    axes[0].grid(True)
    axes[0].legend()

    axes[1].plot(x, df["centerline_angle_magnitude_urad"], label="centerline tilt")
    axes[1].plot(x, df["relative_rotation_angle_magnitude_urad"], label="LCT-STT rotation")
    axes[1].plot(
        x,
        df["stt_relative_los_angle_magnitude_urad"],
        linewidth=2,
        label="STT-relative LOS",
    )
    axes[1].set_xlabel("Femap case index [-]")
    axes[1].set_ylabel("Angle magnitude [urad]")
    axes[1].grid(True)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "femap_stt_relative_los_angles.png", dpi=220)
    plt.close(fig)

    return summary


def summarize_pat_results(results):
    rows = []
    for name, data in results.items():
        success = data[:, 0].astype(bool)
        acq_time = data[:, 1]
        initial_error = data[:, 3]
        thermal_residual = data[:, 5]
        scan_idx = data[:, 6]
        rows.append(
            {
                "case": name,
                "success_rate_percent": np.mean(success) * 100.0,
                "mean_acquisition_time_s": np.nanmean(acq_time),
                "median_acquisition_time_s": np.nanmedian(acq_time),
                "p95_acquisition_time_s": np.nanpercentile(acq_time, 95),
                "mean_initial_error_urad": np.nanmean(initial_error),
                "p95_initial_error_urad": np.nanpercentile(initial_error, 95),
                "mean_thermal_residual_urad": np.nanmean(thermal_residual),
                "p95_thermal_residual_urad": np.nanpercentile(thermal_residual, 95),
                "mean_scan_index": np.nanmean(scan_idx),
            }
        )
    return pd.DataFrame(rows)


def save_pat_summary_and_figures():
    pat = load_pat_module()
    t, theta_true, model_outputs, results, _ = pat.run_simulation()
    time_min = t / 60.0

    summary = summarize_pat_results(results)
    summary.to_csv(OUTPUT_DIR / "pat_performance_summary.csv", index=False)

    fig, axes = plt.subplots(2, 1, figsize=(8.0, 6.0), sharex=True)
    axes[0].plot(time_min, theta_true[:, 0], label="truth x", linewidth=2)
    axes[0].plot(time_min, model_outputs["fourier_ff"][:, 0], "--", label="Fourier FF x")
    axes[0].plot(
        time_min,
        model_outputs["ff_plus_adaptive"][:, 0],
        "-.",
        label="FF + adaptive x",
    )
    axes[0].set_ylabel("LOS bias x [urad]")
    axes[0].set_title("Thermal LOS bias prediction used for coarse acquisition")
    axes[0].grid(True)
    axes[0].legend()

    axes[1].plot(time_min, theta_true[:, 1], label="truth y", linewidth=2)
    axes[1].plot(time_min, model_outputs["fourier_ff"][:, 1], "--", label="Fourier FF y")
    axes[1].plot(
        time_min,
        model_outputs["ff_plus_adaptive"][:, 1],
        "-.",
        label="FF + adaptive y",
    )
    axes[1].set_xlabel("Time [min]")
    axes[1].set_ylabel("LOS bias y [urad]")
    axes[1].grid(True)
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "thermal_los_prediction_comparison.png", dpi=220)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(8.0, 6.0), sharex=True)
    for name, data in results.items():
        axes[0].plot(time_min, data[:, 1], marker="o", markersize=2.5, linewidth=1.0, label=name)
        axes[1].plot(time_min, data[:, 3], linewidth=1.0, label=name)
    axes[0].set_ylabel("Acquisition time [s]")
    axes[0].set_title("Coarse-acquisition performance comparison")
    axes[0].grid(True)
    axes[0].legend(ncol=2, fontsize=8)
    axes[1].set_xlabel("Time [min]")
    axes[1].set_ylabel("Initial pointing error [urad]")
    axes[1].grid(True)
    axes[1].legend(ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "coarse_acquisition_performance_comparison.png", dpi=220)
    plt.close(fig)

    labels = summary["case"].tolist()
    acq_data = [results[name][:, 1][~np.isnan(results[name][:, 1])] for name in labels]
    residual_data = [results[name][:, 5][~np.isnan(results[name][:, 5])] for name in labels]

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.2))
    axes[0].boxplot(acq_data, tick_labels=labels, showfliers=False)
    axes[0].set_ylabel("Acquisition time [s]")
    axes[0].set_title("Acquisition time distribution")
    axes[0].grid(True, axis="y")
    axes[0].tick_params(axis="x", rotation=25)

    axes[1].boxplot(residual_data, tick_labels=labels, showfliers=False)
    axes[1].set_ylabel("Thermal residual [urad]")
    axes[1].set_title("Thermal residual distribution")
    axes[1].grid(True, axis="y")
    axes[1].tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "icso_performance_distributions.png", dpi=220)
    plt.close(fig)

    return summary


def main():
    ensure_output_dirs()
    femap_summary = save_femap_summary()
    pat_summary = save_pat_summary_and_figures()

    print("Generated ICSO result assets.")
    print(f"Femap summary: {OUTPUT_DIR / 'femap_los_summary.csv'}")
    print(f"PAT summary  : {OUTPUT_DIR / 'pat_performance_summary.csv'}")
    print(f"Figures      : {FIGURE_DIR}")
    print()
    print("Femap LOS summary:")
    print(femap_summary.to_string())
    print()
    print("PAT performance summary:")
    print(pat_summary.to_string(index=False))


if __name__ == "__main__":
    main()
