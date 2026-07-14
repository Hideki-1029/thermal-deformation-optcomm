"""Case-level features for b_case ≈ b0(sun) + c_p·I_prop + c_c·I_pcdu."""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd

from pat_acquisition.models.sunface_los.features import normalize_sun_direction

SUN_FACES = ("MX", "MY", "PX", "PY")
DEFAULT_HEAT_FACES = ("MY", "PY")


def heat_indicator(value: Any, threshold_w: float = 0.5) -> int:
    try:
        return int(float(value) > threshold_w)
    except (TypeError, ValueError):
        return 0


def case_heat_flags(case_df: pd.DataFrame) -> tuple[int, int]:
    """Return (I_prop, I_pcdu) from lightweight_dataset case_* columns."""
    row = case_df.iloc[0]
    i_prop = heat_indicator(row.get("case_prop_heat_w", 0.0))
    i_pcdu = heat_indicator(row.get("case_pcdu_heat_w", 0.0))
    return i_prop, i_pcdu


def parse_heat_faces(text: str | None) -> tuple[str, ...]:
    if text is None or not str(text).strip():
        return DEFAULT_HEAT_FACES
    raw = str(text).strip().lower()
    if raw in {"all", "*"}:
        return SUN_FACES
    faces: list[str] = []
    for part in str(text).replace(";", ",").split(","):
        face = normalize_sun_direction(part.strip())
        if face not in SUN_FACES:
            raise ValueError(f"Unsupported heat face {part!r}; expected MX/MY/PX/PY or all")
        if face not in faces:
            faces.append(face)
    if not faces:
        raise ValueError("heat_faces resolved empty")
    return tuple(faces)


def build_bcase_design_matrix(
    sun_faces: Iterable[str],
    i_prop: Iterable[int],
    i_pcdu: Iterable[int],
    *,
    heat_faces: tuple[str, ...] = DEFAULT_HEAT_FACES,
) -> tuple[np.ndarray, list[str]]:
    """
    Design matrix without a global intercept:

      [1_MX, 1_MY, 1_PX, 1_PY, I_prop_eff, I_pcdu_eff]

    Heat indicators are zeroed when sun_face not in ``heat_faces``.
    """
    faces = [normalize_sun_direction(s) for s in sun_faces]
    props = np.asarray(list(i_prop), dtype=float)
    pcdus = np.asarray(list(i_pcdu), dtype=float)
    n = len(faces)
    if len(props) != n or len(pcdus) != n:
        raise ValueError("sun_faces / I_prop / I_pcdu length mismatch")

    heat_set = {normalize_sun_direction(f) for f in heat_faces}
    x = np.zeros((n, 6), dtype=float)
    for i, face in enumerate(faces):
        if face not in SUN_FACES:
            raise ValueError(f"Unsupported sun face for bcase model: {face!r}")
        x[i, SUN_FACES.index(face)] = 1.0
        if face in heat_set:
            x[i, 4] = props[i]
            x[i, 5] = pcdus[i]

    names = [f"b0_{face}" for face in SUN_FACES] + ["c_prop", "c_pcdu"]
    return x, names
