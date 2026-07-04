import argparse
import csv
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_INPUT_DIR = REPO_ROOT / "inputs" / "data_femap_deformation"
DEFAULT_INPUT = DEFAULT_INPUT_DIR / "260629_1505_translation_rotation.xlsx"
DEFAULT_CONFIG = DEFAULT_INPUT_DIR / "stt_lct_node_config.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "femap_deformation"
DEFAULT_FEMAP_MODEL_ROOT = Path("C:/Users/Hide/Femap/research_model")
DEFAULT_CASE_MATRIX = REPO_ROOT / "cases" / "case_matrix.xlsx"
DEFAULT_TEMPERATURE_PROBE_SET_FILE = REPO_ROOT / "cases" / "temperature_probe_sets.yaml"
DEFAULT_TEMPERATURE_PROBE_SET = "default_surface_9points"

TRANSLATION_COMPONENTS = {
    "x": ("T1", "2"),
    "y": ("T2", "3"),
    "z": ("T3", "4"),
}
ROTATION_COMPONENTS = {
    "x": ("R1", "6"),
    "y": ("R2", "7"),
    "z": ("R3", "8"),
}
GRID_ROW_RE = re.compile(
    r"^\s*(\d+)\s+"
    r"([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s+"
    r"([-+0-9.eE]+)\s+"
    r"(\S+)\s+"
    r"([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)"
)


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


def find_result_column(df, node_id, component, quantity, component_number=None):
    node_text = str(node_id)
    matches = [
        col
        for col in df.columns
        if node_text in str(col)
        and re.search(rf"(?:\b|[^A-Za-z0-9]){component}\s+{quantity}\b", str(col))
    ]
    if not matches and component_number is not None:
        matches = [
            col
            for col in df.columns
            if node_text in str(col)
            and f"{component_number}..{component} {quantity}" in str(col)
        ]

    if len(matches) != 1:
        raise ValueError(
            f"Expected one {component} {quantity} column for node {node_id}, "
            f"but found {len(matches)}: {matches}"
        )
    return matches[0]


def find_vector_columns(df, node_id, components, quantity, required=True):
    columns = {}
    for axis, (component, component_number) in components.items():
        try:
            columns[axis] = find_result_column(
                df,
                node_id,
                component,
                quantity,
                component_number=component_number,
            )
        except ValueError:
            if required:
                raise
            return None
    return columns


def extract_vector(df, node_id, components, quantity, required=True):
    columns = find_vector_columns(df, node_id, components, quantity, required=required)
    if columns is None:
        return np.zeros((len(df), 3), dtype=float), False

    values = df[[columns["x"], columns["y"], columns["z"]]].apply(pd.to_numeric)
    return values.to_numpy(dtype=float), True


def extract_case_index(df):
    for col in df.columns:
        values = df[col].astype(str)
        case_numbers = values.str.extract(r"Case\s+(\d+)", expand=False)
        if case_numbers.notna().any():
            return case_numbers.astype(float).to_numpy(), "Femap case index [-]"

    return np.arange(1, len(df) + 1, dtype=float), "sample index [-]"


def path_matches_case_value(value, input_path):
    if pd.isna(value):
        return False

    value_path = Path(str(value))
    input_path = Path(input_path)
    return (
        value_path == input_path
        or value_path.name == input_path.name
        or value_path.stem == input_path.stem
        or input_path.stem in value_path.parts
        or input_path.stem in str(value)
    )


def find_case_matrix_row(case_matrix_path, sheet_name, input_path):
    if not case_matrix_path or not case_matrix_path.exists():
        return None

    case_matrix = pd.read_excel(case_matrix_path, sheet_name=sheet_name)
    input_stem = Path(input_path).stem

    if "case_id" in case_matrix.columns:
        matches = case_matrix[case_matrix["case_id"].astype(str) == input_stem]
        if len(matches) == 1:
            return matches.iloc[0]

    path_columns = [
        column
        for column in (
            "femap_result_stt_lct_path",
            "femap_result_other_path",
            "python_result_path",
            "td_temperature_path",
        )
        if column in case_matrix.columns
    ]
    for column in path_columns:
        matches = case_matrix[
            case_matrix[column].apply(lambda value: path_matches_case_value(value, input_path))
        ]
        if len(matches) == 1:
            return matches.iloc[0]

    return None


def has_duplicate_initial_case(result):
    if len(result) < 2:
        return False

    value_columns = [column for column in result.columns if column != "case_index"]
    first = result.loc[result.index[0], value_columns].to_numpy(dtype=float)
    second = result.loc[result.index[1], value_columns].to_numpy(dtype=float)
    return np.allclose(first, second, rtol=0.0, atol=1e-12)


