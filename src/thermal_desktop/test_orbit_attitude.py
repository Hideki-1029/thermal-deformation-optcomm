"""Tests for orbit additional-rotation → effective sun face mapping."""

from __future__ import annotations

import numpy as np

from src.thermal_desktop.refresh_orbit_catalog_attitude import (
    effective_body_axes,
)


SUN_MZ = np.array([0.0, 0.0, -1.0])
VEL_PY = np.array([0.0, 1.0, 0.0])


def _eff(rot1: float = 0.0, rot2: float = 0.0, rot3: float = 0.0) -> dict:
    return effective_body_axes(
        pointing_vec=SUN_MZ,
        constraint_vec=VEL_PY,
        rot_axes=[0, 1, 2],
        rot_degs=[rot1, rot2, rot3],
    )


def test_mz_identity():
    out = _eff()
    assert out["eff_sun_face"] == "MZ"
    assert out["eff_second_face"] == "PY"
    # velocity × sun: +Y × (−Z) = −X → MX (nadir-sense third axis)
    assert out["eff_triad_third_face"] == "MX"


def test_my_rot1_plus90():
    out = _eff(rot1=90.0)
    assert out["eff_sun_face"] == "MY"


def test_py_rot1_minus90():
    out = _eff(rot1=-90.0)
    assert out["eff_sun_face"] == "PY"


def test_mx_rot2_minus90():
    out = _eff(rot2=-90.0)
    assert out["eff_sun_face"] == "MX"


def test_px_rot2_plus90():
    out = _eff(rot2=90.0)
    assert out["eff_sun_face"] == "PX"


def test_assign_velocity_constraint_splits_columns():
    from src.thermal_desktop.refresh_orbit_catalog_attitude import (
        assign_velocity_nadir_faces,
    )

    out = assign_velocity_nadir_faces(
        constraint_target="velocity",
        eff_second_face="PY",
        eff_triad_third_face="MX",
    )
    assert out["eff_velocity_face"] == "PY"
    assert out["eff_nadir_face"] == "MX"
    assert out["eff_velocity_source"] == "constraint"
    assert out["eff_nadir_source"] == "effective"


def test_assign_nadir_constraint_splits_columns():
    from src.thermal_desktop.refresh_orbit_catalog_attitude import (
        assign_velocity_nadir_faces,
    )

    out = assign_velocity_nadir_faces(
        constraint_target="nadir",
        eff_second_face="PZ",
        eff_triad_third_face="PY",
    )
    assert out["eff_nadir_face"] == "PZ"
    assert out["eff_velocity_face"] == "PY"
    assert out["eff_nadir_source"] == "constraint"
    assert out["eff_velocity_source"] == "effective"


def test_reorder_puts_inputs_before_td_internals():
    import pandas as pd

    from src.thermal_desktop.orbit_catalog_io import (
        DERIVED_COLS,
        INPUT_ATTITUDE_COLS,
        reorder_orbit_catalog_columns,
    )

    df = pd.DataFrame(
        [
            {
                "td_orbit_name": "A",
                "rot1_deg": 0,
                "sun_face": "MZ",
                "constraint_target": "velocity",
                "constraint_face": "PY",
                "eff_nadir_face": "MX",
                "pointing_axis": "-Z",
            }
        ]
    )
    ordered = reorder_orbit_catalog_columns(df)
    cols = list(ordered.columns)
    assert cols.index("sun_face") < cols.index("eff_nadir_face")
    assert cols.index("constraint_face") < cols.index("pointing_axis")
    assert cols.index("eff_nadir_face") < cols.index("rot1_deg")
    assert set(INPUT_ATTITUDE_COLS) <= set(cols)
    assert set(DERIVED_COLS) & set(cols)


def test_attitude_recipe_my_velocity_expects_mz():
    from src.thermal_desktop.create_td_orbits import attitude_recipe

    out = attitude_recipe(sun_face="MY", constraint_target="velocity")
    assert out["eff_sun_face"] == "MY"
    assert out["expected_constraint_face"] == "MZ"
    assert out["rot_degs"] == (90.0, 0.0, 0.0)


def test_merge_fills_blank_constraint_face_from_td():
    import pandas as pd

    from src.thermal_desktop.refresh_orbit_catalog_attitude import merge_into_catalog

    catalog = pd.DataFrame(
        [
            {
                "td_orbit_name": "ORB",
                "sun_face": "MY",
                "constraint_target": "velocity",
                "constraint_face": "",
            }
        ]
    )
    dumps = {
        "ORB": {
            "constraint_target": "velocity",
            "orient_type": "SUN",
            "constraint_type": "VELOCITY",
            "pointing_axis": "-Z",
            "constraint_axis": "+Y",
            "rot1_axis_code": 0,
            "rot1_deg": 90.0,
            "rot2_axis_code": 1,
            "rot2_deg": 0.0,
            "rot3_axis_code": 2,
            "rot3_deg": 0.0,
            "eff_sun_face": "MY",
            "eff_velocity_face": "MZ",
            "eff_nadir_face": "MX",
            "eff_velocity_source": "constraint",
            "eff_nadir_source": "effective",
            "notes_attitude": "ok",
        }
    }
    out = merge_into_catalog(catalog, dumps)
    assert out.at[0, "constraint_face"] == "MZ"
