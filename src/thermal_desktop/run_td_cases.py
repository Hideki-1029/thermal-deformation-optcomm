"""Run TD Case Sets and export PostProcessing DataMapper files to Femap."""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from .case_selection import SelectedCase, case_number_from_name, parse_case_spec, select_cases
from .opentd_runtime import DEFAULT_DWG, connect_thermal_desktop


DEFAULT_FEMAP_MODEL_ROOT = Path(r"C:\Users\Hide\Femap\research_model")
DEFAULT_STAGING_DIR = DEFAULT_FEMAP_MODEL_ROOT / "_td_mapper_staging"
MAPPER_SUBDIR = "mapper_from_TD"
OUTPUT_BASENAME = "output"
# Relative path to set in the TD DataMapper GUI (from the DWG directory).
DEFAULT_STAGING_OUTPUT_REL = (
    r"..\..\Femap\research_model\_td_mapper_staging\output.dat"
)


def _log(msg: str) -> None:
    print(msg, flush=True)


def dwg_directory(dwg_path: Path) -> Path:
    return dwg_path.resolve().parent


def default_staging_dir(femap_root: Path) -> Path:
    return Path(femap_root) / "_td_mapper_staging"


def mapper_dest_dir(femap_root: Path, case_id: str) -> Path:
    return femap_root / case_id / MAPPER_SUBDIR


def mapper_output_dat(femap_root: Path, case_id: str) -> Path:
    return mapper_dest_dir(femap_root, case_id) / f"{OUTPUT_BASENAME}.dat"


def resolve_sav_path(dwg_dir: Path, case: SelectedCase) -> Path:
    """Locate the SINDA save file for a case (usually ``{group}/{sinda}.sav``)."""
    base = case.sinda_filenames
    if base.lower().endswith(".sav"):
        base = base[:-4]
    candidates = [
        dwg_dir / case.group_name / f"{base}.sav",
        dwg_dir / case.group_name / f"{case.name}.sav",
        dwg_dir / f"{base}.sav",
        dwg_dir / f"{case.name}.sav",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        "Save file not found for case "
        f"{case.name!r}. Tried:\n  " + "\n  ".join(str(p) for p in candidates)
    )


def get_data_mapper(td: Any, mapper_handle: str | None = None) -> Any:
    """Return the PostProcessing DataMapper (by handle, or the only/first one)."""
    mappers = list(td.GetPostProcessingDataMappers())
    if not mappers:
        raise RuntimeError(
            "No PostProcessing DataMapper found in the TD model. "
            "Create one in Model Browser first."
        )

    if mapper_handle:
        key = mapper_handle.casefold()
        for mapper in mappers:
            handle = str(getattr(mapper, "Handle", "") or "")
            name = str(getattr(mapper, "Name", "") or "")
            label = str(getattr(mapper, "Label", "") or "")
            if key in {handle.casefold(), name.casefold(), label.casefold()}:
                return mapper
            if key in handle.casefold() or key in name.casefold() or key in label.casefold():
                return mapper
        raise RuntimeError(
            f"DataMapper {mapper_handle!r} not found. "
            f"Available: {[getattr(m, 'Handle', None) or getattr(m, 'Name', '?') for m in mappers]}"
        )

    if len(mappers) > 1:
        handles = [getattr(m, "Handle", None) or getattr(m, "Name", "?") for m in mappers]
        _log(
            f"  warning: {len(mappers)} DataMappers found; using the first one "
            f"({handles[0]}). Pass --mapper-handle to select."
        )
    return mappers[0]


def refresh_mapper(mapper: Any) -> None:
    """Pull latest DWG-side DataMapper state into the client object (read-only)."""
    if hasattr(mapper, "UpdateFromTD"):
        mapper.UpdateFromTD()


def reset_td_graphics(td: Any) -> None:
    if hasattr(td, "ResetGraphics"):
        try:
            td.ResetGraphics()
            _log("  ResetGraphics()")
        except Exception as exc:
            _log(f"  warning: ResetGraphics failed: {exc}")


def wait_while_case_running(td: Any, *, timeout_s: float = 0.0, poll_s: float = 2.0) -> None:
    manager = td.CaseSetManager
    if not hasattr(manager, "IsCaseRunning"):
        return
    start = time.time()
    while True:
        try:
            running = bool(manager.IsCaseRunning())
        except Exception:
            return
        if not running:
            return
        if timeout_s > 0 and (time.time() - start) > timeout_s:
            raise TimeoutError(f"Case still running after {timeout_s:.0f}s")
        time.sleep(poll_s)


