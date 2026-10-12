"""Overlay far-field LOS Y for MY sun-face cases with different dissipation.

Cases 15, 14, 13, and 04 share the orbit and the MY sun face. Dissipation
changes from STT/LCT only, to added PCDU, added PROP, and both.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
FEMAP = ROOT / "results" / "femap_deformation"
OUT = Path(__file__).resolve().parent / "my_cases_04_13_14_15_far_field_los_y.png"

# Drawn back to front so each near-duplicate pair stays visible.
CASES = (
    ("15", "15_LTAN06_800km_1213COLD_MY_STTLCT_HEAT_MY_0p5", "15  STT/LCT only", "#082B52", "-"),
    ("14", "14_LTAN06_800km_1213COLD_MY_STTLCT_PCDU_HEAT_MY_0p5", "14  STT/LCT + PCDU", "#1B74AA", "--"),
    ("13", "13_LTAN06_800km_1213COLD_MY_STTLCT_PROP_HEAT_MY_0p5", "13  STT/LCT + PROP", "#EC9427", "-"),
    ("04", "04_LTAN06_800km_1213COLD_MY_ALL_HEAT_MY_0p5", "04  STT/LCT + PROP + PCDU", "#D03B46", "--"),
)


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 15,
            "axes.labelsize": 17,
            "xtick.labelsize": 13,
            "ytick.labelsize": 13,
            "legend.fontsize": 13,
            "axes.linewidth": 1.1,
        }
    )
    fig, ax = plt.subplots(figsize=(10.4, 5.4))
    ax.axhline(0.0, color="#B9C3CD", linewidth=1.0, zorder=0)
    for _number, dirname, label, color, style in CASES:
        los = pd.read_csv(FEMAP / dirname / "los_angles.csv").drop_duplicates(
            "time_min", keep="first"
        )
        ax.plot(
            los["time_min"],
            los["far_field_los_angle_y_urad"],
            linestyle=style,
            color=color,
            linewidth=2.2,
            label=label,
        )
    ax.set_xlim(0.0, 310.0)
    ax.set_xlabel("Time [min]")
    ax.set_ylabel("Far-field LOS, Y (MY–PY axis) [µrad]")
    ax.grid(True, color="#E6EBEF", linewidth=0.8)
    ax.tick_params(length=0)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(frameon=False, loc="center left", bbox_to_anchor=(1.02, 0.55))
    fig.tight_layout()
    fig.savefig(OUT, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
