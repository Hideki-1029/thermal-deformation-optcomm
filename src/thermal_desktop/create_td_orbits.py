"""
Create Thermal Desktop Orbit objects from orbit_catalog rows.

Human inputs (white columns up to ``notes``):
  sun_face, constraint_target, constraint_face, Keplerian fields

TD internals (pointing / Rot*) are derived from a fixed recipe used by the
existing *_SUN orbits:
  PointingAxis = -Z → Sun, ConstraintAxis = +Y → velocity|nadir,
  Additional Rotations from ``sun_face``.

Usage (TD open)::

  python -m src.thermal_desktop.create_td_orbits --names LTAN18_693km_SENTINEL1_MY_SUN --attach-only --dry-run
  python -m src.thermal_desktop.create_td_orbits --names LTAN18_693km_SENTINEL1_MY_SUN --attach-only
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from .opentd_runtime import DEFAULT_DWG, connect_thermal_desktop
from .refresh_orbit_catalog_attitude import (
    dump_orbit,
    effective_body_axes,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ORBIT_CATALOG = REPO_ROOT / "cases" / "orbit_catalog.xlsx"

# Pointing -Z (code 1), Constraint +Y (code 3) — matches existing *_SUN orbits
_POINTING_AXIS_CODE = 1
_CONSTRAINT_AXIS_CODE = 3
_POINTING_VEC = (0.0, 0.0, -1.0)
_CONSTRAINT_VEC = (0.0, 1.0, 0.0)

# Additional rotations that map -Z→Sun base into the named sun face
# (rot_axes always X,Y,Z = 0,1,2).
_SUN_FACE_ROT_DEG: dict[str, tuple[float, float, float]] = {
    "MZ": (0.0, 0.0, 0.0),
    "MY": (90.0, 0.0, 0.0),
    "PY": (-90.0, 0.0, 0.0),
    "MX": (0.0, -90.0, 0.0),
    "PX": (0.0, 90.0, 0.0),
}

_DEFAULT_RAAN_DEG = 270.0  # same proxy as HOT dawn-dusk orbits when catalog blank
_DEFAULT_ORBIT_INCREMENTS = 36  # match existing research *_SUN orbits


def _log(msg: str) -> None:
    print(msg, flush=True)


def _cell_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "<na>", "-"} else text


def _cell_float(value: Any) -> float | None:
    text = _cell_str(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def attitude_recipe(*, sun_face: str, constraint_target: str) -> dict[str, Any]:
    face = sun_face.strip().upper()
    if face not in _SUN_FACE_ROT_DEG:
        raise ValueError(
            f"Unsupported sun_face={sun_face!r}. Known: {sorted(_SUN_FACE_ROT_DEG)}"
        )
    target = constraint_target.strip().lower()
    if target not in {"velocity", "nadir"}:
        raise ValueError(
            f"constraint_target must be velocity|nadir, got {constraint_target!r}"
        )
    rot = _SUN_FACE_ROT_DEG[face]
    eff = effective_body_axes(
        pointing_vec=_POINTING_VEC,
        constraint_vec=_CONSTRAINT_VEC,
        rot_axes=[0, 1, 2],
        rot_degs=list(rot),
    )
    if target == "velocity":
        expected_constraint_face = eff["eff_second_face"]
        expected_other = eff["eff_triad_third_face"]
    else:
        expected_constraint_face = eff["eff_second_face"]
        expected_other = eff["eff_triad_third_face"]
    return {
        "sun_face": face,
        "constraint_target": target,
        "pointing_axis_code": _POINTING_AXIS_CODE,
        "constraint_axis_code": _CONSTRAINT_AXIS_CODE,
        "rot_degs": rot,
        "expected_constraint_face": expected_constraint_face,
        "expected_triad_third_face": expected_other,
        "eff_sun_face": eff["eff_sun_face"],
    }


def _dimensional_angle(OpenTD: Any, deg: float) -> Any:
    return OpenTD.Dimension.Dimensional[OpenTD.Dimension.Angle](float(deg))


def _dimensional_length(OpenTD: Any, km: float) -> Any:
    return OpenTD.Dimension.Dimensional[OpenTD.Dimension.OrbitLength](float(km))


def _set_rot_deg(orbit: Any, OpenTD: Any, rot_degs: tuple[float, float, float]) -> None:
    orbit.Rot1Axis = 0
    orbit.Rot2Axis = 1
    orbit.Rot3Axis = 2
    orbit.Rot1 = _dimensional_angle(OpenTD, rot_degs[0])
    orbit.Rot2 = _dimensional_angle(OpenTD, rot_degs[1])
    orbit.Rot3 = _dimensional_angle(OpenTD, rot_degs[2])


def _set_equal_orbit_increments(orbit: Any, OpenTD: Any, n: int = _DEFAULT_ORBIT_INCREMENTS) -> None:
    """Set OrbitIncrements and rebuild OrbitPositions at equal true-anomaly steps.

    TD keeps a stale OrbitPositions list if only OrbitIncrements is changed;
    research orbits use n=36 → 37 samples (0°, 10°, …, 360°).
    """
    orbit.OrbitIncrements = int(n)
    orbit.UseEqualInc = 1
    try:
        orbit.OrbitPosInTrueAnom = 1
    except Exception:
        pass
    positions = orbit.OrbitPositions
    try:
        positions.Clear()
    except Exception:
        while getattr(positions, "Count", 0) > 0:
            positions.RemoveAt(0)
    step = 360.0 / float(n)
    for i in range(n + 1):
        positions.Add(_dimensional_angle(OpenTD, i * step))


def apply_catalog_row_to_orbit(
    orbit: Any,
    row: pd.Series,
    OpenTD: Any,
    *,
    allow_constraint_face_mismatch: bool = False,
) -> dict[str, Any]:
    name = _cell_str(row.get("td_orbit_name"))
    sun_face = _cell_str(row.get("sun_face")).upper()
    constraint_target = _cell_str(row.get("constraint_target")).lower()
    constraint_face = _cell_str(row.get("constraint_face")).upper()
    if not name:
        raise ValueError("td_orbit_name is required")
    if not sun_face or not constraint_target:
        raise ValueError(f"{name}: sun_face and constraint_target are required")

    recipe = attitude_recipe(sun_face=sun_face, constraint_target=constraint_target)
    if constraint_face and constraint_face != recipe["expected_constraint_face"]:
        msg = (
            f"{name}: constraint_face={constraint_face} does not match sun_face "
            f"recipe expected {recipe['expected_constraint_face']} "
            f"(pointing -Z, constraint +Y, sun={sun_face})."
        )
        if not allow_constraint_face_mismatch:
            raise ValueError(msg)
        _log(f"WARNING: {msg}")

    OrbitTypes = OpenTD.RadCAD.Orbit.OrbitTypes
    Planets = OpenTD.RadCAD.Orbit.Planets
    OrientTypes = OpenTD.RadCAD.Orbit.OrientTypes

    orbit.OrbitType = OrbitTypes.KEPLERIAN
    orbit.Planet = Planets.EARTH
    orbit.OrientType = OrientTypes.SUN
    orbit.ConstraintType = (
        OrientTypes.VELOCITY if constraint_target == "velocity" else OrientTypes.PLANET
    )
    orbit.PointingAxis = int(recipe["pointing_axis_code"])
    orbit.ConstraintAxis = int(recipe["constraint_axis_code"])
    _set_rot_deg(orbit, OpenTD, recipe["rot_degs"])

    od = orbit.OrbitData
    incl = _cell_float(row.get("inclination_deg"))
    if incl is not None:
        od.Inclination = _dimensional_angle(OpenTD, incl)
    alt_min = _cell_float(row.get("min_alt_km"))
    alt_max = _cell_float(row.get("max_alt_km"))
    if alt_min is not None:
        od.AltMin = _dimensional_length(OpenTD, alt_min)
    if alt_max is not None:
        od.AltMax = _dimensional_length(OpenTD, alt_max)
    elif alt_min is not None:
        od.AltMax = _dimensional_length(OpenTD, alt_min)

    raan = _cell_float(row.get("raan_deg"))
    if raan is None:
        raan = _DEFAULT_RAAN_DEG
        _log(
            f"  {name}: raan_deg blank → using {_DEFAULT_RAAN_DEG} "
            "(HOT-style dawn-dusk proxy; set catalog raan_deg to override)"
        )
    od.RaAscending = _dimensional_angle(OpenTD, raan)
    # Keep RaSun=0 like HOT when using explicit RAAN (not date-driven)
    try:
        od.RaSun = _dimensional_angle(OpenTD, 0.0)
    except Exception:
        pass
    try:
        orbit.UseRightAscensionsOrCalculateFromDate = 0
    except Exception:
        pass

    od.Eccen = 0.0
    try:
        _set_equal_orbit_increments(orbit, OpenTD, _DEFAULT_ORBIT_INCREMENTS)
    except Exception as exc:
        _log(f"  warning: could not set OrbitIncrements={_DEFAULT_ORBIT_INCREMENTS}: {exc}")
    return recipe


def create_or_update_orbit(
    td: Any,
    OpenTD: Any,
    row: pd.Series,
    *,
    update_existing: bool = False,
    dry_run: bool = False,
    allow_constraint_face_mismatch: bool = False,
) -> dict[str, Any]:
    name = _cell_str(row.get("td_orbit_name"))
    existing_names = {str(getattr(o, "Name", "") or "") for o in td.GetOrbits()}
    exists = name in existing_names
    if exists and not update_existing:
        raise ValueError(
            f"Orbit already exists: {name}. Pass --update to overwrite settings."
        )

    recipe = attitude_recipe(
        sun_face=_cell_str(row.get("sun_face")),
        constraint_target=_cell_str(row.get("constraint_target")),
    )
    _log(
        f"{'[dry-run] ' if dry_run else ''}"
        f"{'update' if exists else 'create'} {name}: "
        f"sun={recipe['sun_face']} target={recipe['constraint_target']} "
        f"constraint_face→{recipe['expected_constraint_face']} "
        f"rot={recipe['rot_degs']}"
    )
    if dry_run:
        return {"name": name, "action": "dry-run", "recipe": recipe}

    if exists:
        orbit = td.GetOrbit(name)
    else:
        orbit = td.CreateOrbit(name)

    apply_catalog_row_to_orbit(
        orbit,
        row,
        OpenTD,
        allow_constraint_face_mismatch=allow_constraint_face_mismatch,
    )
    orbit.Update()
    dumped = dump_orbit(orbit)
    _log(
        f"  TD ok: eff_sun={dumped['eff_sun_face']} "
        f"vel={dumped['eff_velocity_face']}({dumped['eff_velocity_source']}) "
        f"nadir={dumped['eff_nadir_face']}({dumped['eff_nadir_source']})"
    )
    return {"name": name, "action": "updated" if exists else "created", "dump": dumped}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create TD Orbits from orbit_catalog attitude/Keplerian inputs."
    )
    parser.add_argument("--orbit-catalog", type=Path, default=DEFAULT_ORBIT_CATALOG)
    parser.add_argument("--sheet", default="orbit_catalog")
    parser.add_argument(
        "--names",
        required=True,
        help="Comma-separated td_orbit_name values",
    )
    parser.add_argument("--template", default="LTAN06_800km_HOT_MY_SUN")
    parser.add_argument("--dwg", type=Path, default=DEFAULT_DWG)
    parser.add_argument("--attach-only", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Overwrite orientation/Keplerian if the Orbit already exists",
    )
    parser.add_argument(
        "--allow-constraint-face-mismatch",
        action="store_true",
        help="Warn instead of failing when constraint_face ≠ sun_face recipe",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    catalog = pd.read_excel(args.orbit_catalog, sheet_name=args.sheet)
    if "td_orbit_name" not in catalog.columns:
        raise ValueError("orbit_catalog missing td_orbit_name")

    wanted = [n.strip() for n in str(args.names).split(",") if n.strip()]
    by_name = {
        str(r["td_orbit_name"]): r
        for _, r in catalog.iterrows()
        if _cell_str(r.get("td_orbit_name"))
    }
    missing = [n for n in wanted if n not in by_name]
    if missing:
        raise ValueError(f"Not in orbit_catalog: {missing}")

    _log("Connecting to TD …")
    td, OpenTD = connect_thermal_desktop(
        dwg_path=args.dwg, attach_only=bool(args.attach_only)
    )

    # template existence is informational (recipes are code-side)
    template = str(args.template)
    if template and template not in {
        str(getattr(o, "Name", "") or "") for o in td.GetOrbits()
    }:
        _log(f"warning: template orbit not in TD: {template}")

    for name in wanted:
        create_or_update_orbit(
            td,
            OpenTD,
            by_name[name],
            update_existing=bool(args.update),
            dry_run=bool(args.dry_run),
            allow_constraint_face_mismatch=bool(args.allow_constraint_face_mismatch),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
