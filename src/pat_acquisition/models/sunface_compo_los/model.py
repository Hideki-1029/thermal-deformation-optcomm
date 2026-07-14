from __future__ import annotations

import numpy as np
import pandas as pd

from pat_acquisition.models._common.targets import extract_targets
from pat_acquisition.models.sunface_compo_los.dataset import within_case_split_mask
from pat_acquisition.models.sunface_compo_los.features import (
    CompoFeatureConfig,
    build_compo_features,
    normalize_sun_direction,
    predict_compo_case,
    resolve_dominant_axis,
    train_compo_axis_model,
)

__all__ = [
    "CompoFeatureConfig",
    "build_compo_features",
    "fit_compo_predictions",
    "normalize_sun_direction",
    "predict_compo_case",
    "resolve_dominant_axis",
    "train_compo_axis_model",
]


def fit_compo_predictions(
    case_df: pd.DataFrame,
    config: CompoFeatureConfig,
    orbit_period_s: float,
    train_orbits: float = 1.0,
) -> dict[str, np.ndarray | str]:
    """
    Within-case fit: first ``train_orbits`` orbits for training, predict all times.
    """
    if "case_sun_direction_body" not in case_df.columns:
        raise ValueError("case_df must include case_sun_direction_body")

    sun_direction = case_df["case_sun_direction_body"].iloc[0]
    sun_face = normalize_sun_direction(sun_direction)
    dominant_axis = resolve_dominant_axis(sun_face)

    x_all, feature_names, _features_df, dominant_axis = build_compo_features(
        case_df, sun_direction, config
    )
    y_all = extract_targets(case_df)
    times_s = case_df["time_s"].to_numpy(dtype=float)
    train_mask = within_case_split_mask(times_s, orbit_period_s, train_orbits)
    if not np.any(train_mask):
        raise ValueError(
            "Train split is empty. Check orbit_period_s and train_orbits."
        )

    axis_idx = 0 if dominant_axis == "x" else 1
    y_train = y_all[train_mask]
    axis_model = train_compo_axis_model(
        x_train=x_all[train_mask],
        y_axis_train=y_train[:, axis_idx],
        feature_names=feature_names,
        config=config,
    )
    static_bias = np.mean(y_train, axis=0)
    pred_compo = predict_compo_case(
        x=x_all,
        dominant_axis=dominant_axis,
        axis_model=axis_model,
        static_bias_xy=static_bias,
    )
    pred_static = np.tile(static_bias, (len(case_df), 1))

    return {
        "static_bias": pred_static,
        "compo": pred_compo,
        "sun_face": sun_face,
        "dominant_axis": dominant_axis,
    }
