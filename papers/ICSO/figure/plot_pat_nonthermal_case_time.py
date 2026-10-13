"""Per-case mean acquisition time with nonthermal pointing error.

Fourteen COLD baseline-surface cases. Times are the published case means:
the mean acquisition time is the mean over successful trials. Cases whose
no-correction success rate is below 100% are marked on the axis.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SUMMARY = (
    ROOT
    / "results"
    / "pat_acquisition"
    / "sunface_deltaT_bcase_los_model"
    / "pat"
    / "summary.csv"
)
OUT = Path(__file__).resolve().parent / "pat_nonthermal_case_acquisition_time.png"

CASES = [
    "04",
    "05",
    "06",
    "08",
    "09",
    "13",
    "14",
    "15",
    "16",
    "17",
    "18",
    "19",
    "20",
    "21",
]
NO = "thermal_plus_nonthermal_no_correction"
HI = "bcase_correction_with_nonthermal"
RED = "#D03B46"
GREEN = "#239571"


def main() -> None:
    frame = pd.read_csv(SUMMARY)
    frame["num"] = frame["case_id"].str.slice(0, 2)
    sub = frame[frame["num"].isin(CASES) & frame["model"].isin([NO, HI])].copy()
    no = sub[sub["model"] == NO].set_index("num").loc[CASES]
    hi = sub[sub["model"] == HI].set_index("num").loc[CASES]
    print(
        f"no mean={no.mean_acquisition_time_s.mean():.3f} "
        f"succ={no.success_rate.mean():.4f}"
    )
    print(
        f"hi mean={hi.mean_acquisition_time_s.mean():.3f} "
        f"succ={hi.success_rate.mean():.4f}"
    )

    labels = [
        f"{case}*" if no.loc[case, "success_rate"] < 0.999 else case for case in CASES
    ]
    x = np.arange(len(CASES))
    width = 0.38

    plt.rcParams.update(
        {
            "font.family": "Arial",
            "axes.labelsize": 20,
            "xtick.labelsize": 15,
            "ytick.labelsize": 16,
            "legend.fontsize": 16,
            "axes.linewidth": 1.1,
        }
    )
    fig, ax = plt.subplots(figsize=(11.2, 5.5))
    ax.bar(
        x - width / 2,
        no["mean_acquisition_time_s"],
        width,
        label="No correction",
        color=RED,
        zorder=2,
    )
    ax.bar(
        x + width / 2,
        hi["mean_acquisition_time_s"],
        width,
        label="Hierarchical model",
        color=GREEN,
        zorder=2,
    )
    ax.set_ylim(0, 48)
    ax.set_ylabel("Mean acquisition time [s]")
    ax.set_xlabel("Case ID")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.grid(True, axis="y", color="#E6EBEF", linewidth=0.8, zorder=0)
    ax.tick_params(length=0)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=2,
        borderaxespad=0.0,
    )
    fig.subplots_adjust(top=0.86, left=0.08, right=0.98, bottom=0.20)
    fig.text(
        0.08,
        0.02,
        "* No-correction mean is over successful trials (Cases 08, 16, 18, 19).",
        fontsize=13,
        color="#5C6670",
        ha="left",
    )
    fig.savefig(OUT, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