def apply_case_matrix_time_axis(result, metadata, input_path, case_matrix_path, sheet_name):
    case_row = find_case_matrix_row(case_matrix_path, sheet_name, input_path)
    if case_row is None:
        return None

    sample_interval_s = case_row.get("sample_interval_s")
    if pd.isna(sample_interval_s):
        return None

    first_time_case_index = 2.0 if has_duplicate_initial_case(result) else 1.0
    time_s = np.maximum(
        result["case_index"].to_numpy(dtype=float) - first_time_case_index,
        0.0,
    ) * float(sample_interval_s)
    result.insert(1, "time_s", time_s)
    result.insert(2, "time_h", time_s / 3600.0)
    metadata["case_label"] = "time [h]"
    metadata["x_axis_column"] = "time_h"
    metadata["case_matrix_id"] = case_row.get("case_id", Path(input_path).stem)
    metadata["sample_interval_s"] = float(sample_interval_s)
    metadata["initial_zero_case_count"] = int(first_time_case_index)
    return case_row


def get_plot_x(result, metadata):
    x_column = metadata.get("x_axis_column", "case_index")
    return result[x_column].to_numpy()


def unit_vector(vector):
    norm = np.linalg.norm(vector)
    if norm == 0.0:
        raise ValueError("Cannot normalize a zero-length vector.")
    return vector / norm


def normalize_rows(vectors):
    norms = np.linalg.norm(vectors, axis=1)
    if np.any(norms == 0.0):
        raise ValueError("Cannot normalize a zero-length row vector.")
    return vectors / norms[:, None]


def rotate_direction(direction, rotation_vectors):
    """Rotate one direction by each row of small Femap rotation vectors [rad]."""
    direction = np.asarray(direction, dtype=float)
    rotated = np.zeros((len(rotation_vectors), 3), dtype=float)

    for i, rotvec in enumerate(rotation_vectors):
        theta = np.linalg.norm(rotvec)
        if theta < 1e-12:
            rotated[i] = direction + np.cross(rotvec, direction)
            continue

        axis = rotvec / theta
        rotated[i] = (
            direction * np.cos(theta)
            + np.cross(axis, direction) * np.sin(theta)
            + axis * np.dot(axis, direction) * (1.0 - np.cos(theta))
        )

    return normalize_rows(rotated)


