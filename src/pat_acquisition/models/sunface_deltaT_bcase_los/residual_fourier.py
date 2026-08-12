"""Fourier on post-thermal-FF innovation (not raw LOS).

Target:

  r(t) = (θ_thermal + e_nonthermal) − θ_ff(t)
  θ_ff = b_case + a·ΔT (+ static other axis)

  r̂(φ) = c0 + Σ_k [ak cos(kφ) + bk sin(kφ)],  φ = 2π t / Torb

This is a post-FF operational layer for the periodic floor (mostly orbit
projection after hierarchical thermal FF), not a thermal-identification Fourier.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pat_acquisition.models._common.ridge import ridge_fit
from pat_acquisition.models.fourier_los.model import fourier_features

__all__ = [
    "ResidualFourierConfig",
    "fit_residual_fourier",
    "predict_residual_fourier",
    "simulate_residual_fourier_theta_hat",
]


@dataclass(frozen=True)
class ResidualFourierConfig:
    orbit_period_s: float = 6050.0
    fourier_order: int = 2
    ridge_lam: float = 1e-3
    # batch: fit on all samples (analysis upper bound)
    # causal: fit orbit n → apply on orbit n+1 (on-orbit-like)
    fit_mode: str = "causal"
    residual_noise_1sigma_urad: float = 0.0
    seed: int = 0


def fit_residual_fourier(
    times_s: np.ndarray,
    residual_urad: np.ndarray,
    *,
    orbit_period_s: float,
    order: int = 2,
    ridge_lam: float = 1e-3,
) -> np.ndarray:
    """Return coef [n_features, 2] for residual Fourier."""
    phi = fourier_features(
        times_s,
        orbit_period_s=orbit_period_s,
        order=order,
        include_drift=False,
    )
    return ridge_fit(phi, np.asarray(residual_urad, dtype=float), lam=ridge_lam)


def predict_residual_fourier(
    times_s: np.ndarray,
    coef: np.ndarray,
    *,
    orbit_period_s: float,
    order: int = 2,
) -> np.ndarray:
    phi = fourier_features(
        times_s,
        orbit_period_s=orbit_period_s,
        order=order,
        include_drift=False,
    )
    return phi @ np.asarray(coef, dtype=float)


def simulate_residual_fourier_theta_hat(
    *,
    pred_bcase: np.ndarray,
    theta_thermal_true: np.ndarray,
    nonthermal_error: np.ndarray,
    times_s: np.ndarray,
    config: ResidualFourierConfig,
) -> dict[str, np.ndarray | list[dict[str, float | int | str]]]:
    """
    Build θ_hat = θ_ff + r̂(φ).

    Innovation used for fitting:
      r = thermal + nonthermal − θ_ff
    (optional small observation noise).
    """
    pred_bcase = np.asarray(pred_bcase, dtype=float)
    theta_thermal_true = np.asarray(theta_thermal_true, dtype=float)
    nonthermal_error = np.asarray(nonthermal_error, dtype=float)
    times_s = np.asarray(times_s, dtype=float)

    if pred_bcase.shape != theta_thermal_true.shape:
        raise ValueError("pred_bcase / thermal shape mismatch")
    if nonthermal_error.shape != theta_thermal_true.shape:
        raise ValueError("nonthermal shape mismatch")
    if config.fit_mode not in {"batch", "causal"}:
        raise ValueError(f"Unsupported fit_mode: {config.fit_mode!r}")

    r_true = theta_thermal_true + nonthermal_error - pred_bcase
    rng = np.random.default_rng(config.seed)
    if config.residual_noise_1sigma_urad > 0.0:
        r_obs = r_true + rng.normal(
            0.0, config.residual_noise_1sigma_urad, size=r_true.shape
        )
    else:
        r_obs = r_true

    history: list[dict[str, float | int | str]] = []
    orbit_idx = np.floor(times_s / float(config.orbit_period_s)).astype(int)
    r_hat = np.zeros_like(pred_bcase)

    if config.fit_mode == "batch":
        coef = fit_residual_fourier(
            times_s,
            r_obs,
            orbit_period_s=config.orbit_period_s,
            order=config.fourier_order,
            ridge_lam=config.ridge_lam,
        )
        r_hat = predict_residual_fourier(
            times_s,
            coef,
            orbit_period_s=config.orbit_period_s,
            order=config.fourier_order,
        )
        resid_after = r_true - r_hat
        history.append(
            {
                "orbit_index": -1,
                "fit_mode": "batch",
                "n_samples": int(len(times_s)),
                "r_obs_norm_mean_urad": float(np.mean(np.linalg.norm(r_obs, axis=1))),
                "r_hat_norm_mean_urad": float(np.mean(np.linalg.norm(r_hat, axis=1))),
                "resid_after_norm_mean_urad": float(
                    np.mean(np.linalg.norm(resid_after, axis=1))
                ),
            }
        )
    else:
        prev_coef: np.ndarray | None = None
        for o in np.unique(orbit_idx):
            mask = orbit_idx == o
            t_o = times_s[mask]
            if prev_coef is None:
                r_hat[mask] = 0.0
            else:
                r_hat[mask] = predict_residual_fourier(
                    t_o,
                    prev_coef,
                    orbit_period_s=config.orbit_period_s,
                    order=config.fourier_order,
                )
            # Fit this orbit's observed innovation for the next orbit.
            coef = fit_residual_fourier(
                t_o,
                r_obs[mask],
                orbit_period_s=config.orbit_period_s,
                order=config.fourier_order,
                ridge_lam=config.ridge_lam,
            )
            resid_o = r_true[mask] - r_hat[mask]
            history.append(
                {
                    "orbit_index": int(o),
                    "fit_mode": "causal",
                    "n_samples": int(np.count_nonzero(mask)),
                    "r_obs_norm_mean_urad": float(
                        np.mean(np.linalg.norm(r_obs[mask], axis=1))
                    ),
                    "r_hat_norm_mean_urad": float(
                        np.mean(np.linalg.norm(r_hat[mask], axis=1))
                    ),
                    "resid_after_norm_mean_urad": float(
                        np.mean(np.linalg.norm(resid_o, axis=1))
                    ),
                }
            )
            prev_coef = coef

    theta_hat = pred_bcase + r_hat
    return {
        "theta_hat": theta_hat,
        "r_hat": r_hat,
        "r_true": r_true,
        "orbit_index": orbit_idx,
        "history": history,
    }
