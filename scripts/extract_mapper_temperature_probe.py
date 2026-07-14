import argparse
import csv
import re
from pathlib import Path

import matplotlib.pyplot as plt
import yaml
from matplotlib.ticker import MultipleLocator


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASE_ID = "06_LTAN06_800km_1213COLD_PX_STTLCT_HEAT_PX_0p5"
DEFAULT_MAPPER_DIR = (
    Path("C:/Users/Hide/Femap/research_model") / DEFAULT_CASE_ID / "mapper_from_TD"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "femap_deformation" / DEFAULT_CASE_ID
DEFAULT_PROBE_SET_FILE = REPO_ROOT / "cases" / "temperature_probe_sets.yaml"

GRID_ROW_RE = re.compile(
    r"^\s*(\d+)\s+"
    r"([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s+"
    r"([-+0-9.eE]+)\s+"
    r"(\S+)\s+"
    r"([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)"
)


def parse_grid_points(grid_path, panel_name):
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


def choose_probe_point(points, target_xyz=None):
    if target_xyz is None:
        target_xyz = tuple(
            sum(point[key] for point in points) / len(points)
            for key in ("x_mm", "y_mm", "z_mm")
        )

    def distance_squared(point):
        return (
            (point["x_mm"] - target_xyz[0]) ** 2
            + (point["y_mm"] - target_xyz[1]) ** 2
            + (point["z_mm"] - target_xyz[2]) ** 2
        )

    return min(points, key=distance_squared), target_xyz


def parse_scalar(value):
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


def load_probe_set(probe_set_path, probe_set_name):
    with open(probe_set_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    probe_sets = data.get("probe_sets") or {}
    if probe_set_name not in probe_sets:
        raise ValueError(f"{probe_set_name!r} was not found in {probe_set_path}")
    return probe_sets[probe_set_name]


def _explicit_probes_from_set(probe_set):
    """Return probes defined via explicit xyz_mm, or None if not used."""
    raw = probe_set.get("probes")
    if not raw:
        return None

    if isinstance(raw, dict):
        items = [{"name": name, **definition} for name, definition in raw.items()]
    else:
        items = list(raw)

    probes = []
    for item in items:
        xyz = item.get("xyz_mm")
        if xyz is None or len(xyz) != 3:
            raise ValueError(f"Probe {item.get('name')!r} requires xyz_mm: [x, y, z]")
        panel = item.get("panel")
        name = item.get("name")
        if not panel or not name:
            raise ValueError("Explicit probes require both name and panel")
        probes.append(
            {
                "name": str(name),
                "panel": str(panel),
                "target_xyz": (float(xyz[0]), float(xyz[1]), float(xyz[2])),
            }
        )
    return probes


def expand_probe_set(probe_set):
    explicit = _explicit_probes_from_set(probe_set)
    if explicit is not None:
        return explicit

    points = probe_set.get("points")
    if not points:
        points = (probe_set.get("pattern") or {}).get("points") or {}
    faces = probe_set.get("faces") or {}
    if not points or not faces:
        raise ValueError(
            "Probe set must define either 'probes' (explicit xyz) "
            "or pattern points + faces"
        )

    probes = []
    for panel_name, face in faces.items():
        axes = face["axes"]
        fixed_axis = face["fixed_axis"]
        fixed_value = face["fixed_value_mm"]

        for point_name, point_definition in points.items():
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


def read_temperature_history(transient_path, femap_node_id):
    with open(transient_path, encoding="utf-8") as f:
        node_count = int(next(f).strip())
        node_names = [next(f).strip() for _ in range(node_count)]

        target_name = f"NASTRAN.{femap_node_id}"
        try:
            target_index = node_names.index(target_name)
        except ValueError as exc:
            raise ValueError(f"{target_name} was not found in {transient_path}") from exc

        times = []
        temperatures = []
        while True:
            time_line = f.readline()
            if not time_line:
                break

            time_s = float(time_line.strip())
            temperature = None
            for index in range(node_count):
                value_line = f.readline()
                if not value_line:
                    raise ValueError("Unexpected end of file inside a temperature block.")
                if index == target_index:
                    temperature = float(value_line.strip())

            times.append(time_s)
            temperatures.append(temperature)

    return times, temperatures


def read_temperature_histories(transient_path, femap_node_ids):
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


def write_temperature_csv(output_csv, times, temperatures, probe_point, target_xyz):
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "time_s",
        "temperature",
        "femap_node_id",
        "x_mm",
        "y_mm",
        "z_mm",
        "mapped_entity_name",
        "target_x_mm",
        "target_y_mm",
        "target_z_mm",
    ]
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for time_s, temperature in zip(times, temperatures):
            writer.writerow(
                {
                    "time_s": time_s,
                    "temperature": temperature,
                    "femap_node_id": probe_point["femap_node_id"],
                    "x_mm": probe_point["x_mm"],
                    "y_mm": probe_point["y_mm"],
                    "z_mm": probe_point["z_mm"],
                    "mapped_entity_name": probe_point["mapped_entity_name"],
                    "target_x_mm": target_xyz[0],
                    "target_y_mm": target_xyz[1],
                    "target_z_mm": target_xyz[2],
                }
            )


def write_probe_set_csv(output_csv, times, probe_results):
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "time_s",
        "probe_name",
        "panel",
        "temperature",
        "femap_node_id",
        "x_mm",
        "y_mm",
        "z_mm",
        "mapped_entity_name",
        "target_x_mm",
        "target_y_mm",
        "target_z_mm",
    ]
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
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
                        "temperature": temperature,
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


