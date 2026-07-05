from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sgp4.api import Satrec, jday

from orbit.frames import teme_to_ecef


CELESTRAK_TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?CATNR={catnr}&FORMAT=TLE"


@dataclass(frozen=True)
class TleRecord:
    name: str
    line1: str
    line2: str
    epoch_utc: datetime

    @property
    def satrec(self) -> Satrec:
        return Satrec.twoline2rv(self.line1, self.line2)

    def propagate_ecef(self, unix_times_s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return propagate_tle_ecef(self, unix_times_s)


def _epoch_from_line1(line1: str) -> datetime:
    year = int(line1[18:20])
    year = 2000 + year if year < 57 else 1900 + year
    day_of_year = float(line1[20:32])
    whole_day = int(day_of_year)
    fraction = day_of_year - whole_day
    epoch = datetime(year, 1, 1, tzinfo=timezone.utc)
    return datetime.fromtimestamp(
        epoch.timestamp() + (whole_day - 1) * 86400.0 + fraction * 86400.0,
        tz=timezone.utc,
    )


def parse_tle_text(text: str) -> list[TleRecord]:
    """Parse one or more TLE triplets from plain text."""
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    records: list[TleRecord] = []
    index = 0

    while index < len(lines):
        if lines[index].startswith("1 "):
            if index + 1 >= len(lines) or not lines[index + 1].startswith("2 "):
                raise ValueError(f"Incomplete TLE starting at line {index + 1}")
            records.append(
                TleRecord(
                    name="UNKNOWN",
                    line1=lines[index],
                    line2=lines[index + 1],
                    epoch_utc=_epoch_from_line1(lines[index]),
                )
            )
            index += 2
            continue

        if index + 2 < len(lines) and lines[index + 1].startswith("1 "):
            records.append(
                TleRecord(
                    name=lines[index].strip(),
                    line1=lines[index + 1],
                    line2=lines[index + 2],
                    epoch_utc=_epoch_from_line1(lines[index + 1]),
                )
            )
            index += 3
            continue

        raise ValueError(f"Unrecognized TLE format near line {index + 1}: {lines[index]!r}")

    return records


def load_tle_file(path: Path) -> list[TleRecord]:
    return parse_tle_text(path.read_text(encoding="utf-8"))


def fetch_celestrak_tle(norad_cat_id: int) -> TleRecord:
    url = CELESTRAK_TLE_URL.format(catnr=norad_cat_id)
    with urllib.request.urlopen(url, timeout=30) as response:
        text = response.read().decode("utf-8")
    records = parse_tle_text(text)
    if not records:
        raise ValueError(f"No TLE returned for NORAD ID {norad_cat_id}")
    return records[0]


def fetch_celestrak_json(norad_cat_id: int) -> dict:
    url = (
        "https://celestrak.org/NORAD/elements/gp.php?"
        f"CATNR={norad_cat_id}&FORMAT=JSON"
    )
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = json.load(response)
    if not payload:
        raise ValueError(f"No GP JSON returned for NORAD ID {norad_cat_id}")
    return payload[0]


def select_tle_for_age(records: list[TleRecord], evaluation_time: datetime) -> TleRecord:
    """Pick the latest TLE whose epoch is not after the evaluation time."""
    evaluation_time = evaluation_time.astimezone(timezone.utc)
    eligible = [record for record in records if record.epoch_utc <= evaluation_time]
    if not eligible:
        raise ValueError(
            "No TLE/GP record with epoch <= evaluation time. "
            "Provide GP history covering the POD window instead of a single future TLE."
        )
    return max(eligible, key=lambda record: record.epoch_utc)


def select_ephemeris_for_time(
    records: list,
    evaluation_time: datetime,
):
    """Pick the latest ephemeris record usable for forward propagation at evaluation_time."""
    return select_tle_for_age(records, evaluation_time)


def propagate_tle_ecef(
    record: TleRecord,
    unix_times_s: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Propagate a TLE to ECEF position/velocity using SGP4."""
    satrec = record.satrec
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
