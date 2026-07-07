from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class LightweightModelConfig:
    orbit_period_s: float = 6050.0
    auto_orbit_period: bool = True
    train_fraction: float = 1.0
    fourier_order: int = 2
    include_drift: bool = False
    ridge_lam: float = 1e-3


def fourier_features(
    times_s: np.ndarray,
    orbit_period_s: float,
    order: int = 2,
    include_drift: bool = False,
) -> np.ndarray:
    times_s = np.asarray(times_s, dtype=float)
    phi = 2.0 * np.pi * times_s / orbit_period_s

    cols = [np.ones_like(times_s)]
    for n in range(1, order + 1):
        cols.append(np.sin(n * phi))
        cols.append(np.cos(n * phi))

    if include_drift:
        total_span = max(times_s[-1] - times_s[0], 1.0)
        tau = (times_s - times_s[0]) / total_span
        cols.append(tau)

    return np.column_stack(cols)


def ridge_fit(phi: np.ndarray, y: np.ndarray, lam: float = 1e-3) -> np.ndarray:
    p = phi.shape[1]
    a = phi.T @ phi + lam * np.eye(p)
    b = phi.T @ y
    return np.linalg.solve(a, b)


def build_static_prediction(theta_reference_urad: np.ndarray) -> np.ndarray:
    return np.mean(theta_reference_urad, axis=0)


def build_fourier_prediction(
    times_s: np.ndarray,
    theta_reference_urad: np.ndarray,
    orbit_period_s: float,
    order: int = 2,
    include_drift: bool = False,
    ridge_lam: float = 1e-3,
) -> tuple[np.ndarray, np.ndarray]:
    phi = fourier_features(
        times_s,
        orbit_period_s=orbit_period_s,
        order=order,
        include_drift=include_drift,
    )
    coef = ridge_fit(phi, theta_reference_urad, lam=ridge_lam)
    return phi @ coef, coef


def estimate_orbit_period_s(
    times_s: np.ndarray,
    theta_thermal_true_urad: np.ndarray | None = None,
) -> float:
    """Estimate orbit period from sample spacing and total span."""
    times_s = np.asarray(times_s, dtype=float)
    total_span = max(times_s[-1] - times_s[0], 1.0)

    if theta_thermal_true_urad is not None:
        magnitude = np.linalg.norm(np.asarray(theta_thermal_true_urad, dtype=float), axis=1)
        min_distance = max(len(times_s) // 8, 3)
        minima = []
        for i in range(1, len(magnitude) - 1):
            if magnitude[i] <= magnitude[i - 1] and magnitude[i] <= magnitude[i + 1]:
                minima.append(times_s[i])
        if len(minima) >= 2:
            periods = np.diff(minima)
            positive = periods[periods > 0.0]
            if len(positive) > 0:
                return float(np.median(positive))

    for n_orbits in (3, 2, 1):
        period = total_span / n_orbits
        if period > 0.0:
            return float(period)

    return float(total_span)


def train_mask_from_config(times_s: np.ndarray, config: LightweightModelConfig) -> np.ndarray:
    times_s = np.asarray(times_s, dtype=float)
    train_end = config.train_fraction * config.orbit_period_s
    if train_end <= times_s[0]:
        train_end = config.train_fraction * (times_s[-1] - times_s[0])
    return times_s <= (times_s[0] + train_end)


def fit_lightweight_predictions(
    times_s: np.ndarray,
    theta_thermal_true_urad: np.ndarray,
    config: LightweightModelConfig,
) -> dict[str, np.ndarray]:
    times_s = np.asarray(times_s, dtype=float)
    theta_thermal_true_urad = np.asarray(theta_thermal_true_urad, dtype=float)
    train_mask = train_mask_from_config(times_s, config)

    theta_train = theta_thermal_true_urad[train_mask]
    times_train = times_s[train_mask]
    if len(theta_train) < 3:
        raise ValueError("Need at least 3 training samples for lightweight models")

    static_bias = build_static_prediction(theta_train)
    theta_static = np.tile(static_bias, (len(times_s), 1))

    _, coef_fourier = build_fourier_prediction(
        times_train,
        theta_train,
        orbit_period_s=config.orbit_period_s,
        order=config.fourier_order,
        include_drift=False,
        ridge_lam=config.ridge_lam,
    )
    phi_all = fourier_features(
        times_s,
        orbit_period_s=config.orbit_period_s,
        order=config.fourier_order,
        include_drift=False,
    )
    theta_fourier = phi_all @ coef_fourier

    _, coef_fourier_drift = build_fourier_prediction(
        times_train,
        theta_train,
        orbit_period_s=config.orbit_period_s,
        order=config.fourier_order,
        include_drift=True,
        ridge_lam=config.ridge_lam,
    )
    phi_all_drift = fourier_features(
        times_s,
        orbit_period_s=config.orbit_period_s,
        order=config.fourier_order,
        include_drift=True,
    )
    theta_fourier_drift = phi_all_drift @ coef_fourier_drift

    return {
        "static_bias": theta_static,
        "fourier_ff": theta_fourier,
        "fourier_plus_drift": theta_fourier_drift,
    }
