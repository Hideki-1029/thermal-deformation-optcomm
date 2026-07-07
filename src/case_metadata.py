from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

MU_EARTH_M3_S2 = 3.986004418e14
EARTH_RADIUS_M = 6378137.0


@dataclass(frozen=True)
class CaseMetadataPaths:
    case_matrix_xlsx: Path
    case_matrix_sheet: str = "case_matrix"
    orbit_catalog_xlsx: Path | None = None
    orbit_catalog_sheet: str = "orbit_catalog"


def _is_valid_number(value: Any) -> bool:
    if value is None:
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number > 0.0


def keplerian_period_s_from_altitude_km(altitude_km: float) -> float:
    semi_major_axis_m = EARTH_RADIUS_M + altitude_km * 1000.0
    return float(2.0 * math.pi * math.sqrt(semi_major_axis_m**3 / MU_EARTH_M3_S2))


def _read_excel_table(path: Path, sheet_name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Case metadata Excel not found: {path}")
    return pd.read_excel(path, sheet_name=sheet_name)


def _find_case_matrix_row(case_matrix: pd.DataFrame, case_id: str) -> pd.Series | None:
    if "case_id" not in case_matrix.columns:
        return None

    matches = case_matrix[case_matrix["case_id"].astype(str) == case_id]
    if len(matches) == 1:
        return matches.iloc[0]
    if len(matches) > 1:
        raise ValueError(f"case_id {case_id!r} matched multiple rows in case_matrix")
    return None


def _find_orbit_catalog_row(
    orbit_catalog: pd.DataFrame,
    orbit_case: str,
) -> pd.Series | None:
    if "td_orbit_name" not in orbit_catalog.columns:
        return None

    names = orbit_catalog["td_orbit_name"].astype(str)
    exact = orbit_catalog[names == orbit_case]
    if len(exact) == 1:
        return exact.iloc[0]
    if len(exact) > 1:
        raise ValueError(f"orbit_case {orbit_case!r} matched multiple orbit_catalog rows")

    prefix_matches: list[tuple[int, pd.Series]] = []
    for _, row in orbit_catalog.iterrows():
        catalog_name = str(row["td_orbit_name"])
        if orbit_case.startswith(catalog_name):
            prefix_matches.append((len(catalog_name), row))

    if not prefix_matches:
        return None

    return max(prefix_matches, key=lambda item: item[0])[1]


def _orbit_period_from_catalog_row(row: pd.Series) -> float | None:
    if "orbit_period_s" in row.index and _is_valid_number(row["orbit_period_s"]):
        return float(row["orbit_period_s"])

    altitudes_km: list[float] = []
    for column in ("min_alt_km", "max_alt_km"):
        if column in row.index and _is_valid_number(row[column]):
            altitudes_km.append(float(row[column]))

    if not altitudes_km:
        return None

    mean_altitude_km = sum(altitudes_km) / len(altitudes_km)
    return keplerian_period_s_from_altitude_km(mean_altitude_km)


def resolve_orbit_period_s(
    case_id: str,
    metadata_paths: CaseMetadataPaths,
    default_period_s: float,
) -> float:
    """
    Resolve orbit period [s] for a case from Excel metadata.

    Priority:
    1. case_matrix.orbit_period_s for the case_id row
    2. orbit_catalog.orbit_period_s via case_matrix.orbit_case
    3. Keplerian period from orbit_catalog min/max altitude when orbit_period_s is blank
    4. default_period_s from config
    """
    if not _is_valid_number(default_period_s):
        raise ValueError(f"default_period_s must be positive, got {default_period_s!r}")

    case_matrix = _read_excel_table(
        metadata_paths.case_matrix_xlsx,
        metadata_paths.case_matrix_sheet,
    )
    case_row = _find_case_matrix_row(case_matrix, case_id)
    if case_row is None:
        return float(default_period_s)

    if "orbit_period_s" in case_row.index and _is_valid_number(case_row["orbit_period_s"]):
        return float(case_row["orbit_period_s"])

    orbit_case = case_row.get("orbit_case")
    if (
        metadata_paths.orbit_catalog_xlsx is None
        or pd.isna(orbit_case)
        or str(orbit_case).strip() == ""
    ):
        return float(default_period_s)

    orbit_catalog = _read_excel_table(
        metadata_paths.orbit_catalog_xlsx,
        metadata_paths.orbit_catalog_sheet,
    )
    orbit_row = _find_orbit_catalog_row(orbit_catalog, str(orbit_case))
    if orbit_row is None:
        return float(default_period_s)

    orbit_period_s = _orbit_period_from_catalog_row(orbit_row)
    if orbit_period_s is None:
        return float(default_period_s)

    return float(orbit_period_s)
