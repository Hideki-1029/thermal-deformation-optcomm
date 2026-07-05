from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

from orbit.isl_geometry import (
    nominal_isl_partner_position,
    position_error_to_isl_angle_urad,
    position_error_to_rtn,
)
from orbit.sentinel1_pod import OrbitState, states_to_arrays
from orbit.tle_sources import select_ephemeris_for_time


@dataclass(frozen=True)
class OrbitPredictionErrorResult:
    unix_times_s: np.ndarray
    elapsed_time_s: np.ndarray
    tle_age_days: np.ndarray
    position_error_ecef_m: np.ndarray
    position_error_rtn_m: np.ndarray
    position_error_norm_m: np.ndarray
    isl_angle_error_urad: np.ndarray
    isl_angle_error_norm_urad: np.ndarray
    tle_age_median_days: float
    tle_age_max_days: float


def compute_tle_vs_pod_error(
    pod_states: list[OrbitState],
    ephemeris_records: list,
    isl_range_m: float = 800_000.0,
    sample_interval_s: float | None = 60.0,
) -> OrbitPredictionErrorResult:
    """
    Compare TLE/SGP4 propagation against Sentinel-1 POD truth.

    At each evaluation epoch, the latest TLE/GP record with epoch <= evaluation
    time is propagated forward to that epoch. Position error is converted to an
    ISL LOS angular error assuming the partner satellite is known via GNSS.
    """
    times_s, truth_positions_m, truth_velocities_m_s = states_to_arrays(pod_states)
    if sample_interval_s is not None and sample_interval_s > 0.0:
        start = times_s[0]
        sampled_times = np.arange(start, times_s[-1] + 1.0e-9, sample_interval_s)
        indices = np.searchsorted(times_s, sampled_times)
        indices = np.clip(indices, 0, len(times_s) - 1)
        times_s = times_s[indices]
        truth_positions_m = truth_positions_m[indices]
        truth_velocities_m_s = truth_velocities_m_s[indices]
        pod_states = [pod_states[index] for index in indices]

    predicted_positions_m = np.zeros_like(truth_positions_m)
    position_error = np.zeros_like(truth_positions_m)
    rtn_errors = np.zeros_like(truth_positions_m)
    isl_errors = np.zeros((len(times_s), 2), dtype=float)
    tle_age_days = np.zeros(len(times_s), dtype=float)

    for index, state in enumerate(pod_states):
        record = select_ephemeris_for_time(ephemeris_records, state.utc)
        predicted_positions_m[index, :], _ = record.propagate_ecef(
            np.array([times_s[index]])
        )
        position_error[index, :] = predicted_positions_m[index, :] - truth_positions_m[index, :]
        rtn_errors[index, :] = position_error_to_rtn(
            position_error[index, :],
            truth_positions_m[index, :],
            truth_velocities_m_s[index, :],
        )
        partner_position = nominal_isl_partner_position(
            truth_positions_m[index, :],
            truth_velocities_m_s[index, :],
            isl_range_m,
        )
        isl_errors[index, :] = position_error_to_isl_angle_urad(
            position_error[index, :],
            truth_positions_m[index, :],
            partner_position,
        )
        tle_age_days[index] = (
            state.utc - record.epoch_utc
        ).total_seconds() / 86400.0

    elapsed_time_s = times_s - times_s[0]
    return OrbitPredictionErrorResult(
        unix_times_s=times_s,
        elapsed_time_s=elapsed_time_s,
        tle_age_days=tle_age_days,
        position_error_ecef_m=position_error,
        position_error_rtn_m=rtn_errors,
        position_error_norm_m=np.linalg.norm(position_error, axis=1),
        isl_angle_error_urad=isl_errors,
        isl_angle_error_norm_urad=np.linalg.norm(isl_errors, axis=1),
        tle_age_median_days=float(np.median(tle_age_days)),
        tle_age_max_days=float(np.max(tle_age_days)),
    )


def summarize_by_tle_age(
    result: OrbitPredictionErrorResult,
    age_bins_days: tuple[float, ...] = (0.0, 1.0, 3.0, 7.0),
) -> list[dict[str, float]]:
    """Summarize RMS position/angle errors for samples below each age bin."""
    summaries: list[dict[str, float]] = []
    for max_age in age_bins_days:
        mask = result.tle_age_days <= max_age + 1.0e-9
        if not np.any(mask):
            continue
        summaries.append(
            {
                "max_tle_age_days": max_age,
                "sample_count": float(np.count_nonzero(mask)),
                "position_rms_m": float(
                    np.sqrt(np.mean(result.position_error_norm_m[mask] ** 2))
                ),
                "position_p95_m": float(
                    np.percentile(result.position_error_norm_m[mask], 95)
                ),
                "isl_angle_rms_urad": float(
                    np.sqrt(np.mean(result.isl_angle_error_norm_urad[mask] ** 2))
                ),
                "isl_angle_p95_urad": float(
                    np.percentile(result.isl_angle_error_norm_urad[mask], 95)
                ),
            }
        )
    return summaries
