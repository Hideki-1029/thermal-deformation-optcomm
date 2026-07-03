import argparse
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
    x = result["case_index"].to_numpy()
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
    x = result["case_index"].to_numpy()
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
    x = result["case_index"].to_numpy()
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
    x = result["case_index"].to_numpy()
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

    print(f"Input Excel          : {args.input}")
    print(f"Config               : {args.config}")
    print(
        f"Nodes                : {metadata['from_label']} {metadata['from_node']} -> "
        f"{metadata['to_label']} {metadata['to_node']}"
    )
    print(f"Baseline             : {metadata['baseline_m']:.6f} m")
    print(f"Rotation columns     : {'yes' if metadata['has_rotation'] else 'no'}")
    print(f"Output CSV           : {output_csv}")
    print(f"Overview PNG         : {output_overview_png}")
    print(f"Far-field budget PNG : {output_far_field_budget_png}")
    print(f"Global budget PNG    : {output_global_budget_png}")
    print(f"STT bookkeeping PNG  : {output_stt_budget_png}")
    print(f"Comparison PNG       : {output_comparison_png}")
    print(f"Plane sketch PNG     : {output_plane_png}")
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
