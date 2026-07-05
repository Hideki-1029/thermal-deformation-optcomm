from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


def load_orbit_error_timeseries_csv(
    path: Path,
) -> tuple[np.ndarray, np.ndarray, str]:
    """
    Load ISL orbit angle error [urad, 2] and the associated time base.

    Returns (times_s, errors_urad, time_mode) where time_mode is either
    ``elapsed_time_s`` or ``unix_time_s``.
    """
    times_s: list[float] = []
    errors: list[list[float]] = []
    time_column = "elapsed_time_s"

    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        if "elapsed_time_s" in fieldnames:
            time_column = "elapsed_time_s"
        elif "unix_time_s" in fieldnames:
            time_column = "unix_time_s"
        else:
            raise ValueError(
                f"{path} must contain elapsed_time_s or unix_time_s columns"
            )

        required = {time_column, "isl_angle_x_urad", "isl_angle_y_urad"}
        missing = required.difference(fieldnames)
        if missing:
            raise ValueError(f"{path} is missing required columns: {sorted(missing)}")

        for row in reader:
            times_s.append(float(row[time_column]))
            errors.append(
                [float(row["isl_angle_x_urad"]), float(row["isl_angle_y_urad"])]
            )

    if not times_s:
        raise ValueError(f"No rows found in {path}")

    if time_column == "unix_time_s":
        times = np.asarray(times_s, dtype=float)
        times = times - times[0]
        return times, np.asarray(errors, dtype=float), "unix_time_s"

    return np.asarray(times_s, dtype=float), np.asarray(errors, dtype=float), "elapsed_time_s"


def resample_orbit_error_to_times(
    orbit_times_s: np.ndarray,
    orbit_error_urad: np.ndarray,
    target_times_s: np.ndarray,
    mode: str = "cyclic",
) -> np.ndarray:
    """Resample orbit error to Femap simulation times."""
    target_times_s = np.asarray(target_times_s, dtype=float)
    orbit_times_s = np.asarray(orbit_times_s, dtype=float)
    if len(orbit_times_s) == 1:
        return np.repeat(orbit_error_urad[:1], len(target_times_s), axis=0)

    duration = float(orbit_times_s[-1] - orbit_times_s[0])
    if duration <= 0.0:
        return np.repeat(orbit_error_urad[:1], len(target_times_s), axis=0)

    if mode == "cyclic":
        mapped_times = np.mod(target_times_s, duration)
    elif mode == "clamp":
        mapped_times = np.clip(target_times_s, orbit_times_s[0], orbit_times_s[-1])
    else:
        raise ValueError(f"Unsupported orbit error resample mode: {mode}")

    resampled = np.zeros((len(target_times_s), 2), dtype=float)
    for axis in range(2):
        resampled[:, axis] = np.interp(
            mapped_times,
            orbit_times_s,
            orbit_error_urad[:, axis],
        )
    return resampled