def vector_angle_magnitude_urad(direction_change):
    return np.linalg.norm(direction_change[:, :2], axis=1) * 1e6


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

    nominal_axis = (
        config.get("reference_surfaces", {})
        .get("LCT_nominal_los_axis", {})
        .get("unit_vector", original_unit)
    )
    nominal_axis = unit_vector(np.asarray(nominal_axis, dtype=float))

    from_disp_m, _ = extract_vector(
        df,
        from_node,
        TRANSLATION_COMPONENTS,
        "Translation",
        required=True,
    )
    to_disp_m, _ = extract_vector(
        df,
        to_node,
        TRANSLATION_COMPONENTS,
        "Translation",
        required=True,
    )
    from_rot_rad, has_from_rotation = extract_vector(
        df,
        from_node,
        ROTATION_COMPONENTS,
        "Rotation",
        required=False,
    )
    to_rot_rad, has_to_rotation = extract_vector(
        df,
        to_node,
        ROTATION_COMPONENTS,
        "Rotation",
        required=False,
    )

    relative_disp_m = to_disp_m - from_disp_m
    relative_rot_rad = to_rot_rad - from_rot_rad

    deformed_centerline = original_vector[None, :] + relative_disp_m
    deformed_centerline_unit = normalize_rows(deformed_centerline)
    centerline_change = deformed_centerline_unit - original_unit[None, :]

    stt_axis_unit = rotate_direction(nominal_axis, from_rot_rad)
    lct_axis_unit = rotate_direction(nominal_axis, to_rot_rad)
    relative_axis_unit = rotate_direction(nominal_axis, relative_rot_rad)
    stt_rotation_change = stt_axis_unit - nominal_axis[None, :]
    lct_rotation_change = lct_axis_unit - nominal_axis[None, :]
    relative_rotation_change = relative_axis_unit - nominal_axis[None, :]

    # PAT/far-field LOS is the outgoing LCT optical-axis deviation observed
    # in the STT-defined attitude frame. Translation of the LCT point is not
    # added here because far-field parallax scales with target range, not with
    # the internal STT-LCT baseline.
    far_field_los_change = relative_rotation_change

    # Bookkeeping definitions retained for angle-budget diagnostics.
    # These combine the internal STT-LCT centerline tilt with rotation terms.
    global_los_unit = normalize_rows(
        nominal_axis[None, :] + centerline_change + lct_rotation_change
    )
    stt_relative_los_unit = normalize_rows(
        nominal_axis[None, :] + centerline_change + relative_rotation_change
    )
    global_los_change = global_los_unit - nominal_axis[None, :]
    stt_relative_los_change = stt_relative_los_unit - nominal_axis[None, :]

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
            "stt_rx_urad": from_rot_rad[:, 0] * 1e6,
            "stt_ry_urad": from_rot_rad[:, 1] * 1e6,
            "stt_rz_urad": from_rot_rad[:, 2] * 1e6,
            "lct_rx_urad": to_rot_rad[:, 0] * 1e6,
            "lct_ry_urad": to_rot_rad[:, 1] * 1e6,
            "lct_rz_urad": to_rot_rad[:, 2] * 1e6,
            "rel_rx_urad": relative_rot_rad[:, 0] * 1e6,
            "rel_ry_urad": relative_rot_rad[:, 1] * 1e6,
            "rel_rz_urad": relative_rot_rad[:, 2] * 1e6,
            "centerline_angle_x_urad": centerline_change[:, 0] * 1e6,
            "centerline_angle_y_urad": centerline_change[:, 1] * 1e6,
            "centerline_angle_z_urad": centerline_change[:, 2] * 1e6,
            "centerline_angle_magnitude_urad": vector_angle_magnitude_urad(
                centerline_change
            ),
            "stt_rotation_angle_x_urad": stt_rotation_change[:, 0] * 1e6,
            "stt_rotation_angle_y_urad": stt_rotation_change[:, 1] * 1e6,
            "stt_rotation_angle_z_urad": stt_rotation_change[:, 2] * 1e6,
            "stt_rotation_angle_magnitude_urad": vector_angle_magnitude_urad(
                stt_rotation_change
            ),
            "lct_rotation_angle_x_urad": lct_rotation_change[:, 0] * 1e6,
            "lct_rotation_angle_y_urad": lct_rotation_change[:, 1] * 1e6,
            "lct_rotation_angle_z_urad": lct_rotation_change[:, 2] * 1e6,
            "lct_rotation_angle_magnitude_urad": vector_angle_magnitude_urad(
                lct_rotation_change
            ),
            "relative_rotation_angle_x_urad": relative_rotation_change[:, 0] * 1e6,
            "relative_rotation_angle_y_urad": relative_rotation_change[:, 1] * 1e6,
            "relative_rotation_angle_z_urad": relative_rotation_change[:, 2] * 1e6,
            "relative_rotation_angle_magnitude_urad": vector_angle_magnitude_urad(
                relative_rotation_change
            ),
            "far_field_los_angle_x_urad": far_field_los_change[:, 0] * 1e6,
            "far_field_los_angle_y_urad": far_field_los_change[:, 1] * 1e6,
            "far_field_los_angle_z_urad": far_field_los_change[:, 2] * 1e6,
            "far_field_los_angle_magnitude_urad": vector_angle_magnitude_urad(
                far_field_los_change
            ),
            "global_los_angle_x_urad": global_los_change[:, 0] * 1e6,
            "global_los_angle_y_urad": global_los_change[:, 1] * 1e6,
            "global_los_angle_z_urad": global_los_change[:, 2] * 1e6,
            "global_los_angle_magnitude_urad": vector_angle_magnitude_urad(
                global_los_change
            ),
            "stt_relative_los_angle_x_urad": stt_relative_los_change[:, 0] * 1e6,
            "stt_relative_los_angle_y_urad": stt_relative_los_change[:, 1] * 1e6,
            "stt_relative_los_angle_z_urad": stt_relative_los_change[:, 2] * 1e6,
            "stt_relative_los_angle_magnitude_urad": vector_angle_magnitude_urad(
                stt_relative_los_change
            ),
        }
    )

    metadata = {
        "from_label": from_label,
        "to_label": to_label,
        "from_node": from_node,
        "to_node": to_node,
        "from_position": from_position,
        "to_position": to_position,
        "from_disp_m": from_disp_m,
        "to_disp_m": to_disp_m,
        "to_rot_rad": to_rot_rad,
        "baseline_m": baseline_m,
        "case_label": case_label,
        "has_rotation": has_from_rotation and has_to_rotation,
        "nominal_axis": nominal_axis,
    }
    return result, metadata


def plot_relative_motion(result, metadata, output_png, show=False):
    x = get_plot_x(result, metadata)
    title_prefix = (
        f"{metadata['from_label']} node {metadata['from_node']} -> "
        f"{metadata['to_label']} node {metadata['to_node']}"
    )

    fig, axes = plt.subplots(3, 1, figsize=(11, 10), sharex=True)

    axes[0].plot(x, result["rel_dx_um"], label="dx")
    axes[0].plot(x, result["rel_dy_um"], label="dy")
    axes[0].plot(x, result["rel_dz_um"], label="dz")
    axes[0].plot(x, result["rel_transverse_um"], "--", label="transverse norm")
    axes[0].set_ylabel("relative displacement [um]")
    axes[0].set_title(f"{title_prefix}: relative displacement")
    axes[0].grid(True)
    axes[0].legend()

    axes[1].plot(x, result["rel_rx_urad"], label="relative R1")
    axes[1].plot(x, result["rel_ry_urad"], label="relative R2")
    axes[1].plot(x, result["rel_rz_urad"], label="relative R3")
    axes[1].set_ylabel("LCT - STT rotation [urad]")
    axes[1].set_title("Relative node rotation DOF")
    axes[1].grid(True)
    axes[1].legend()

    axes[2].plot(x, result["centerline_angle_magnitude_urad"], label="centerline tilt")
    axes[2].plot(x, result["stt_rotation_angle_magnitude_urad"], label="STT axis rotation")
    axes[2].plot(x, result["lct_rotation_angle_magnitude_urad"], label="LCT axis rotation")
    axes[2].plot(
        x,
        result["far_field_los_angle_magnitude_urad"],
        linewidth=2,
        label="far-field PAT LOS",
    )
    axes[2].plot(
        x,
        result["stt_relative_los_angle_magnitude_urad"],
        "--",
        label="centerline + relative rotation",
    )
    axes[2].set_xlabel(metadata["case_label"])
    axes[2].set_ylabel("angle magnitude [urad]")
    axes[2].set_title(
        f"Baseline = {metadata['baseline_m']:.3f} m, LOS definitions compared"
    )
    axes[2].grid(True)
    axes[2].legend()

    fig.tight_layout()
    fig.savefig(output_png, dpi=200)

    if show:
        plt.show()
    else:
        plt.close(fig)


