from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CoarseAcquisitionConfig:
    max_range_urad: float = 1600.0
    step_urad: float = 120.0
    detect_radius_urad: float = 150.0
    dwell_time_s: float = 0.1

    def __post_init__(self) -> None:
        # Farthest point in a square cell is at step/√2 from a scan point.
        if self.step_urad / np.sqrt(2.0) > self.detect_radius_urad:
            raise ValueError(
                "scan has coverage holes: "
                f"step/sqrt(2)={self.step_urad / np.sqrt(2.0):.1f} µrad "
                f"> detect_radius={self.detect_radius_urad:.1f} µrad"
            )


def rectangular_spiral_scan(max_range_urad: float, step_urad: float) -> np.ndarray:
    """Generate rectangular spiral scan points around the commanded scan center."""
    points = [(0.0, 0.0)]
    n = int(max_range_urad // step_urad)

    for r in range(1, n + 1):
        vals = np.arange(-r, r + 1) * step_urad

        for x in vals:
            points.append((x, r * step_urad))
            points.append((x, -r * step_urad))

        for y in vals[1:-1]:
            points.append((r * step_urad, y))
            points.append((-r * step_urad, y))

    return np.asarray(points, dtype=float)


def coarse_acquisition(
    pointing_error_urad: np.ndarray,
    scan_points_urad: np.ndarray,
    detect_radius_urad: float,
    dwell_time_s: float,
) -> tuple[bool, float, np.ndarray, float]:
    """Return whether coarse acquisition succeeds and the first hit time."""
    diffs = scan_points_urad - pointing_error_urad
    distances = np.linalg.norm(diffs, axis=1)
    hit = np.where(distances <= detect_radius_urad)[0]

    if len(hit) == 0:
        return False, np.nan, np.array([np.nan, np.nan]), np.nan

    scan_index = int(hit[0])
    acquisition_time_s = (scan_index + 1) * dwell_time_s
    residual_after_acq = pointing_error_urad - scan_points_urad[scan_index]
    return True, acquisition_time_s, residual_after_acq, float(scan_index)


def evaluate_coarse_acquisition(
    theta_thermal_true_urad: np.ndarray,
    theta_correction_hat_urad: np.ndarray,
    config: CoarseAcquisitionConfig,
    nonthermal_error_urad: np.ndarray | None = None,
) -> np.ndarray:
    """
    Evaluate coarse acquisition at each opportunity.

    The scan-center error is modeled as:
        nonthermal_error + thermal_true - thermal_correction_hat
    """
    theta_thermal_true_urad = np.asarray(theta_thermal_true_urad, dtype=float)
    theta_correction_hat_urad = np.asarray(theta_correction_hat_urad, dtype=float)

    if theta_thermal_true_urad.shape != theta_correction_hat_urad.shape:
        raise ValueError("theta_thermal_true_urad and theta_correction_hat_urad must match")

    if nonthermal_error_urad is None:
        nonthermal_error_urad = np.zeros_like(theta_thermal_true_urad)
    else:
        nonthermal_error_urad = np.asarray(nonthermal_error_urad, dtype=float)

    if theta_thermal_true_urad.shape != nonthermal_error_urad.shape:
        raise ValueError("nonthermal_error_urad must match theta_thermal_true_urad")

    scan_points = rectangular_spiral_scan(config.max_range_urad, config.step_urad)
    rows = []

    for i, theta_true in enumerate(theta_thermal_true_urad):
        pointing_error = nonthermal_error_urad[i] + theta_true - theta_correction_hat_urad[i]
        ok, tacq, residual, scan_idx = coarse_acquisition(
            pointing_error,
            scan_points,
            detect_radius_urad=config.detect_radius_urad,
            dwell_time_s=config.dwell_time_s,
        )

        rows.append(
            [
                float(ok),
                tacq,
                residual[0],
                residual[1],
                np.linalg.norm(residual),
                pointing_error[0],
                pointing_error[1],
                np.linalg.norm(pointing_error),
                np.linalg.norm(theta_true - theta_correction_hat_urad[i]),
                scan_idx,
            ]
        )

    return np.asarray(rows, dtype=float)


def summarize_acquisition(results: np.ndarray) -> dict[str, float]:
    success = results[:, 0].astype(bool)
    acquisition_time = results[:, 1]
    initial_error = results[:, 7]
    thermal_residual = results[:, 8]

    return {
        "success_rate": float(np.mean(success)),
        "mean_acquisition_time_s": float(np.nanmean(acquisition_time)),
        "median_acquisition_time_s": float(np.nanmedian(acquisition_time)),
        "p95_acquisition_time_s": float(np.nanpercentile(acquisition_time, 95)),
        "mean_initial_error_urad": float(np.nanmean(initial_error)),
        "p95_initial_error_urad": float(np.nanpercentile(initial_error, 95)),
        "mean_thermal_residual_urad": float(np.nanmean(thermal_residual)),
        "p95_thermal_residual_urad": float(np.nanpercentile(thermal_residual, 95)),
    }
