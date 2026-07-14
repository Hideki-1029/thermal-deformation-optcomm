"""
Features:
  LOS ~ b
      + a   * (T_sun - T_opp)
      + d_p * (T_prop_attach - T_PY_center)
      + d_c * (T_pcdu_attach - T_MY_center)

Local attach-minus-panel-center terms avoid absolute T-T_ref collinearity with ΔT.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from pat_acquisition.models._common.ridge import (
    RidgeModel,
    predict_ridge_with_intercept,
    ridge_fit_with_intercept,
)
from pat_acquisition.models.sunface_los.features import (
    SUN_FACE_OPPOSITE,
    SUN_FACE_TO_DOMINANT_AXIS,
    normalize_sun_direction,
    panel_center_temp_column,
    resolve_dominant_axis,
)

__all__ = [
    "CompoLocalFeatureConfig",
    "PROP_ATTACH_TEMP_COL",
    "PCDU_ATTACH_TEMP_COL",
    "PROP_PANEL",
    "PCDU_PANEL",
    "SUN_FACE_OPPOSITE",
    "SUN_FACE_TO_DOMINANT_AXIS",
    "build_compo_local_features",
    "normalize_sun_direction",
    "predict_compo_local_case",
    "resolve_dominant_axis",
    "train_compo_local_axis_model",
]

PROP_ATTACH_TEMP_COL = "temp_prop_attach_c"
PCDU_ATTACH_TEMP_COL = "temp_pcdu_attach_c"
PROP_PANEL = "PY"
PCDU_PANEL = "MY"


@dataclass(frozen=True)
class CompoLocalFeatureConfig:
    ridge_lam: float = 1e-3


def build_compo_local_features(
    df: pd.DataFrame,
    sun_direction: Any,
    config: CompoLocalFeatureConfig | None = None,
) -> tuple[np.ndarray, list[str], pd.DataFrame, str]:
    del config  # ridge lam lives on the trainer
    face = normalize_sun_direction(sun_direction)
    dominant_axis = resolve_dominant_axis(face)
    sun_col = panel_center_temp_column(face)
    if sun_col not in df.columns:
        raise ValueError(f"Missing sun-face temperature column: {sun_col}")

    opp = SUN_FACE_OPPOSITE.get(face)
    if opp is None:
        raise ValueError(f"No opposite face for sun direction {face!r}")
    opp_col = panel_center_temp_column(opp)
    if opp_col not in df.columns:
        raise ValueError(f"Missing opposite-face temperature column: {opp_col}")

    prop_panel_col = panel_center_temp_column(PROP_PANEL)
    pcdu_panel_col = panel_center_temp_column(PCDU_PANEL)
    required = (
        PROP_ATTACH_TEMP_COL,
        PCDU_ATTACH_TEMP_COL,
        prop_panel_col,
        pcdu_panel_col,
    )
    for col in required:
        if col not in df.columns:
            raise ValueError(
                f"Missing temperature column: {col}. "
                "Rebuild lightweight_dataset after extracting compo_attach_points."
            )

    t_sun = df[sun_col].to_numpy(dtype=float)
    t_opp = df[opp_col].to_numpy(dtype=float)
    t_prop = df[PROP_ATTACH_TEMP_COL].to_numpy(dtype=float)
    t_pcdu = df[PCDU_ATTACH_TEMP_COL].to_numpy(dtype=float)
    t_py_center = df[prop_panel_col].to_numpy(dtype=float)
    t_my_center = df[pcdu_panel_col].to_numpy(dtype=float)

    dT = t_sun - t_opp
    local_prop = t_prop - t_py_center
    local_pcdu = t_pcdu - t_my_center

    feature_names = [
        "t_sunface_minus_opposite_c",
        "t_prop_attach_minus_py_center_c",
        "t_pcdu_attach_minus_my_center_c",
    ]
    x = np.column_stack([dT, local_prop, local_pcdu]).astype(float)
    features_df = pd.DataFrame(
        {
            "t_sunface_c": t_sun,
            "t_opposite_c": t_opp,
            "t_sunface_minus_opposite_c": dT,
            "t_prop_attach_c": t_prop,
            "t_pcdu_attach_c": t_pcdu,
            "t_py_center_c": t_py_center,
            "t_my_center_c": t_my_center,
            "t_prop_attach_minus_py_center_c": local_prop,
            "t_pcdu_attach_minus_my_center_c": local_pcdu,
        },
        index=df.index,
    )
    return x, feature_names, features_df, dominant_axis


def train_compo_local_axis_model(
    x_train: np.ndarray,
    y_axis_train: np.ndarray,
    feature_names: list[str],
    config: CompoLocalFeatureConfig,
) -> RidgeModel:
    y = np.asarray(y_axis_train, dtype=float).reshape(-1, 1)
    coef = ridge_fit_with_intercept(x_train, y, lam=config.ridge_lam)
    return RidgeModel(feature_names=tuple(feature_names), coef=coef)


def predict_compo_local_case(
    x: np.ndarray,
    dominant_axis: str,
    axis_model: RidgeModel,
    static_bias_xy: np.ndarray,
) -> np.ndarray:
    pred = np.tile(np.asarray(static_bias_xy, dtype=float).reshape(1, 2), (len(x), 1))
    axis_pred = predict_ridge_with_intercept(axis_model, x)[:, 0]
    if dominant_axis == "x":
        pred[:, 0] = axis_pred
    elif dominant_axis == "y":
        pred[:, 1] = axis_pred
    else:
        raise ValueError(f"dominant_axis must be 'x' or 'y', got {dominant_axis!r}")
    return pred
