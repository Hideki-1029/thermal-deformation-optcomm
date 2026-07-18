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


def _earth_rotation_matrix(unix_time_s: float) -> np.ndarray:
    theta = _gmst_rad(unix_time_s)
    cos_theta = math.cos(theta)
    sin_theta = math.sin(theta)
    return np.array(
        [
            [cos_theta, sin_theta, 0.0],
            [-sin_theta, cos_theta, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=float,
    )


def teme_to_ecef(
    position_teme_m: np.ndarray,
    velocity_teme_m_s: np.ndarray,
    unix_time_s: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert TEME state vectors to ECEF using a simple Earth-rotation model."""
    rotation = _earth_rotation_matrix(unix_time_s)
    omega_earth_rad_s = 7.2921150e-5
    omega = np.array([0.0, 0.0, omega_earth_rad_s], dtype=float)
    position_ecef = rotation @ position_teme_m
    velocity_ecef = rotation @ velocity_teme_m_s - np.cross(omega, position_ecef)
    return position_ecef, velocity_ecef


def sun_unit_eci(utc: datetime) -> np.ndarray:
    """Low-precision sun direction in mean equator / equinox of date (unit)."""
    jd, fr = jday(
        utc.year,
        utc.month,
        utc.day,
        utc.hour,
        utc.minute,
        utc.second + utc.microsecond * 1e-6,
    )
    n = (jd - 2451545.0) + fr
    mean_lon_deg = (280.460 + 0.9856474 * n) % 360.0
    mean_anom_deg = (357.528 + 0.9856003 * n) % 360.0
    g = math.radians(mean_anom_deg)
    ecliptic_lon = math.radians(
        mean_lon_deg + 1.915 * math.sin(g) + 0.020 * math.sin(2.0 * g)
    )
    eps = math.radians(23.439 - 0.0000004 * n)
    return np.array(
        [
            math.cos(ecliptic_lon),
            math.cos(eps) * math.sin(ecliptic_lon),
            math.sin(eps) * math.sin(ecliptic_lon),
        ],
        dtype=float,
    )


def sun_unit_ecef(utc: datetime) -> np.ndarray:
    """Approximate sun unit vector in ECEF (same GMST model as TEME→ECEF)."""
    if utc.tzinfo is None:
        utc = utc.replace(tzinfo=timezone.utc)
    else:
        utc = utc.astimezone(timezone.utc)
    unix_time_s = utc.timestamp()
    sun_eci = sun_unit_eci(utc)
    return _earth_rotation_matrix(unix_time_s) @ sun_eci
