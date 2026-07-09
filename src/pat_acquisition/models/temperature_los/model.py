from __future__ import annotations

from pat_acquisition.models._common.ridge import RidgeModel, predict_ridge_with_intercept
from pat_acquisition.models.temperature_los.features import (
    TemperatureFeatureConfig,
    build_temperature_features,
    train_ridge_temperature_model,
)

predict_ridge = predict_ridge_with_intercept

__all__ = [
    "RidgeModel",
    "TemperatureFeatureConfig",
    "build_temperature_features",
    "predict_ridge",
    "train_ridge_temperature_model",
]
