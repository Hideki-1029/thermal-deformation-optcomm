from __future__ import annotations

import numpy as np


def compute_error_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    residual = y_true - y_pred
    norm = np.linalg.norm(residual, axis=1)
    return {
        "rmse_x_urad": float(np.sqrt(np.mean(residual[:, 0] ** 2))),
        "rmse_y_urad": float(np.sqrt(np.mean(residual[:, 1] ** 2))),
        "rmse_norm_urad": float(np.sqrt(np.mean(norm**2))),
        "mae_x_urad": float(np.mean(np.abs(residual[:, 0]))),
        "mae_y_urad": float(np.mean(np.abs(residual[:, 1]))),
        "mae_norm_urad": float(np.mean(norm)),
        "p95_error_norm_urad": float(np.percentile(norm, 95)),
        "max_error_norm_urad": float(np.max(norm)),
    }
