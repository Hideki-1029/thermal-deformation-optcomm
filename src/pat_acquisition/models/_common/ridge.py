from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RidgeModel:
    feature_names: tuple[str, ...]
    coef: np.ndarray  # shape=(n_features+1, n_outputs) when intercept is included


def ridge_fit(phi: np.ndarray, y: np.ndarray, lam: float = 1e-3) -> np.ndarray:
    """Plain Ridge: phi already contains any intercept column."""
    p = phi.shape[1]
    a = phi.T @ phi + lam * np.eye(p)
    b = phi.T @ y
    return np.linalg.solve(a, b)


def ridge_fit_with_intercept(
    x: np.ndarray,
    y: np.ndarray,
    lam: float = 1e-3,
) -> np.ndarray:
    """Ridge with an unregularized intercept column prepended."""
    x_aug = np.column_stack([np.ones(len(x), dtype=float), x])
    p = x_aug.shape[1]
    reg = lam * np.eye(p)
    reg[0, 0] = 0.0
    return np.linalg.solve(x_aug.T @ x_aug + reg, x_aug.T @ y)


def predict_ridge_with_intercept(model: RidgeModel, x: np.ndarray) -> np.ndarray:
    x_aug = np.column_stack([np.ones(len(x), dtype=float), x])
    return x_aug @ model.coef
