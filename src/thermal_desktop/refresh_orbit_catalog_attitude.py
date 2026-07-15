"""
Dump TD Orbit orientation and refresh orbit_catalog attitude columns.

Catalog editing model
---------------------
Edit (white): ``sun_face``, ``constraint_target``, ``constraint_face``,
Keplerian / notes.
Script-filled (gray): effective faces + TD internals (pointing, Rot*,
``constraint_type``, …). See ``orbit_catalog_io.py``.

Second-axis policy (option C)
-----------------------------
- ``constraint_target``: human ``velocity`` | ``nadir``
- ``constraint_face``: body face aimed at that target (second axis)
- ``constraint_type``: raw TD ``VELOCITY`` | ``PLANET`` (same fact, dump only)
- Both ``eff_velocity_face`` and ``eff_nadir_face`` are always filled;
  ``constraint_target`` decides which is the TD constraint vs triad third.

TD axis encoding (OpenTDv241, this model)
----------------------------------------
- PointingAxis: 0=+Z, 1=-Z (GUI only allows ±Z)
- ConstraintAxis: 3=+Y observed on all current *_SUN orbits
- Rot1/2/3Axis: 0=X, 1=Y, 2=Z  (0 is valid; never coalesce with ``or 1``)
- Effective body vectors: ``R.T @ v0`` with TD angles as stored

Usage (TD open)::

  python -m src.thermal_desktop.refresh_orbit_catalog_attitude --attach-only --dry-run
  python -m src.thermal_desktop.refresh_orbit_catalog_attitude --attach-only

Reorder / gray-style only (no TD)::

  python -m src.thermal_desktop.refresh_orbit_catalog_attitude --layout-only
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .opentd_runtime import DEFAULT_DWG, connect_thermal_desktop
from .orbit_catalog_io import load_archive_sheet, write_orbit_catalog_xlsx

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ORBIT_CATALOG = REPO_ROOT / "cases" / "orbit_catalog.xlsx"
SUN_FACE_RE = re.compile(r"_([MP][XYZ])_SUN$", re.IGNORECASE)

# Pointing (GUI ±Z only)
_POINTING_CODE_TO_VEC: dict[int, np.ndarray] = {
    0: np.array([0.0, 0.0, 1.0]),  # +Z
    1: np.array([0.0, 0.0, -1.0]),  # -Z
}

# Constraint codes observed / inferred for this DWG
_CONSTRAINT_CODE_TO_VEC: dict[int, np.ndarray] = {
    3: np.array([0.0, 1.0, 0.0]),  # +Y (GUI Additional Constraint on *_SUN)
}

# Additional-rotation axes: 0-based X/Y/Z
_ROT_AXIS_CODE_TO_VEC: dict[int, np.ndarray] = {
    0: np.array([1.0, 0.0, 0.0]),
    1: np.array([0.0, 1.0, 0.0]),
    2: np.array([0.0, 0.0, 1.0]),
}


def _log(msg: str) -> None:
    print(msg, flush=True)


def _fnum(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if hasattr(value, "GetValueSI"):
            return float(value.GetValueSI())
    except Exception:
        pass
    try:
        return float(str(value).replace("\r", "").replace("\n", "").split()[0])
    except Exception:
        return None


def _enum_name(value: Any) -> str:
    text = str(value)
    if "." in text:
        text = text.split(".")[-1]
    return text.strip().upper()


def vec_to_face_label(vec: np.ndarray, *, tol: float = 0.15) -> str:
    v = np.asarray(vec, dtype=float)
    n = np.linalg.norm(v)
    if n < 1e-12:
        return "UNKNOWN"
    v = v / n
    faces = [
        ("PX", np.array([1.0, 0.0, 0.0])),
        ("MX", np.array([-1.0, 0.0, 0.0])),
        ("PY", np.array([0.0, 1.0, 0.0])),
        ("MY", np.array([0.0, -1.0, 0.0])),
        ("PZ", np.array([0.0, 0.0, 1.0])),
        ("MZ", np.array([0.0, 0.0, -1.0])),
    ]
    best_name, best_dot = "UNKNOWN", -2.0
    for name, axis in faces:
        dot = float(np.dot(v, axis))
        if dot > best_dot:
            best_dot, best_name = dot, name
    if best_dot >= 1.0 - tol:
        return best_name
    return f"{best_name}~{best_dot:.2f}"


def vec_to_signed_axis_label(vec: np.ndarray) -> str:
    face = vec_to_face_label(vec, tol=0.01)
    return {
        "PX": "+X",
        "MX": "-X",
        "PY": "+Y",
        "MY": "-Y",
        "PZ": "+Z",
        "MZ": "-Z",
    }.get(face, face)


def rotation_matrix_axis_angle(axis_vec: np.ndarray, angle_deg: float) -> np.ndarray:
    axis = np.asarray(axis_vec, dtype=float)
    axis = axis / np.linalg.norm(axis)
    th = math.radians(float(angle_deg))
    c, s = math.cos(th), math.sin(th)
    x, y, z = axis
    return np.array(
        [
            [c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
            [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
            [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)],
        ],
        dtype=float,
    )


def additional_rotation_matrix(rot_axes: list[int], rot_degs: list[float]) -> np.ndarray:
    r = np.eye(3)
    for axis_code, angle in zip(rot_axes, rot_degs):
        if abs(float(angle)) < 1e-12:
            continue
        if int(axis_code) not in _ROT_AXIS_CODE_TO_VEC:
            raise KeyError(f"Unknown Rot*Axis code {axis_code}")
        axis = _ROT_AXIS_CODE_TO_VEC[int(axis_code)]
        r = rotation_matrix_axis_angle(axis, float(angle)) @ r
    return r


def effective_body_axes(
    *,
    pointing_vec: np.ndarray,
    constraint_vec: np.ndarray,
    rot_axes: list[int],
    rot_degs: list[float],
) -> dict[str, Any]:
    sun0 = np.asarray(pointing_vec, dtype=float)
    second0 = np.asarray(constraint_vec, dtype=float)
    sun0 = sun0 / np.linalg.norm(sun0)
    second0 = second0 / np.linalg.norm(second0)
    # Third axis of the attitude triad. Sign convention:
    # use velocity × sun (not sun × velocity) so that when sun ∥ orbit normal
    # (dawn-dusk / |β|~90°), third ≈ nadir (−r̂), not zenith (+r̂).
    third0 = np.cross(second0, sun0)
    n3 = np.linalg.norm(third0)
    if n3 < 1e-8:
        raise ValueError("Pointing and constraint axes are parallel")
    third0 = third0 / n3

    r = additional_rotation_matrix(rot_axes, rot_degs)
    rt = r.T
    return {
        "eff_sun_face": vec_to_face_label(rt @ sun0),
        "eff_second_face": vec_to_face_label(rt @ second0),
        "eff_triad_third_face": vec_to_face_label(rt @ third0),
    }


def assign_velocity_nadir_faces(
    *,
    constraint_target: str,
    eff_second_face: str,
    eff_triad_third_face: str,
) -> dict[str, str]:
    """
    Split second-axis vs triad-third into velocity / nadir columns.

    - constraint_target=velocity → velocity is set (second), nadir is effective (third)
    - constraint_target=nadir    → nadir is set (second), velocity is effective (third)
    """
    target = constraint_target.lower()
    if target == "velocity":
        return {
            "eff_velocity_face": eff_second_face,
            "eff_nadir_face": eff_triad_third_face,
            "eff_velocity_source": "constraint",
            "eff_nadir_source": "effective",
        }
    if target == "nadir":
        return {
            "eff_velocity_face": eff_triad_third_face,
            "eff_nadir_face": eff_second_face,
            "eff_velocity_source": "effective",
            "eff_nadir_source": "constraint",
        }
    return {
        "eff_velocity_face": "",
        "eff_nadir_face": "",
        "eff_velocity_source": "",
        "eff_nadir_source": "",
    }


def constraint_target_from_type(constraint_type: str) -> str:
    key = constraint_type.upper()
    if key in {"VELOCITY", "VEL"}:
        return "velocity"
    if key in {"PLANET", "NADIR"}:
        return "nadir"
    return key.lower()


def dump_orbit(orbit: Any) -> dict[str, Any]:
    # UpdateFromTD is unimplemented for Orbit on some OpenTD builds; attrs still work.
    try:
        orbit.UpdateFromTD()
    except Exception:
        pass

    pointing_code = int(getattr(orbit, "PointingAxis"))
    constraint_code = int(getattr(orbit, "ConstraintAxis"))
    orient = _enum_name(getattr(orbit, "OrientType", ""))
    constraint = _enum_name(getattr(orbit, "ConstraintType", ""))

    rot_axes = [
        int(getattr(orbit, "Rot1Axis")),
        int(getattr(orbit, "Rot2Axis")),
        int(getattr(orbit, "Rot3Axis")),
    ]
    rot_degs = [
        _fnum(getattr(orbit, "Rot1", 0.0)) or 0.0,
        _fnum(getattr(orbit, "Rot2", 0.0)) or 0.0,
        _fnum(getattr(orbit, "Rot3", 0.0)) or 0.0,
    ]

    if pointing_code not in _POINTING_CODE_TO_VEC:
        raise KeyError(f"Unknown PointingAxis code {pointing_code}")
    if constraint_code not in _CONSTRAINT_CODE_TO_VEC:
        raise KeyError(
            f"Unknown ConstraintAxis code {constraint_code}; "
            f"extend _CONSTRAINT_CODE_TO_VEC (known {sorted(_CONSTRAINT_CODE_TO_VEC)})"
        )

    pointing_vec = _POINTING_CODE_TO_VEC[pointing_code]
    constraint_vec = _CONSTRAINT_CODE_TO_VEC[constraint_code]
    constraint_target = constraint_target_from_type(constraint)

    eff = effective_body_axes(
        pointing_vec=pointing_vec,
        constraint_vec=constraint_vec,
        rot_axes=rot_axes,
        rot_degs=rot_degs,
    )
    vn = assign_velocity_nadir_faces(
        constraint_target=constraint_target,
        eff_second_face=eff["eff_second_face"],
        eff_triad_third_face=eff["eff_triad_third_face"],
    )

    return {
        "td_orbit_name": str(getattr(orbit, "Name", "") or ""),
        "orient_type": orient,
        "constraint_type": constraint,
        "constraint_target": constraint_target,
        "pointing_axis_code": pointing_code,
        "pointing_axis": vec_to_signed_axis_label(pointing_vec),
        "constraint_axis_code": constraint_code,
        "constraint_axis": vec_to_signed_axis_label(constraint_vec),
        "rot1_axis_code": rot_axes[0],
        "rot1_deg": rot_degs[0],
        "rot2_axis_code": rot_axes[1],
        "rot2_deg": rot_degs[1],
        "rot3_axis_code": rot_axes[2],
        "rot3_deg": rot_degs[2],
        "eff_sun_face": eff["eff_sun_face"],
        "eff_velocity_face": vn["eff_velocity_face"],
        "eff_nadir_face": vn["eff_nadir_face"],
        "eff_velocity_source": vn["eff_velocity_source"],
        "eff_nadir_source": vn["eff_nadir_source"],
        "notes_attitude": (
            f"constraint_target={constraint_target}. "
            "eff_velocity_face / eff_nadir_face are always both filled: "
            "the constrained one has source=constraint, the other source=effective "
            "(velocity×sun triad third when velocity is constrained; "
            "sign chosen so |β|~90° → nadir not zenith)."
        ),
    }


def infer_sun_face_from_name(name: str) -> str | None:
    match = SUN_FACE_RE.search(name)
    return match.group(1).upper() if match else None


def _cell_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "<na>"} else text


def constrained_face_from_dump(dump: dict[str, Any]) -> str:
    """Body face that TD constrains to velocity or nadir."""
    target = str(dump.get("constraint_target", "") or "").lower()
    if target == "velocity":
        return str(dump.get("eff_velocity_face", "") or "")
    if target == "nadir":
        return str(dump.get("eff_nadir_face", "") or "")
    return ""


def merge_into_catalog(
    catalog: pd.DataFrame, dumps: dict[str, dict[str, Any]]
) -> pd.DataFrame:
    # Derived / TD dump only — do not treat constraint_face as overwrite-from-TD
    attitude_cols = [
        "orient_type",
        "constraint_type",
        "pointing_axis",
        "constraint_axis",
        "rot1_axis_code",
        "rot1_deg",
        "rot2_axis_code",
        "rot2_deg",
        "rot3_axis_code",
        "rot3_deg",
        "eff_sun_face",
        "eff_velocity_face",
        "eff_nadir_face",
        "eff_velocity_source",
        "eff_nadir_source",
        "notes_attitude",
    ]
    out = catalog.copy()
    for col in list(attitude_cols) + ["constraint_target", "constraint_face", "sun_face"]:
        if col not in out.columns:
            out[col] = pd.NA

    for idx, row in out.iterrows():
        name = str(row["td_orbit_name"])
        dump = dumps.get(name)
        if dump is None:
            continue
        for col in attitude_cols:
            out.at[idx, col] = dump.get(col)

        # constraint_target: fill if blank; otherwise keep intent and warn on mismatch
        catalog_target = _cell_str(row.get("constraint_target")).lower()
        dump_target = _cell_str(dump.get("constraint_target")).lower()
        if not catalog_target:
            out.at[idx, "constraint_target"] = dump_target
            catalog_target = dump_target
        elif dump_target and catalog_target != dump_target:
            note = _cell_str(out.at[idx, "notes_attitude"])
            out.at[idx, "notes_attitude"] = (
                note
                + f" WARNING: catalog constraint_target={catalog_target} "
                f"vs TD={dump_target}."
            )

        dump_constraint_face = constrained_face_from_dump(dump)
        catalog_face = _cell_str(row.get("constraint_face")).upper()
        if not catalog_face:
            out.at[idx, "constraint_face"] = dump_constraint_face or pd.NA
        elif (
            dump_constraint_face
            and catalog_face != dump_constraint_face
            and "~" not in dump_constraint_face
        ):
            note = _cell_str(out.at[idx, "notes_attitude"])
            out.at[idx, "notes_attitude"] = (
                note
                + f" WARNING: catalog constraint_face={catalog_face} "
                f"vs TD={dump_constraint_face}."
            )

        if not _cell_str(row.get("sun_face")):
            out.at[idx, "sun_face"] = (
                infer_sun_face_from_name(name) or dump.get("eff_sun_face")
            )
        catalog_sun = _cell_str(out.at[idx, "sun_face"])
        eff_sun = _cell_str(dump.get("eff_sun_face"))
        if catalog_sun and eff_sun and catalog_sun != eff_sun and "~" not in eff_sun:
            note = _cell_str(out.at[idx, "notes_attitude"])
            out.at[idx, "notes_attitude"] = (
                note
                + f" WARNING: catalog sun_face={catalog_sun} vs eff_sun_face={eff_sun}."
            )
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refresh orbit_catalog attitude columns from open TD orbits."
    )
    parser.add_argument("--orbit-catalog", type=Path, default=DEFAULT_ORBIT_CATALOG)
    parser.add_argument("--sheet", default="orbit_catalog")
    parser.add_argument("--dwg", type=Path, default=DEFAULT_DWG)
    parser.add_argument("--attach-only", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--layout-only",
        action="store_true",
        help="Reorder columns and gray-style derived cells; do not connect to TD.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    catalog = pd.read_excel(args.orbit_catalog, sheet_name=args.sheet)
    if "td_orbit_name" not in catalog.columns:
        raise ValueError("orbit_catalog missing td_orbit_name")

    if args.layout_only:
        if args.dry_run:
            from .orbit_catalog_io import reorder_orbit_catalog_columns

            ordered = reorder_orbit_catalog_columns(catalog)
            _log("dry-run layout columns:")
            _log(", ".join(map(str, ordered.columns)))
            return 0
        archive = load_archive_sheet(args.orbit_catalog)
        write_orbit_catalog_xlsx(
            args.orbit_catalog,
            catalog,
            sheet_name=args.sheet,
            archive=archive,
        )
        _log(f"layout-only wrote {args.orbit_catalog}")
        return 0

    wanted = set(catalog["td_orbit_name"].astype(str))
    _log("Connecting to TD …")
    td, _ = connect_thermal_desktop(
        dwg_path=args.dwg, attach_only=bool(args.attach_only)
    )

    dumps: dict[str, dict[str, Any]] = {}
    for orbit in list(td.GetOrbits()):
        name = str(getattr(orbit, "Name", "") or "")
        if name not in wanted:
            continue
        try:
            dumps[name] = dump_orbit(orbit)
        except Exception as exc:
            _log(f"  skip {name}: {exc}")

    missing = sorted(wanted - set(dumps))
    if missing:
        _log(f"warning: not found in TD: {missing}")

    _log("\n=== attitude dump ===")
    for name in sorted(dumps):
        dump = dumps[name]
        _log(
            f"{name}: target={dump['constraint_target']} "
            f"point={dump['pointing_axis']} constr={dump['constraint_axis']} "
            f"rot=({dump['rot1_deg']},{dump['rot2_deg']},{dump['rot3_deg']}) "
            f"eff_sun={dump['eff_sun_face']} "
            f"vel={dump['eff_velocity_face']}({dump['eff_velocity_source']}) "
            f"nadir={dump['eff_nadir_face']}({dump['eff_nadir_source']})"
        )

    updated = merge_into_catalog(catalog, dumps)
    drop_cols = [
        c
        for c in (
            "eff_velocity_or_nadir_face",
            "eff_triad_third_face",
        )
        if c in updated.columns
    ]
    if drop_cols:
        updated = updated.drop(columns=drop_cols)

    if args.dry_run:
        _log("\ndry-run: catalog not written")
        return 0

    archive = load_archive_sheet(args.orbit_catalog)
    write_orbit_catalog_xlsx(
        args.orbit_catalog,
        updated,
        sheet_name=args.sheet,
        archive=archive,
    )
    _log(f"\nwrote {args.orbit_catalog}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
