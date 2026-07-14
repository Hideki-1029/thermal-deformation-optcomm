"""Minimal sunface features: dominant axis ~ b + a * (T_sun - T_opp)."""

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
    "DeltaTFeatureConfig",
    "SUN_FACE_OPPOSITE",
    "SUN_FACE_TO_DOMINANT_AXIS",
    "build_deltaT_features",
    "normalize_sun_direction",
    "predict_deltaT_case",
    "resolve_dominant_axis",
    "train_deltaT_axis_model",
]


@dataclass(frozen=True)
class DeltaTFeatureConfig:
    ridge_lam: float = 1e-3


def build_deltaT_features(
    df: pd.DataFrame,
    sun_direction: Any,
    config: DeltaTFeatureConfig | None = None,
) -> tuple[np.ndarray, list[str], pd.DataFrame, str]:
    """
    Build the single physical feature ``T_sunface - T_opposite``.

    ``t_sunface_c`` is kept in the returned frame for diagnostics/plots only;
    it is not part of the regression design matrix.
    """
    del config  # reserved for future knobs; ridge lam lives on the trainer
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

    t_sun = df[sun_col].to_numpy(dtype=float)
    t_opp = df[opp_col].to_numpy(dtype=float)
    dT = t_sun - t_opp

    feature_names = ["t_sunface_minus_opposite_c"]
    x = dT.reshape(-1, 1).astype(float)
    features_df = pd.DataFrame(
        {
            "t_sunface_c": t_sun,
            "t_opposite_c": t_opp,
            "t_sunface_minus_opposite_c": dT,
        },
        index=df.index,
    )
    return x, feature_names, features_df, dominant_axis


def train_deltaT_axis_model(
    x_train: np.ndarray,
    y_axis_train: np.ndarray,
    feature_names: list[str],
    config: DeltaTFeatureConfig,
) -> RidgeModel:
    y = np.asarray(y_axis_train, dtype=float).reshape(-1, 1)
    coef = ridge_fit_with_intercept(x_train, y, lam=config.ridge_lam)
    return RidgeModel(feature_names=tuple(feature_names), coef=coef)


def predict_deltaT_case(
    x: np.ndarray,
    dominant_axis: str,
    axis_model: RidgeModel,
    static_bias_xy: np.ndarray,
) -> np.ndarray:
    """Predict [dtheta_x, dtheta_y]; non-dominant axis uses train-set static bias."""
    pred = np.tile(np.asarray(static_bias_xy, dtype=float).reshape(1, 2), (len(x), 1))
    axis_pred = predict_ridge_with_intercept(axis_model, x)[:, 0]
    if dominant_axis == "x":
        pred[:, 0] = axis_pred
    elif dominant_axis == "y":
        pred[:, 1] = axis_pred
    else:
        raise ValueError(f"dominant_axis must be 'x' or 'y', got {dominant_axis!r}")
    return pred
