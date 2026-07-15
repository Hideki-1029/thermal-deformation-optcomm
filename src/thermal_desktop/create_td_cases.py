"""Create TD Case Sets from case_matrix rows by cloning a template Case Set."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .case_selection import case_number_from_name, parse_case_spec
from .opentd_runtime import DEFAULT_DWG, connect_thermal_desktop


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASE_MATRIX = REPO_ROOT / "cases" / "case_matrix.xlsx"
DEFAULT_ORBIT_CATALOG = REPO_ROOT / "cases" / "orbit_catalog.xlsx"
DEFAULT_OPTICAL_YAML = REPO_ROOT / "cases" / "thermal_optical_properties.yaml"

# Transient window and TD Thermal Output Increment from orbit_catalog.orbit_period_s.
DURATION_ORBIT_MULTIPLIER = 3.0
OUTPUT_PERIOD_DIVISOR = 100.0

_HEAT_SYMBOLS = {
    "lct_heat_w": "INT_HEAT_LCT",
    "stt_heat_w": "INT_HEAT_STT",
    "prop_heat_w": "INT_HEAT_PROP",
    "pcdu_heat_w": "INT_HEAT_PCDU",
}

_COMPO_FLAGS = {
    "ALL_HEAT": {"LCT": 1, "STT": 1, "PROP": 1, "PCDU": 1},
    "ZERO_HEAT": {"LCT": 0, "STT": 0, "PROP": 0, "PCDU": 0},
    "STTLCT_HEAT": {"LCT": 1, "STT": 1, "PROP": 0, "PCDU": 0},
    "STTLCT_PROP_HEAT": {"LCT": 1, "STT": 1, "PROP": 1, "PCDU": 0},
    "STTLCT_PCDU_HEAT": {"LCT": 1, "STT": 1, "PROP": 0, "PCDU": 1},
}


def _log(msg: str) -> None:
    print(msg, flush=True)


def _clean_symbol_value(value: Any) -> str:
    text = str(value).replace("\r", "").replace("\n", "").strip()
    return text


def _is_zero_heat(value: Any) -> bool:
    try:
        return abs(float(_clean_symbol_value(value))) < 1e-12
    except (TypeError, ValueError):
        return False


def _clear_net_list(seq: Any) -> None:
    if seq is None:
        return
    if hasattr(seq, "Clear"):
        seq.Clear()
        return
    while getattr(seq, "Count", 0) > 0:
        seq.RemoveAt(0)


def _set_string_list(seq: Any, values: list[str]) -> None:
    _clear_net_list(seq)
    for value in values:
        seq.Add(str(value))


def load_optical_catalog(path: Path) -> dict[str, dict[str, float]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    props = raw.get("properties") or {}
    out: dict[str, dict[str, float]] = {}
    for name, entry in props.items():
        out[str(name)] = {
            "alpha": float(entry["solar_absorptivity"]),
            "eps": float(entry["infrared_emissivity"]),
        }
    return out


def power_mode_flags(power_mode: str) -> dict[str, int]:
    key = str(power_mode or "").strip().upper()
    if key not in _COMPO_FLAGS:
        raise ValueError(
            f"Unsupported power_mode {power_mode!r}. "
            f"Known: {sorted(_COMPO_FLAGS)}"
        )
    return dict(_COMPO_FLAGS[key])


def find_case_set(
    td: Any, *, group: str, number: int | None = None, name: str | None = None
):
    group_key = group.strip().casefold()
    matches = []
    for case in list(td.GetCaseSets()):
        case_group = str(getattr(case, "GroupName", "") or "")
        if case_group.casefold() != group_key:
            continue
        case_name = str(getattr(case, "Name", "") or "")
        if name is not None and case_name == name:
            return case
        if number is not None and case_number_from_name(case_name) == number:
            matches.append(case)
    if name is not None:
        raise ValueError(f"Case Set not found: group={group!r} name={name!r}")
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(f"Case Set not found: group={group!r} number={number}")
    raise ValueError(f"Multiple Case Sets matched number {number} in group {group!r}")


def case_exists(td: Any, *, group: str, name: str) -> bool:
    group_key = group.strip().casefold()
    for case in list(td.GetCaseSets()):
        if str(getattr(case, "GroupName", "") or "").casefold() != group_key:
            continue
        if str(getattr(case, "Name", "") or "") == name:
            return True
    return False


def dump_symbol_map(case: Any) -> dict[str, str]:
    case.UpdateFromTD()
    names = [_clean_symbol_value(x) for x in list(case.SymbolNames or [])]
    values = [_clean_symbol_value(x) for x in list(case.SymbolValues or [])]
    if len(names) != len(values):
        raise RuntimeError(
            f"SymbolNames/Values length mismatch on {case.Name}: "
            f"{len(names)} vs {len(values)}"
        )
    return dict(zip(names, values))


def build_symbol_overrides_from_row(
    row: pd.Series,
    *,
    optical: dict[str, dict[str, float]],
) -> tuple[dict[str, str], dict[str, str]]:
    """
    Map one case_matrix row to TD symbol overrides.

    Returns ``(value_overrides, comment_overrides)``.

    Policy
    ------
    - Non-zero ``*_heat_w`` → ``INT_HEAT_*``
    - Zero ``*_heat_w`` → skip (keep template nominal W; OFF is ``IS_COMPO_*=0``)
    - ``power_mode`` → ``IS_COMPO_*``
    - Sun-face ``Opt_{face}`` only → ``{face}_alpha`` / ``{face}_ips``
      (non-sun Opt_* stay model defaults; no Case Set override)
    """
    overrides: dict[str, str] = {}
    comments: dict[str, str] = {}

    for col, symbol in _HEAT_SYMBOLS.items():
        if col not in row.index or pd.isna(row[col]):
            continue
        if _is_zero_heat(row[col]):
            continue
        overrides[symbol] = _clean_symbol_value(row[col])

    if "power_mode" in row.index and pd.notna(row["power_mode"]):
        flags = power_mode_flags(str(row["power_mode"]))
        for compo, flag in flags.items():
            overrides[f"IS_COMPO_{compo}"] = str(flag)

    sun_face = str(row.get("sun_direction_body", "") or "").strip().upper()
    opt_col = f"Opt_{sun_face}" if sun_face else ""
    if sun_face and opt_col in row.index and pd.notna(row[opt_col]):
        prop_name = str(row[opt_col]).strip()
        if prop_name not in optical:
            raise ValueError(
                f"Unknown optical property {prop_name!r} for {opt_col}. "
                f"Known: {sorted(optical)}"
            )
        alpha_sym = f"{sun_face}_alpha"
        eps_sym = f"{sun_face}_ips"
        overrides[alpha_sym] = _clean_symbol_value(optical[prop_name]["alpha"])
        overrides[eps_sym] = _clean_symbol_value(optical[prop_name]["eps"])
        comments[alpha_sym] = prop_name
        comments[eps_sym] = prop_name

    return overrides, comments


def copy_sinda_control(dst: Any, src: Any) -> None:
    src_ctrl = getattr(src, "SindaControl", None)
    dst_ctrl = getattr(dst, "SindaControl", None)
    if src_ctrl is None or dst_ctrl is None:
        return
    for attr in ("timend", "output", "outptf", "CSGFAC", "NLOOPS"):
        if hasattr(src_ctrl, attr) and hasattr(dst_ctrl, attr):
            try:
                setattr(dst_ctrl, attr, getattr(src_ctrl, attr))
            except Exception:
                pass


def load_orbit_period_map(
    orbit_catalog: Path, *, sheet: str = "orbit_catalog"
) -> dict[str, float]:
    df = pd.read_excel(orbit_catalog, sheet_name=sheet)
    if "td_orbit_name" not in df.columns or "orbit_period_s" not in df.columns:
        raise ValueError(
            f"{orbit_catalog} must have td_orbit_name and orbit_period_s columns"
        )
    out: dict[str, float] = {}
    for _, row in df.iterrows():
        name = str(row["td_orbit_name"]).strip()
        if not name or name.casefold() == "nan":
            continue
        period = row["orbit_period_s"]
        if pd.isna(period):
            continue
        out[name] = float(period)
    return out


def resolve_case_timing(
    *,
    orbit_name: str | None,
    orbit_periods: dict[str, float],
    matrix_duration_s: float | None = None,
    matrix_sample_interval_s: float | None = None,
) -> tuple[float | None, float | None, float | None]:
    """Return (orbit_period_s, duration_s, output_interval_s).

    Prefer ``orbit_catalog.orbit_period_s``:
    - End time (timend) = 3 * period
    - Thermal Output Increment (OUTPUT) = period / 100

    Fall back to case_matrix ``duration_s`` / ``sample_interval_s`` when the
    orbit period is unavailable.
    """
    period: float | None = None
    if orbit_name and orbit_name in orbit_periods:
        period = float(orbit_periods[orbit_name])

    duration_s: float | None = None
    output_s: float | None = None
    if period is not None and period > 0.0:
        duration_s = DURATION_ORBIT_MULTIPLIER * period
        output_s = period / OUTPUT_PERIOD_DIVISOR
        if matrix_duration_s is not None and abs(matrix_duration_s - duration_s) > 1.0:
            _log(
                f"  note: case_matrix duration_s={matrix_duration_s} "
                f"differs from {DURATION_ORBIT_MULTIPLIER:g}*orbit_period "
                f"({duration_s}); using orbit_catalog"
            )
        if (
            matrix_sample_interval_s is not None
            and abs(matrix_sample_interval_s - output_s) > 0.5
        ):
            _log(
                f"  note: case_matrix sample_interval_s={matrix_sample_interval_s} "
                f"differs from orbit_period/{OUTPUT_PERIOD_DIVISOR:g} "
                f"({output_s}); using orbit_catalog"
            )
        return period, duration_s, output_s

    duration_s = matrix_duration_s
    output_s = matrix_sample_interval_s
    if duration_s is None and output_s is None:
        _log(
            "  warning: no orbit_period_s and no matrix duration/sample; "
            "keeping template SindaControl timing"
        )
    elif period is None and orbit_name:
        _log(
            f"  warning: orbit {orbit_name!r} missing orbit_period_s; "
            "using case_matrix timing fields if present"
        )
    return period, duration_s, output_s


def _set_sinda_time_attr(
    case: Any, OpenTD: Any, attr: str, seconds: float
) -> None:
    ctrl = getattr(case, "SindaControl", None)
    if ctrl is None or not hasattr(ctrl, attr):
        return
    try:
        setattr(
            ctrl,
            attr,
            OpenTD.Dimension.Dimensional[OpenTD.Dimension.Time](float(seconds)),
        )
    except Exception as exc:
        _log(f"  warning: could not set {attr}={seconds}: {exc}")


def apply_duration_s(case: Any, OpenTD: Any, duration_s: float) -> None:
    _set_sinda_time_attr(case, OpenTD, "timend", duration_s)


def apply_output_interval_s(case: Any, OpenTD: Any, output_s: float) -> None:
    # OpenTD property is lowercase ``output`` (Thermal Output Increment).
    _set_sinda_time_attr(case, OpenTD, "output", output_s)


def sinda_time_value_s(value: Any) -> float | None:
    if value is None:
        return None
    if hasattr(value, "GetValueSI"):
        try:
            return float(value.GetValueSI())
        except (TypeError, ValueError):
            pass
    for attr in ("Value", "value"):
        if hasattr(value, attr):
            try:
                return float(getattr(value, attr))
            except (TypeError, ValueError):
                pass
    try:
        text = str(value).strip().split()[0]
        return float(text)
    except (TypeError, ValueError, IndexError):
        return None


def copy_radiation_tasks(
    dst: Any, src: Any, *, orbit_name: str | None, OpenTD: Any
) -> None:
    src.UpdateFromTD()
    _clear_net_list(dst.RadiationTasks)
    calc_type = OpenTD.RadiationTaskData.calcType
    for task in list(src.RadiationTasks or []):
        new_task = OpenTD.RadiationTaskData()
        type_calc = getattr(task, "TypeCalc", None)
        new_task.TypeCalc = type_calc
        new_task.AnalGroup = str(getattr(task, "AnalGroup", "") or "BASE")
        old_orbit = str(getattr(task, "OrbitName", "") or "")
        type_name = str(type_calc)
        if orbit_name and (
            "HEATRATE" in type_name.upper()
            or type_calc == getattr(calc_type, "HEATRATE", None)
        ):
            new_task.OrbitName = orbit_name
        else:
            new_task.OrbitName = old_orbit
        dst.RadiationTasks.Add(new_task)


def clone_case_set(
    td: Any,
    OpenTD: Any,
    *,
    template: Any,
    new_name: str,
    group: str,
    orbit_name: str | None,
    symbol_overrides: dict[str, str],
    comment_overrides: dict[str, str] | None = None,
    duration_s: float | None = None,
    output_interval_s: float | None = None,
    dry_run: bool = False,
) -> Any | None:
    template.UpdateFromTD()
    base_symbols = dump_symbol_map(template)
    merged = dict(base_symbols)
    merged.update({k: _clean_symbol_value(v) for k, v in symbol_overrides.items()})
    comment_overrides = comment_overrides or {}

    missing = [k for k in symbol_overrides if k not in base_symbols]
    if missing:
        _log(
            f"  warning: override symbols not present on template "
            f"{template.Name}: {missing} (will still add them)"
        )

    _log(f"  template : {template.Name}")
    _log(f"  new case : {new_name} (group={group})")
    _log(f"  orbit    : {orbit_name or '(keep template)'}")
    if duration_s is not None:
        _log(f"  timend   : {duration_s}")
    if output_interval_s is not None:
        _log(f"  output  : {output_interval_s}")
    changed = {
        k: merged[k] for k in symbol_overrides if base_symbols.get(k) != merged[k]
    }
    if changed:
        _log("  symbol deltas:")
        for key, value in changed.items():
            _log(f"    {key}: {base_symbols.get(key)!r} -> {value!r}")
    else:
        _log("  symbol deltas: (none vs template after overrides)")

    if dry_run:
        return None

    if case_exists(td, group=group, name=new_name):
        raise RuntimeError(
            f"Case Set already exists: {new_name!r} in group {group!r}. "
            "Delete it in TD first, or choose another case_id."
        )

    created = td.CreateCaseSet(new_name, group, new_name)
    for attr in (
        "SteadyState",
        "Transient",
        "SaveAll",
        "OpticOverride",
        "ThermoOverride",
        "UseUserDirectory",
        "UserDirectory",
        "PostprocessSindaSave",
        "SaveTemp",
        "SaveTie",
        "SaveLump",
        "SavePath",
        "SaveAllSS",
        "GenerateLogFile",
        "AsciiPath",
    ):
        if hasattr(template, attr) and hasattr(created, attr):
            try:
                setattr(created, attr, getattr(template, attr))
            except Exception:
                pass
    # Research cases always write under the group folder (e.g. transient/).
    if hasattr(created, "UseUserDirectory"):
        created.UseUserDirectory = 1
    if hasattr(created, "UserDirectory"):
        created.UserDirectory = str(group)

    copy_sinda_control(created, template)
    if duration_s is not None:
        apply_duration_s(created, OpenTD, duration_s)
    if output_interval_s is not None:
        apply_output_interval_s(created, OpenTD, output_interval_s)
    copy_radiation_tasks(created, template, orbit_name=orbit_name, OpenTD=OpenTD)

    names = list(merged.keys())
    values = [merged[k] for k in names]
    comments = [""] * len(names)
    try:
        t_names = [_clean_symbol_value(x) for x in list(template.SymbolNames or [])]
        t_comments = [str(x) for x in list(template.SymbolComments or [])]
        comment_map = dict(zip(t_names, t_comments))
        comment_map.update(comment_overrides)
        comments = [comment_map.get(n, "") for n in names]
    except Exception:
        comments = [comment_overrides.get(n, "") for n in names]

    _set_string_list(created.SymbolNames, names)
    _set_string_list(created.SymbolValues, values)
    _set_string_list(created.SymbolComments, comments)

    created.Update()
    created.UpdateFromTD()
    return created


def patch_case_timing(
    case: Any,
    OpenTD: Any,
    *,
    duration_s: float | None,
    output_interval_s: float | None,
    dry_run: bool = False,
) -> None:
    case.UpdateFromTD()
    ctrl = getattr(case, "SindaControl", None)
    before_t = sinda_time_value_s(getattr(ctrl, "timend", None) if ctrl else None)
    before_o = sinda_time_value_s(getattr(ctrl, "output", None) if ctrl else None)
    _log(f"  before  : timend={before_t} output={before_o}")
    if duration_s is not None:
        _log(f"  set     : timend={duration_s}")
    if output_interval_s is not None:
        _log(f"  set     : output={output_interval_s}")
    if dry_run:
        return
    if duration_s is not None:
        apply_duration_s(case, OpenTD, duration_s)
    if output_interval_s is not None:
        apply_output_interval_s(case, OpenTD, output_interval_s)
    case.Update()
    case.UpdateFromTD()
    ctrl = getattr(case, "SindaControl", None)
    after_t = sinda_time_value_s(getattr(ctrl, "timend", None) if ctrl else None)
    after_o = sinda_time_value_s(getattr(ctrl, "output", None) if ctrl else None)
    _log(f"  after   : timend={after_t} output={after_o}")


def load_case_rows(case_matrix: Path, sheet: str, numbers: list[int]) -> list[pd.Series]:
    df = pd.read_excel(case_matrix, sheet_name=sheet)
    if "case_id" not in df.columns:
        raise ValueError(f"{case_matrix} has no case_id column")
    wanted = set(numbers)
    rows: list[pd.Series] = []
    found: set[int] = set()
    for _, row in df.iterrows():
        case_id = str(row["case_id"])
        number = case_number_from_name(case_id)
        if number is None or number not in wanted:
            continue
        rows.append(row)
        found.add(number)
    missing = sorted(wanted - found)
    if missing:
        raise ValueError(f"case_matrix missing case number(s): {missing}")
    rows.sort(key=lambda r: case_number_from_name(str(r["case_id"])) or 0)
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create TD Case Sets from case_matrix by cloning a template Case Set "
            "(symbols + radiation orbit). Timing defaults to "
            f"{DURATION_ORBIT_MULTIPLIER:g}*orbit_period_s (timend) and "
            f"orbit_period_s/{OUTPUT_PERIOD_DIVISOR:g} (OUTPUT) from orbit_catalog."
        )
    )
    parser.add_argument("--cases", required=True, help="Case numbers, e.g. 22 or 22,23")
    parser.add_argument(
        "--template",
        default="4",
        help="Template case number to clone (default: 4; ignored with --patch-timing)",
    )
    parser.add_argument(
        "--patch-timing",
        action="store_true",
        help=(
            "Update timend/OUTPUT on existing Case Sets from orbit_catalog "
            "(do not create)"
        ),
    )
    parser.add_argument("--group", default="transient")
    parser.add_argument("--case-matrix", type=Path, default=DEFAULT_CASE_MATRIX)
    parser.add_argument("--case-matrix-sheet", default="case_matrix")
    parser.add_argument("--orbit-catalog", type=Path, default=DEFAULT_ORBIT_CATALOG)
    parser.add_argument("--orbit-catalog-sheet", default="orbit_catalog")
    parser.add_argument("--optical-yaml", type=Path, default=DEFAULT_OPTICAL_YAML)
    parser.add_argument("--dwg", type=Path, default=DEFAULT_DWG)
    parser.add_argument("--attach-only", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--symbols-from-matrix",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Apply heat/power/sun-face optical overrides from case_matrix "
            "(default: enabled). Use --no-symbols-from-matrix to clone only."
        ),
    )
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        metavar="SYMBOL=VALUE",
        help="Explicit symbol override (repeatable). Example: INT_HEAT_PROP=12.5",
    )
    return parser


def parse_overrides(items: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Invalid --override {item!r}; expected SYMBOL=VALUE")
        key, value = item.split("=", 1)
        out[key.strip()] = _clean_symbol_value(value)
    return out


def _matrix_optional_float(row: pd.Series, column: str) -> float | None:
    if column not in row.index or pd.isna(row[column]):
        return None
    return float(row[column])


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    numbers = parse_case_spec(args.cases)
    rows = load_case_rows(args.case_matrix, args.case_matrix_sheet, numbers)
    orbit_periods = load_orbit_period_map(
        args.orbit_catalog, sheet=args.orbit_catalog_sheet
    )

    _log(f"Connecting to TD (attach_only={args.attach_only}) …")
    td, OpenTD = connect_thermal_desktop(
        dwg_path=args.dwg,
        attach_only=bool(args.attach_only),
    )

    if args.patch_timing:
        for row in rows:
            case_id = str(row["case_id"])
            orbit_name = None
            if "orbit_case" in row.index and pd.notna(row["orbit_case"]):
                orbit_name = str(row["orbit_case"]).strip()
            period, duration_s, output_s = resolve_case_timing(
                orbit_name=orbit_name,
                orbit_periods=orbit_periods,
                matrix_duration_s=_matrix_optional_float(row, "duration_s"),
                matrix_sample_interval_s=_matrix_optional_float(
                    row, "sample_interval_s"
                ),
            )
            _log(f"\n=== patch timing {case_id} ===")
            _log(f"  orbit_period_s: {period}")
            case = find_case_set(td, group=args.group, name=case_id)
            patch_case_timing(
                case,
                OpenTD,
                duration_s=duration_s,
                output_interval_s=output_s,
                dry_run=args.dry_run,
            )
            if args.dry_run:
                _log("  dry-run: not written to TD")
        _log("\nDone.")
        return 0

    template_number = parse_case_spec(args.template)
    if len(template_number) != 1:
        raise ValueError("--template must be a single case number")
    template_number = template_number[0]
    optical = load_optical_catalog(args.optical_yaml)
    cli_overrides = parse_overrides(args.override)
    template = find_case_set(td, group=args.group, number=template_number)

    for row in rows:
        case_id = str(row["case_id"])
        orbit_name = None
        if "orbit_case" in row.index and pd.notna(row["orbit_case"]):
            orbit_name = str(row["orbit_case"]).strip()

        period, duration_s, output_s = resolve_case_timing(
            orbit_name=orbit_name,
            orbit_periods=orbit_periods,
            matrix_duration_s=_matrix_optional_float(row, "duration_s"),
            matrix_sample_interval_s=_matrix_optional_float(row, "sample_interval_s"),
        )

        symbol_overrides: dict[str, str] = {}
        comment_overrides: dict[str, str] = {}
        if args.symbols_from_matrix:
            symbol_overrides, comment_overrides = build_symbol_overrides_from_row(
                row, optical=optical
            )
        symbol_overrides.update(cli_overrides)

        _log(f"\n=== create {case_id} ===")
        _log(
            "  symbols-from-matrix: "
            + ("on" if args.symbols_from_matrix else "off")
        )
        if period is not None:
            _log(f"  orbit_period_s: {period}")
        created = clone_case_set(
            td,
            OpenTD,
            template=template,
            new_name=case_id,
            group=args.group,
            orbit_name=orbit_name,
            symbol_overrides=symbol_overrides,
            comment_overrides=comment_overrides,
            duration_s=duration_s,
            output_interval_s=output_s,
            dry_run=args.dry_run,
        )
        if args.dry_run:
            _log("  dry-run: not written to TD")
            continue

        verify = dump_symbol_map(created)
        for key, expected in symbol_overrides.items():
            actual = verify.get(key)
            if _clean_symbol_value(actual) != _clean_symbol_value(expected):
                raise RuntimeError(
                    f"Post-create symbol mismatch on {case_id}: "
                    f"{key}={actual!r}, expected {expected!r}"
                )
        _log(f"  created OK: {created.Name}")

    _log("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