def run_case(td: Any, case: SelectedCase) -> None:
    _log(f"  running Case Set: {case.name} (group={case.group_name})")
    try:
        td.CaseSetManager.Run(case.name, case.group_name)
    except TypeError:
        td.CaseSetManager.Run(case.name, case.group_name, False)
    except Exception:
        case.case_set.Run()
    wait_while_case_running(td)
    _log("  Case Set run finished")


def dataset_ref_for_sav(dwg_dir: Path, sav_path: Path) -> str:
    try:
        return str(sav_path.resolve().relative_to(dwg_dir.resolve()))
    except ValueError:
        return str(sav_path.resolve())


def casefold_path_match(a: str, b: str) -> bool:
    na = a.replace("/", "\\").casefold()
    nb = b.replace("/", "\\").casefold()
    return na == nb or na.endswith(nb) or nb.endswith(na)


def legacy_com(td: Any, command: str, *, delay_ms: int = 0) -> str:
    _log(f"  SendLegacyComCommand: {command}")
    try:
        if delay_ms:
            return str(td.SendLegacyComCommand(command, delay_ms) or "")
        return str(td.SendLegacyComCommand(command) or "")
    except TypeError:
        return str(td.SendLegacyComCommand(command) or "")


def dataset_lookup_names(sav_ref: str, sav_name: str) -> list[str]:
    """Names to try with DatasetManager.GetDataset (relative refs first)."""
    names = [sav_ref, sav_ref.replace("\\", "/"), sav_name]
    deduped: list[str] = []
    seen: set[str] = set()
    for name in names:
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(name)
    return deduped


def _dataset_name_for_create(sav_ref: str) -> str:
    return sav_ref.replace("\\", "_")


def _is_absolute_path_ref(path_ref: str) -> bool:
    ref = path_ref.strip()
    if not ref:
        return False
    if ref.startswith("\\\\"):
        return True
    if len(ref) >= 2 and ref[1] == ":":
        return True
    return ref.startswith("/")


def _normalized_path_ref(path_ref: str) -> str:
    return path_ref.replace("/", "\\").casefold()


def _exact_dataset_ref_match(ds_name: str, sav_ref: str) -> bool:
    left = _normalized_path_ref(ds_name)
    right = _normalized_path_ref(sav_ref)
    return left == right or left == _normalized_path_ref(sav_ref.replace("\\", "/"))


def _matching_dataset_entries(
    datasets: list[Any],
    *,
    sav_ref: str,
    sav_name: str,
) -> list[tuple[int, str, Any]]:
    """Return matching datasets, preferring relative-path registry entries."""
    matches: list[tuple[int, str, Any]] = []
    for ds in datasets:
        ds_name = str(getattr(ds, "Name", "") or "")
        if _exact_dataset_ref_match(ds_name, sav_ref):
            priority = 0
        elif ds_name.casefold() == sav_name.casefold():
            priority = 1
        elif sav_name.casefold() in ds_name.casefold() or casefold_path_match(
            ds_name, sav_ref
        ):
            priority = 2
        else:
            continue
        if _is_absolute_path_ref(ds_name):
            priority += 3
        matches.append((priority, ds_name, ds))
    matches.sort(key=lambda item: (item[0], item[1].casefold()))
    return matches


def activate_dataset(td: Any, OpenTD: Any, *, sav_path: Path, dwg_dir: Path) -> str:
    """Make ``sav_path`` the active post-processing dataset and verify it stuck.

    Registry entries use the DWG-relative ``.sav`` path only so Postprocessing
    Datasets does not accumulate duplicate absolute-path rows.
    """
    sav_ref = dataset_ref_for_sav(dwg_dir, sav_path)
    sav_name = sav_path.name
    manager = td.DatasetManager

    for name in dataset_lookup_names(sav_ref, sav_name):
        try:
            ds = manager.GetDataset(name)
        except Exception:
            ds = None
        if ds is None:
            continue
        _log(f"  GetDataset({name!r}) → SetCurrent()")
        try:
            ds.SetCurrent()
        except Exception as exc:
            _log(f"  warning: SetCurrent failed: {exc}")
        break
    else:
        try:
            matches = _matching_dataset_entries(
                list(manager.GetDatasets()),
                sav_ref=sav_ref,
                sav_name=sav_name,
            )
            for _, ds_name, ds in matches:
                _log(f"  activating dataset: {ds_name!r}")
                try:
                    ds.SetCurrent()
                except Exception as exc:
                    _log(f"  warning: SetCurrent failed: {exc}")
                break
        except Exception as exc:
            _log(f"  warning: GetDatasets failed: {exc}")

    try:
        legacy_com(td, f'ppsavefile "{sav_ref}"')
    except Exception as exc:
        _log(f"  warning: ppsavefile {sav_ref!r} failed: {exc}")

    current_name = ""
    try:
        current = manager.GetCurrentDataset()
        if current is not None:
            current_name = str(getattr(current, "Name", "") or "")
    except Exception as exc:
        _log(f"  warning: GetCurrentDataset failed: {exc}")

    _log(f"  current dataset after activate: {current_name!r}")
    if sav_name.casefold() not in current_name.casefold() and not casefold_path_match(
        current_name, sav_ref
    ):
        _log(f"  creating dataset for {sav_path.name}")
        Dataset = OpenTD.PostProcessing.Dataset
        dataset = manager.CreateDataset(
            _dataset_name_for_create(sav_ref),
            sav_ref,
            Dataset.DataSourceTypes.SF,
        )
        try:
            dataset.SetCurrent()
        except Exception:
            pass
        current_name = str(getattr(dataset, "Name", "") or sav_ref)
        _log(f"  current dataset after create: {current_name!r}")

    if sav_name.casefold() not in current_name.casefold() and not casefold_path_match(
        current_name, sav_ref
    ):
        raise RuntimeError(
            f"Could not activate PP dataset for {sav_name}. "
            f"GetCurrentDataset()={current_name!r}. "
            "Open the sav in TD's Postprocessing Datasets dialog and retry."
        )
    return current_name