def write_probe_set_summary_csv(output_csv, probe_results):
    output_csv.parent.mkdir(parents=True, exist_ok=True)
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
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
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


def plot_temperature_history(output_png, times, temperatures, probe_point, panel_name):
    output_png.parent.mkdir(parents=True, exist_ok=True)
    time_hours = [time_s / 3600.0 for time_s in times]

    fig, ax = plt.subplots(figsize=(8.0, 4.5))
    ax.plot(time_hours, temperatures, linewidth=2)
    ax.set_xlabel("time [h]")
    ax.set_ylabel("temperature [℃]")
    ax.yaxis.set_major_locator(MultipleLocator(1.0))
    ax.set_title(
        f"{panel_name} temperature probe at Femap node {probe_point['femap_node_id']}"
    )
    ax.grid(True)

    note = (
        f"x={probe_point['x_mm']:.1f} mm, "
        f"y={probe_point['y_mm']:.1f} mm, "
        f"z={probe_point['z_mm']:.1f} mm"
    )
    ax.text(
        0.02,
        0.96,
        note,
        transform=ax.transAxes,
        va="top",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8},
    )

    fig.tight_layout()
    fig.savefig(output_png, dpi=220)
    plt.close(fig)


def run_probe_set(args, grid_path, transient_path):
    probe_set = load_probe_set(args.probe_set_file, args.probe_set)
    probes = expand_probe_set(probe_set)
    points_by_panel = {
        panel: parse_grid_points(grid_path, panel)
        for panel in sorted({probe["panel"] for probe in probes})
    }

    selections = []
    for probe in probes:
        point, _ = choose_probe_point(
            points_by_panel[probe["panel"]], target_xyz=probe["target_xyz"]
        )
        selections.append({"probe": probe, "point": point})

    times, histories = read_temperature_histories(
        transient_path, [selection["point"]["femap_node_id"] for selection in selections]
    )
    for selection in selections:
        selection["temperatures"] = histories[selection["point"]["femap_node_id"]]

    output_csv = args.output_dir / f"{args.probe_set}_temperatures.csv"
    summary_csv = args.output_dir / f"{args.probe_set}_nodes.csv"
    write_probe_set_csv(output_csv, times, selections)
    write_probe_set_summary_csv(summary_csv, selections)

    print(f"Probe set file  : {args.probe_set_file}")
    print(f"Probe set       : {args.probe_set}")
    print(f"Probe count     : {len(selections)}")
    print(f"Time steps      : {len(times)}")
    print(f"Output CSV      : {output_csv}")
    print(f"Node summary CSV: {summary_csv}")


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Extract one representative Femap-node temperature history from "
            "Thermal Desktop mapper output."
        )
    )
    parser.add_argument("--mapper-dir", type=Path, default=DEFAULT_MAPPER_DIR)
    parser.add_argument("--panel", default="PANEL_PX")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--probe-set-file", type=Path, default=DEFAULT_PROBE_SET_FILE)
    parser.add_argument("--probe-set")
    parser.add_argument("--target-x-mm", type=float)
    parser.add_argument("--target-y-mm", type=float)
    parser.add_argument("--target-z-mm", type=float)
    return parser.parse_args()


def main():
    args = parse_args()
    grid_path = args.mapper_dir / "outputMapSummaryGridPoints.txt"
    transient_path = args.mapper_dir / "outputTransient.txt"

    if args.probe_set:
        run_probe_set(args, grid_path, transient_path)
        return

    target_values = (args.target_x_mm, args.target_y_mm, args.target_z_mm)
    target_xyz = None if any(value is None for value in target_values) else target_values

    points = parse_grid_points(grid_path, args.panel)
    probe_point, target_xyz = choose_probe_point(points, target_xyz=target_xyz)
    times, temperatures = read_temperature_history(
        transient_path, probe_point["femap_node_id"]
    )

    stem = f"{args.panel.lower()}_temperature_probe"
    output_csv = args.output_dir / f"{stem}.csv"
    output_png = args.output_dir / f"{stem}.png"
    write_temperature_csv(output_csv, times, temperatures, probe_point, target_xyz)
    plot_temperature_history(output_png, times, temperatures, probe_point, args.panel)

    print(f"Mapper dir       : {args.mapper_dir}")
    print(f"Panel            : {args.panel}")
    print(f"Panel point count: {len(points)}")
    print(f"Target xyz [mm]  : {target_xyz[0]:.3f}, {target_xyz[1]:.3f}, {target_xyz[2]:.3f}")
    print(f"Femap node       : {probe_point['femap_node_id']}")
    print(
        "Node xyz [mm]    : "
        f"{probe_point['x_mm']:.3f}, {probe_point['y_mm']:.3f}, {probe_point['z_mm']:.3f}"
    )
    print(f"Mapped entity    : {probe_point['mapped_entity_name']}")
    print(f"Time steps       : {len(times)}")
    print(f"Temperature min  : {min(temperatures):.3f}")
    print(f"Temperature max  : {max(temperatures):.3f}")
    print(f"Output CSV       : {output_csv}")
    print(f"Output PNG       : {output_png}")


if __name__ == "__main__":
    main()
