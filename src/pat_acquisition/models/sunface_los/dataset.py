from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from thermal_desktop.case_selection import case_number_from_name, parse_case_spec

from pat_acquisition.models.sunface_los.features import (
    normalize_sun_direction,
    resolve_dominant_axis,
)

DEFAULT_DATASET = (
    Path(__file__).resolve().parents[4]
    / "results"
    / "pat_acquisition"
    / "lightweight_dataset"
    / "lightweight_dataset_all.csv"
)
DEFAULT_OUTPUT_ROOT = (
    Path(__file__).resolve().parents[4]
    / "results"
    / "pat_acquisition"
    / "sunface_los_model"
)

CASE_PRESETS = {
    "04": "04_LTAN06_800km_1213COLD_MY_ALL_HEAT_MY_0p5",
    "05": "05_LTAN06_800km_1213COLD_PX_ALL_HEAT_PX_0p5",
    "06": "06_LTAN06_800km_1213COLD_PX_STTLCT_HEAT_PX_0p5",
}


def list_supported_case_ids(dataset_path: Path) -> list[str]:
    df = pd.read_csv(dataset_path, usecols=["case_id", "case_sun_direction_body"])
    rows = df.groupby("case_id", sort=True)["case_sun_direction_body"].first()
    supported: list[str] = []
    for case_id, sun_direction in rows.items():
        face = normalize_sun_direction(sun_direction)
        try:
            resolve_dominant_axis(face)
        except ValueError:
            continue
        supported.append(str(case_id))
    return supported


def list_numbered_cases(dataset_path: Path) -> list[tuple[int, str, str, bool]]:
    """Return ``(number, case_id, sun_face, supported)`` for each dataset case."""
    df = pd.read_csv(dataset_path, usecols=["case_id", "case_sun_direction_body"])
    rows = df.groupby("case_id", sort=True)["case_sun_direction_body"].first()
    numbered: list[tuple[int, str, str, bool]] = []
    for case_id, sun_direction in rows.items():
        number = case_number_from_name(str(case_id))
        if number is None:
            continue
        sun_face = normalize_sun_direction(sun_direction)
        try:
            resolve_dominant_axis(sun_face)
            supported = True
        except ValueError:
            supported = False
        numbered.append((number, str(case_id), sun_face, supported))
    numbered.sort(key=lambda row: row[0])
    return numbered


def case_ids_from_numbers(dataset_path: Path, numbers: list[int]) -> list[str]:
    by_number = {number: case_id for number, case_id, _, _ in list_numbered_cases(dataset_path)}
    missing = sorted(set(numbers) - set(by_number))
    if missing:
        available = sorted(by_number)
        raise ValueError(
            f"Case number(s) not found in dataset: {missing}. "
            f"Available: {available}. "
            "Run with --list-cases to inspect case ids."
        )
    return [by_number[number] for number in sorted(numbers)]


def resolve_short_case(dataset_path: Path, case: str) -> str:
    """Resolve ``--case 4`` / ``--case 04`` to a full case id."""
    text = str(case).strip()
    if text.isdigit():
        return case_ids_from_numbers(dataset_path, [int(text)])[0]
    if text in CASE_PRESETS:
        return CASE_PRESETS[text]
    raise ValueError(
        f"Unknown --case {case!r}. Use a case number (4 or 04) or run --list-cases."
    )


def resolve_sunface_case_ids(
    dataset_path: Path,
    *,
    cases: str | None = None,
    case: str | None = None,
    case_ids: list[str] | None = None,
    default_all_supported: bool = False,
) -> tuple[list[str], list[str]]:
    """
    Resolve case IDs from CLI options.

    Returns ``(selected_case_ids, skipped_unsupported)``.
    """
    requested: list[str] = []
    if case_ids:
        requested.extend(case_ids)
    if case:
        requested.append(resolve_short_case(dataset_path, case))
    if cases:
        requested.extend(case_ids_from_numbers(dataset_path, parse_case_spec(cases)))

    if not requested:
        if default_all_supported:
            return list_supported_case_ids(dataset_path), []
        raise ValueError("Specify --cases, --case, or --case-id.")

    seen: set[str] = set()
    unique_requested: list[str] = []
    for case_id in requested:
        if case_id not in seen:
            seen.add(case_id)
            unique_requested.append(case_id)

    supported = set(list_supported_case_ids(dataset_path))
    selected: list[str] = []
    skipped: list[str] = []
    for case_id in unique_requested:
        if case_id in supported:
            selected.append(case_id)
        else:
            skipped.append(case_id)

    if not selected:
        raise ValueError("No supported sunface cases in selection (need MX/MY/PX/PY).")
    return selected, skipped


def short_case_tag(case_id: str) -> str:
    prefix = str(case_id).split("_", 1)[0]
    return f"case{prefix}" if prefix.isdigit() else "case"


def load_case_frame(dataset_path: Path, case_id: str) -> pd.DataFrame:
    df = pd.read_csv(dataset_path)
    case_df = df[df["case_id"].astype(str) == case_id].copy()
    if case_df.empty:
        raise ValueError(f"No rows found for case_id={case_id!r} in {dataset_path}")

    case_df = case_df.sort_values("time_s")
    case_df = case_df.groupby("time_s", as_index=False).mean(numeric_only=True)
    meta = df[df["case_id"].astype(str) == case_id].iloc[0]
    for col in ("case_id", "case_sun_direction_body", "case_stt_location", "case_lct_location"):
        if col in meta.index:
            case_df[col] = meta[col]
    return case_df.reset_index(drop=True)


def within_case_split_mask(
    times_s: np.ndarray,
    orbit_period_s: float,
    train_orbits: float,
) -> np.ndarray:
    t0 = float(times_s[0])
    train_end = t0 + train_orbits * orbit_period_s
    return times_s <= train_end
