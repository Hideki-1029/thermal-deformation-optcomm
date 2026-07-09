"""Export STT/LCT translation and rotation from Femap results to Excel/CSV.

The Excel layout matches the existing hand-exported files under
inputs/data_femap_deformation/:
  Set ID | Set Value | Set Title | Study ID | node vectors...
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


def load_stt_lct_nodes(config_path: Path | None = None) -> dict[str, int]:
    path = Path(config_path) if config_path else DEFAULT_NODE_CONFIG
    with path.open(encoding="utf-8") as f:
        config = json.load(f)
    points = config["points"]
    return {
        "LCT": int(points["LCT"]["node_id"]),
        "STT": int(points["STT"]["node_id"]),
    }


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
) -> Path:
    nodes = load_stt_lct_nodes(node_config_path)
    lct_id = nodes["LCT"]
    stt_id = nodes["STT"]

    set_ids = _output_set_ids(app)
    if not set_ids:
        raise FemapComError("No output sets available to export.")

    node_obj = app.feNode
    for label, nid in nodes.items():
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

        def vals(nid: int) -> dict[str, float]:
            return {
                "total_t": _get_scalar_at_node(results, set_id, VEC_TOTAL_T, nid),
                "t1": _get_scalar_at_node(results, set_id, VEC_T1, nid),
                "t2": _get_scalar_at_node(results, set_id, VEC_T2, nid),
                "t3": _get_scalar_at_node(results, set_id, VEC_T3, nid),
                "total_r": _get_scalar_at_node(results, set_id, VEC_TOTAL_R, nid),
                "r1": _get_scalar_at_node(results, set_id, VEC_R1, nid),
                "r2": _get_scalar_at_node(results, set_id, VEC_R2, nid),
                "r3": _get_scalar_at_node(results, set_id, VEC_R3, nid),
            }

        lct = vals(lct_id)
        stt = vals(stt_id)
        rows.append(
            {
                "セット ID": set_id,
                "セットの値": value,
                "セット　タイトル": title,
                "スタディID": study_id,
                f"ノード {lct_id}, 1..Total Translation": lct["total_t"],
                f"ノード {stt_id}, 1..Total Translation": stt["total_t"],
                f"ノード {lct_id}, 2..T1 Translation": lct["t1"],
                f"ノード {stt_id}, 2..T1 Translation": stt["t1"],
                f"ノード {lct_id}, 3..T2 Translation": lct["t2"],
                f"ノード {stt_id}, 3..T2 Translation": stt["t2"],
                f"ノード {lct_id}, 4..T3 Translation": lct["t3"],
                f"ノード {stt_id}, 4..T3 Translation": stt["t3"],
                f"ノード {lct_id}, 5..Total Rotation": lct["total_r"],
                f"ノード {stt_id}, 5..Total Rotation": stt["total_r"],
                f"ノード {lct_id}, 6..R1 Rotation": lct["r1"],
                f"ノード {stt_id}, 6..R1 Rotation": stt["r1"],
                f"ノード {lct_id}, 7..R2 Rotation": lct["r2"],
                f"ノード {stt_id}, 7..R2 Rotation": stt["r2"],
                f"ノード {lct_id}, 8..R3 Rotation": lct["r3"],
                f"ノード {stt_id}, 8..R3 Rotation": stt["r3"],
            }
        )

    df = pd.DataFrame(rows)
    excel_path = Path(excel_path)
    excel_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(excel_path, index=False, sheet_name="ノード")
    return excel_path