def plot_far_field_los_budget(result, metadata, output_png, show=False):
    x = get_plot_x(result, metadata)
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    for axis_name, ax in zip(("x", "y"), axes):
        ax.plot(
            x,
            result[f"centerline_angle_{axis_name}_urad"],
            ":",
            label=f"centerline {axis_name} (aux)",
        )
        ax.plot(
            x,
            result[f"stt_rotation_angle_{axis_name}_urad"],
            "--",
            label=f"STT rotation {axis_name}",
        )
        ax.plot(
            x,
            result[f"lct_rotation_angle_{axis_name}_urad"],
            "--",
            label=f"LCT rotation {axis_name}",
        )
        ax.plot(
            x,
            result[f"far_field_los_angle_{axis_name}_urad"],
            linewidth=2,
            label=f"far-field PAT LOS {axis_name}",
        )
        ax.set_ylabel(f"{axis_name} angle [urad]")
        ax.grid(True)
        ax.legend()

    axes[0].set_title("Far-field PAT LOS angle budget by component")
    axes[1].set_xlabel(metadata["case_label"])
    fig.tight_layout()
    fig.savefig(output_png, dpi=200)

    if show:
        plt.show()
    else:
        plt.close(fig)


def plot_angle_budget(result, metadata, output_png, los_prefix, los_label, show=False):
    x = get_plot_x(result, metadata)
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    for axis_name, ax in zip(("x", "y"), axes):
        ax.plot(
            x,
            result[f"centerline_angle_{axis_name}_urad"],
            label=f"centerline {axis_name}",
        )
        if los_prefix == "global_los":
            rotation_column = f"lct_rotation_angle_{axis_name}_urad"
            rotation_label = f"LCT rotation {axis_name}"
        elif los_prefix == "stt_relative_los":
            rotation_column = f"relative_rotation_angle_{axis_name}_urad"
            rotation_label = f"LCT - STT rotation {axis_name}"
        else:
            raise ValueError(f"Unsupported LOS prefix: {los_prefix}")

        ax.plot(
            x,
            result[f"stt_rotation_angle_{axis_name}_urad"],
            ":",
            label=f"STT rotation {axis_name}",
        )
        if los_prefix == "stt_relative_los":
            ax.plot(
                x,
                result[f"lct_rotation_angle_{axis_name}_urad"],
                "--",
                label=f"LCT rotation {axis_name}",
            )
        ax.plot(x, result[rotation_column], label=rotation_label)
        ax.plot(
            x,
            result[f"{los_prefix}_angle_{axis_name}_urad"],
            linewidth=2,
            label=f"{los_label} {axis_name}",
        )
        ax.set_ylabel(f"{axis_name} angle [urad]")
        ax.grid(True)
        ax.legend()

    axes[0].set_title(f"{los_label} angle budget by component")
    axes[1].set_xlabel(metadata["case_label"])
    fig.tight_layout()
    fig.savefig(output_png, dpi=200)

    if show:
        plt.show()
    else:
        plt.close(fig)


def plot_los_definition_comparison(result, metadata, output_png, show=False):
    x = get_plot_x(result, metadata)
    fig, axes = plt.subplots(3, 1, figsize=(11, 10), sharex=True)

    axes[0].plot(
        x,
        result["far_field_los_angle_x_urad"],
        linewidth=2,
        label="far-field PAT x",
    )
    axes[0].plot(
        x,
        result["stt_relative_los_angle_x_urad"],
        "--",
        label="centerline + relative rotation x",
    )
    axes[0].plot(
        x,
        result["global_los_angle_x_urad"],
        ":",
        label="global bookkeeping x",
    )
    axes[0].set_ylabel("x angle [urad]")
    axes[0].grid(True)
    axes[0].legend()

    axes[1].plot(
        x,
        result["far_field_los_angle_y_urad"],
        linewidth=2,
        label="far-field PAT y",
    )
    axes[1].plot(
        x,
        result["stt_relative_los_angle_y_urad"],
        "--",
        label="centerline + relative rotation y",
    )
    axes[1].plot(
        x,
        result["global_los_angle_y_urad"],
        ":",
        label="global bookkeeping y",
    )
    axes[1].set_ylabel("y angle [urad]")
    axes[1].grid(True)
    axes[1].legend()

    axes[2].plot(
        x,
        result["far_field_los_angle_magnitude_urad"],
        linewidth=2,
        label="far-field PAT magnitude",
    )
    axes[2].plot(
        x,
        result["stt_relative_los_angle_magnitude_urad"],
        "--",
        label="centerline + relative rotation magnitude",
    )
    axes[2].plot(
        x,
        result["global_los_angle_magnitude_urad"],
        ":",
        label="global bookkeeping magnitude",
    )
    axes[2].set_xlabel(metadata["case_label"])
    axes[2].set_ylabel("angle magnitude [urad]")
    axes[2].grid(True)
    axes[2].legend()

    axes[0].set_title("Far-field PAT LOS vs bookkeeping LOS definitions")
    fig.tight_layout()
    fig.savefig(output_png, dpi=200)

    if show:
        plt.show()
    else:
        plt.close(fig)


