"""Run the Femap thermal-deformation workflow for one or more TD case folders.

Prerequisites
-------------
1. Open ``C:/Users/Hide/Femap/research_model/research_model.modfem`` in Femap.
2. Prepare each case folder with ``mapper_from_TD/output.dat`` already present
   (from ``python -m src.thermal_desktop.run_td_cases --cases ...``).

What this script does per case
------------------------------
1. Delete existing load sets and output sets in the open Femap model.
2. Import ``mapper_from_TD/output.dat`` as Nastran TEMP* load sets.
3. Point Nastran output to the case folder.
4. Rebuild analysis cases (one per temperature load set) and run analysis.
5. Export STT/LCT translation+rotation Excel into
   ``inputs/data_femap_deformation/{case_id}.xlsx``.

Example
-------
# Same case-number syntax as TD:
python -m src.femap_deformation.run_femap_case --cases 8,9

# Or full folder name:
python -m src.femap_deformation.run_femap_case --case-id 08_LTAN06_...
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

from src.thermal_desktop.case_selection import case_number_from_name, parse_case_spec

from .export_stt_lct_excel import export_stt_lct_results
from .femap_com import (
    FE_OK,
    FT_LOAD_DIR,
    FT_OUT_CASE,
    FAP_NX_NASTRAN,
    connect_femap,
    delete_all_of_type,
    entity_count,
    FemapComError,
    rebuild_analysis_cases_from_loads,
    require_ok,
    set_nastran_output_dir,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FEMAP_MODEL_ROOT = Path(r"C:\Users\Hide\Femap\research_model")
DEFAULT_EXCEL_DIR = REPO_ROOT / "inputs" / "data_femap_deformation"
DEFAULT_NODE_CONFIG = DEFAULT_EXCEL_DIR / "stt_lct_node_config.json"
DEFAULT_ANALYSIS_ID = 1


def _log(msg: str) -> None:
    print(msg, flush=True)


def resolve_case_dir(model_root: Path, case_id: str) -> Path:
    case_dir = model_root / case_id
    if not case_dir.is_dir():
        raise FileNotFoundError(f"Case folder not found: {case_dir}")
    mapper = case_dir / "mapper_from_TD" / "output.dat"
    if not mapper.is_file():
        raise FileNotFoundError(f"Missing mapper file: {mapper}")
    return case_dir


def list_numbered_case_folders(model_root: Path) -> list[tuple[int, str]]:
    """Return ``(case_number, folder_name)`` for ``NN_*`` dirs under model_root."""
    rows: list[tuple[int, str]] = []
    if not model_root.is_dir():
        return rows
    for path in sorted(model_root.iterdir(), key=lambda p: p.name.casefold()):
        if not path.is_dir() or path.name.startswith("_"):
            continue
        number = case_number_from_name(path.name)
        if number is not None:
            rows.append((number, path.name))
    return rows


def resolve_case_ids_from_numbers(model_root: Path, numbers: list[int]) -> list[str]:
    """
    Map case numbers (same syntax as TD ``--cases``) to Femap folder names.

    Expects one ``NN_*`` folder per number under ``model_root``.
    """
    by_num: dict[int, list[str]] = {}
    for number, name in list_numbered_case_folders(model_root):
        by_num.setdefault(number, []).append(name)

    case_ids: list[str] = []
    missing: list[int] = []
    ambiguous: list[str] = []
    for number in numbers:
        names = by_num.get(number, [])
        if not names:
            missing.append(number)
            continue
        if len(names) > 1:
            ambiguous.append(f"{number} → {names}")
            continue
        case_ids.append(names[0])

    if missing or ambiguous:
        available = ", ".join(f"{n}:{name}" for n, name in list_numbered_case_folders(model_root))
        parts: list[str] = []
        if missing:
            parts.append(f"not found: {missing}")
        if ambiguous:
            parts.append(f"ambiguous: {ambiguous}")
        raise FileNotFoundError(
            "Could not resolve --cases under "
            f"{model_root} ({'; '.join(parts)}). Available: {available or '(none)'}"
        )
    return case_ids


def clean_previous_loads_and_results(app) -> dict[str, int]:
    n_out = delete_all_of_type(app, FT_OUT_CASE)
    n_load = delete_all_of_type(app, FT_LOAD_DIR)
    _log(f"  deleted output sets: {n_out}")
    _log(f"  deleted load sets  : {n_load}")
    return {"output_sets": n_out, "load_sets": n_load}


def import_mapper_temperature_loads(app, mapper_dat: Path) -> int:
    """
    Import TD mapper Nastran TEMP* cards into the open model as load sets.

    ``feFileReadNastran(brand, filename)`` with brand=FAP_NX_NASTRAN matches the
    GUI 'Import analysis model' path used in the manual workflow.
    """
    before = entity_count(app, FT_LOAD_DIR)
    app.DialogAutoSkip = 1
    try:
        rc = app.feFileReadNastran(FAP_NX_NASTRAN, str(mapper_dat))
    finally:
        app.DialogAutoSkip = 0
    require_ok(rc, f"feFileReadNastran({mapper_dat})")
    after = entity_count(app, FT_LOAD_DIR)
    added = after - before
    _log(f"  load sets after import: {after} (added {added})")
    if added <= 0:
        raise FemapComError(
            "Mapper import did not create load sets. "
            "Check that output.dat contains TEMP* cards and that Femap accepted the import."
        )
    return added


# Nastran/Femap run artifacts (not STT/LCT Excel, not mapper_from_TD).
SOLVER_FILE_GLOBS = (
    "research_model-*.dat",
    "research_model-*.f04",
    "research_model-*.f06",
    "research_model-*.log",
    "research_model-*.mon*",
    "research_model-*.op2",
    "research_model-*.xdb",
    "research_model-*.plt",
    "research_model-*.pch",
    "thermal.dat",
    "thermal*.dat",
    "thermal*.f04",
    "thermal*.f06",
    "thermal*.log",
    "thermal*.op2",
    "thermal*.mon*",
)

# Never move these out of the model root.
_MODEL_ROOT_KEEP = frozenset(
    {
        "research_model.modfem",
        "research_model.bdf",
        "sat_model.step",
    }
)


def clear_case_solver_outputs(case_dir: Path) -> None:
    """Remove previous Nastran run artifacts in the case folder (keep mapper_from_TD)."""
    removed = 0
    for pattern in SOLVER_FILE_GLOBS:
        for path in case_dir.glob(pattern):
            if path.is_file():
                path.unlink(missing_ok=True)
                removed += 1
    if removed:
        _log(f"  cleared {removed} previous solver file(s) in case folder")


def collect_solver_outputs_into_case_dir(
    *,
    case_dir: Path,
    model_root: Path,
) -> list[Path]:
    """
    Ensure Nastran/Femap solver artifacts live under ``case_dir``.

    Primary path: AnalysisMgr.NasExecOutDir writes them there directly.
    Fallback: move leftovers from ``model_root`` (where Femap dumps
    ``research_model-####.*`` when NasExecOutDir was empty/ignored).
    STT/LCT Excel is intentionally not moved here.
    """
    case_dir = Path(case_dir)
    model_root = Path(model_root)
    case_dir.mkdir(parents=True, exist_ok=True)

    moved: list[Path] = []
    for pattern in SOLVER_FILE_GLOBS:
        for src in model_root.glob(pattern):
            if not src.is_file():
                continue
            if src.name in _MODEL_ROOT_KEEP:
                continue
            # Only files directly under model_root (not nested case folders).
            if src.parent.resolve() != model_root.resolve():
                continue
            dest = case_dir / src.name
            if dest.resolve() == src.resolve():
                continue
            if dest.exists():
                dest.unlink()
            shutil.move(str(src), str(dest))
            moved.append(dest)
            _log(f"  moved solver file -> {dest.name}")

    present = [
        p
        for pattern in SOLVER_FILE_GLOBS
        for p in case_dir.glob(pattern)
        if p.is_file()
    ]
    _log(f"  solver files in case folder: {len(present)}")
    return moved


def _nastran_process_count() -> int:
    try:
        import psutil
    except ImportError:
        # Fallback without psutil: approximate via tasklist on Windows.
        import subprocess

        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", "IMAGENAME eq nastran.exe"],
                text=True,
                errors="replace",
            )
            return sum(1 for line in out.splitlines() if "nastran.exe" in line.lower())
        except Exception:
            return -1
    return sum(1 for p in psutil.process_iter(["name"]) if (p.info.get("name") or "").lower() == "nastran.exe")


def wait_for_analysis_results(
    app,
    *,
    expected_output_sets: int,
    poll_sec: float = 5.0,
    timeout_sec: float = 1800.0,
    stable_polls: int = 2,
) -> int:
    """
    ``Analyze()`` returns immediately after launching Nastran. Wait until Femap
    has loaded enough output sets.

    Completion criteria:
    - output-set count >= expected_output_sets
    - count stays unchanged for ``stable_polls`` consecutive polls
      (avoids racing while Femap is still attaching results)
    """
    if expected_output_sets <= 0:
        raise FemapComError("expected_output_sets must be positive")

    t0 = time.time()
    last_count = -1
    stable = 0
    _log(
        f"  waiting for >= {expected_output_sets} output sets "
        f"(poll={poll_sec:.0f}s, timeout={timeout_sec:.0f}s)..."
    )

    while True:
        n_out = entity_count(app, FT_OUT_CASE)
        n_nas = _nastran_process_count()
        elapsed = time.time() - t0

        if n_out == last_count:
            stable += 1
        else:
            stable = 0
            last_count = n_out

        nas_txt = "?" if n_nas < 0 else str(n_nas)
        _log(
            f"  ... t={elapsed:6.1f}s  output_sets={n_out}/{expected_output_sets}  "
            f"nastran_procs={nas_txt}  stable={stable}/{stable_polls}"
        )

        if n_out >= expected_output_sets and stable >= stable_polls:
            _log(f"  analysis results ready: {n_out} output sets in {elapsed:.1f}s")
            return n_out

        if elapsed >= timeout_sec:
            raise FemapComError(
                f"Timed out after {elapsed:.1f}s waiting for analysis results "
                f"(have {n_out}/{expected_output_sets} output sets)."
            )
        time.sleep(poll_sec)


def run_analysis(
    app,
    analysis_id: int = DEFAULT_ANALYSIS_ID,
    *,
    expected_output_sets: int,
    case_dir: Path,
    poll_sec: float = 5.0,
    timeout_sec: float = 1800.0,
) -> int:
    am = app.feAnalysisMgr
    require_ok(am.Get(analysis_id), f"AnalysisMgr.Get({analysis_id})")
    # Keep Output Directory on the analysis set (manual Femap workflow).
    # Clearing NasExecOutDir previously dumped research_model-####.* into model root.
    am.NasExecOutDir = str(case_dir)
    am.NasExecAnalyzeFilename = ""
    require_ok(am.Put(analysis_id), f"AnalysisMgr.Put({analysis_id})")

    n_before = entity_count(app, FT_OUT_CASE)
    _log(f"  starting Analyze({analysis_id}) ... (output sets before: {n_before})")
    _log(f"  NasExecOutDir = {am.NasExecOutDir!r}")
    t0 = time.time()
    rc = am.Analyze(analysis_id)
    launch_dt = time.time() - t0
    require_ok(rc, f"Analyze({analysis_id})")
    _log(f"  Analyze() returned in {launch_dt:.1f}s (Nastran launched asynchronously)")

    return wait_for_analysis_results(
        app,
        expected_output_sets=expected_output_sets,
        poll_sec=poll_sec,
        timeout_sec=timeout_sec,
    )


def export_case_excel(
    app,
    *,
    case_id: str,
    case_dir: Path,
    excel_dir: Path,
    node_config: Path,
) -> Path:
    excel_path = excel_dir / f"{case_id}.xlsx"
    _log(f"  exporting STT/LCT Excel -> {excel_path}")
    export_stt_lct_results(app, excel_path, node_config_path=node_config)
    case_excel = case_dir / f"{case_id}.xlsx"
    shutil.copy2(excel_path, case_excel)
    _log(f"  copied Excel to case folder: {case_excel}")
    return excel_path


def run_one_case(
    app,
    *,
    case_id: str,
    model_root: Path,
    excel_dir: Path,
    node_config: Path,
    skip_analyze: bool = False,
    skip_export: bool = False,
    export_only: bool = False,
    analysis_id: int = DEFAULT_ANALYSIS_ID,
    max_loads: int | None = None,
    poll_sec: float = 5.0,
    timeout_sec: float = 1800.0,
) -> dict:
    case_dir = resolve_case_dir(model_root, case_id)
    mapper_dat = case_dir / "mapper_from_TD" / "output.dat"
    excel_path = excel_dir / f"{case_id}.xlsx"

    _log(f"=== case {case_id} ===")
    _log(f"  case dir : {case_dir}")
    _log(f"  mapper   : {mapper_dat}")

    if export_only:
        n_out = entity_count(app, FT_OUT_CASE)
        _log(f"  export-only: using existing Femap results ({n_out} output sets)")
        if n_out <= 0:
            raise FemapComError("export-only requested but no output sets exist in Femap.")
        out = export_case_excel(
            app,
            case_id=case_id,
            case_dir=case_dir,
            excel_dir=excel_dir,
            node_config=node_config,
        )
        return {
            "case_id": case_id,
            "case_dir": str(case_dir),
            "n_loads": None,
            "n_cases": None,
            "excel_path": str(out),
            "analyzed": False,
            "exported_only": True,
        }

    clear_case_solver_outputs(case_dir)
    _log("  cleaning previous loads/results in Femap model...")
    clean_previous_loads_and_results(app)

    _log("  importing mapper temperature loads...")
    n_loads = import_mapper_temperature_loads(app, mapper_dat)

    set_nastran_output_dir(app, case_dir, analysis_id=analysis_id)
    _log(f"  Nastran output dir -> {case_dir}")

    _log("  rebuilding analysis cases from load sets...")
    if max_loads is not None:
        _log(f"  max-loads limit: {max_loads}")
    n_cases = rebuild_analysis_cases_from_loads(
        app,
        analysis_id=analysis_id,
        max_loads=max_loads,
    )
    _log(f"  analysis cases: {n_cases}")

    result = {
        "case_id": case_id,
        "case_dir": str(case_dir),
        "n_loads": n_loads,
        "n_cases": n_cases,
        "excel_path": None,
        "analyzed": False,
    }

    if skip_analyze:
        _log("  skip-analyze: stopping before Analyze()")
        return result

    n_out = run_analysis(
        app,
        analysis_id=analysis_id,
        expected_output_sets=n_cases,
        case_dir=case_dir,
        poll_sec=poll_sec,
        timeout_sec=timeout_sec,
    )
    result["analyzed"] = True
    result["n_output_sets"] = n_out

    _log("  collecting solver outputs into case folder...")
    moved = collect_solver_outputs_into_case_dir(case_dir=case_dir, model_root=model_root)
    result["solver_files_moved"] = len(moved)

    if skip_export:
        _log("  skip-export: solver results left in Femap / case folder only")
        return result

    out = export_case_excel(
        app,
        case_id=case_id,
        case_dir=case_dir,
        excel_dir=excel_dir,
        node_config=node_config,
    )
    result["excel_path"] = str(out)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--cases",
        help=(
            "Case numbers under --model-root, same syntax as TD: "
            "7,8,9 or 10-15 or 7,10-12,15. Resolves NN_* folder names."
        ),
    )
    p.add_argument(
        "--case-id",
        action="append",
        dest="case_ids",
        help="Full case folder name under --model-root. Repeatable.",
    )
    p.add_argument(
        "--case-dir",
        type=Path,
        help="Absolute path to one case folder (alternative to --case-id / --cases).",
    )
    p.add_argument(
        "--list-cases",
        action="store_true",
        help="List NN_* case folders under --model-root and exit.",
    )
    p.add_argument(
        "--model-root",
        type=Path,
        default=DEFAULT_FEMAP_MODEL_ROOT,
        help=f"Femap research_model root (default: {DEFAULT_FEMAP_MODEL_ROOT})",
    )
    p.add_argument(
        "--excel-dir",
        type=Path,
        default=DEFAULT_EXCEL_DIR,
        help=f"Directory for STT/LCT Excel exports (default: {DEFAULT_EXCEL_DIR})",
    )
    p.add_argument(
        "--node-config",
        type=Path,
        default=DEFAULT_NODE_CONFIG,
        help=f"STT/LCT node config JSON (default: {DEFAULT_NODE_CONFIG})",
    )
    p.add_argument(
        "--analysis-id",
        type=int,
        default=DEFAULT_ANALYSIS_ID,
        help="Femap Analysis Set ID to reuse (default: 1 = thermal_def).",
    )
    p.add_argument(
        "--skip-analyze",
        action="store_true",
        help="Stop after load import + analysis-case rebuild (no Nastran run).",
    )
    p.add_argument(
        "--skip-export",
        action="store_true",
        help="Run analysis but skip STT/LCT Excel export.",
    )
    p.add_argument(
        "--export-only",
        action="store_true",
        help="Skip clean/import/analyze; export STT/LCT Excel from existing Femap results.",
    )
    p.add_argument(
        "--max-loads",
        type=int,
        default=None,
        help="Only build/run the first N temperature load sets (smoke test).",
    )
    p.add_argument(
        "--poll-sec",
        type=float,
        default=5.0,
        help="Seconds between analysis-completion polls (default: 5).",
    )
    p.add_argument(
        "--timeout-sec",
        type=float,
        default=1800.0,
        help="Max seconds to wait for analysis results (default: 1800).",
    )
    p.add_argument(
        "--start-femap",
        action="store_true",
        help="Dispatch a new Femap if none is running (still need the model open).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    model_root = Path(args.model_root)
    case_ids: list[str] = list(args.case_ids or [])

    if args.case_dir is not None:
        case_dir = Path(args.case_dir)
        case_ids.append(case_dir.name)
        model_root = case_dir.parent

    if args.list_cases:
        rows = list_numbered_case_folders(model_root)
        if not rows:
            _log(f"No NN_* case folders under {model_root}")
            return 0
        _log(f"Cases under {model_root}:")
        for number, name in rows:
            mapper = model_root / name / "mapper_from_TD" / "output.dat"
            flag = "mapper=OK" if mapper.is_file() else "mapper=MISSING"
            _log(f"  {number:>3d}  {name}  ({flag})")
        return 0

    if args.cases:
        try:
            numbers = parse_case_spec(args.cases)
            case_ids.extend(resolve_case_ids_from_numbers(model_root, numbers))
        except (ValueError, FileNotFoundError) as exc:
            _log(f"ERROR: {exc}")
            return 1

    seen: set[str] = set()
    unique_ids: list[str] = []
    for case_id in case_ids:
        if case_id not in seen:
            seen.add(case_id)
            unique_ids.append(case_id)
    case_ids = unique_ids

    if not case_ids:
        raise SystemExit("Provide --cases and/or --case-id and/or --case-dir.")

    _log("Resolved cases: " + ", ".join(case_ids))

    try:
        app, model_name = connect_femap(start_if_needed=args.start_femap)
    except FemapComError as exc:
        _log(f"ERROR: {exc}")
        return 1

    _log(f"Femap model: {model_name or '(unknown)'}")
    if model_name and "research_model" not in model_name.replace("\\", "/").lower():
        _log("WARNING: expected research_model.modfem to be open.")

    failures: list[str] = []
    for case_id in case_ids:
        try:
            run_one_case(
                app,
                case_id=case_id,
                model_root=model_root,
                excel_dir=Path(args.excel_dir),
                node_config=Path(args.node_config),
                skip_analyze=args.skip_analyze,
                skip_export=args.skip_export,
                export_only=args.export_only,
                analysis_id=args.analysis_id,
                max_loads=args.max_loads,
                poll_sec=args.poll_sec,
                timeout_sec=args.timeout_sec,
            )
        except Exception as exc:
            _log(f"ERROR on {case_id}: {exc}")
            failures.append(case_id)
            if len(case_ids) == 1:
                raise

    if failures:
        _log(f"Failed cases: {failures}")
        return 1
    _log("All requested cases finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
