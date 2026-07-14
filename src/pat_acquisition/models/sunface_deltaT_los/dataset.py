"""Dataset helpers for the minimal sunface ΔT model."""

from __future__ import annotations

from pathlib import Path

# Reuse case resolution / loading from the original sunface package.
from pat_acquisition.models.sunface_los.dataset import (  # noqa: F401
    CASE_PRESETS,
    DEFAULT_DATASET,
    case_ids_from_numbers,
    list_numbered_cases,
    list_supported_case_ids,
    load_case_frame,
    resolve_short_case,
    resolve_sunface_case_ids,
    short_case_tag,
    within_case_split_mask,
)

DEFAULT_OUTPUT_ROOT = (
    Path(__file__).resolve().parents[4]
    / "results"
    / "pat_acquisition"
    / "sunface_deltaT_los_model"
)