def make_plane(center, normal, size=0.18):
    normal = unit_vector(normal)
    basis_1 = np.array([1.0, 0.0, 0.0])
    if abs(np.dot(basis_1, normal)) > 0.95:
        basis_1 = np.array([0.0, 1.0, 0.0])
    basis_1 = unit_vector(basis_1 - np.dot(basis_1, normal) * normal)
    basis_2 = np.cross(normal, basis_1)

    corners = []
    for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1)]:
        corners.append(center + size * (sx * basis_1 + sy * basis_2))
    return np.asarray(corners)


def plot_plane_sketch(result, metadata, output_png, show=False, exaggeration=250.0):
    idx = int(result["far_field_los_angle_magnitude_urad"].idxmax())
    case_index = result.loc[idx, "case_index"]

    stt_center = metadata["from_position"]
    lct_center_initial = metadata["to_position"]
    lct_center_deformed = (
        lct_center_initial + metadata["to_disp_m"][idx] * exaggeration
    )

    stt_normal = np.array([0.0, 0.0, 1.0])
    lct_nominal_axis = metadata["nominal_axis"]
    lct_rot_exaggerated = metadata["to_rot_rad"][idx] * exaggeration
    lct_normal_deformed = rotate_direction(lct_nominal_axis, lct_rot_exaggerated[None, :])[0]

    stt_plane = make_plane(stt_center, stt_normal)
    lct_plane = make_plane(lct_center_deformed, lct_normal_deformed)

    fig = plt.figure(figsize=(9, 7))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(stt_plane[:, 0], stt_plane[:, 1], stt_plane[:, 2], color="tab:blue")
    ax.plot(lct_plane[:, 0], lct_plane[:, 1], lct_plane[:, 2], color="tab:red")
    ax.scatter(*stt_center, color="tab:blue", label="STT initial reference plane")
    ax.scatter(*lct_center_deformed, color="tab:red", label="LCT deformed plane")

    ax.quiver(
        *stt_center,
        *stt_normal,
        length=0.15,
        color="tab:blue",
        normalize=True,
    )
    ax.quiver(
        *lct_center_deformed,
        *lct_normal_deformed,
        length=0.15,
        color="tab:red",
        normalize=True,
    )

    all_points = np.vstack(
        [stt_plane, lct_plane, stt_center[None, :], lct_center_deformed[None, :]]
    )
    center = all_points.mean(axis=0)
    span = np.max(np.ptp(all_points, axis=0))
    for setter, value in zip(
        (ax.set_xlim, ax.set_ylim, ax.set_zlim),
        zip(center - span * 0.6, center + span * 0.6),
    ):
        setter(*value)

    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.set_zlabel("Z [m]")
    ax.set_title(
        f"Plane sketch at case {case_index:g} "
        f"(deformation exaggerated x{exaggeration:g})"
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_png, dpi=200)

    if show:
        plt.show()
    else:
        plt.close(fig)


def parse_probe_scalar(value):
    value = value.strip()
    if value.startswith("["):
        parsed_values = []
        for item in value.strip("[]").split(","):
            item = item.strip()
            try:
                parsed_values.append(float(item))
            except ValueError:
                parsed_values.append(item.strip("\"'"))
        return parsed_values
    try:
        return float(value)
    except ValueError:
        return value


def load_temperature_probe_set(probe_set_path, probe_set_name):
    probe_sets = {}
    current_set = None
    section = None
    current_point = None
    current_face = None

    with open(probe_set_path, encoding="utf-8") as f:
        for raw_line in f:
            if not raw_line.strip() or raw_line.lstrip().startswith("#"):
                continue

            indent = len(raw_line) - len(raw_line.lstrip(" "))
            stripped = raw_line.strip()

            if indent == 0 and stripped.endswith(":"):
                key = stripped[:-1]
                if key != "probe_sets":
                    current_set = None
                    section = None
                continue

            if indent == 2 and stripped.endswith(":"):
                current_set = stripped[:-1]
                probe_sets[current_set] = {"points": {}, "faces": {}}
                section = None
                continue

            if current_set is None:
                continue

            if indent == 6 and stripped == "points:":
                section = "points"
                continue
            if indent == 4 and stripped == "faces:":
                section = "faces"
                continue

            if section == "points":
                if indent == 8 and stripped.endswith(":"):
                    current_point = stripped[:-1]
                    probe_sets[current_set]["points"][current_point] = {}
                    continue
                if indent == 10 and current_point and ":" in stripped:
                    key, value = stripped.split(":", 1)
                    probe_sets[current_set]["points"][current_point][key] = (
                        parse_probe_scalar(value)
                    )
                    continue

            if section == "faces":
                if indent == 6 and stripped.endswith(":"):
                    current_face = stripped[:-1]
                    probe_sets[current_set]["faces"][current_face] = {}
                    continue
                if indent == 8 and current_face and ":" in stripped:
                    key, value = stripped.split(":", 1)
                    value = value.strip()
                    if key == "ranges_mm":
                        probe_sets[current_set]["faces"][current_face][key] = {}
                    elif value:
                        probe_sets[current_set]["faces"][current_face][key] = (
                            parse_probe_scalar(value)
                        )
                    continue
                if indent == 10 and current_face and ":" in stripped:
                    key, value = stripped.split(":", 1)
                    probe_sets[current_set]["faces"][current_face]["ranges_mm"][
                        key
                    ] = parse_probe_scalar(value)

    if probe_set_name not in probe_sets:
        raise ValueError(f"{probe_set_name!r} was not found in {probe_set_path}")
    return probe_sets[probe_set_name]


