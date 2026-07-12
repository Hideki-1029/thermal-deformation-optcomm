"""Thin COM helpers for talking to a running Simcenter Femap session."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FE_OK = -1
FT_NODE = 7
FT_LOAD_DIR = 12
FT_OUT_CASE = 28
FT_AMGR_DIR = 60
FT_AMGR_CASE = 61
FAP_NX_NASTRAN = 36
FAT_STATIC = 1
FSF_CSV = 1

# Output vector IDs used by Femap for nodal translation / rotation.
VEC_TOTAL_T = 1
VEC_T1 = 2
VEC_T2 = 3
VEC_T3 = 4
VEC_TOTAL_R = 5
VEC_R1 = 6
VEC_R2 = 7
VEC_R3 = 8


class FemapComError(RuntimeError):
    pass


@dataclass(frozen=True)
class FemapConstants:
    fe_ok: int = FE_OK
    ft_node: int = FT_NODE
    ft_load_dir: int = FT_LOAD_DIR
    ft_out_case: int = FT_OUT_CASE
    ft_amgr_dir: int = FT_AMGR_DIR
    ft_amgr_case: int = FT_AMGR_CASE
    fap_nx_nastran: int = FAP_NX_NASTRAN
    fat_static: int = FAT_STATIC


def connect_femap(*, start_if_needed: bool = False):
    """Connect to an already-running Femap, optionally Dispatch a new one."""
    try:
        from win32com.client import Dispatch, GetActiveObject
    except ImportError as exc:
        raise FemapComError(
            "pywin32 is required for Femap automation. Install with: pip install pywin32"
        ) from exc

    try:
        app = GetActiveObject("femap.model")
    except Exception:
        if not start_if_needed:
            raise FemapComError(
                "No running Femap session found. Open research_model.modfem in Femap first."
            )
        app = Dispatch("femap.model")

    version = getattr(app, "Info_Version", None)
    model_name = getattr(app, "ModelName", "")
    app.feAppMessage(0, f"[thermal-deformation-optcomm] connected (v={version})")
    return app, str(model_name)


def require_ok(rc, action: str) -> None:
    if rc != FE_OK:
        raise FemapComError(f"{action} failed with Femap return code {rc}")


def entity_count(app, entity_type: int) -> int:
    entity_set = app.feSet
    require_ok(entity_set.AddAll(entity_type), f"AddAll({entity_type})")
    return int(entity_set.Count())


def _collect_ids(app, entity_type: int) -> list[int]:
    entity_set = app.feSet
    require_ok(entity_set.AddAll(entity_type), f"AddAll({entity_type})")
    ids: list[int] = []
    entity_set.Reset()
    while entity_set.Next():
        ids.append(int(entity_set.CurrentID))
    return ids


def delete_all_of_type(app, entity_type: int) -> int:
    """Delete every entity of the given type. Returns how many were deleted."""
    ids = _collect_ids(app, entity_type)
    if not ids:
        return 0

    # Avoid modal "are you sure?" dialogs during batch cleanup.
    prev_skip = getattr(app, "DialogAutoSkip", 0)
    prev_msg = getattr(app, "DialogAutoSkipMsg", 0)
    app.DialogAutoSkip = 1
    app.DialogAutoSkipMsg = 1
    try:
        if entity_type == FT_OUT_CASE:
            # Faster path for results: delete all output without confirmation.
            require_ok(app.feDeleteAll(False, False, True, False), "feDeleteAll(output)")
            return len(ids)

        if entity_type == FT_LOAD_DIR:
            load_set = app.feLoadSet
            for load_id in ids:
                rc = load_set.Delete(load_id)
                if rc != FE_OK:
                    # Fall back to set-based delete for this ID.
                    one = app.feSet
                    one.Add(load_id)
                    require_ok(app.feDelete(entity_type, one.ID), f"feDelete load {load_id}")
            return len(ids)

        entity_set = app.feSet
        require_ok(entity_set.AddAll(entity_type), f"AddAll({entity_type})")
        require_ok(app.feDelete(entity_type, entity_set.ID), f"feDelete({entity_type})")
        return len(ids)
    finally:
        app.DialogAutoSkip = prev_skip
        app.DialogAutoSkipMsg = prev_msg


# File type for feFileReadNastranResults when importing *.op2 / Nastran results.
# Matches Siemens community examples for File > Import > Analysis Results.
FNR_NASTRAN_RESULTS = 8


def delete_all_output_sets(app) -> int:
    """Delete every Femap output set (analysis results). Returns count deleted."""
    return delete_all_of_type(app, FT_OUT_CASE)


def import_nastran_results_op2(app, op2_path: Path) -> int:
    """
    Import a Nastran ``.op2`` via ``feFileReadNastranResults``.

    This mirrors the GUI path File > Import > Analysis Results.
    Returns the number of output sets present after import.
    """
    op2_path = Path(op2_path)
    if not op2_path.is_file():
        raise FemapComError(f"OP2 file not found: {op2_path}")

    before = entity_count(app, FT_OUT_CASE)
    prev_skip = getattr(app, "DialogAutoSkip", 0)
    prev_msg = getattr(app, "DialogAutoSkipMsg", 0)
    app.DialogAutoSkip = 1
    app.DialogAutoSkipMsg = 1
    try:
        rc = app.feFileReadNastranResults(FNR_NASTRAN_RESULTS, str(op2_path))
        require_ok(rc, f"feFileReadNastranResults({op2_path})")
    finally:
        app.DialogAutoSkip = prev_skip
        app.DialogAutoSkipMsg = prev_msg

    try:
        app.feAppUpdatePanes(True)
    except Exception:
        pass

    after = entity_count(app, FT_OUT_CASE)
    if after <= before:
        raise FemapComError(
            f"OP2 import did not create output sets: {op2_path} "
            f"(sets before={before}, after={after})"
        )
    return after


def set_nastran_output_dir(app, output_dir: Path, *, analysis_id: int = 1) -> None:
    """Point Nastran scratch/output files at the per-case folder.

    Manual Femap workflow sets Analysis Set -> Output Directory to
    ``research_model/{case_id}``. That maps to ``AnalysisMgr.NasExecOutDir``.
    Pref_NastranOutputPath alone is not enough on this Femap build.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out = str(output_dir)

    app.Pref_NastranOutputPath = out
    # Prefer "Other / specified path" over model directory when available.
    # Empirically Pref_NastranOutputTo=1 still wrote to the model folder when
    # NasExecOutDir was empty, so AnalysisMgr.NasExecOutDir is the real lever.
    try:
        app.Pref_NastranOutputTo = 1
    except Exception:
        pass
    app.Pref_API_HonorWorkingDirectory = True
    app.feFileCurrentDirectory(out)

    am = ensure_analysis_mgr(app, analysis_id=analysis_id)
    am.NasExecOutDir = out
    am.NasExecAnalyzeFilename = ""
    require_ok(am.Put(analysis_id), f"AnalysisMgr.Put({analysis_id}) after output dir")


