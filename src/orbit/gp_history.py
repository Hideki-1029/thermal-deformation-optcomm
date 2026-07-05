from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import numpy as np
from sgp4.api import Satrec, WGS72, jday
from sgp4 import omm

from orbit.frames import teme_to_ecef


class EphemerisRecord(Protocol):
    name: str
    epoch_utc: datetime

    def propagate_ecef(self, unix_times_s: np.ndarray) -> tuple[np.ndarray, np.ndarray]: ...


@dataclass(frozen=True)
class GpRecord:
    name: str
    norad_cat_id: int
    epoch_utc: datetime
    fields: dict[str, str]

    def propagate_ecef(self, unix_times_s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return propagate_gp_record(self, unix_times_s)


def _row_to_omm_fields(row, norad_cat_id: int) -> dict[str, str]:
    epoch = row["epoch"].to_pydatetime().replace(tzinfo=None)
    return {
        "CLASSIFICATION_TYPE": "U",
        "OBJECT_ID": str(row.get("intl_designator", "2014-016A")),
        "EPHEMERIS_TYPE": "0",
        "ELEMENT_SET_NO": "999",
        "REV_AT_EPOCH": "0",
        "EPOCH": epoch.strftime("%Y-%m-%dT%H:%M:%S.") + f"{epoch.microsecond:06d}",
        "MEAN_MOTION_DOT": str(row["mean_motion_dot"] if row["mean_motion_dot"] is not None else 0.0),
        "MEAN_MOTION_DDOT": "0",
        "BSTAR": str(row["bstar"] if row["bstar"] is not None else 0.0),
        "ECCENTRICITY": str(row["eccentricity"]),
        "ARG_OF_PERICENTER": str(row["arg_perigee"]),
        "INCLINATION": str(row["inclination"]),
        "MEAN_ANOMALY": str(row["mean_anomaly"]),
        "MEAN_MOTION": str(row["mean_motion"]),
        "RA_OF_ASC_NODE": str(row["raan"]),
        "NORAD_CAT_ID": str(norad_cat_id),
    }


def load_gp_history_parquet(path: Path, norad_cat_id: int) -> list[GpRecord]:
    """Load NORAD GP history rows from a Space-Track-style parquet export."""
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ImportError(
            "pyarrow is required to read GP history parquet. "
            "Install it with: python -m pip install pyarrow"
        ) from exc

    table = pq.read_table(path, filters=[("norad_id", "==", norad_cat_id)])
    dataframe = table.to_pandas().sort_values("epoch").reset_index(drop=True)
    if dataframe.empty:
        raise ValueError(f"No GP records for NORAD {norad_cat_id} in {path}")

    records: list[GpRecord] = []
    for _, row in dataframe.iterrows():
        fields = _row_to_omm_fields(row, norad_cat_id)
        records.append(
            GpRecord(
                name="SENTINEL-1A",
                norad_cat_id=norad_cat_id,
                epoch_utc=datetime.fromisoformat(fields["EPOCH"]).replace(tzinfo=timezone.utc),
                fields=fields,
            )
        )
    return records


def propagate_gp_record(
    record: GpRecord,
    unix_times_s: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Propagate one GP record forward to ECEF position/velocity using SGP4."""
    satrec = Satrec()
    omm.initialize(satrec, record.fields, WGS72)

    positions = np.zeros((len(unix_times_s), 3), dtype=float)
    velocities = np.zeros((len(unix_times_s), 3), dtype=float)
    for index, unix_time in enumerate(unix_times_s):
        dt = datetime.fromtimestamp(float(unix_time), tz=timezone.utc)
        jd, fr = jday(
            dt.year,
            dt.month,
            dt.day,
            dt.hour,
            dt.minute,
            dt.second + dt.microsecond * 1e-6,
        )
        error_code, position_teme, velocity_teme = satrec.sgp4(jd, fr)
        if error_code != 0:
            positions[index, :] = np.nan
            velocities[index, :] = np.nan
            continue

        position_teme_m = np.asarray(position_teme, dtype=float) * 1000.0
        velocity_teme_m_s = np.asarray(velocity_teme, dtype=float) * 1000.0
        position_ecef, velocity_ecef = teme_to_ecef(
            position_teme_m,
            velocity_teme_m_s,
            float(unix_time),
        )
        positions[index, :] = position_ecef
        velocities[index, :] = velocity_ecef

    return positions, velocities
