from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

S1_ORBITS_BASE_URL = "https://s1-orbits.s3.us-west-2.amazonaws.com"


@dataclass(frozen=True)
class OrbitState:
    utc: datetime
    position_m: np.ndarray
    velocity_m_s: np.ndarray


def _parse_utc(value: str) -> datetime:
    cleaned = value.removeprefix("UTC=")
    return datetime.fromisoformat(cleaned).replace(tzinfo=timezone.utc)


def load_sentinel1_eof(path: Path) -> list[OrbitState]:
    """Parse a Sentinel-1 AUX_*ORB .EOF file (Earth-fixed position/velocity)."""
    root = ET.parse(path).getroot()
    states: list[OrbitState] = []

    for osv in root.findall(".//OSV"):
        utc_text = osv.findtext("UTC")
        if utc_text is None:
            continue

        position = np.array(
            [
                float(osv.findtext("X")),
                float(osv.findtext("Y")),
                float(osv.findtext("Z")),
            ],
            dtype=float,
        )
        velocity = np.array(
            [
                float(osv.findtext("VX")),
                float(osv.findtext("VY")),
                float(osv.findtext("VZ")),
            ],
            dtype=float,
        )
        states.append(
            OrbitState(
                utc=_parse_utc(utc_text),
                position_m=position,
                velocity_m_s=velocity,
            )
        )

    if not states:
        raise ValueError(f"No OSV records found in {path}")

    states.sort(key=lambda item: item.utc)
    return states


def load_sentinel1_poeorb(path: Path) -> list[OrbitState]:
    """Parse a Sentinel-1 AUX_POEORB .EOF file (alias of ``load_sentinel1_eof``)."""
    return load_sentinel1_eof(path)


def parse_orbit_key_validity(key: str) -> tuple[datetime, datetime] | None:
    """Parse validity [start, stop] from an S1 orbit object key / filename."""
    name = Path(key).name
    marker = name.split("_V", maxsplit=1)
    if len(marker) != 2:
        return None
    start_stop = marker[1].removesuffix(".EOF").split("_", maxsplit=1)
    if len(start_stop) != 2:
        return None
    try:
        start_time = datetime.strptime(start_stop[0], "%Y%m%dT%H%M%S").replace(
            tzinfo=timezone.utc
        )
        stop_time = datetime.strptime(start_stop[1], "%Y%m%dT%H%M%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None
    return start_time, stop_time


def find_resorb_keys_covering(
    t_start: datetime,
    t_stop: datetime,
    *,
    prefix: str = "AUX_RESORB/S1A_",
) -> list[str]:
    """List RESORB keys whose validity window overlaps ``[t_start, t_stop]``."""
    start = t_start.astimezone(timezone.utc)
    stop = t_stop.astimezone(timezone.utc)
    keys = list_s1_orbit_keys(prefix=prefix)
    covering: list[str] = []
    for key in keys:
        window = parse_orbit_key_validity(key)
        if window is None:
            continue
        key_start, key_stop = window
        if key_start <= stop and key_stop >= start:
            covering.append(key)
    return sorted(covering)


def list_s1_orbit_keys(prefix: str = "AUX_POEORB/S1A_", max_keys: int = 1000) -> list[str]:
    """List object keys in the public s1-orbits S3 bucket (no AWS account required)."""
    keys: list[str] = []
    continuation_token: str | None = None

    while True:
        query = {
            "list-type": "2",
            "prefix": prefix,
            "max-keys": str(max_keys),
        }
        if continuation_token is not None:
            query["continuation-token"] = continuation_token

        url = f"{S1_ORBITS_BASE_URL}/?{urllib.parse.urlencode(query)}"
        with urllib.request.urlopen(url, timeout=60) as response:
            root = ET.fromstring(response.read())

        namespace = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
        keys.extend(
            key.text
            for key in root.findall("s3:Contents/s3:Key", namespace)
            if key.text is not None
        )

        truncated = root.findtext("s3:IsTruncated", default="false", namespaces=namespace)
        token_element = root.find("s3:NextContinuationToken", namespace)
        if truncated != "true" or token_element is None or token_element.text is None:
            break
        continuation_token = token_element.text

    return keys


def download_s1_orbit_key(key: str, output_path: Path) -> Path:
    """Download one Sentinel-1 orbit file from the public s1-orbits bucket."""
    url = f"{S1_ORBITS_BASE_URL}/{key}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, output_path)
    return output_path


def find_poeorb_key_nearest_to_time(target_time: datetime) -> str | None:
    """Find the POEORB file whose validity interval is closest to target_time."""
    target = target_time.astimezone(timezone.utc)
    keys = list_s1_orbit_keys()

    best_key: str | None = None
    best_delta = float("inf")
    for key in keys:
        marker = key.split("_V", maxsplit=1)
        if len(marker) != 2:
            continue
        start_stop = marker[1].removesuffix(".EOF").split("_", maxsplit=1)
        if len(start_stop) != 2:
            continue
        try:
            start_time = datetime.strptime(start_stop[0], "%Y%m%dT%H%M%S").replace(
                tzinfo=timezone.utc
            )
            stop_time = datetime.strptime(start_stop[1], "%Y%m%dT%H%M%S").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue

        if start_time <= target <= stop_time:
            return key

        delta = min(abs((start_time - target).total_seconds()), abs((stop_time - target).total_seconds()))
        if delta < best_delta:
            best_delta = delta
            best_key = key
    return best_key


def find_poeorb_key_for_validity_start(validity_start: datetime) -> str | None:
    """Find a POEORB file whose validity start is closest to the requested UTC time."""
    target = validity_start.astimezone(timezone.utc)
    target_token = target.strftime("V%Y%m%dT225942")

    keys = list_s1_orbit_keys()
    candidates = [key for key in keys if target_token in key]
    if candidates:
        return sorted(candidates)[0]

    best_key: str | None = None
    best_delta = float("inf")
    for key in keys:
        marker = key.split("_V", maxsplit=1)
        if len(marker) != 2:
            continue
        start_token = marker[1].split("_", maxsplit=1)[0]
        try:
            start_time = datetime.strptime(start_token, "%Y%m%dT%H%M%S").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
        delta = abs((start_time - target).total_seconds())
        if delta < best_delta:
            best_delta = delta
            best_key = key
    return best_key


def states_to_arrays(states: list[OrbitState]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return unix time [s], position [N,3], velocity [N,3] arrays."""
    times_s = np.array([state.utc.timestamp() for state in states], dtype=float)
    positions_m = np.stack([state.position_m for state in states], axis=0)
    velocities_m_s = np.stack([state.velocity_m_s for state in states], axis=0)
    return times_s, positions_m, velocities_m_s