def ensure_analysis_mgr(app, analysis_id: int = 1):
    am = app.feAnalysisMgr
    if am.Exist(analysis_id) != FE_OK:
        am.InitAnalysisMgr(FAP_NX_NASTRAN, FAT_STATIC, True)
        am.title = "thermal_def"
        am.SetBCSet(0, 1)
        am.SetBCSet(2, 0)
        require_ok(am.Put(analysis_id), f"AnalysisMgr.Put({analysis_id})")
    else:
        require_ok(am.Get(analysis_id), f"AnalysisMgr.Get({analysis_id})")
    return am


def rebuild_analysis_cases_from_loads(
    app,
    analysis_id: int = 1,
    *,
    max_loads: int | None = None,
) -> int:
    """
    Mirror the stock Femap example Create_Multiple_Analysis_Subcase.BAS:
    one analysis case per load set, sharing the existing constraint set.

    If ``max_loads`` is set, only the first N load sets are turned into
    analysis cases (useful for smoke-testing before a full 300-case run).
    """
    am = ensure_analysis_mgr(app, analysis_id=analysis_id)
    am.SetBCSet(0, 1)
    am.SetBCSet(2, 0)

    # Drop previous analysis cases via the dedicated API (feDelete(FT_AMGR_CASE)
    # returns FE_INVALID=3 on this Femap build).
    ac = app.feAnalysisCase
    old_cases = app.feSet
    require_ok(old_cases.AddAll(FT_AMGR_CASE), "AddAll(FT_AMGR_CASE)")
    if int(old_cases.Count()) > 0:
        case_ids = []
        old_cases.Reset()
        while old_cases.Next():
            case_ids.append(int(old_cases.CurrentID))
        for old_id in case_ids:
            rc = ac.DeleteAnalysisCase(analysis_id, old_id)
            # FE_OK / FE_NOT_EXIST are both acceptable when clearing leftovers.
            if rc not in (FE_OK, 4):
                # Fallback: AnalysisCase.Delete(caseID)
                rc2 = ac.Delete(old_id)
                if rc2 not in (FE_OK, 4):
                    raise FemapComError(
                        f"DeleteAnalysisCase({analysis_id}, {old_id}) failed "
                        f"with codes {rc}/{rc2}"
                    )

    load_set_ids = app.feSet
    require_ok(load_set_ids.AddAll(FT_LOAD_DIR), "AddAll(FT_LOAD_DIR)")
    n_loads = int(load_set_ids.Count())
    if n_loads == 0:
        raise FemapComError("No load sets found after mapper import.")

    load_obj = app.feLoadSet
    case_id = 1
    load_set_ids.Reset()
    while load_set_ids.Next():
        if max_loads is not None and case_id > max_loads:
            break
        load_id = int(load_set_ids.CurrentID)
        require_ok(load_obj.Get(load_id), f"LoadSet.Get({load_id})")
        ac.SetID = analysis_id
        ac.caseID = case_id
        title = getattr(load_obj, "title", "") or f"Load {load_id}"
        ac.CaseTitle = str(title)
        require_ok(ac.InitAnalysisCase(analysis_id, case_id), f"InitAnalysisCase({case_id})")
        ac.SetBCSet(2, load_id)
        require_ok(ac.Put(case_id), f"AnalysisCase.Put({case_id})")
        case_id += 1

    require_ok(am.Put(analysis_id), f"AnalysisMgr.Put({analysis_id})")
    return case_id - 1