def expand_temperature_probe_set(probe_set):
    probes = []
    for panel_name, face in probe_set["faces"].items():
        axes = face["axes"]
        fixed_axis = face["fixed_axis"]
        fixed_value = face["fixed_value_mm"]

        for point_name, point_definition in probe_set["points"].items():
            fractions = point_definition["fractions"]
            target = {fixed_axis: fixed_value}
            for axis, fraction in zip(axes, fractions):
                range_min, range_max = face["ranges_mm"][axis]
                target[axis] = range_min + fraction * (range_max - range_min)

            probes.append(
                {
                    "name": f"{panel_name.lower()}_{point_name}",
                    "panel": panel_name,
                    "target_xyz": (target["x"], target["y"], target["z"]),
                }
            )
    return probes


def parse_mapper_grid_points(grid_path, panel_name):
    points = []
    with open(grid_path, encoding="utf-8") as f:
        for line in f:
            match = GRID_ROW_RE.match(line)
            if not match:
                continue

            entity_name = match.group(6)
            panel_match = re.search(r"PANEL_[A-Z]+", entity_name)
            panel = panel_match.group(0) if panel_match else ""
            if panel != panel_name:
                continue

            points.append(
                {
                    "femap_node_id": int(match.group(1)),
                    "x_mm": float(match.group(2)),
                    "y_mm": float(match.group(3)),
                    "z_mm": float(match.group(4)),
                    "mapped_tolerance": float(match.group(5)),
                    "mapped_entity_name": entity_name,
                    "u": float(match.group(7)),
                    "v": float(match.group(8)),
                    "w": float(match.group(9)),
                }
            )

    if not points:
        raise ValueError(f"No grid points found for {panel_name} in {grid_path}")
    return points


def choose_nearest_mapper_point(points, target_xyz):
    def distance_squared(point):
        return (
            (point["x_mm"] - target_xyz[0]) ** 2
            + (point["y_mm"] - target_xyz[1]) ** 2
            + (point["z_mm"] - target_xyz[2]) ** 2
        )

    return min(points, key=distance_squared)


def read_mapper_temperature_histories(transient_path, femap_node_ids):
    requested_ids = list(dict.fromkeys(femap_node_ids))
    with open(transient_path, encoding="utf-8") as f:
        node_count = int(next(f).strip())
        node_names = [next(f).strip() for _ in range(node_count)]

        index_to_node_id = {}
        for node_id in requested_ids:
            target_name = f"NASTRAN.{node_id}"
            try:
                index_to_node_id[node_names.index(target_name)] = node_id
            except ValueError as exc:
                raise ValueError(f"{target_name} was not found in {transient_path}") from exc

        times = []
        histories = {node_id: [] for node_id in requested_ids}
        while True:
            time_line = f.readline()
            if not time_line:
                break

            times.append(float(time_line.strip()))
            block_values = {}
            for index in range(node_count):
                value_line = f.readline()
                if not value_line:
                    raise ValueError("Unexpected end of file inside a temperature block.")
                if index in index_to_node_id:
                    block_values[index_to_node_id[index]] = float(value_line.strip())

            for node_id in requested_ids:
                histories[node_id].append(block_values[node_id])

    return times, histories


