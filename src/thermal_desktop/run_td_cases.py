"""Run TD Case Sets and export PostProcessing DataMapper files to Femap."""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from .case_selection import SelectedCase, parse_case_spec, select_cases
from .opentd_runtime import (
    DEFAULT_DWG,
    connect_thermal_desktop,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FEMAP_MODEL_ROOT = Path(r"C:\Users\Hide\Femap\research_model")
DEFAULT_NASTRAN_BDF = DEFAULT_FEMAP_MODEL_ROOT / "research_model.bdf"
MAPPER_SUBDIR = "mapper_from_TD"
OUTPUT_BASENAME = "output"
REQUIRED_MAPPER_FILES = ("output.dat",)


def _log(msg: str) -> None:
    print(msg, flush=True)


def dwg_directory(dwg_path: Path) -> Path:
    return dwg_path.resolve().parent


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


def mapper_dest_dir(femap_root: Path, case_id: str) -> Path:
    return femap_root / case_id / MAPPER_SUBDIR


def mapper_output_dat(femap_root: Path, case_id: str) -> Path:
    return mapper_dest_dir(femap_root, case_id) / f"{OUTPUT_BASENAME}.dat"


def get_data_mapper(td: Any, mapper_handle: str | None = None) -> Any:
    """Return the PostProcessing DataMapper (by handle, or the only/first one)."""
    mappers = list(td.GetPostProcessingDataMappers())
    if not mappers:
        raise RuntimeError(
            "No PostProcessing DataMapper found in the TD model. "
            "Create one in Model Browser (Mesh Displayers / PP Mappers) first."
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


def set_mapper_enabled(mapper: Any, enabled: bool) -> None:
    """
    Set DataMapper.Enabled via Update().

    Avoid calling this unless necessary — ``DataMapper.Update`` has crashed TD
    with ``eNotOpenForWrite`` on this model. Prefer leaving Enabled=0 and using
    explicit ``Map()``.
    """
    desired = 1 if enabled else 0
    try:
        current = int(mapper.Enabled)
    except Exception:
        current = -1
    if current == desired:
        return
    mapper.Enabled = desired
    mapper.Update()


def refresh_mapper(mapper: Any) -> None:
    """Pull latest DWG-side DataMapper state into the client object (read-only)."""
    if hasattr(mapper, "UpdateFromTD"):
        mapper.UpdateFromTD()


def reset_td_graphics(td: Any) -> None:
    """Hide contour plots / PP graphics that can lock DWG objects for write."""
    if hasattr(td, "ResetGraphics"):
        try:
            td.ResetGraphics()
            _log("  ResetGraphics()")
        except Exception as exc:
            _log(f"  warning: ResetGraphics failed: {exc}")


def wait_while_case_running(td: Any, *, timeout_s: float = 0.0, poll_s: float = 2.0) -> None:
    """Poll CaseSetManager.IsCaseRunning when available (Dynamic SINDA etc.)."""
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
    """Run by name/group to avoid stale CaseSet client objects from GetCaseSets()."""
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
    """
    Build the CurrentPPDataset string TD expects.

    Mapper logs show values like ``transient\\09_....sav`` (relative to DWG dir).
    """
    try:
        rel = sav_path.resolve().relative_to(dwg_dir.resolve())
        return str(rel)
    except ValueError:
        return str(sav_path.resolve())


def casefold_path_match(a: str, b: str) -> bool:
    na = a.replace("/", "\\").casefold()
    nb = b.replace("/", "\\").casefold()
    return na == nb or na.endswith(nb) or nb.endswith(na)


def activate_dataset(td: Any, OpenTD: Any, *, sav_path: Path, dwg_dir: Path) -> str:
    """
    Make ``sav_path`` the active post-processing dataset and verify it stuck.

    ``tdmapallmappers`` may still ignore this and use DataMapper.CurrentPPDataset
    baked into the DWG; ``mapnastran`` uses the current PP dataset.
    """
    sav_ref = dataset_ref_for_sav(dwg_dir, sav_path)
    sav_name = sav_path.name
    manager = td.DatasetManager
    candidates = [
        sav_ref,
        sav_ref.replace("\\", "/"),
        str(sav_path.resolve()),
        sav_name,
    ]

    # Exact GetDataset names first.
    for name in candidates:
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
        # Scan list for a matching sav.
        try:
            for ds in list(manager.GetDatasets()):
                ds_name = str(getattr(ds, "Name", "") or "")
                if sav_name.casefold() in ds_name.casefold() or casefold_path_match(ds_name, sav_ref):
                    _log(f"  activating dataset: {ds_name!r}")
                    try:
                        ds.SetCurrent()
                    except Exception as exc:
                        _log(f"  warning: SetCurrent failed: {exc}")
                    break
        except Exception as exc:
            _log(f"  warning: GetDatasets failed: {exc}")

    # Legacy load/refresh — relative path matches TD dataset naming.
    for ppsave in (sav_ref, str(sav_path.resolve())):
        try:
            legacy_com(td, f'ppsavefile "{ppsave}"')
        except Exception as exc:
            _log(f"  warning: ppsavefile {ppsave!r} failed: {exc}")

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
        # Last resort: create a fresh SF dataset for this sav.
        _log(f"  creating dataset for {sav_path.name}")
        Dataset = OpenTD.PostProcessing.Dataset
        dataset = manager.CreateDataset(
            sav_ref.replace("\\", "_"),
            str(sav_path.resolve()),
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
    """Fail fast if output.dat header still points at another case's .sav."""
    try:
        with output_dat.open("r", encoding="utf-8", errors="replace") as fh:
            header = "".join(fh.readline() for _ in range(5))
    except OSError as exc:
        raise RuntimeError(f"Could not read {output_dat}: {exc}") from exc

    needle = case.name.casefold()
    header_l = header.casefold()
    if needle in header_l:
        _log(f"  verified output.dat header mentions {case.name}")
        return

    # mapnastran may omit the dataset comment line; accept TEMP* cards if the
    # file is freshly written and does not name a *different* case.
    other = None
    for token in header.replace("/", "\\").split("'"):
        if "ltan" in token.casefold() and token.casefold().endswith(".sav"):
            other = token
            break
    if other and case.name.casefold() not in other.casefold():
        raise RuntimeError(
            f"{output_dat} still references another dataset ({other!r}), "
            f"not case {case.name}.\nHeader:\n{header.strip()}\n"
            "Close any editor that has output.dat open, delete the stale file, "
            "and retry. If this persists, mapnastran may be ignoring the current "
            "dataset — check TD's Postprocessing Datasets dialog."
        )

    if "temp*" in header_l or "temp " in header_l:
        _log(
            "  warning: output.dat has TEMP cards but no case-id comment; "
            "assuming mapnastran format is OK"
        )
        return

    raise RuntimeError(
        f"{output_dat} does not look like mapped temperature data for {case.name}.\n"
        f"Header:\n{header.strip()}"
    )


def resolve_mapper_output_path(mapper: Any, dwg_dir: Path) -> Path:
    """Resolve DataMapper.OutputFile to an absolute path (file or stem)."""
    raw = str(getattr(mapper, "OutputFile", "") or "").strip()
    if not raw:
        raise RuntimeError(
            "DataMapper.OutputFile is empty. In TD, set the mapper Output File "
            "once (e.g. to a staging folder) and save the DWG. This script no "
            "longer calls DataMapper.Update() because it crashes AutoCAD on this model."
        )
    path = Path(raw)
    if not path.is_absolute():
        path = (dwg_dir / path).resolve()
    else:
        path = path.resolve()
    return path


def mapper_output_dir(output_file: Path) -> Path:
    """Directory containing mapper outputs (parent of output.dat / output stem)."""
    if output_file.suffix:
        return output_file.parent
    return output_file.parent if output_file.name else output_file


def copy_mapper_outputs(src_dir: Path, dest_dir: Path) -> list[Path]:
    """Copy output* mapper artifacts from src_dir into dest_dir."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    patterns = ("output.dat", "output*.txt", "output*.dat")
    seen: set[str] = set()
    for pattern in patterns:
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


def legacy_com(td: Any, command: str, *, delay_ms: int = 0) -> str:
    """Run a TD legacy COM-style command (server-side; no DataMapper.Update)."""
    _log(f"  SendLegacyComCommand: {command}")
    try:
        if delay_ms:
            return str(td.SendLegacyComCommand(command, delay_ms) or "")
        return str(td.SendLegacyComCommand(command) or "")
    except TypeError:
        return str(td.SendLegacyComCommand(command) or "")


def run_existing_mappers_server_side(td: Any) -> None:
    """
    Execute mappers already defined in the DWG without round-tripping DataMapper.

    ``DataMapper.Map()`` internally calls ``Update()`` → ``SetPostProcessingDataMapper``,
    which crashes this model with ``eNotOpenForWrite``. ``tdmapallmappers`` runs
    the DWG-side mapper configuration in-place instead.

    Do **not** pass ``""`` as the append argument: TD inserts that literally and
    produces broken names like ``output""MapSummaryGridPoints.txt``.
    """
    legacy_com(td, "tdmapallmappers")


def clear_output_files(dest_dir: Path) -> None:
    """Delete previous mapper outputs so a failed map cannot leave stale case data."""
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
                f"Cannot delete {path} (is it open in Notepad/Excel?). "
                f"Close the file and retry. OS error: {exc}"
            ) from exc
    if removed:
        _log(f"  cleared {removed} previous output file(s) in {dest_dir}")


def run_mapnastran_legacy(
    td: Any,
    *,
    bdf_path: Path,
    output_dat: Path,
) -> None:
    """Map current PP dataset to Nastran TEMP cards at ``output_dat``."""
    output_dat.parent.mkdir(parents=True, exist_ok=True)
    clear_output_files(output_dat.parent)

    # Make sure TD UI/current-PP pointer matches DatasetManager.
    try:
        legacy_com(td, "displaycurrentdataset")
    except Exception as exc:
        _log(f"  warning: displaycurrentdataset failed: {exc}")

    legacy_com(td, "setmapcurrentorall ALL")
    # Write to a temp name first, then rename — proves mapnastran actually wrote.
    tmp_dat = output_dat.with_name(f"{output_dat.stem}.mapnastran_tmp{output_dat.suffix}")
    if tmp_dat.exists():
        try:
            tmp_dat.unlink()
        except OSError as exc:
            raise RuntimeError(f"Cannot delete temp file {tmp_dat}: {exc}") from exc

    cmd = f'mapnastran "{bdf_path}" "{tmp_dat}"'
    legacy_com(td, cmd)

    # Some TD builds may ignore the custom name and write output.dat in the same folder.
    produced: Path | None = None
    if tmp_dat.is_file() and tmp_dat.stat().st_size > 0:
        produced = tmp_dat
    elif output_dat.is_file() and output_dat.stat().st_size > 0:
        produced = output_dat
        _log(f"  mapnastran wrote {output_dat.name} directly")
    else:
        # Search for any new dat in the folder.
        dats = sorted(
            output_dat.parent.glob("*.dat"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if dats:
            produced = dats[0]
            _log(f"  mapnastran produced {produced.name} (unexpected name)")

    if produced is None:
        raise FileNotFoundError(
            f"mapnastran did not create an output file under {output_dat.parent}. "
            "Check the AutoCAD/TD command line for mapnastran errors."
        )

    if produced.resolve() != output_dat.resolve():
        if output_dat.exists():
            output_dat.unlink()
        produced.replace(output_dat)
        _log(f"  renamed {produced.name} → {output_dat.name}")


def map_case_to_femap(
    td: Any,
    OpenTD: Any,
    *,
    case: SelectedCase,
    dwg_dir: Path,
    femap_root: Path,
    mapper: Any | None,
    enable_mapper: bool = False,
    map_backend: str = "mapnastran",
    nastran_bdf: Path | None = None,
) -> Path:
    """
    Map temperatures for one case into Femap ``mapper_from_TD``.

    Default backend is ``mapnastran`` (maps the *current* PP dataset to
    ``output.dat``). ``tdmapallmappers`` uses the DataMapper's baked-in
    ``CurrentPPDataset`` (often stuck on a previous case) and is easy to misuse.
    Avoid ``DataMapper.Map()`` — it calls ``Update()`` and crashes this DWG.
    """
    sav_path = resolve_sav_path(dwg_dir, case)
    dest_dir = mapper_dest_dir(femap_root, case.name)
    dest_dat = mapper_output_dat(femap_root, case.name)
    # TD cannot create mapper_from_TD itself; same requirement as the manual GUI flow.
    dest_dir.mkdir(parents=True, exist_ok=True)

    _log(f"  sav: {sav_path}")
    _log(f"  femap dest: {dest_dat}")
    _log(f"  map backend: {map_backend}")

    reset_td_graphics(td)
    activate_dataset(td, OpenTD, sav_path=sav_path, dwg_dir=dwg_dir)

    if enable_mapper and mapper is not None:
        _log("  --enable-mapper: attempting Enabled=1 via Update (may crash TD)")
        set_mapper_enabled(mapper, True)

    if map_backend == "tdmapallmappers":
        if mapper is not None:
            refresh_mapper(mapper)
            baked = str(getattr(mapper, "CurrentPPDataset", "") or "")
            _log(f"  DataMapper.CurrentPPDataset (baked): {baked!r}")
            # Empty baked value usually means "use the current PP dataset" (GUI has
            # no separate dataset picker). Only warn when a *different* case is named.
            if baked and case.name.casefold() not in baked.casefold():
                _log(
                    f"  warning: baked CurrentPPDataset={baked!r} does not name "
                    f"{case.name}; Map may still use the active dataset. "
                    "Verify output.dat header after mapping."
                )
            td_output = resolve_mapper_output_path(mapper, dwg_dir)
            td_out_dir = mapper_output_dir(td_output)
            _log(f"  TD mapper OutputFile: {td_output}")
            # OutputFile may point at dest_dir or a staging path; both must exist.
            td_out_dir.mkdir(parents=True, exist_ok=True)
        else:
            td_out_dir = dest_dir
            _log("  warning: no mapper object; expecting outputs already under dest")

        run_existing_mappers_server_side(td)

        if not any(td_out_dir.glob("output*")):
            raise FileNotFoundError(
                f"tdmapallmappers finished but no output* under {td_out_dir}. "
                "Check DataMapper Output File in TD / MapperPP_*.log. "
                "If you see names like output\"\"MapSummary*.txt, an old script "
                "bug inserted quotes into the append string — pull the latest fix."
            )
        copy_mapper_outputs(td_out_dir, dest_dir)

    elif map_backend == "mapnastran":
        bdf = Path(nastran_bdf) if nastran_bdf else DEFAULT_NASTRAN_BDF
        if not bdf.is_file():
            raise FileNotFoundError(f"Nastran BDF not found: {bdf}")
        run_mapnastran_legacy(td, bdf_path=bdf, output_dat=dest_dat)

    elif map_backend == "opentd-map":
        if mapper is None:
            raise RuntimeError("opentd-map backend requires a DataMapper object")
        _log("  WARNING: DataMapper.Map() calls Update() and often crashes this DWG")
        clear_output_files(dest_dir)
        mapper.Map()
        refresh_mapper(mapper)
        td_out_dir = mapper_output_dir(resolve_mapper_output_path(mapper, dwg_dir))
        copy_mapper_outputs(td_out_dir, dest_dir)
    else:
        raise ValueError(f"Unknown map backend: {map_backend!r}")

    if enable_mapper and mapper is not None:
        try:
            set_mapper_enabled(mapper, False)
        except Exception as exc:
            _log(f"  warning: failed to disable mapper: {exc}")

    if not dest_dat.is_file():
        dats = sorted(dest_dir.glob("*.dat"))
        if dats and dats[0].name.casefold() != "output.dat":
            shutil.copy2(dats[0], dest_dat)
            _log(f"  normalized {dats[0].name} → output.dat")

    if not dest_dat.is_file():
        raise FileNotFoundError(f"Expected {dest_dat} after mapping, but it is missing.")

    assert_output_dat_matches_case(dest_dat, case)
    size_mb = dest_dat.stat().st_size / (1024 * 1024)
    _log(f"  wrote {dest_dat} ({size_mb:.1f} MB)")
    return dest_dat


def clear_mapper_dir(dest_dir: Path) -> None:
    if not dest_dir.is_dir():
        return
    removed = 0
    for path in dest_dir.iterdir():
        if path.is_file():
            path.unlink()
            removed += 1
    if removed:
        _log(f"  cleared {removed} previous file(s) in {dest_dir}")


def copy_mapper_sidecars_if_needed(
    *,
    dwg_dir: Path,
    dest_dir: Path,
) -> None:
    """
    If TD wrote mapper sidecars next to the DWG instead of dest_dir, copy them.

    Normally OutputFile already points at mapper_from_TD, so this is a no-op.
    """
    patterns = [
        f"{OUTPUT_BASENAME}.dat",
        f"{OUTPUT_BASENAME}Transient.txt",
        f"{OUTPUT_BASENAME}Map*.txt",
    ]
    for pattern in patterns:
        for src in dwg_dir.glob(pattern):
            target = dest_dir / src.name
            if target.resolve() == src.resolve():
                continue
            if not target.exists() or src.stat().st_mtime > target.stat().st_mtime:
                shutil.copy2(src, target)
                _log(f"  copied sidecar {src.name} → {dest_dir}")


def list_group_cases(td: Any, group: str) -> None:
    all_cases = list(td.GetCaseSets())
    group_key = group.strip().casefold()
    rows = []
    for case in all_cases:
        g = str(getattr(case, "GroupName", "") or "")
        if g.casefold() != group_key:
            continue
        name = str(getattr(case, "Name", "") or "")
        from .case_selection import case_number_from_name

        num = case_number_from_name(name)
        rows.append((num, name))
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
    all_cases = list(td.GetCaseSets())
    selected = select_cases(all_cases, group=args.group, numbers=numbers)
    _log(
        f"Selected {len(selected)} case(s) in group {args.group!r}: "
        + ", ".join(f"{c.number}:{c.name}" for c in selected)
    )

    if args.dry_run:
        for case in selected:
            dest = mapper_output_dat(femap_root, case.name)
            sav = None
            try:
                sav = resolve_sav_path(dwg_dir, case)
            except FileNotFoundError as exc:
                sav = f"(missing) {exc}"
            _log(f"  [{case.number}] {case.name}")
            _log(f"       sav → {sav}")
            _log(f"       map → {dest}")
        return 0

    mapper = None
    mapper_handle = args.mapper_handle
    if args.map_backend != "mapnastran" or args.enable_mapper:
        try:
            mapper = get_data_mapper(td, args.mapper_handle)
            mapper_handle = str(getattr(mapper, "Handle", "") or mapper_handle or "")
            _log(
                f"  using DataMapper handle={mapper_handle or '?'} "
                f"Enabled={getattr(mapper, 'Enabled', '?')}"
            )
        except Exception as exc:
            if args.map_backend == "mapnastran":
                _log(f"  warning: could not load DataMapper ({exc}); continuing with mapnastran")
            else:
                raise

    failures: list[str] = []
    for case in selected:
        _log(f"\n=== case {case.number}: {case.name} ===")
        try:
            if not args.map_only:
                run_case(td, case)

            if not args.skip_map:
                if args.clear_mapper_dir:
                    clear_mapper_dir(mapper_dest_dir(femap_root, case.name))
                if args.map_backend != "mapnastran":
                    try:
                        mapper = get_data_mapper(td, args.mapper_handle or mapper_handle or None)
                    except Exception as exc:
                        _log(f"  warning: re-fetch DataMapper failed: {exc}")
                map_case_to_femap(
                    td,
                    OpenTD,
                    case=case,
                    dwg_dir=dwg_dir,
                    femap_root=femap_root,
                    mapper=mapper,
                    enable_mapper=args.enable_mapper,
                    map_backend=args.map_backend,
                    nastran_bdf=args.nastran_bdf,
                )
                copy_mapper_sidecars_if_needed(
                    dwg_dir=dwg_dir,
                    dest_dir=mapper_dest_dir(femap_root, case.name),
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
            "Run Thermal Desktop Case Sets in a group and export DataMapper "
            "output into each Femap case's mapper_from_TD folder."
        )
    )
    p.add_argument(
        "--group",
        default="transient",
        help="Case Set Manager group name (default: transient)",
    )
    p.add_argument(
        "--cases",
        help="Case numbers to run, e.g. 7,8,9 or 10-15 or 7,10-12,15",
    )
    p.add_argument(
        "--dwg",
        type=Path,
        default=DEFAULT_DWG,
        help=f"Path to research_thermal_model.dwg (default: {DEFAULT_DWG})",
    )
    p.add_argument(
        "--femap-root",
        type=Path,
        default=DEFAULT_FEMAP_MODEL_ROOT,
        help=f"Femap research_model root (default: {DEFAULT_FEMAP_MODEL_ROOT})",
    )
    p.add_argument(
        "--mapper-handle",
        default=None,
        help="DataMapper handle/name/label if multiple exist (e.g. 7C8A)",
    )
    p.add_argument(
        "--opentd-dll",
        default=None,
        help="Optional full path to OpenTD.dll (else OPENTD_DLL / auto-detect)",
    )
    p.add_argument(
        "--attach-only",
        action="store_true",
        help="Attach to an already-open TD instance (recommended; default when acad.exe is running)",
    )
    p.add_argument(
        "--start-new",
        action="store_true",
        help="Force starting a new TD instance (avoid if the DWG is already open)",
    )
    p.add_argument(
        "--map-only",
        action="store_true",
        help="Skip Case Set run; only map existing .sav results",
    )
    p.add_argument(
        "--map-backend",
        choices=("mapnastran", "tdmapallmappers", "opentd-map"),
        default="mapnastran",
        help=(
            "How to run mapping. Default mapnastran maps the *current* PP dataset "
            "to each case's mapper_from_TD/output.dat. tdmapallmappers uses the "
            "DataMapper's baked CurrentPPDataset (often stuck on a previous case). "
            "opentd-map calls DataMapper.Map()/Update and often crashes."
        ),
    )
    p.add_argument(
        "--nastran-bdf",
        type=Path,
        default=DEFAULT_NASTRAN_BDF,
        help=f"BDF for --map-backend mapnastran (default: {DEFAULT_NASTRAN_BDF})",
    )
    p.add_argument(
        "--enable-mapper",
        action="store_true",
        help=(
            "Temporarily set DataMapper.Enabled=1 via Update(). "
            "Usually unnecessary and may crash TD on this model."
        ),
    )
    p.add_argument(
        "--skip-map",
        action="store_true",
        help="Run Case Sets only; do not enable/run the DataMapper",
    )
    p.add_argument(
        "--clear-mapper-dir",
        action="store_true",
        help="Delete previous files in mapper_from_TD before mapping",
    )
    p.add_argument(
        "--list-cases",
        action="store_true",
        help="List Case Sets in --group and exit",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Connect to TD, resolve cases/paths, print the plan, do not run/map",
    )
    p.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on the first case failure",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.list_cases and not args.cases:
        parser.error("--cases is required unless --list-cases is set")
    if args.map_only and args.skip_map:
        parser.error("Cannot combine --map-only and --skip-map")
    if args.attach_only and args.start_new:
        parser.error("Cannot combine --attach-only and --start-new")
    try:
        return run_pipeline(args)
    except KeyboardInterrupt:
        _log("Interrupted.")
        return 130
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else (1 if code else 0)
    except Exception as exc:
        _log(f"Fatal: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
