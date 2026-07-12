"""Re-import case ``.op2`` results in Femap and refresh Excel exports.

Use this when analysis is already done and you only need to:
1. Delete previous output sets in the open Femap model
2. Import ``research_model-*.op2`` (or ``thermal*.op2``) from the case folder
3. Export STT/LCT + panel-center nodal translation/rotation to
   ``inputs/data_femap_deformation/{case_id}.xlsx``

Prerequisites
-------------
Open ``C:/Users/Hide/Femap/research_model/research_model.modfem`` in Femap.
Do not run this while another ``run_femap_case`` Analyze() is in progress.

Example
-------
python -m src.femap_deformation.reexport_from_op2 --cases 3-15
python -m src.femap_deformation.reexport_from_op2 --cases 4,5 --dry-run
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .export_stt_lct_excel import export_stt_lct_results, load_export_nodes
from .femap_com import (
    FT_OUT_CASE,
    connect_femap,
    delete_all_output_sets,
    entity_count,
    FemapComError,
    import_nastran_results_op2,
)
from .run_femap_case import (
    DEFAULT_EXCEL_DIR,
    DEFAULT_FEMAP_MODEL_ROOT,
    DEFAULT_NODE_CONFIG,
    list_numbered_case_folders,
    resolve_case_ids_from_numbers,
)
from src.thermal_desktop.case_selection import parse_case_spec


OP2_GLOBS = (
    "research_model-*.op2",
    "thermal*.op2",
)


def _log(msg: str) -> None:
    print(msg, flush=True)


def find_case_op2_files(case_dir: Path) -> list[Path]:
    """Return OP2 files in the case folder, sorted by name."""
    found: list[Path] = []
    seen: set[Path] = set()
    for pattern in OP2_GLOBS:
        for path in sorted(case_dir.glob(pattern)):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            found.append(path)
    return found


def resolve_case_dir_for_op2(model_root: Path, case_id: str) -> Path:
    case_dir = model_root / case_id
    if not case_dir.is_dir():
        raise FileNotFoundError(f"Case folder not found: {case_dir}")
    return case_dir


def reexport_one_case(
    app,
    *,
    case_id: str,
    model_root: Path,
    excel_dir: Path,
    node_config: Path,
    include_panel_centers: bool = True,
    dry_run: bool = False,
) -> dict:
    case_dir = resolve_case_dir_for_op2(model_root, case_id)
    op2_files = find_case_op2_files(case_dir)
    excel_path = excel_dir / f"{case_id}.xlsx"
    nodes = load_export_nodes(node_config, include_panel_centers=include_panel_centers)

    _log(f"=== case {case_id} ===")
    _log(f"  case dir : {case_dir}")
    _log(f"  op2 files: {len(op2_files)}")
    for path in op2_files:
        _log(f"    - {path.name}")
    _log(f"  export nodes ({len(nodes)}): " + ", ".join(f"{lab}:{nid}" for lab, nid in nodes))
    _log(f"  excel    : {excel_path}")

    if not op2_files:
        raise FileNotFoundError(f"No .op2 files found under {case_dir}")

    if dry_run:
        _log("  dry-run: skip delete / import / export")
        return {
            "case_id": case_id,
            "case_dir": str(case_dir),
            "op2_files": [str(p) for p in op2_files],
            "excel_path": str(excel_path),
            "n_output_sets": None,
            "dry_run": True,
        }

    n_deleted = delete_all_output_sets(app)
    _log(f"  deleted output sets: {n_deleted}")

    n_out = 0
    for path in op2_files:
        _log(f"  importing results: {path.name}")
        n_out = import_nastran_results_op2(app, path)
        _log(f"  output sets after import: {n_out}")

    if n_out <= 0:
        raise FemapComError(f"No output sets after OP2 import for {case_id}")

    _log(f"  exporting Excel ({len(nodes)} nodes) -> {excel_path}")
    export_stt_lct_results(
        app,
        excel_path,
        node_config_path=node_config,
        include_panel_centers=include_panel_centers,
    )
    case_excel = case_dir / f"{case_id}.xlsx"
    shutil.copy2(excel_path, case_excel)
    _log(f"  copied Excel to case folder: {case_excel}")

    return {
        "case_id": case_id,
        "case_dir": str(case_dir),
        "op2_files": [str(p) for p in op2_files],
        "excel_path": str(excel_path),
        "n_output_sets": n_out,
        "n_nodes": len(nodes),
        "dry_run": False,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--cases",
        help=(
            "Case numbers under --model-root, same syntax as TD/Femap: "
            "7,8,9 or 10-15 or 7,10-12,15."
        ),
    )
    p.add_argument(
        "--case-id",
        action="append",
        dest="case_ids",
        help="Full case folder name under --model-root. Repeatable.",
    )
    p.add_argument(
        "--list-cases",
        action="store_true",
        help="List NN_* case folders that have .op2 files and exit.",
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
        help=f"Excel output directory (default: {DEFAULT_EXCEL_DIR})",
    )
    p.add_argument(
        "--node-config",
        type=Path,
        default=DEFAULT_NODE_CONFIG,
        help=f"Node config JSON (default: {DEFAULT_NODE_CONFIG})",
    )
    p.add_argument(
        "--stt-lct-only",
        action="store_true",
        help="Export STT/LCT only (skip panel-center nodes).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve cases/OP2 paths and print plan without touching Femap.",
    )
    p.add_argument(
        "--start-femap",
        action="store_true",
        help="Start Femap via COM if no session is running (usually keep model open).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    model_root = Path(args.model_root)

    if args.list_cases:
        rows = list_numbered_case_folders(model_root)
        if not rows:
            _log(f"No NN_* case folders under {model_root}")
            return 1
        for number, name in rows:
            case_dir = model_root / name
            n_op2 = len(find_case_op2_files(case_dir))
            flag = "op2=OK" if n_op2 else "op2=MISSING"
            _log(f"  {number:2d}  {name}  ({flag}, n={n_op2})")
        return 0

    case_ids: list[str] = []
    if args.cases:
        case_ids.extend(resolve_case_ids_from_numbers(model_root, parse_case_spec(args.cases)))
    if args.case_ids:
        case_ids.extend(args.case_ids)

    # Preserve order, drop duplicates.
    seen: set[str] = set()
    ordered: list[str] = []
    for case_id in case_ids:
        if case_id not in seen:
            seen.add(case_id)
            ordered.append(case_id)
    case_ids = ordered

    if not case_ids:
        _log("Specify --cases and/or --case-id (or --list-cases).")
        return 2

    include_panel_centers = not args.stt_lct_only
    nodes = load_export_nodes(args.node_config, include_panel_centers=include_panel_centers)
    _log(f"Will export {len(nodes)} nodes: " + ", ".join(f"{lab}:{nid}" for lab, nid in nodes))

    app = None
    if not args.dry_run:
        app, model_name = connect_femap(start_if_needed=args.start_femap)
        _log(f"Connected to Femap model: {model_name or '(unnamed)'}")
        n_existing = entity_count(app, FT_OUT_CASE)
        _log(f"Existing output sets before first case: {n_existing}")

    results = []
    failures: list[tuple[str, str]] = []
    for case_id in case_ids:
        try:
            results.append(
                reexport_one_case(
                    app,
                    case_id=case_id,
                    model_root=model_root,
                    excel_dir=Path(args.excel_dir),
                    node_config=Path(args.node_config),
                    include_panel_centers=include_panel_centers,
                    dry_run=args.dry_run,
                )
            )
        except Exception as exc:
            _log(f"  ERROR: {exc}")
            failures.append((case_id, str(exc)))

    _log("")
    _log(f"Done: {len(results)} ok, {len(failures)} failed / {len(case_ids)} requested")
    for case_id, err in failures:
        _log(f"  FAIL {case_id}: {err}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
