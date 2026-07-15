"""Unit tests for case_matrix → TD symbol mapping."""

from __future__ import annotations

import pandas as pd

from src.thermal_desktop.create_td_cases import (
    build_symbol_overrides_from_row,
    power_mode_flags,
    resolve_case_timing,
)


OPTICAL = {
    "0p5": {"alpha": 0.5, "eps": 0.5},
    "Black": {"alpha": 0.974, "eps": 0.920},
    "alodine1000": {"alpha": 0.15, "eps": 0.038},
}


def test_resolve_timing_from_orbit_catalog():
    period, duration, output = resolve_case_timing(
        orbit_name="LTAN06_800km_1213COLD_MY_SUN",
        orbit_periods={"LTAN06_800km_1213COLD_MY_SUN": 6052.0},
        matrix_duration_s=18157.3,
        matrix_sample_interval_s=60.50,
    )
    assert period == 6052.0
    assert duration == 18156.0
    assert output == 60.52


def test_resolve_timing_falls_back_to_matrix():
    period, duration, output = resolve_case_timing(
        orbit_name="MISSING",
        orbit_periods={},
        matrix_duration_s=17748.0,
        matrix_sample_interval_s=59.16,
    )
    assert period is None
    assert duration == 17748.0
    assert output == 59.16


def test_power_mode_flags_sttlct_prop():
    assert power_mode_flags("STTLCT_PROP_HEAT") == {
        "LCT": 1,
        "STT": 1,
        "PROP": 1,
        "PCDU": 0,
    }


def test_build_overrides_all_heat_skips_nothing_nonzero():
    row = pd.Series(
        {
            "power_mode": "ALL_HEAT",
            "sun_direction_body": "MY",
            "lct_heat_w": 10,
            "stt_heat_w": 1.5,
            "prop_heat_w": 25,
            "pcdu_heat_w": 10,
            "Opt_MY": "0p5",
            "Opt_MX": "alodine1000",
        }
    )
    values, comments = build_symbol_overrides_from_row(row, optical=OPTICAL)
    assert values["INT_HEAT_PROP"] == "25"
    assert values["INT_HEAT_PCDU"] == "10"
    assert values["IS_COMPO_PROP"] == "1"
    assert values["MY_alpha"] == "0.5"
    assert values["MY_ips"] == "0.5"
    assert comments["MY_alpha"] == "0p5"
    assert "MX_alpha" not in values


def test_build_overrides_zero_heat_keeps_nominal_watts():
    row = pd.Series(
        {
            "power_mode": "STTLCT_HEAT",
            "sun_direction_body": "PX",
            "lct_heat_w": 10,
            "stt_heat_w": 1.5,
            "prop_heat_w": 0,
            "pcdu_heat_w": 0,
            "Opt_PX": "0p5",
            "Opt_MY": "Black",
        }
    )
    values, comments = build_symbol_overrides_from_row(row, optical=OPTICAL)
    assert "INT_HEAT_PROP" not in values
    assert "INT_HEAT_PCDU" not in values
    assert values["INT_HEAT_LCT"] == "10"
    assert values["IS_COMPO_PROP"] == "0"
    assert values["IS_COMPO_PCDU"] == "0"
    assert values["IS_COMPO_LCT"] == "1"
    assert values["PX_alpha"] == "0.5"
    assert "MY_alpha" not in values
    assert comments["PX_ips"] == "0p5"


def test_build_overrides_half_prop_continuous_w():
    row = pd.Series(
        {
            "power_mode": "ALL_HEAT",
            "sun_direction_body": "MY",
            "lct_heat_w": 10,
            "stt_heat_w": 1.5,
            "prop_heat_w": 12.5,
            "pcdu_heat_w": 10,
            "Opt_MY": "0p5",
        }
    )
    values, _ = build_symbol_overrides_from_row(row, optical=OPTICAL)
    assert values["INT_HEAT_PROP"] == "12.5"
