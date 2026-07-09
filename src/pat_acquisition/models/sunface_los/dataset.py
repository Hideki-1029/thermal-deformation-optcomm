from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_DATASET = (
    Path(__file__).resolve().parents[4]
    / "results"
    / "pat_acquisition"
    / "lightweight_dataset"
    / "lightweight_dataset_all.csv"
)
DEFAULT_OUTPUT_ROOT = (
    Path(__file__).resolve().parents[4]
    / "results"
    / "pat_acquisition"
    / "sunface_los_model"
)

CASE_PRESETS = {
    "04": "04_LTAN06_800km_1213COLD_MY_ALL_HEAT_MY_0p5",
    "05": "05_LTAN06_800km_1213COLD_PX_ALL_HEAT_PX_0p5",
}


def short_case_tag(case_id: str) -> str:
    prefix = str(case_id).split("_", 1)[0]
    return f"case{prefix}" if prefix.isdigit() else "case"


def load_case_frame(dataset_path: Path, case_id: str) -> pd.DataFrame:
    df = pd.read_csv(dataset_path)
    case_df = df[df["case_id"].astype(str) == case_id].copy()
    if case_df.empty:
        raise ValueError(f"No rows found for case_id={case_id!r} in {dataset_path}")

    case_df = case_df.sort_values("time_s")
    case_df = case_df.groupby("time_s", as_index=False).mean(numeric_only=True)
    meta = df[df["case_id"].astype(str) == case_id].iloc[0]
    for col in ("case_id", "case_sun_direction_body", "case_stt_location", "case_lct_location"):
        if col in meta.index:
            case_df[col] = meta[col]
    return case_df.reset_index(drop=True)


def within_case_split_mask(
    times_s: np.ndarray,
    orbit_period_s: float,
    train_orbits: float,
) -> np.ndarray:
    t0 = float(times_s[0])
    train_end = t0 + train_orbits * orbit_period_s
    return times_s <= train_end
