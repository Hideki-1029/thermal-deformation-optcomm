from __future__ import annotations

import numpy as np


def predict_no_correction(n_samples: int) -> np.ndarray:
    return np.zeros((n_samples, 2), dtype=float)


def predict_static_bias(y_train: np.ndarray, n_samples: int) -> np.ndarray:
    bias = np.mean(np.asarray(y_train, dtype=float), axis=0)
    return np.tile(bias, (n_samples, 1))


def static_bias_vector(theta_reference_urad: np.ndarray) -> np.ndarray:
    return np.mean(np.asarray(theta_reference_urad, dtype=float), axis=0)
