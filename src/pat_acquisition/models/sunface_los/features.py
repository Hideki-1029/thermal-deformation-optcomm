from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from pat_acquisition.models._common.ridge import RidgeModel, ridge_fit_with_intercept, predict_ridge_with_intercept


SUN_FACE_TO_DOMINANT_AXIS = {
    "MX": "x",
    "PX": "x",
    "MY": "y",
    "PY": "y",
}

SUN_FACE_OPPOSITE = {
    "MX": "PX",
    "PX": "MX",
    "MY": "PY",
    "PY": "MY",
    "MZ": "PZ",
    "PZ": "MZ",
}


@dataclass(frozen=True)
class SunfaceFeatureConfig:
    t_ref_c: float = 23.9
    ridge_lam: float = 1e-3
    include_opposite_diff: bool = True
    include_ref_diff: bool = True


def normalize_sun_direction(sun_direction: Any) -> str:
    text = str(sun_direction).strip().upper()
    aliases = {
        "+X": "PX",
        "-X": "MX",
        "+Y": "PY",
        "-Y": "MY",
        "+Z": "PZ",
        "-Z": "MZ",
    }
    return aliases.get(text, text)


def panel_center_temp_column(panel: str) -> str:
    return f"temp_panel_{panel.lower()}_center_c"


def resolve_dominant_axis(sun_direction: Any) -> str:
    face = normalize_sun_direction(sun_direction)
    if face not in SUN_FACE_TO_DOMINANT_AXIS:
        raise ValueError(
            f"Unsupported sun direction for dominant-axis mapping: {sun_direction!r}. "
            "Expected one of MX/MY/PX/PY (or +/-X, +/-Y)."
        )
    return SUN_FACE_TO_DOMINANT_AXIS[face]


def build_sunface_features(
    df: pd.DataFrame,
    sun_direction: Any,
    config: SunfaceFeatureConfig,
) -> tuple[np.ndarray, list[str], pd.DataFrame, str]:
    """
    Build features from the sun-facing panel temperature.

    Primary insight:
      sun-facing panel temperature tracks the dominant LOS axis waveform.
    """
    face = normalize_sun_direction(sun_direction)
    dominant_axis = resolve_dominant_axis(face)
    sun_col = panel_center_temp_column(face)
    if sun_col not in df.columns:
        raise ValueError(f"Missing sun-face temperature column: {sun_col}")

    t_sun = df[sun_col].to_numpy(dtype=float)
    feature_map: dict[str, np.ndarray] = {
        "t_sunface_c": t_sun,
    }

    if config.include_ref_diff:
        feature_map["t_sunface_minus_ref_c"] = t_sun - config.t_ref_c

    if config.include_opposite_diff:
        opp = SUN_FACE_OPPOSITE.get(face)
        if opp is not None:
            opp_col = panel_center_temp_column(opp)
            if opp_col in df.columns:
                feature_map["t_sunface_minus_opposite_c"] = (
                    t_sun - df[opp_col].to_numpy(dtype=float)
                )

    feature_names = list(feature_map.keys())
    x = np.column_stack([feature_map[name] for name in feature_names]).astype(float)
    features_df = pd.DataFrame(feature_map, index=df.index)
    return x, feature_names, features_df, dominant_axis


def train_sunface_axis_model(
    x_train: np.ndarray,
    y_axis_train: np.ndarray,
    feature_names: list[str],
    config: SunfaceFeatureConfig,
) -> RidgeModel:
    """Fit a 1-output Ridge model for the dominant LOS axis."""
    y = np.asarray(y_axis_train, dtype=float).reshape(-1, 1)
    coef = ridge_fit_with_intercept(x_train, y, lam=config.ridge_lam)
    return RidgeModel(feature_names=tuple(feature_names), coef=coef)


def predict_sunface_case(
    x: np.ndarray,
    dominant_axis: str,
    axis_model: RidgeModel,
    static_bias_xy: np.ndarray,
) -> np.ndarray:
    """
    Predict [dtheta_x, dtheta_y].

    Dominant axis: sunface Ridge prediction.
    Other axis: train-set static bias.
    """
    pred = np.tile(np.asarray(static_bias_xy, dtype=float).reshape(1, 2), (len(x), 1))
    axis_pred = predict_ridge_with_intercept(axis_model, x)[:, 0]
    if dominant_axis == "x":
        pred[:, 0] = axis_pred
    elif dominant_axis == "y":
        pred[:, 1] = axis_pred
    else:
        raise ValueError(f"dominant_axis must be 'x' or 'y', got {dominant_axis!r}")
    return pred