def write_temperature_probe_outputs(output_dir, probe_set_name, times, probe_results):
    temperatures_csv = output_dir / f"{probe_set_name}_temperatures.csv"
    nodes_csv = output_dir / f"{probe_set_name}_nodes.csv"

    with open(temperatures_csv, "w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "time_s",
            "probe_name",
            "panel",
            "temperature_c",
            "femap_node_id",
            "x_mm",
            "y_mm",
            "z_mm",
            "mapped_entity_name",
            "target_x_mm",
            "target_y_mm",
            "target_z_mm",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in probe_results:
            probe = result["probe"]
            point = result["point"]
            for time_s, temperature in zip(times, result["temperatures"]):
                writer.writerow(
                    {
                        "time_s": time_s,
                        "probe_name": probe["name"],
                        "panel": probe["panel"],
                        "temperature_c": temperature,
                        "femap_node_id": point["femap_node_id"],
                        "x_mm": point["x_mm"],
                        "y_mm": point["y_mm"],
                        "z_mm": point["z_mm"],
                        "mapped_entity_name": point["mapped_entity_name"],
                        "target_x_mm": probe["target_xyz"][0],
                        "target_y_mm": probe["target_xyz"][1],
                        "target_z_mm": probe["target_xyz"][2],
                    }
                )

    with open(nodes_csv, "w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "probe_name",
            "panel",
            "femap_node_id",
            "x_mm",
            "y_mm",
            "z_mm",
            "target_x_mm",
            "target_y_mm",
            "target_z_mm",
            "mapped_entity_name",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in probe_results:
            probe = result["probe"]
            point = result["point"]
            writer.writerow(
                {
                    "probe_name": probe["name"],
                    "panel": probe["panel"],
                    "femap_node_id": point["femap_node_id"],
                    "x_mm": point["x_mm"],
                    "y_mm": point["y_mm"],
                    "z_mm": point["z_mm"],
                    "target_x_mm": probe["target_xyz"][0],
                    "target_y_mm": probe["target_xyz"][1],
                    "target_z_mm": probe["target_xyz"][2],
                    "mapped_entity_name": point["mapped_entity_name"],
                }
            )

    return temperatures_csv, nodes_csv


def plot_temperature_probe_overview(output_png, times, probe_results, show=False):
    panels = sorted({result["probe"]["panel"] for result in probe_results})
    time_hours = np.asarray(times, dtype=float) / 3600.0
    fig, axes = plt.subplots(len(panels), 1, figsize=(10, 2.4 * len(panels)), sharex=True)
    if len(panels) == 1:
        axes = [axes]

    for ax, panel in zip(axes, panels):
        panel_results = [
            result for result in probe_results if result["probe"]["panel"] == panel
        ]
        for result in panel_results:
            ax.plot(
                time_hours,
                result["temperatures"],
                linewidth=1.1,
                label=result["probe"]["name"].replace(f"{panel.lower()}_", ""),
            )
        ax.set_ylabel("temp [C]")
        ax.set_title(panel)
        ax.grid(True)
        ax.legend(ncol=3, fontsize=7)

    axes[-1].set_xlabel("time [h]")
    fig.tight_layout()
    fig.savefig(output_png, dpi=200)

    if show:
        plt.show()
    else:
        plt.close(fig)


def extract_temperature_probe_set(
    mapper_dir, probe_set_path, probe_set_name, output_dir, show=False
):
    grid_path = mapper_dir / "outputMapSummaryGridPoints.txt"
    transient_path = mapper_dir / "outputTransient.txt"

    probe_set = load_temperature_probe_set(probe_set_path, probe_set_name)
    probes = expand_temperature_probe_set(probe_set)
    points_by_panel = {
        panel: parse_mapper_grid_points(grid_path, panel)
        for panel in sorted({probe["panel"] for probe in probes})
    }

    probe_results = []
    for probe in probes:
        point = choose_nearest_mapper_point(
            points_by_panel[probe["panel"]], probe["target_xyz"]
        )
        probe_results.append({"probe": probe, "point": point})

    times, histories = read_mapper_temperature_histories(
        transient_path, [result["point"]["femap_node_id"] for result in probe_results]
    )
    for result in probe_results:
        result["temperatures"] = histories[result["point"]["femap_node_id"]]

    temperatures_csv, nodes_csv = write_temperature_probe_outputs(
        output_dir, probe_set_name, times, probe_results
    )
    overview_png = output_dir / f"{probe_set_name}_temperature_overview.png"
    plot_temperature_probe_overview(overview_png, times, probe_results, show=show)

    return {
        "probe_count": len(probe_results),
        "time_count": len(times),
        "temperatures_csv": temperatures_csv,
        "nodes_csv": nodes_csv,
        "overview_png": overview_png,
    }


def parse_sheet_name(value):
    try:
        return int(value)
    except ValueError:
        return value


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Plot STT-LCT relative displacement, rotation, and far-field PAT LOS "
            "angle from Femap Excel."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--sheet", type=parse_sheet_name, default=0)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--case-matrix",
        type=Path,
        default=DEFAULT_CASE_MATRIX,
        help="Case matrix workbook used to map Femap case index to elapsed time.",
    )
    parser.add_argument(
        "--case-matrix-sheet",
        default="case_matrix",
        help="Sheet name in the case matrix workbook.",
    )
    parser.add_argument(
        "--mapper-dir",
        type=Path,
        help=(
            "Directory containing TD mapper output. Defaults to "
            "C:/Users/Hide/Femap/research_model/{input_stem}/mapper_from_TD."
        ),
    )
    parser.add_argument(
        "--temperature-probe-set-file",
        type=Path,
        default=DEFAULT_TEMPERATURE_PROBE_SET_FILE,
    )
    parser.add_argument(
        "--temperature-probe-set",
        default=DEFAULT_TEMPERATURE_PROBE_SET,
        help="Probe set name defined in cases/temperature_probe_sets.yaml.",
    )
    parser.add_argument(
        "--skip-temperature-probes",
        action="store_true",
        help="Skip mapper temperature probe extraction.",
    )
    parser.add_argument("--show", action="store_true")
    parser.add_argument(
        "--plane-exaggeration",
        type=float,
        default=250.0,
        help="Scale factor for displacement and rotation in the 3D plane sketch.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config(args.config)
    df = pd.read_excel(args.input, sheet_name=args.sheet)

    result, metadata = compute_relative_motion(df, config)
    case_matrix_row = apply_case_matrix_time_axis(
        result,
        metadata,
        input_path=args.input,
        case_matrix_path=args.case_matrix,
        sheet_name=args.case_matrix_sheet,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.input.stem
    detail_output_dir = args.output_dir / stem
    detail_output_dir.mkdir(parents=True, exist_ok=True)

    output_csv = detail_output_dir / "los_angles.csv"
    output_overview_png = detail_output_dir / "stt_lct_motion_overview.png"
    output_global_budget_png = detail_output_dir / "global_los_angle_budget.png"
    output_far_field_budget_png = (
        args.output_dir / f"{stem}_far_field_los_angle_budget.png"
    )
    output_stt_budget_png = detail_output_dir / "stt_relative_los_angle_budget.png"
    output_comparison_png = detail_output_dir / "los_definition_comparison.png"
    output_plane_png = detail_output_dir / "stt_lct_plane_sketch.png"

    result.to_csv(output_csv, index=False)
    plot_relative_motion(result, metadata, output_overview_png, show=args.show)
    plot_far_field_los_budget(
        result,
        metadata,
        output_far_field_budget_png,
        show=args.show,
    )
    plot_angle_budget(
        result,
        metadata,
        output_global_budget_png,
        los_prefix="global_los",
        los_label="global LOS",
        show=args.show,
    )
    plot_angle_budget(
        result,
        metadata,
        output_stt_budget_png,
        los_prefix="stt_relative_los",
        los_label="STT-relative LOS bookkeeping",
        show=args.show,
    )
    plot_los_definition_comparison(
        result,
        metadata,
        output_comparison_png,
        show=args.show,
    )
    plot_plane_sketch(
        result,
        metadata,
        output_plane_png,
        show=args.show,
        exaggeration=args.plane_exaggeration,
    )

    temperature_outputs = None
    if not args.skip_temperature_probes and args.temperature_probe_set:
        mapper_dir = args.mapper_dir or DEFAULT_FEMAP_MODEL_ROOT / stem / "mapper_from_TD"
        if mapper_dir.exists():
            temperature_outputs = extract_temperature_probe_set(
                mapper_dir=mapper_dir,
                probe_set_path=args.temperature_probe_set_file,
                probe_set_name=args.temperature_probe_set,
                output_dir=detail_output_dir,
                show=args.show,
            )
        else:
            print(f"Temperature probes skipped: mapper dir not found: {mapper_dir}")

    print(f"Input Excel          : {args.input}")
    print(f"Config               : {args.config}")
    print(
        f"Nodes                : {metadata['from_label']} {metadata['from_node']} -> "
        f"{metadata['to_label']} {metadata['to_node']}"
    )
    print(f"Baseline             : {metadata['baseline_m']:.6f} m")
    print(f"Rotation columns     : {'yes' if metadata['has_rotation'] else 'no'}")
    if case_matrix_row is not None:
        print(f"Case matrix          : {args.case_matrix}")
        print(f"Case ID              : {metadata['case_matrix_id']}")
        print(f"Sample interval      : {metadata['sample_interval_s']:.6g} s")
        print(f"Initial zero cases   : {metadata['initial_zero_case_count']}")
        print(f"Plot x axis          : {metadata['case_label']}")
    print(f"Output CSV           : {output_csv}")
    print(f"Overview PNG         : {output_overview_png}")
    print(f"Far-field budget PNG : {output_far_field_budget_png}")
    print(f"Global budget PNG    : {output_global_budget_png}")
    print(f"STT bookkeeping PNG  : {output_stt_budget_png}")
    print(f"Comparison PNG       : {output_comparison_png}")
    print(f"Plane sketch PNG     : {output_plane_png}")
    if temperature_outputs is not None:
        print(f"Temperature probes   : {temperature_outputs['probe_count']}")
        print(f"Temperature steps    : {temperature_outputs['time_count']}")
        print(f"Temperature CSV      : {temperature_outputs['temperatures_csv']}")
        print(f"Temperature nodes CSV: {temperature_outputs['nodes_csv']}")
        print(f"Temperature PNG      : {temperature_outputs['overview_png']}")
    print()
    summary_columns = [
        "centerline_angle_magnitude_urad",
        "stt_rotation_angle_magnitude_urad",
        "lct_rotation_angle_magnitude_urad",
        "relative_rotation_angle_magnitude_urad",
        "far_field_los_angle_magnitude_urad",
        "global_los_angle_magnitude_urad",
        "stt_relative_los_angle_magnitude_urad",
    ]
    print(result[summary_columns].describe().loc[["mean", "min", "max"]].to_string())


if __name__ == "__main__":
    main()
