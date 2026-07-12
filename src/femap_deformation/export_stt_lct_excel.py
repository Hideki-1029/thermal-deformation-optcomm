"""Export nodal translation and rotation from Femap results to Excel/CSV.

The Excel layout matches the existing hand-exported files under
inputs/data_femap_deformation/:
  Set ID | Set Value | Set Title | Study ID | node vectors...

By default this exports STT/LCT plus the six panel-center nodes defined in
``stt_lct_node_config.json`` (``points`` + ``panel_center_points``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .femap_com import (
    FE_OK,
    FT_OUT_CASE,
    VEC_R1,
    VEC_R2,
    VEC_R3,
    VEC_T1,
    VEC_T2,
    VEC_T3,
    VEC_TOTAL_R,
    VEC_TOTAL_T,
    FemapComError,
    require_ok,
)


DEFAULT_NODE_CONFIG = (
    Path(__file__).resolve().parents[2]
    / "inputs"
    / "data_femap_deformation"
    / "stt_lct_node_config.json"
)

# Keep LCT/STT first for backward-compatible column layout, then panels.
_PANEL_CENTER_ORDER = (
    "PANEL_MX",
    "PANEL_PX",
    "PANEL_MY",
    "PANEL_PY",
    "PANEL_MZ",
    "PANEL_PZ",
)

_VECTOR_SPECS = (
    (VEC_TOTAL_T, "1..Total Translation"),
    (VEC_T1, "2..T1 Translation"),
    (VEC_T2, "3..T2 Translation"),
    (VEC_T3, "4..T3 Translation"),
    (VEC_TOTAL_R, "5..Total Rotation"),
    (VEC_R1, "6..R1 Rotation"),
    (VEC_R2, "7..R2 Rotation"),
    (VEC_R3, "8..R3 Rotation"),
)


def load_node_config(config_path: Path | None = None) -> dict:
    path = Path(config_path) if config_path else DEFAULT_NODE_CONFIG
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_stt_lct_nodes(config_path: Path | None = None) -> dict[str, int]:
    """Return ``{"LCT": id, "STT": id}`` (legacy helper)."""
    points = load_node_config(config_path)["points"]
    return {
        "LCT": int(points["LCT"]["node_id"]),
        "STT": int(points["STT"]["node_id"]),
    }


def load_export_nodes(
    config_path: Path | None = None,
    *,
    include_panel_centers: bool = True,
) -> list[tuple[str, int]]:
    """
    Ordered ``(label, node_id)`` list for Excel export.

    Order: LCT, STT, then PANEL_MX..PANEL_PZ when present in the config.
    """
    config = load_node_config(config_path)
    points = config["points"]
    nodes: list[tuple[str, int]] = [
        ("LCT", int(points["LCT"]["node_id"])),
        ("STT", int(points["STT"]["node_id"])),
    ]
    if not include_panel_centers:
        return nodes

    panel_points = config.get("panel_center_points") or {}
    for label in _PANEL_CENTER_ORDER:
        entry = panel_points.get(label)
        if not isinstance(entry, dict) or "node_id" not in entry:
            continue
        nodes.append((label, int(entry["node_id"])))
    return nodes


def _output_set_ids(app) -> list[int]:
    out_set = app.feSet
    require_ok(out_set.AddAll(FT_OUT_CASE), "AddAll(FT_OUT_CASE)")
    ids: list[int] = []
    out_set.Reset()
    while out_set.Next():
        ids.append(int(out_set.CurrentID))
    return ids


def _get_scalar_at_node(results, output_set_id: int, vector_id: int, node_id: int) -> float:
    # Results.EntityValueV2(setID, vectorID, entityID) -> (rc, value)
    rc, value = results.EntityValueV2(output_set_id, vector_id, node_id)
    if rc != FE_OK:
        raise FemapComError(
            f"EntityValueV2(set={output_set_id}, vec={vector_id}, node={node_id}) "
            f"failed with code {rc}"
        )
    return float(value)


def export_stt_lct_results(
    app,
    excel_path: Path,
    *,
    node_config_path: Path | None = None,
    include_panel_centers: bool = True,
) -> Path:
    nodes = load_export_nodes(
        node_config_path,
        include_panel_centers=include_panel_centers,
    )
    if not nodes:
        raise FemapComError("No export nodes found in node config.")

    set_ids = _output_set_ids(app)
    if not set_ids:
        raise FemapComError("No output sets available to export.")

    node_obj = app.feNode
    for label, nid in nodes:
        if node_obj.Exist(nid) != FE_OK:
            raise FemapComError(f"{label} node {nid} does not exist in the model.")

    results = app.feResults
    out_meta = app.feOutputSet
    rows = []
    for set_id in set_ids:
        require_ok(out_meta.Get(set_id), f"OutputSet.Get({set_id})")
        title = str(getattr(out_meta, "title", "") or f"Case {set_id}")
        value = float(getattr(out_meta, "value", 0.0) or 0.0)
        study_id = int(getattr(out_meta, "studyID", 1) or 1)

        row: dict[str, object] = {
            "セット ID": set_id,
            "セットの値": value,
            "セット　タイトル": title,
            "スタディID": study_id,
        }
        for vec_id, suffix in _VECTOR_SPECS:
            for _label, nid in nodes:
                row[f"ノード {nid}, {suffix}"] = _get_scalar_at_node(
                    results, set_id, vec_id, nid
                )
        rows.append(row)

    df = pd.DataFrame(rows)
    excel_path = Path(excel_path)
    excel_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(excel_path, index=False, sheet_name="ノード")
    return excel_path