def assert_output_dat_matches_case(output_dat: Path, case: SelectedCase) -> None:
    """Require output.dat header to name this case's .sav (guards against mix-ups)."""
    try:
        with output_dat.open("r", encoding="utf-8", errors="replace") as fh:
            header = "".join(fh.readline() for _ in range(5))
    except OSError as exc:
        raise RuntimeError(f"Could not read {output_dat}: {exc}") from exc

    if case.name.casefold() in header.casefold():
        _log(f"  verified output.dat header mentions {case.name}")
        return

    other = None
    for token in header.replace("/", "\\").split("'"):
        if token.casefold().endswith(".sav"):
            other = token
            break
    raise RuntimeError(
        f"{output_dat} header does not mention case {case.name}"
        + (f" (found {other!r})" if other else "")
        + ".\nRefusing to treat this as the mapped result.\n"
        f"Header:\n{header.strip()}"
    )


def resolve_mapper_output_path(mapper: Any, dwg_dir: Path) -> Path:
    raw = str(getattr(mapper, "OutputFile", "") or "").strip()
    if not raw:
        raise RuntimeError(
            "DataMapper.OutputFile is empty. In TD, set Output File to the staging "
            f"path ({DEFAULT_STAGING_OUTPUT_REL}) and save the DWG. "
            "This script does not call DataMapper.Update()."
        )
    path = Path(raw)
    if not path.is_absolute():
        path = (dwg_dir / path).resolve()
    else:
        path = path.resolve()
    return path


def mapper_output_dir(output_file: Path) -> Path:
    if output_file.suffix:
        return output_file.parent
    return output_file.parent if output_file.name else output_file


def assert_mapper_writes_to_staging(
    mapper: Any,
    dwg_dir: Path,
    staging_dir: Path,
) -> Path:
    """Ensure DataMapper.OutputFile points at the shared staging folder."""
    td_output = resolve_mapper_output_path(mapper, dwg_dir)
    td_out_dir = mapper_output_dir(td_output).resolve()
    expected = staging_dir.resolve()
    if td_out_dir != expected:
        raise RuntimeError(
            "DataMapper OutputFile is not the shared staging folder.\n"
            f"  OutputFile → {td_output}\n"
            f"  resolved dir → {td_out_dir}\n"
            f"  expected staging → {expected}\n"
            "In the TD DataMapper dialog set Output File to:\n"
            f"  {DEFAULT_STAGING_OUTPUT_REL}\n"
            f"  (or absolute: {expected / 'output.dat'})\n"
            "Keep the mapper Enabled, save the DWG, then retry."
        )
    return td_out_dir


def ensure_mapper_enabled(mapper: Any) -> None:
    try:
        enabled = int(mapper.Enabled)
    except Exception:
        enabled = -1
    if enabled != 1:
        raise RuntimeError(
            f"DataMapper Enabled={enabled!r} (need 1). "
            "Enable the mapper in the TD GUI, save the DWG, and retry. "
            "Do not toggle Enabled via OpenTD Update (crashes this model)."
        )


