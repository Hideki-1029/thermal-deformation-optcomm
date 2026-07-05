from __future__ import annotations

import math
from datetime import datetime, timezone

import numpy as np
from sgp4.api import jday


def _gmst_rad(unix_time_s: float) -> float:
    dt = datetime.fromtimestamp(unix_time_s, tz=timezone.utc)
    jd, fr = jday(
        dt.year,
        dt.month,
        dt.day,
        dt.hour,
        dt.minute,
        dt.second + dt.microsecond * 1e-6,
    )
    julian_centuries = ((jd - 2451545.0) + fr) / 36525.0
    gmst_deg = (
        280.46061837
        + 360.98564736629 * ((jd - 2451545.0) + fr)
        + 0.000387933 * julian_centuries**2
        - julian_centuries**3 / 38710000.0
    )
    return math.radians(gmst_deg % 360.0)


def teme_to_ecef(
    position_teme_m: np.ndarray,
    velocity_teme_m_s: np.ndarray,
    unix_time_s: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert TEME state vectors to ECEF using a simple Earth-rotation model."""
    theta = _gmst_rad(unix_time_s)
    cos_theta = math.cos(theta)
    sin_theta = math.sin(theta)

    rotation = np.array(
        [
            [cos_theta, sin_theta, 0.0],
            [-sin_theta, cos_theta, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    omega_earth_rad_s = 7.2921150e-5
    omega = np.array([0.0, 0.0, omega_earth_rad_s], dtype=float)
    position_ecef = rotation @ position_teme_m
    velocity_ecef = rotation @ velocity_teme_m_s - np.cross(omega, position_ecef)
    return position_ecef, velocity_ecef
