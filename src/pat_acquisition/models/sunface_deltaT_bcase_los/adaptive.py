"""Two-layer adaptive toy: fast δb[mode] (+ optional slow b_adapt with geometry gate).

Toy-1: δb only (enable_slow_b=False)
Toy-2: δb + slow b_adapt via w_orbit_small from sun-face geometry (TLE age not used)

Update cadence: once per orbit after that orbit's opportunities, so the next
orbit sees the updated table (pass-to-pass story).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from pat_acquisition.models.sunface_deltaT_bcase_los.features import case_heat_flags
from pat_acquisition.models.sunface_deltaT_los.features import normalize_sun_direction

__all__ = [
    "AdaptiveConfig",
    "AdaptiveTables",
    "ModeKey",
    "mode_key_from_case",
    "simulate_adaptive_theta_hat",
    "w_orbit_small_geometry",
]


ModeKey = tuple[str, int, int]  # (sun_face, I_prop, I_pcdu)


@dataclass(frozen=True)
class AdaptiveConfig:
    gamma_fast: float = 0.4
    gamma_slow: float = 0.05
    enable_slow_b: bool = False
    # Soft geometry weights (TLE-only prior; see research note §6.3).
    w_my_py: float = 1.0
    w_px: float = 0.1
    w_other: float = 0.0
    residual_noise_1sigma_urad: float = 5.0
    seed: int = 0


@dataclass
class AdaptiveTables:
    """Per-mode fast δb and slow b_adapt (both [µrad, 2])."""

    delta_b: dict[ModeKey, np.ndarray] = field(default_factory=dict)
    b_adapt: dict[ModeKey, np.ndarray] = field(default_factory=dict)

    def get_delta_b(self, mode: ModeKey) -> np.ndarray:
        if mode not in self.delta_b:
            self.delta_b[mode] = np.zeros(2, dtype=float)
        return self.delta_b[mode]

    def get_b_adapt(self, mode: ModeKey) -> np.ndarray:
        if mode not in self.b_adapt:
            self.b_adapt[mode] = np.zeros(2, dtype=float)
        return self.b_adapt[mode]


def mode_key_from_case(case_df, sun_face: str | None = None) -> ModeKey:
    face = normalize_sun_direction(
        sun_face
        if sun_face is not None
        else case_df["case_sun_direction_body"].iloc[0]
    )
    i_prop, i_pcdu = case_heat_flags(case_df)
    return (face, int(i_prop), int(i_pcdu))


def w_orbit_small_geometry(sun_face: str, config: AdaptiveConfig) -> float:
    """Geometry-only soft weight (no TLE age)."""
    face = normalize_sun_direction(sun_face)
    if face in {"MY", "PY"}:
        return float(config.w_my_py)
    if face == "PX":
        return float(config.w_px)
    return float(config.w_other)


def simulate_adaptive_theta_hat(
    *,
    pred_bcase: np.ndarray,
    theta_thermal_true: np.ndarray,
    nonthermal_error: np.ndarray,
    times_s: np.ndarray,
    orbit_period_s: float,
    mode: ModeKey,
    tables: AdaptiveTables,
    config: AdaptiveConfig,
) -> dict[str, np.ndarray | list[dict[str, float | int]]]:
    """
    Build time-varying θ_ff = pred_bcase + b_adapt[mode] + δb[mode].

    After each completed orbit, update tables from the mean innovation
    r ≈ (thermal + nonthermal) − θ_ff over that orbit (noisy QD/FPM proxy).
    """
    pred_bcase = np.asarray(pred_bcase, dtype=float)
    theta_thermal_true = np.asarray(theta_thermal_true, dtype=float)
    nonthermal_error = np.asarray(nonthermal_error, dtype=float)
    times_s = np.asarray(times_s, dtype=float)

    if pred_bcase.shape != theta_thermal_true.shape:
        raise ValueError("pred_bcase and theta_thermal_true shape mismatch")
    if nonthermal_error.shape != theta_thermal_true.shape:
        raise ValueError("nonthermal_error shape mismatch")
    if orbit_period_s <= 0.0:
        raise ValueError("orbit_period_s must be positive")

    n = len(times_s)
    theta_hat = np.zeros_like(pred_bcase)
    orbit_idx = np.floor(times_s / float(orbit_period_s)).astype(int)
    rng = np.random.default_rng(config.seed)
    sun_face = mode[0]
    history: list[dict[str, float | int]] = []

    for o in np.unique(orbit_idx):
        mask = orbit_idx == o
        delta_b = tables.get_delta_b(mode).copy()
        b_adapt = tables.get_b_adapt(mode).copy()
        theta_hat[mask] = pred_bcase[mask] + b_adapt + delta_b

        # Innovation at each opportunity (scan-center error before spiral).
        r = (
            theta_thermal_true[mask]
            + nonthermal_error[mask]
            - theta_hat[mask]
        )
        r_mean = np.mean(r, axis=0)
        noise = rng.normal(0.0, config.residual_noise_1sigma_urad, size=2)
        r_obs = r_mean + noise

        delta_b = delta_b + float(config.gamma_fast) * r_obs
        w = w_orbit_small_geometry(sun_face, config)
        promoted = np.zeros(2, dtype=float)
        if config.enable_slow_b and w > 0.0:
            promoted = float(config.gamma_slow) * float(w) * delta_b
            b_adapt = b_adapt + promoted
            delta_b = delta_b - promoted

        tables.delta_b[mode] = delta_b
        tables.b_adapt[mode] = b_adapt
        history.append(
            {
                "orbit_index": int(o),
                "n_samples": int(np.count_nonzero(mask)),
                "r_obs_x_urad": float(r_obs[0]),
                "r_obs_y_urad": float(r_obs[1]),
                "r_obs_norm_urad": float(np.linalg.norm(r_obs)),
                "delta_b_x_urad": float(delta_b[0]),
                "delta_b_y_urad": float(delta_b[1]),
                "b_adapt_x_urad": float(b_adapt[0]),
                "b_adapt_y_urad": float(b_adapt[1]),
                "w_orbit_small": float(w),
                "promoted_norm_urad": float(np.linalg.norm(promoted)),
            }
        )

    return {
        "theta_hat": theta_hat,
        "orbit_index": orbit_idx,
        "history": history,
    }