def clear_output_files(dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    removed = 0
    for path in list(dest_dir.glob("output*")) + list(dest_dir.glob("*.dat")):
        if not path.is_file():
            continue
        try:
            path.unlink()
            removed += 1
        except OSError as exc:
            raise RuntimeError(
                f"Cannot delete {path} (is it open in an editor?). "
                f"Close the file and retry. OS error: {exc}"
            ) from exc
    if removed:
        _log(f"  cleared {removed} previous output file(s) in {dest_dir}")


def copy_mapper_outputs(src_dir: Path, dest_dir: Path) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    seen: set[str] = set()
    for pattern in ("output.dat", "output*.txt", "output*.dat"):
        for src in src_dir.glob(pattern):
            if not src.is_file():
                continue
            key = src.name.casefold()
            if key in seen:
                continue
            seen.add(key)
            target = dest_dir / src.name
            shutil.copy2(src, target)
            copied.append(target)
            _log(f"  copied {src.name} → {dest_dir}")
    return copied


def run_tdmapallmappers(td: Any) -> None:
    """
    Run DWG-side mappers without DataMapper.Update/Map.

    Do not pass an append argument: ``tdmapallmappers ""`` inserts literal quotes
    into filenames (e.g. output\"\"MapSummaryGridPoints.txt).
    """
    legacy_com(td, "tdmapallmappers")


def map_case_to_femap(
    td: Any,
    OpenTD: Any,
    *,
    case: SelectedCase,
    dwg_dir: Path,
    femap_root: Path,
    mapper: Any,
    staging_dir: Path,
) -> Path:
    """
    Map one case via staging:

    clear staging → Set Current → tdmapallmappers → header check →
    copy to ``{case}/mapper_from_TD`` → clear staging.
    """
    sav_path = resolve_sav_path(dwg_dir, case)
    dest_dir = mapper_dest_dir(femap_root, case.name)
    dest_dat = mapper_output_dat(femap_root, case.name)
    dest_dir.mkdir(parents=True, exist_ok=True)

    _log(f"  sav: {sav_path}")
    _log(f"  femap dest: {dest_dat}")

    reset_td_graphics(td)
    activate_dataset(td, OpenTD, sav_path=sav_path, dwg_dir=dwg_dir)

    refresh_mapper(mapper)
    ensure_mapper_enabled(mapper)
    baked = str(getattr(mapper, "CurrentPPDataset", "") or "")
    _log(f"  DataMapper.CurrentPPDataset (baked): {baked!r}")

    td_out_dir = assert_mapper_writes_to_staging(mapper, dwg_dir, staging_dir)
    _log(f"  staging dir: {td_out_dir}")
    td_out_dir.mkdir(parents=True, exist_ok=True)

    clear_output_files(td_out_dir)
    run_tdmapallmappers(td)

    staging_dat = td_out_dir / f"{OUTPUT_BASENAME}.dat"
    if not staging_dat.is_file():
        raise FileNotFoundError(
            f"tdmapallmappers finished but {staging_dat} is missing. "
            "Check MapperPP_*.log / DataMapper Enabled + Output File."
        )

    assert_output_dat_matches_case(staging_dat, case)

    clear_output_files(dest_dir)
    copied = copy_mapper_outputs(td_out_dir, dest_dir)
    if not copied:
        raise FileNotFoundError(f"No output* files to copy from {td_out_dir}")

    clear_output_files(td_out_dir)

    if not dest_dat.is_file():
        raise FileNotFoundError(f"Expected {dest_dat} after mapping, but it is missing.")
    assert_output_dat_matches_case(dest_dat, case)

    size_mb = dest_dat.stat().st_size / (1024 * 1024)
    _log(f"  wrote {dest_dat} ({size_mb:.1f} MB)")
    return dest_dat


def list_group_cases(td: Any, group: str) -> None:
    group_key = group.strip().casefold()
    rows = []
    for case in list(td.GetCaseSets()):
        g = str(getattr(case, "GroupName", "") or "")
        if g.casefold() != group_key:
            continue
        name = str(getattr(case, "Name", "") or "")
        rows.append((case_number_from_name(name), name))
    if not rows:
        _log(f"No cases in group {group!r}")
        return
    _log(f"Cases in group {group!r}:")
    for num, name in rows:
        prefix = f"{num:>3d}" if num is not None else "  ?"
        _log(f"  {prefix}  {name}")


def run_pipeline(args: argparse.Namespace) -> int:
    dwg_path = Path(args.dwg)
    femap_root = Path(args.femap_root)
    dwg_dir = dwg_directory(dwg_path)
    staging = Path(args.staging_dir) if args.staging_dir else default_staging_dir(femap_root)

    _log(f"Connecting to TD: {dwg_path}")
    td, OpenTD = connect_thermal_desktop(
        dwg_path=dwg_path,
        dll_path=args.opentd_dll,
        attach_only=args.attach_only,
        start_new=args.start_new,
    )

    if args.list_cases:
        list_group_cases(td, args.group)
        return 0

    numbers = parse_case_spec(args.cases)
    selected = select_cases(list(td.GetCaseSets()), group=args.group, numbers=numbers)
    _log(
        f"Selected {len(selected)} case(s) in group {args.group!r}: "
        + ", ".join(f"{c.number}:{c.name}" for c in selected)
    )

    if args.dry_run:
        _log(f"  staging (TD Output File must match): {staging / 'output.dat'}")
        _log(f"  GUI relative path hint: {DEFAULT_STAGING_OUTPUT_REL}")
        for case in selected:
            try:
                sav: Path | str = resolve_sav_path(dwg_dir, case)
            except FileNotFoundError as exc:
                sav = f"(missing) {exc}"
            _log(f"  [{case.number}] {case.name}")
            _log(f"       sav → {sav}")
            _log(f"       map → staging → {mapper_output_dat(femap_root, case.name)}")
        return 0

    mapper = get_data_mapper(td, args.mapper_handle)
    mapper_handle = str(getattr(mapper, "Handle", "") or args.mapper_handle or "")
    _log(
        f"  using DataMapper handle={mapper_handle or '?'} "
        f"Enabled={getattr(mapper, 'Enabled', '?')}"
    )

    failures: list[str] = []
    for case in selected:
        _log(f"\n=== case {case.number}: {case.name} ===")
        try:
            if not args.map_only:
                run_case(td, case)

            if not args.skip_map:
                mapper = get_data_mapper(td, args.mapper_handle or mapper_handle or None)
                map_case_to_femap(
                    td,
                    OpenTD,
                    case=case,
                    dwg_dir=dwg_dir,
                    femap_root=femap_root,
                    mapper=mapper,
                    staging_dir=staging,
                )
        except Exception as exc:
            _log(f"  ERROR: {exc}")
            failures.append(f"{case.name}: {exc}")
            if args.fail_fast:
                break

    if failures:
        _log("\nFailed cases:")
        for line in failures:
            _log(f"  - {line}")
        return 1

    _log("\nDone.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Run Thermal Desktop Case Sets and copy DataMapper output from a "
            "fixed staging folder into each Femap case's mapper_from_TD."
        )
    )
    p.add_argument("--group", default="transient", help="Case Set group (default: transient)")
    p.add_argument("--cases", help="Case numbers, e.g. 7,8,9 or 10-15 or 7,10-12,15")
    p.add_argument("--dwg", type=Path, default=DEFAULT_DWG, help=f"TD DWG (default: {DEFAULT_DWG})")
    p.add_argument(
        "--femap-root",
        type=Path,
        default=DEFAULT_FEMAP_MODEL_ROOT,
        help=f"Femap research_model root (default: {DEFAULT_FEMAP_MODEL_ROOT})",
    )
    p.add_argument(
        "--staging-dir",
        type=Path,
        default=None,
        help=f"Shared mapper output folder (default: {DEFAULT_STAGING_DIR})",
    )
    p.add_argument(
        "--mapper-handle",
        default=None,
        help="DataMapper handle if multiple exist (e.g. 7C8A)",
    )
    p.add_argument(
        "--opentd-dll",
        default=None,
        help="Optional path to OpenTD.dll / OpenTDv241.dll (else OPENTD_DLL / auto)",
    )
    p.add_argument(
        "--attach-only",
        action="store_true",
        help="Attach to already-open TD (recommended; also auto when acad.exe runs)",
    )
    p.add_argument(
        "--start-new",
        action="store_true",
        help="Force a new TD instance (avoid if the DWG is already open)",
    )
    p.add_argument(
        "--map-only",
        action="store_true",
        help="Skip Case Set run; only map existing .sav results",
    )
    p.add_argument(
        "--skip-map",
        action="store_true",
        help="Run Case Sets only; do not map",
    )
    p.add_argument("--list-cases", action="store_true", help="List cases in --group and exit")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve cases/paths and print the plan; do not run/map",
    )
    p.add_argument("--fail-fast", action="store_true", help="Stop on the first case failure")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.attach_only and args.start_new:
        parser.error("Cannot combine --attach-only and --start-new")
    if args.map_only and args.skip_map:
        parser.error("Cannot combine --map-only and --skip-map")
    if not args.list_cases and not args.cases:
        parser.error("--cases is required unless --list-cases")

    try:
        return run_pipeline(args)
    except KeyboardInterrupt:
        _log("\nInterrupted.")
        return 130
    except Exception as exc:
        _log(f"Fatal: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
