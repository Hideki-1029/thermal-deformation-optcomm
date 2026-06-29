import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR / "data_femap_deformation" / "260629_1414_deformation.xlsx"
DEFAULT_CONFIG = SCRIPT_DIR / "data_femap_deformation" / "stt_lct_node_config.json"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR.parents[1] / "results" / "femap_deformation"

COMPONENTS = {
    "x": "T1",
    "y": "T2",
    "z": "T3",
}


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    points = config["points"]
    from_label = config["relative_vector_from"]
    to_label = config["relative_vector_to"]

    for label in (from_label, to_label):
        if label not in points:
            raise ValueError(f"{label!r} is not defined in config points.")

    return config


def find_translation_columns(df, node_id):
    columns = {}
    node_text = str(node_id)

    for axis, component in COMPONENTS.items():
        matches = [
            col
            for col in df.columns
            if node_text in str(col)
            and re.search(rf"(?:\b|[^A-Za-z0-9]){component}\s+Translation\b", str(col))
        ]
        if not matches:
            # Femap exports often look like "..., 2..T1 Translation".
            component_number = {"T1": "2", "T2": "3", "T3": "4"}[component]
            matches = [
                col
                for col in df.columns
                if node_text in str(col)
                and f"{component_number}..{component} Translation" in str(col)
            ]

        if len(matches) != 1:
            raise ValueError(
                f"Expected one {component} Translation column for node {node_id}, "
                f"but found {len(matches)}: {matches}"
            )
        columns[axis] = matches[0]

    return columns


def extract_displacement(df, node_id):
    columns = find_translation_columns(df, node_id)
    values = df[[columns["x"], columns["y"], columns["z"]]].apply(pd.to_numeric)
    return values.to_numpy(dtype=float)


def extract_case_index(df):
    for col in df.columns:
        values = df[col].astype(str)
        case_numbers = values.str.extract(r"Case\s+(\d+)", expand=False)
        if case_numbers.notna().any():
            return case_numbers.astype(float).to_numpy(), "Femap case index [-]"

    return np.arange(1, len(df) + 1, dtype=float), "sample index [-]"


def unit_vector(vector):
    norm = np.linalg.norm(vector)
    if norm == 0.0:
        raise ValueError("Cannot normalize a zero-length vector.")
    return vector / norm


def compute_relative_motion(df, config):
    points = config["points"]
    from_label = config["relative_vector_from"]
    to_label = config["relative_vector_to"]

    from_point = points[from_label]
    to_point = points[to_label]
    from_node = int(from_point["node_id"])
    to_node = int(to_point["node_id"])

    from_position = np.asarray(from_point["cad_position_m"], dtype=float)
    to_position = np.asarray(to_point["cad_position_m"], dtype=float)
    original_vector = to_position - from_position
    original_unit = unit_vector(original_vector)
    baseline_m = np.linalg.norm(original_vector)

    from_disp_m = extract_displacement(df, from_node)
    to_disp_m = extract_displacement(df, to_node)
    relative_disp_m = to_disp_m - from_disp_m

    deformed_vectors = original_vector[None, :] + relative_disp_m
    deformed_units = deformed_vectors / np.linalg.norm(deformed_vectors, axis=1)[:, None]

    dot = np.clip(deformed_units @ original_unit, -1.0, 1.0)
    angle_magnitude_urad = np.arccos(dot) * 1e6

    direction_change_urad = (deformed_units - original_unit[None, :]) * 1e6
    axial_disp_m = relative_disp_m @ original_unit
    transverse_disp_m = np.linalg.norm(
        relative_disp_m - axial_disp_m[:, None] * original_unit[None, :],
        axis=1,
    )

    case_index, case_label = extract_case_index(df)

    result = pd.DataFrame(
        {
            "case_index": case_index,
            "rel_dx_um": relative_disp_m[:, 0] * 1e6,
            "rel_dy_um": relative_disp_m[:, 1] * 1e6,
            "rel_dz_um": relative_disp_m[:, 2] * 1e6,
            "rel_axial_um": axial_disp_m * 1e6,
            "rel_transverse_um": transverse_disp_m * 1e6,
            "angle_x_urad": direction_change_urad[:, 0],
            "angle_y_urad": direction_change_urad[:, 1],
            "angle_z_urad": direction_change_urad[:, 2],
            "angle_magnitude_urad": angle_magnitude_urad,
        }
    )

    metadata = {
        "from_label": from_label,
        "to_label": to_label,
        "from_node": from_node,
        "to_node": to_node,
        "baseline_m": baseline_m,
        "case_label": case_label,
    }
    return result, metadata


def plot_relative_motion(result, metadata, output_png, show=False):
    x = result["case_index"].to_numpy()
    title_prefix = (
        f"{metadata['from_label']} node {metadata['from_node']} -> "
        f"{metadata['to_label']} node {metadata['to_node']}"
    )

    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    axes[0].plot(x, result["rel_dx_um"], label="dx")
    axes[0].plot(x, result["rel_dy_um"], label="dy")
    axes[0].plot(x, result["rel_dz_um"], label="dz")
    axes[0].plot(x, result["rel_transverse_um"], "--", label="transverse norm")
    axes[0].set_ylabel("relative displacement [um]")
    axes[0].set_title(f"{title_prefix}: relative displacement")
    axes[0].grid(True)
    axes[0].legend()

    axes[1].plot(x, result["angle_x_urad"], label="direction change x")
    axes[1].plot(x, result["angle_y_urad"], label="direction change y")
    axes[1].plot(x, result["angle_magnitude_urad"], "--", label="angle magnitude")
    axes[1].set_xlabel(metadata["case_label"])
    axes[1].set_ylabel("relative angle [urad]")
    axes[1].set_title(
        f"Baseline = {metadata['baseline_m']:.3f} m, angle from deformed STT-LCT vector"
    )
    axes[1].grid(True)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(output_png, dpi=200)

    if show:
        plt.show()
    else:
        plt.close(fig)


def parse_sheet_name(value):
    try:
        return int(value)
    except ValueError:
        return value


def parse_args():
    parser = argparse.ArgumentParser(
        description="Plot STT-LCT relative displacement and angle from Femap deformation Excel."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--sheet", type=parse_sheet_name, default=0)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--show", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config(args.config)
    df = pd.read_excel(args.input, sheet_name=args.sheet)

    result, metadata = compute_relative_motion(df, config)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.input.stem
    output_csv = args.output_dir / f"{stem}_stt_lct_relative_motion.csv"
    output_png = args.output_dir / f"{stem}_stt_lct_relative_motion.png"

    result.to_csv(output_csv, index=False)
    plot_relative_motion(result, metadata, output_png, show=args.show)

    print(f"Input Excel : {args.input}")
    print(f"Config      : {args.config}")
    print(f"Nodes       : {metadata['from_label']} {metadata['from_node']} -> "
          f"{metadata['to_label']} {metadata['to_node']}")
    print(f"Baseline    : {metadata['baseline_m']:.6f} m")
    print(f"Output CSV  : {output_csv}")
    print(f"Output PNG  : {output_png}")
    print()
    print(result.describe().loc[["mean", "min", "max"]].to_string())


if __name__ == "__main__":
    main()
