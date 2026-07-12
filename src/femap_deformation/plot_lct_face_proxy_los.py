"""Far-field LOS proxy with LCT placed on a panel-center node (metric B).

STT attitude node is fixed. Each requested LCT face uses that face's outward
normal as the nominal optical axis, then:

    far_field ≈ rotate(u0, R_proxy - R_STT) - u0

Outputs go under ``results/femap_deformation/lct_face_proxy/{case_id}/``.
A merged ``summary.csv`` is kept at the ``lct_face_proxy/`` root.
Timeseries / plots are opt-in.

Examples
--------
python -m src.femap_deformation.plot_lct_face_proxy_los --cases 4,5 --lct-faces MX,MY
python -m src.femap_deformation.plot_lct_face_proxy_los --cases 4 --lct-faces MX --write-timeseries --plot
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.thermal_desktop.case_selection import parse_case_spec

from .plot_stt_lct_relative_deformation import (
    DEFAULT_CASE_MATRIX,
    DEFAULT_CONFIG,
    DEFAULT_INPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    ROTATION_COMPONENTS,
    apply_case_matrix_time_axis,
    extract_case_index,
    extract_vector,
    get_plot_x,
    list_numbered_excel_cases,
    load_config,
    resolve_case_ids_from_numbers,
    rotate_direction,
    unit_vector,
)


PROXY_ROOT_NAME = "lct_face_proxy"

# Outward panel normals in the CAD/Femap global frame.
FACE_OUTWARD_NORMALS: dict[str, np.ndarray] = {
    "LCT": np.array([0.0, 0.0, -1.0]),  # historical LCT on MZ side
    "MX": np.array([-1.0, 0.0, 0.0]),
    "PX": np.array([1.0, 0.0, 0.0]),
    "MY": np.array([0.0, -1.0, 0.0]),
    "PY": np.array([0.0, 1.0, 0.0]),
    "MZ": np.array([0.0, 0.0, -1.0]),
    "PZ": np.array([0.0, 0.0, 1.0]),
}

FACE_ALIASES = {
    "LCT": "LCT",
    "MX": "MX",
    "PX": "PX",
    "MY": "MY",
    "PY": "PY",
    "MZ": "MZ",
    "PZ": "PZ",
    "PANEL_MX": "MX",
    "PANEL_PX": "PX",
    "PANEL_MY": "MY",
    "PANEL_PY": "PY",
    "PANEL_MZ": "MZ",
    "PANEL_PZ": "PZ",
}


def _log(msg: str) -> None:
    print(msg, flush=True)


def normalize_face_label(raw: str) -> str:
    key = raw.strip().upper().replace("-", "_")
    if key.startswith("PANEL_"):
        pass
    if key not in FACE_ALIASES:
        raise ValueError(
            f"Unknown LCT face {raw!r}. Choose from: {', '.join(sorted(FACE_OUTWARD_NORMALS))}"
        )
    return FACE_ALIASES[key]


def parse_face_list(spec: str) -> list[str]:
    faces: list[str] = []
    seen: set[str] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        face = normalize_face_label(part)
        if face not in seen:
            seen.add(face)
            faces.append(face)
    if not faces:
        raise ValueError("--lct-faces must list at least one face")
    return faces


def resolve_proxy_node(config: dict, face: str) -> tuple[str, int]:
    """Return ``(label_for_logs, node_id)`` for the LCT proxy face."""
    if face == "LCT":
        node_id = int(config["points"]["LCT"]["node_id"])
        return "LCT", node_id

    panel_key = f"PANEL_{face}"
    panel_points = config.get("panel_center_points") or {}
    entry = panel_points.get(panel_key)
    if not isinstance(entry, dict) or "node_id" not in entry:
        raise KeyError(
            f"{panel_key} is missing from config panel_center_points "
            f"(needed for --lct-faces {face})"
        )
    return panel_key, int(entry["node_id"])


def resolve_stt_node(config: dict) -> tuple[str, int]:
    return "STT", int(config["points"]["STT"]["node_id"])


def far_field_from_relative_rotation(
    nominal_axis: np.ndarray,
    stt_rot_rad: np.ndarray,
    proxy_rot_rad: np.ndarray,
) -> pd.DataFrame:
    """Metric B: rotate face outward normal by (R_proxy - R_STT)."""
    u0 = unit_vector(np.asarray(nominal_axis, dtype=float))
    relative_rot = proxy_rot_rad - stt_rot_rad
    rotated = rotate_direction(u0, relative_rot)
    change = rotated - u0[None, :]

    # Transverse component ≈ sin(theta) ≈ theta [rad] for small angles.
    axial = change @ u0
    transverse = change - axial[:, None] * u0[None, :]
    mag_urad = np.linalg.norm(transverse, axis=1) * 1e6

    return pd.DataFrame(
        {
            "far_field_los_angle_x_urad": change[:, 0] * 1e6,
            "far_field_los_angle_y_urad": change[:, 1] * 1e6,
            "far_field_los_angle_z_urad": change[:, 2] * 1e6,
            "far_field_los_angle_magnitude_urad": mag_urad,
            "stt_rx_urad": stt_rot_rad[:, 0] * 1e6,
            "stt_ry_urad": stt_rot_rad[:, 1] * 1e6,
            "stt_rz_urad": stt_rot_rad[:, 2] * 1e6,
            "proxy_rx_urad": proxy_rot_rad[:, 0] * 1e6,
            "proxy_ry_urad": proxy_rot_rad[:, 1] * 1e6,
            "proxy_rz_urad": proxy_rot_rad[:, 2] * 1e6,
            "rel_rx_urad": relative_rot[:, 0] * 1e6,
            "rel_ry_urad": relative_rot[:, 1] * 1e6,
            "rel_rz_urad": relative_rot[:, 2] * 1e6,
        }
    )


def summarize_timeseries(ts: pd.DataFrame) -> dict[str, float]:
    mag = ts["far_field_los_angle_magnitude_urad"].to_numpy(dtype=float)
    x = ts["far_field_los_angle_x_urad"].to_numpy(dtype=float)
    y = ts["far_field_los_angle_y_urad"].to_numpy(dtype=float)
    z = ts["far_field_los_angle_z_urad"].to_numpy(dtype=float)
    return {
        "n_samples": float(len(ts)),
        "rms_mag_urad": float(np.sqrt(np.mean(mag**2))),
        "peak_mag_urad": float(np.max(np.abs(mag))),
        "mean_mag_urad": float(np.mean(mag)),
        "rms_x_urad": float(np.sqrt(np.mean(x**2))),
        "rms_y_urad": float(np.sqrt(np.mean(y**2))),
        "rms_z_urad": float(np.sqrt(np.mean(z**2))),
        "peak_x_urad": float(np.max(np.abs(x))),
        "peak_y_urad": float(np.max(np.abs(y))),
        "peak_z_urad": float(np.max(np.abs(z))),
    }


def compute_case_face_timeseries(
    df: pd.DataFrame,
    config: dict,
    face: str,
    *,
    excel_path: Path,
    case_matrix_path: Path,
    sheet_name,
) -> tuple[pd.DataFrame, dict]:
    stt_label, stt_node = resolve_stt_node(config)
    proxy_label, proxy_node = resolve_proxy_node(config, face)
    u0 = FACE_OUTWARD_NORMALS[face]

    stt_rot, ok_stt = extract_vector(
        df, stt_node, ROTATION_COMPONENTS, "Rotation", required=True
    )
    proxy_rot, ok_proxy = extract_vector(
        df, proxy_node, ROTATION_COMPONENTS, "Rotation", required=True
    )
    if not (ok_stt and ok_proxy):
        raise ValueError(f"Missing rotation columns for STT={stt_node} or {proxy_label}={proxy_node}")

    ts = far_field_from_relative_rotation(u0, stt_rot, proxy_rot)
    case_index, case_label = extract_case_index(df)
    ts.insert(0, "case_index", case_index)

    metadata = {
        "stt_label": stt_label,
        "stt_node": stt_node,
        "proxy_label": proxy_label,
        "proxy_node": proxy_node,
        "lct_face": face,
        "nominal_axis": u0,
        "case_label": case_label,
        "x_axis_column": "case_index",
    }
    apply_case_matrix_time_axis(ts, metadata, excel_path, case_matrix_path, sheet_name)
    return ts, metadata


def _dominant_los_axis(ts: pd.DataFrame) -> str:
    """Return 'x'/'y'/'z' with the largest RMS far-field component."""
    scores = {
        axis: float(np.sqrt(np.mean(ts[f"far_field_los_angle_{axis}_urad"].to_numpy(dtype=float) ** 2)))
        for axis in ("x", "y", "z")
    }
    return max(scores, key=scores.get)


def plot_proxy_los(ts: pd.DataFrame, metadata: dict, output_png: Path, show: bool = False) -> None:
    x = get_plot_x(ts, metadata)
    dominant = _dominant_los_axis(ts)
    others = [axis for axis in ("x", "y", "z") if axis != dominant]
    colors = {"x": "tab:blue", "y": "tab:orange", "z": "tab:green"}

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    title = (
        f"STT {metadata['stt_node']} -> {metadata['lct_face']} "
        f"({metadata['proxy_label']} {metadata['proxy_node']})"
    )

    dom_col = f"far_field_los_angle_{dominant}_urad"
    axes[0].plot(x, ts[dom_col], color=colors[dominant], label=dominant)
    axes[0].set_ylabel("far-field LOS [urad]")
    axes[0].set_title(f"{title}: dominant axis ({dominant})")
    axes[0].grid(True)
    axes[0].legend()

    for axis in others:
        axes[1].plot(
            x,
            ts[f"far_field_los_angle_{axis}_urad"],
            color=colors[axis],
            label=axis,
        )
    axes[1].set_ylabel("far-field LOS [urad]")
    axes[1].set_xlabel(metadata.get("case_label", "case index"))
    axes[1].set_title(f"Non-dominant axes ({', '.join(others)})")
    axes[1].grid(True)
    axes[1].legend()

    fig.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=150)
    if show:
        plt.show()
    plt.close(fig)


def plot_summary_heatmap(summary: pd.DataFrame, output_png: Path, value_col: str = "rms_mag_urad") -> None:
    pivot = summary.pivot(index="case_id", columns="lct_face", values=value_col)
    # Stable face order when present.
    face_order = [f for f in FACE_OUTWARD_NORMALS if f in pivot.columns]
    pivot = pivot.reindex(columns=face_order)

    fig, ax = plt.subplots(figsize=(1.2 * max(len(pivot.columns), 1) + 4, 0.35 * max(len(pivot), 1) + 3))
    im = ax.imshow(pivot.to_numpy(dtype=float), aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(list(pivot.columns))
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([str(i) for i in pivot.index], fontsize=8)
    ax.set_xlabel("LCT proxy face")
    ax.set_ylabel("case_id")
    ax.set_title(f"LCT-face proxy far-field LOS ({value_col})")
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02, label="urad")
    fig.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=150)
    plt.close(fig)


def merge_summary_csv(path: Path, new_rows: pd.DataFrame) -> pd.DataFrame:
    """Replace rows for case_ids present in ``new_rows``, keep other cases."""
    case_ids = set(new_rows["case_id"].astype(str))
    if path.is_file():
        old = pd.read_csv(path)
        keep = old[~old["case_id"].astype(str).isin(case_ids)]
        merged = pd.concat([keep, new_rows], ignore_index=True)
    else:
        merged = new_rows.copy()
    # Stable-ish order: by case_id then face order.
    face_order = {face: i for i, face in enumerate(FACE_OUTWARD_NORMALS)}
    merged = merged.copy()
    merged["_face_order"] = merged["lct_face"].map(lambda f: face_order.get(f, 999))
    merged = merged.sort_values(["case_id", "_face_order"]).drop(columns=["_face_order"])
    path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(path, index=False)
    return merged


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--cases", help="Case numbers: 4,5,8 or 4-15 (Excel stems under --excel-dir).")
    p.add_argument(
        "--case-id",
        action="append",
        dest="case_ids",
        help="Full case id / Excel stem. Repeatable.",
    )
    p.add_argument(
        "--list-cases",
        action="store_true",
        help="List numbered Excel cases and exit.",
    )
    p.add_argument(
        "--lct-faces",
        default="LCT,MX,PX,MY,PY,MZ,PZ",
        help="Comma-separated LCT proxy faces (default: LCT,MX,PX,MY,PY,MZ,PZ).",
    )
    p.add_argument("--excel-dir", type=Path, default=DEFAULT_INPUT_DIR)
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--case-matrix", type=Path, default=DEFAULT_CASE_MATRIX)
    p.add_argument("--sheet-name", default=0)
    p.add_argument(
        "--write-timeseries",
        action="store_true",
        help="Write per case/face CSV under {case_id}/timeseries/.",
    )
    p.add_argument(
        "--plot",
        action="store_true",
        help="Write per case/face PNG under {case_id}/plots/.",
    )
    p.add_argument(
        "--heatmap",
        action="store_true",
        help="Write summary heatmap PNG at lct_face_proxy/ root.",
    )
    p.add_argument("--show", action="store_true", help="Show plot windows (implies --plot).")
    return p.parse_args(argv)


def resolve_excel_paths(args: argparse.Namespace) -> list[Path]:
    excel_dir = Path(args.excel_dir)
    case_ids: list[str] = list(args.case_ids or [])
    if args.cases:
        case_ids.extend(resolve_case_ids_from_numbers(excel_dir, parse_case_spec(args.cases)))
    if not case_ids:
        raise SystemExit("Specify --cases and/or --case-id (or --list-cases).")

    seen: set[str] = set()
    ordered: list[str] = []
    for case_id in case_ids:
        if case_id not in seen:
            seen.add(case_id)
            ordered.append(case_id)

    paths = []
    missing = []
    for case_id in ordered:
        path = excel_dir / f"{case_id}.xlsx"
        if path.is_file():
            paths.append(path)
        else:
            missing.append(case_id)
    if missing:
        raise FileNotFoundError(f"Missing Excel for cases: {missing}")
    return paths


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    excel_dir = Path(args.excel_dir)

    if args.list_cases:
        rows = list_numbered_excel_cases(excel_dir)
        if not rows:
            _log(f"No NN_*.xlsx under {excel_dir}")
            return 1
        for number, case_id in rows:
            _log(f"  {number:2d}  {case_id}")
        return 0

    faces = parse_face_list(args.lct_faces)
    excel_paths = resolve_excel_paths(args)
    config = load_config(args.config)
    proxy_root = Path(args.output_dir) / PROXY_ROOT_NAME
    proxy_root.mkdir(parents=True, exist_ok=True)

    if args.show:
        args.plot = True

    _log(f"Output root: {proxy_root}")
    _log(f"Cases      : {len(excel_paths)}")
    _log(f"LCT faces  : {', '.join(faces)}")
    _log(f"STT node   : {resolve_stt_node(config)[1]} (fixed)")
    for face in faces:
        label, nid = resolve_proxy_node(config, face)
        u0 = FACE_OUTWARD_NORMALS[face]
        _log(f"  {face}: node {nid} ({label}), u0={u0.tolist()}")

    summary_rows: list[dict] = []
    failures: list[tuple[str, str, str]] = []

    for excel_path in excel_paths:
        case_id = excel_path.stem
        case_dir = proxy_root / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        _log(f"=== {case_id} ===")
        df = pd.read_excel(excel_path)
        case_rows: list[dict] = []
        for face in faces:
            try:
                ts, metadata = compute_case_face_timeseries(
                    df,
                    config,
                    face,
                    excel_path=excel_path,
                    case_matrix_path=Path(args.case_matrix),
                    sheet_name=args.sheet_name,
                )
                stats = summarize_timeseries(ts)
                row = {
                    "case_id": case_id,
                    "lct_face": face,
                    "stt_node": metadata["stt_node"],
                    "proxy_label": metadata["proxy_label"],
                    "proxy_node": metadata["proxy_node"],
                    "u0_x": float(metadata["nominal_axis"][0]),
                    "u0_y": float(metadata["nominal_axis"][1]),
                    "u0_z": float(metadata["nominal_axis"][2]),
                    **stats,
                }
                summary_rows.append(row)
                case_rows.append(row)
                _log(
                    f"  {face}: rms={stats['rms_mag_urad']:.2f} urad, "
                    f"peak={stats['peak_mag_urad']:.2f} urad"
                )

                if args.write_timeseries:
                    out_csv = case_dir / "timeseries" / f"LCT_{face}.csv"
                    out_csv.parent.mkdir(parents=True, exist_ok=True)
                    ts.to_csv(out_csv, index=False)

                if args.plot:
                    out_png = case_dir / "plots" / f"LCT_{face}.png"
                    plot_proxy_los(ts, metadata, out_png, show=args.show)

            except Exception as exc:
                _log(f"  ERROR {face}: {exc}")
                failures.append((case_id, face, str(exc)))

        if case_rows:
            pd.DataFrame(case_rows).to_csv(case_dir / "summary.csv", index=False)

    if not summary_rows:
        _log("No summary rows produced.")
        return 1

    summary = pd.DataFrame(summary_rows)
    summary_path = proxy_root / "summary.csv"
    merged = merge_summary_csv(summary_path, summary)
    _log(f"Wrote summary: {summary_path} ({len(merged)} rows)")

    if args.heatmap:
        heat_path = proxy_root / "summary_heatmap_rms_mag.png"
        plot_summary_heatmap(merged, heat_path)
        _log(f"Wrote heatmap: {heat_path}")

    _log(f"Done: {len(summary_rows)} ok, {len(failures)} failed")
    for case_id, face, err in failures:
        _log(f"  FAIL {case_id} / {face}: {err}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
