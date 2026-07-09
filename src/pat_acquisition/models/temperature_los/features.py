from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from pat_acquisition.models._common.ridge import RidgeModel, ridge_fit_with_intercept


@dataclass(frozen=True)
class TemperatureFeatureConfig:
    t_ref_c: float = 23.9
    ridge_lam: float = 1e-3
    include_dtmid_dt: bool = True


def _location_to_temp_column(location: Any) -> str | None:
    if location is None:
        return None
    text = str(location).strip()
    if not text:
        return None
    return f"temp_panel_{text.lower()}_c"


def _resolve_temperature_series(
    df: pd.DataFrame, preferred_col: str | None
) -> np.ndarray:
    if preferred_col and preferred_col in df.columns:
        return df[preferred_col].to_numpy(dtype=float)

    center_cols = sorted(
        c
        for c in df.columns
        if c.startswith("temp_panel_") and c.endswith("_center_c")
    )
    if center_cols:
        return df[center_cols].mean(axis=1).to_numpy(dtype=float)

    temp_cols = sorted(
        c for c in df.columns if c.startswith("temp_") and c.endswith("_c")
    )
    if temp_cols:
        return df[temp_cols].mean(axis=1).to_numpy(dtype=float)

    raise ValueError("No temperature columns found to build features")


def build_temperature_features(
    df: pd.DataFrame,
    config: TemperatureFeatureConfig,
) -> tuple[np.ndarray, list[str], pd.DataFrame]:
    """
    Build temperature-derived features.

    Features:
    - T_STT - T_ref
    - T_LCT - T_ref
    - T_MID - T_ref
    - T_STT - T_LCT
    - T_MID_FRONT - T_MID_BACK (if available)
    - dT_MID/dt (optional)
    """
    if "case_stt_location" not in df.columns or "case_lct_location" not in df.columns:
        raise ValueError(
            "Dataset must include case_stt_location and case_lct_location columns"
        )
    if "time_s" not in df.columns:
        raise ValueError("Dataset must include time_s column")
    if "case_id" not in df.columns:
        raise ValueError("Dataset must include case_id column")

    stt_col = _location_to_temp_column(df["case_stt_location"].iloc[0])
    lct_col = _location_to_temp_column(df["case_lct_location"].iloc[0])

    t_stt = _resolve_temperature_series(df, stt_col)
    t_lct = _resolve_temperature_series(df, lct_col)

    t_mid_col = "temp_panel_mz_center_c" if "temp_panel_mz_center_c" in df.columns else None
    t_mid = _resolve_temperature_series(df, t_mid_col)

    feature_map: dict[str, np.ndarray] = {
        "t_stt_minus_ref_c": t_stt - config.t_ref_c,
        "t_lct_minus_ref_c": t_lct - config.t_ref_c,
        "t_mid_minus_ref_c": t_mid - config.t_ref_c,
        "t_stt_minus_t_lct_c": t_stt - t_lct,
    }

    front_col = "temp_mid_front_c"
    back_col = "temp_mid_back_c"
    if front_col in df.columns and back_col in df.columns:
        feature_map["t_mid_front_minus_back_c"] = (
            df[front_col].to_numpy(dtype=float) - df[back_col].to_numpy(dtype=float)
        )

    if config.include_dtmid_dt:
        dt_mid_dt = np.zeros(len(df), dtype=float)
        for _, idx in df.groupby("case_id").groups.items():
            sub = df.loc[idx].sort_values("time_s")
            t = sub["time_s"].to_numpy(dtype=float)
            y = t_mid[sub.index.to_numpy()]
            if len(sub) > 1:
                dt = np.diff(t)
                positive_dt = dt[dt > 0.0]
                if len(positive_dt) > 0 and np.all(dt > 0.0):
                    dt_mid_dt_sub = np.gradient(y, t, edge_order=1)
                else:
                    scale_dt = float(np.median(positive_dt)) if len(positive_dt) > 0 else 1.0
                    dt_mid_dt_sub = np.gradient(y, edge_order=1) / max(scale_dt, 1e-12)
            else:
                dt_mid_dt_sub = np.zeros_like(y)
            dt_mid_dt[sub.index.to_numpy()] = dt_mid_dt_sub
        feature_map["dt_mid_dt_c_per_s"] = dt_mid_dt

    feature_names = list(feature_map.keys())
    x = np.column_stack([feature_map[name] for name in feature_names]).astype(float)
    features_df = pd.DataFrame(feature_map, index=df.index)
    return x, feature_names, features_df


def train_ridge_temperature_model(
    x_train: np.ndarray,
    y_train: np.ndarray,
    feature_names: list[str],
    config: TemperatureFeatureConfig,
) -> RidgeModel:
    coef = ridge_fit_with_intercept(x_train, y_train, lam=config.ridge_lam)
    return RidgeModel(feature_names=tuple(feature_names), coef=coef)
