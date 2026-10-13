"""Grouped bars: raw dominant-axis RMS vs leave-one-case-out prediction RMSE.

Uses the saved hierarchical-model metrics and the lightweight dataset.
Raw RMS is the dominant-axis RMS of the far-field LOS. Prediction RMSE is
the nested leave-one-case-out test-orbit error (model b_pred_loo_a_shared).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[3]
METRICS = (
    ROOT
    / "results"
    / "pat_acquisition"
    / "sunface_deltaT_bcase_los_model"
    / "bcase_los_metrics.csv"
)
DATASET = (
    ROOT
    / "results"
    / "pat_acquisition"
    / "lightweight_dataset"
    / "lightweight_dataset_all.csv"
)
OUT = Path(__file__).resolve().parent / "loo_raw_vs_prediction_rmse.png"

RAW = "#9AA3AD"
PRED = "#1B74AA"
NAVY = "#082B52"


def raw_rms_by_case(frame: pd.DataFrame) -> pd.Series:
    rows: dict[str, float] = {}
    for case_id, group in frame.groupby("case_id", sort=False):
        face = str(group["sun_face"].iloc[0])
        column = (
            "far_field_los_angle_x_urad"
            if face in {"MX", "PX"}
            else "far_field_los_angle_y_urad"
        )
        values = group[column].to_numpy(dtype=float)
        rows[str(case_id)] = float(np.sqrt(np.mean(values**2)))
    return pd.Series(rows, name="raw_rms")


def main() -> None:
    metrics = pd.read_csv(METRICS)
    loo = metrics.loc[
        metrics["model"] == "b_pred_loo_a_shared",
        ["case_id", "sun_face", "rmse_dom_test_urad"],
    ].copy()
    dataset = pd.read_csv(
        DATASET,
        usecols=[
            "case_id",
            "far_field_los_angle_x_urad",
            "far_field_los_angle_y_urad",
        ],
    )
    face = loo.set_index("case_id")["sun_face"]
    dataset = dataset.join(face, on="case_id")
    dataset = dataset.dropna(subset=["sun_face"])
    loo["raw_rms"] = loo["case_id"].map(raw_rms_by_case(dataset))
    loo["number"] = loo["case_id"].str.slice(0, 2).astype(int)
    loo = loo.sort_values("number").reset_index(drop=True)

    raw_median = float(np.median(loo["raw_rms"]))
    rmse_median = float(np.median(loo["rmse_dom_test_urad"]))
    print(f"n={len(loo)} raw_median={raw_median:.1f} rmse_median={rmse_median:.2f}")

    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 18,
            "axes.labelsize": 22,
            "xtick.labelsize": 15,
            "ytick.labelsize": 18,
            "legend.fontsize": 18,
            "axes.linewidth": 1.1,
        }
    )
    fig, ax = plt.subplots(figsize=(11.6, 5.3))
    x = np.arange(len(loo))
    width = 0.38
    ax.bar(
        x - width / 2,
        loo["raw_rms"],
        width,
        label="Raw RMS",
        color=RAW,
        zorder=2,
    )
    ax.bar(
        x + width / 2,
        loo["rmse_dom_test_urad"],
        width,
        label="Prediction RMSE",
        color=PRED,
        zorder=2,
    )
    ax.axhline(4.9, color=PRED, linewidth=1.3, linestyle=":", zorder=1)
    ax.set_yscale("log")
    ax.set_ylim(0.8, 3000)
    ax.set_yticks([1, 10, 100, 1000])
    ax.set_yticklabels(["1", "10", "100", "1000"])
    ax.set_ylabel("Error [µrad]")
    ax.set_xlabel("Case ID")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{n:02d}" for n in loo["number"]])
    ax.grid(True, axis="y", which="major", color="#E6EBEF", linewidth=0.8, zorder=0)
    ax.tick_params(length=0)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    median_line = Line2D([0], [0], color=PRED, lw=1.6, ls=":", label="Median 4.9")
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles + [median_line],
        labels + ["Median 4.9"],
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=3,
        borderaxespad=0.0,
    )
    fig.subplots_adjust(top=0.86, left=0.08, right=0.98, bottom=0.14)
    fig.savefig(OUT, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
