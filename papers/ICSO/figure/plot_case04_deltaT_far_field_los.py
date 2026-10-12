"""Case 04 slide figure: MY−PY center ΔT beside far-field LOS Y.

Reads the existing Femap exports for
04_LTAN06_800km_1213COLD_MY_ALL_HEAT_MY_0p5. Does not rerun Thermal Desktop
or Femap. The Y component is the far-field LOS that follows this temperature
difference (body axis from MY toward PY).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
CASE = ROOT / "results" / "femap_deformation" / "04_LTAN06_800km_1213COLD_MY_ALL_HEAT_MY_0p5"
OUT = Path(__file__).resolve().parent / "case04_deltaT_far_field_los_y.png"

BLUE = "#1B74AA"


def panel_center_c(temp: pd.DataFrame, probe: str) -> pd.DataFrame:
    series = temp.loc[temp["probe_name"] == probe, ["time_s", "temperature_c"]]
    series = series.drop_duplicates("time_s", keep="first")
    return series.sort_values("time_s")


def main() -> None:
    los = pd.read_csv(CASE / "los_angles.csv").drop_duplicates("time_min", keep="first")
    temp = pd.read_csv(CASE / "default_surface_9points_temperatures.csv")
    my = panel_center_c(temp, "panel_my_center")
    py = panel_center_c(temp, "panel_py_center")
    if len(my) != len(py) or not my["time_s"].reset_index(drop=True).equals(
        py["time_s"].reset_index(drop=True)
    ):
        raise ValueError("MY and PY center temperatures are not on the same times")

    time_min = los["time_min"].to_numpy()
    los_y = los["far_field_los_angle_y_urad"].to_numpy()
    delta_t = (my["temperature_c"].to_numpy() - py["temperature_c"].to_numpy())
    temp_min = my["time_s"].to_numpy() / 60.0

    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 16,
            "axes.labelsize": 18,
            "axes.titlesize": 20,
            "xtick.labelsize": 14,
            "ytick.labelsize": 14,
            "axes.linewidth": 1.1,
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.7), sharex=True)
    series = (
        (axes[0], temp_min, delta_t, "Temperature difference [°C]"),
        (axes[1], time_min, los_y, "Y (MY–PY axis) [µrad]"),
    )
    for ax, x, y, ylabel in series:
        ax.axhline(0.0, color="#B9C3CD", linewidth=1.0, zorder=0)
        ax.plot(x, y, color=BLUE, linewidth=2.6)
        ax.set_ylabel(ylabel)
        ax.set_xlabel("Time [min]")
        ax.set_xlim(0.0, 310.0)
        ax.grid(True, color="#E6EBEF", linewidth=0.8)
        ax.tick_params(length=0)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)

    fig.tight_layout(w_pad=3.0)
    fig.savefig(OUT, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
