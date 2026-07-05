from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def position_error_to_rtn(
    position_error_ecef_m: np.ndarray,
    position_ecef_m: np.ndarray,
    velocity_ecef_m_s: np.ndarray,
) -> np.ndarray:
    """Project ECEF position error into radial / along-track / cross-track [m]."""
    radial = position_ecef_m / np.linalg.norm(position_ecef_m)
    cross_track = np.cross(position_ecef_m, velocity_ecef_m_s)
    cross_norm = np.linalg.norm(cross_track)
    if cross_norm <= 0.0:
        raise ValueError("Cannot define RTN frame from collinear position and velocity")
    cross_track /= cross_norm
    along_track = np.cross(cross_track, radial)

    basis = np.vstack([radial, along_track, cross_track])
    return basis @ position_error_ecef_m


def position_error_to_isl_angle_urad(
    position_error_ecef_m: np.ndarray,
    position_ecef_m: np.ndarray,
    partner_position_ecef_m: np.ndarray,
) -> np.ndarray:
    """
    Convert chaser position error to ISL LOS angular error [urad, 2].

    The partner satellite is treated as perfectly known (GNSS-equipped).
    """
    range_vector = partner_position_ecef_m - position_ecef_m
    range_m = np.linalg.norm(range_vector)
    if range_m <= 0.0:
        raise ValueError("Partner range must be positive")

    los_unit = range_vector / range_m
    perpendicular = position_error_ecef_m - np.dot(position_error_ecef_m, los_unit) * los_unit
    angle_rad = np.linalg.norm(perpendicular) / range_m

    if np.linalg.norm(perpendicular) <= 0.0:
        return np.zeros(2, dtype=float)

    # Map the perpendicular error into an arbitrary but stable 2D PAT basis.
    reference = np.array([0.0, 0.0, 1.0], dtype=float)
    if abs(np.dot(reference, los_unit)) > 0.95:
        reference = np.array([0.0, 1.0, 0.0], dtype=float)
    axis_x = np.cross(los_unit, reference)
    axis_x /= np.linalg.norm(axis_x)
    axis_y = np.cross(los_unit, axis_x)
    components = np.array(
        [
            np.dot(perpendicular, axis_x),
            np.dot(perpendicular, axis_y),
        ],
        dtype=float,
    )
    scale = angle_rad / np.linalg.norm(perpendicular)
    return components * scale * 1.0e6


def nominal_isl_partner_position(
    position_ecef_m: np.ndarray,
    velocity_ecef_m_s: np.ndarray,
    range_m: float,
) -> np.ndarray:
    """Place a partner satellite range_m ahead along the along-track direction."""
    rtn_offset = np.array([0.0, range_m, 0.0], dtype=float)
    radial = position_ecef_m / np.linalg.norm(position_ecef_m)
    cross_track = np.cross(position_ecef_m, velocity_ecef_m_s)
    cross_track /= np.linalg.norm(cross_track)
    along_track = np.cross(cross_track, radial)
    basis = np.vstack([radial, along_track, cross_track])
    return position_ecef_m + rtn_offset @ basis
