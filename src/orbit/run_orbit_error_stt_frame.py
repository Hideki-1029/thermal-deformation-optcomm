"""
Project TLE vs POD position error into STT-frame LOS angles.

Partner is placed along the LCT boresight (body -Z):
- ~nadir  → ground station at altitude range
- ~zenith → computable proxy (flagged unrealistic)
- otherwise → ISL at configured range (default 800 km)

Examples:

```powershell
python src/orbit/run_orbit_error_stt_frame.py --td-orbit-name LTAN06_800km_1213COLD_MY_SUN
python src/orbit/run_orbit_error_stt_frame.py --all-bcase-orbits --update-orbit-catalog
```
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    import yaml
except ImportError as exc:
    raise ImportError(
        "PyYAML is required. Install it with: python -m pip install pyyaml"
    ) from exc

SRC_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from orbit.body_attitude import (  # noqa: E402
    FACE_OUTWARD_BODY,
    build_body_attitude_ecef,
    classify_partner_geometry,
    position_error_to_stt_los_angle_urad,
    rtn_unit_vectors,
)
from orbit.frames import sun_unit_ecef  # noqa: E402
from orbit.run_orbit_prediction_error import (  # noqa: E402
    DEFAULT_CONFIG,
    _load_ephemeris_records,
    _load_pod_states,
    _resolve_path,
)
from orbit.sentinel1_pod import states_to_arrays  # noqa: E402
from thermal_desktop.orbit_catalog_io import write_orbit_catalog_xlsx  # noqa: E402

DEFAULT_ORBIT_NAME = "LTAN06_800km_1213COLD_MY_SUN"
DEFAULT_ORBIT_PERIOD_S = 6050.0
BCASE_CASE_NUMBERS = set(list(range(4, 7)) + list(range(8, 26)))

# PAT default after wiring stt_body into pat_femap_los_config.yaml.
PAT_ORBIT_ERROR_FRAME = "stt_body_lct_boresight_cyclic"
STT_ANALYSIS_FRAME = "stt_body_lct_boresight"


def _load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML config must be a mapping: {path}")
    return data


def _load_orbit_faces(orbit_catalog_xlsx: Path, td_orbit_name: str) -> dict:
    catalog = pd.read_excel(orbit_catalog_xlsx, sheet_name="orbit_catalog")
    matches = catalog[catalog["td_orbit_name"].astype(str) == td_orbit_name]
    if matches.empty:
        raise ValueError(f"{td_orbit_name!r} not found in {orbit_catalog_xlsx}")
    row = matches.iloc[0]
    period = row.get("orbit_period_s")
    return {
        "sun_face": str(row["eff_sun_face"] or row["sun_face"]),
        "velocity_face": str(row["eff_velocity_face"]),
        "nadir_face": str(row["eff_nadir_face"]),
        "orbit_period_s": float(period)
        if pd.notna(period)
        else DEFAULT_ORBIT_PERIOD_S,
    }


def list_bcase_orbit_names(case_matrix_xlsx: Path) -> list[str]:
    case = pd.read_excel(case_matrix_xlsx, sheet_name="case_matrix")
    names: list[str] = []
    for _, row in case.iterrows():
        case_id = str(row.get("case_id", ""))
        prefix = case_id.split("_", 1)[0]
        if not prefix.isdigit():
            continue
        if int(prefix) not in BCASE_CASE_NUMBERS:
            continue
        orbit = row.get("orbit_case")
        if pd.isna(orbit):
            continue
        names.append(str(orbit))
    # stable unique
    return list(dict.fromkeys(names))


def _match_pod_to_timeseries(
    timeseries: pd.DataFrame,
    pod_states: list,
    sample_interval_s: float,
) -> tuple[np.ndarray, np.ndarray, list]:
    times_s, positions, velocities = states_to_arrays(pod_states)
    start = times_s[0]
    sampled_times = np.arange(start, times_s[-1] + 1.0e-9, sample_interval_s)
    indices = np.clip(np.searchsorted(times_s, sampled_times), 0, len(times_s) - 1)
    times_s = times_s[indices]
    positions = positions[indices]
    velocities = velocities[indices]
    pod_sampled = [pod_states[i] for i in indices]

    csv_times = timeseries["unix_time_s"].to_numpy(dtype=float)
    if len(csv_times) != len(times_s):
        raise ValueError(
            f"Timeseries length {len(csv_times)} != sampled POD length {len(times_s)}. "
            "Re-run src/orbit/run_orbit_prediction_error.py first."
        )
    if np.max(np.abs(csv_times - times_s)) > 1.0:
        raise ValueError(
            "Timeseries unix_time_s does not match sampled POD times. "
            "Re-run src/orbit/run_orbit_prediction_error.py first."
        )
    return positions, velocities, pod_sampled


def compute_stt_angles(
    timeseries: pd.DataFrame,
    positions_m: np.ndarray,
    velocities_m_s: np.ndarray,
    pod_states_sampled: list,
    *,
    sun_face: str,
    velocity_face: str,
    nadir_face: str,
    isl_range_m: float,
) -> dict[str, np.ndarray | str | bool]:
    n = len(timeseries)
    stt = np.zeros((n, 2), dtype=float)
    ranges = np.zeros(n, dtype=float)
    legacy = timeseries[["isl_angle_x_urad", "isl_angle_y_urad"]].to_numpy(dtype=float)
    pos_err = timeseries[["pos_err_x_m", "pos_err_y_m", "pos_err_z_m"]].to_numpy(
        dtype=float
    )
    align_sun = np.zeros(n, dtype=float)
    align_vel = np.zeros(n, dtype=float)
    align_nadir = np.zeros(n, dtype=float)
    partner_mode = ""
    realistic = True
    partner_notes = ""

    for index in range(n):
        sun = sun_unit_ecef(pod_states_sampled[index].utc)
        attitude = build_body_attitude_ecef(
            position_ecef_m=positions_m[index],
            velocity_ecef_m_s=velocities_m_s[index],
            sun_ecef_unit=sun,
            sun_face=sun_face,
            velocity_face=velocity_face,
            nadir_face=nadir_face,
        )
        partner = classify_partner_geometry(
            position_ecef_m=positions_m[index],
            velocity_ecef_m_s=velocities_m_s[index],
            attitude=attitude,
            isl_range_m=isl_range_m,
        )
        if index == 0:
            partner_mode = partner.mode
            realistic = partner.realistic_link
            partner_notes = partner.notes
        ranges[index] = partner.range_m
        stt[index] = position_error_to_stt_los_angle_urad(
            pos_err[index], attitude, partner.range_m
        )
        radial, along, _ = rtn_unit_vectors(positions_m[index], velocities_m_s[index])
        R = attitude.R_ecef_from_body
        align_sun[index] = float(np.dot(R @ FACE_OUTWARD_BODY[sun_face], sun))
        align_vel[index] = float(np.dot(R @ FACE_OUTWARD_BODY[velocity_face], along))
        align_nadir[index] = float(
            np.dot(R @ FACE_OUTWARD_BODY[nadir_face], -radial)
        )

    return {
        "stt_x": stt[:, 0],
        "stt_y": stt[:, 1],
        "stt_norm": np.linalg.norm(stt, axis=1),
        "legacy_x": legacy[:, 0],
        "legacy_y": legacy[:, 1],
        "legacy_norm": np.linalg.norm(legacy, axis=1),
        "range_m": ranges,
        "align_sun": align_sun,
        "align_vel": align_vel,
        "align_nadir": align_nadir,
        "partner_mode": partner_mode,
        "realistic_link": realistic,
        "partner_notes": partner_notes,
    }


def write_csv(
    path: Path,
    timeseries: pd.DataFrame,
    angles: dict,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "unix_time_s",
                "elapsed_time_s",
                "utc",
                "tle_age_days",
                "partner_range_m",
                "isl_angle_x_urad_legacy",
                "isl_angle_y_urad_legacy",
                "isl_angle_norm_urad_legacy",
                "stt_los_angle_x_urad",
                "stt_los_angle_y_urad",
                "stt_los_angle_norm_urad",
                "align_sun_dot",
                "align_vel_dot",
                "align_nadir_dot",
            ]
        )
        for i in range(len(timeseries)):
            row = timeseries.iloc[i]
            writer.writerow(
                [
                    row["unix_time_s"],
                    row["elapsed_time_s"],
                    row["utc"],
                    row["tle_age_days"],
                    angles["range_m"][i],
                    angles["legacy_x"][i],
                    angles["legacy_y"][i],
                    angles["legacy_norm"][i],
                    angles["stt_x"][i],
                    angles["stt_y"][i],
                    angles["stt_norm"][i],
                    angles["align_sun"][i],
                    angles["align_vel"][i],
                    angles["align_nadir"][i],
                ]
            )


def plot_stt_comparison(
    path: Path,
    elapsed_time_s: np.ndarray,
    angles: dict,
    *,
    orbit_period_s: float,
    n_orbits: float,
    title: str,
) -> None:
    """Plot STT-frame LOS only (legacy comparison panels retired)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    t_max = n_orbits * orbit_period_s
    mask = elapsed_time_s <= t_max
    t_min = elapsed_time_s[mask] / 60.0

    fig, ax = plt.subplots(1, 1, figsize=(10, 4))
    ax.plot(t_min, angles["stt_x"][mask], label="STT x")
    ax.plot(t_min, angles["stt_y"][mask], label="STT y")
    ax.plot(t_min, angles["stt_norm"][mask], label="STT norm", linewidth=2)
    ax.set_ylabel("STT-frame LOS [urad]")
    ax.set_xlabel("Time [min]")
    ax.grid(True)
    ax.legend(loc="upper right", fontsize=8)

    for k in range(1, int(np.floor(n_orbits)) + 1):
        ax.axvline(
            k * orbit_period_s / 60.0,
            color="0.7",
            linestyle="--",
            linewidth=0.8,
            zorder=0,
        )

    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def run_one_orbit(
    *,
    td_orbit_name: str,
    config: dict,
    timeseries: pd.DataFrame,
    positions: np.ndarray,
    velocities: np.ndarray,
    pod_sampled: list,
    orbit_catalog_xlsx: Path,
    output_dir: Path,
    n_orbits: float,
) -> dict:
    analysis = config.get("analysis", {})
    isl_range_m = float(analysis.get("isl_range_km", 800.0)) * 1000.0
    faces = _load_orbit_faces(orbit_catalog_xlsx, td_orbit_name)
    orbit_period_s = float(faces["orbit_period_s"])

    angles = compute_stt_angles(
        timeseries,
        positions,
        velocities,
        pod_sampled,
        sun_face=faces["sun_face"],
        velocity_face=faces["velocity_face"],
        nadir_face=faces["nadir_face"],
        isl_range_m=isl_range_m,
    )

    csv_path = output_dir / f"orbit_error_stt_{td_orbit_name}.csv"
    png_path = output_dir / f"orbit_error_stt_{td_orbit_name}_3orbits.png"
    write_csv(csv_path, timeseries, angles)
    plot_stt_comparison(
        png_path,
        timeseries["elapsed_time_s"].to_numpy(dtype=float),
        angles,
        orbit_period_s=orbit_period_s,
        n_orbits=n_orbits,
        title=(
            f"TLE orbit error -> STT LOS ({td_orbit_name})\n"
            f"sun={faces['sun_face']}, vel={faces['velocity_face']}, "
            f"nadir={faces['nadir_face']}; partner={angles['partner_mode']}"
        ),
    )

    mask = timeseries["elapsed_time_s"].to_numpy() <= n_orbits * orbit_period_s
    status = "ready" if angles["realistic_link"] else "ready_unrealistic_link"
    summary = {
        "td_orbit_name": td_orbit_name,
        "partner_mode": str(angles["partner_mode"]),
        "partner_notes": str(angles["partner_notes"]),
        "realistic_link": bool(angles["realistic_link"]),
        "stt_status": status,
        "align_sun_mean": float(angles["align_sun"][mask].mean()),
        "align_vel_mean": float(angles["align_vel"][mask].mean()),
        "align_nadir_mean": float(angles["align_nadir"][mask].mean()),
        "stt_norm_mean": float(angles["stt_norm"][mask].mean()),
        "legacy_norm_mean": float(angles["legacy_norm"][mask].mean()),
        "csv": str(csv_path),
        "png": str(png_path),
    }
    print(
        f"[{td_orbit_name}] partner={summary['partner_mode']} "
        f"status={status} "
        f"align(sun/vel/nadir)="
        f"{summary['align_sun_mean']:.3f}/"
        f"{summary['align_vel_mean']:.3f}/"
        f"{summary['align_nadir_mean']:.3f} "
        f"STT norm mean={summary['stt_norm_mean']:.1f}"
    )
    print(f"  {angles['partner_notes']}")
    print(f"  PNG: {png_path}")
    return summary


def update_orbit_catalog_columns(
    orbit_catalog_xlsx: Path,
    summaries: list[dict],
    *,
    bcase_orbit_names: set[str],
) -> None:
    catalog = pd.read_excel(orbit_catalog_xlsx, sheet_name="orbit_catalog")
    try:
        archive = pd.read_excel(orbit_catalog_xlsx, sheet_name="orbit_catalog_archive")
    except Exception:
        archive = None

    by_name = {s["td_orbit_name"]: s for s in summaries}
    for col, default in [
        ("pat_orbit_error_frame", PAT_ORBIT_ERROR_FRAME),
        ("orbit_error_stt_frame", ""),
        ("orbit_error_partner_mode", ""),
        ("orbit_error_stt_status", "n/a"),
        ("orbit_error_stt_notes", ""),
    ]:
        if col not in catalog.columns:
            catalog[col] = default

    for i, row in catalog.iterrows():
        name = str(row["td_orbit_name"])
        # PAT injection is still legacy for every orbit until wired.
        catalog.at[i, "pat_orbit_error_frame"] = PAT_ORBIT_ERROR_FRAME
        if name in by_name:
            s = by_name[name]
            catalog.at[i, "orbit_error_stt_frame"] = STT_ANALYSIS_FRAME
            catalog.at[i, "orbit_error_partner_mode"] = s["partner_mode"]
            catalog.at[i, "orbit_error_stt_status"] = s["stt_status"]
            catalog.at[i, "orbit_error_stt_notes"] = s["partner_notes"]
        elif name in bcase_orbit_names:
            catalog.at[i, "orbit_error_stt_status"] = "missing"
            catalog.at[i, "orbit_error_stt_notes"] = "bcase orbit but STT run missing"
        else:
            catalog.at[i, "orbit_error_stt_frame"] = ""
            catalog.at[i, "orbit_error_partner_mode"] = ""
            catalog.at[i, "orbit_error_stt_status"] = "n/a"
            catalog.at[i, "orbit_error_stt_notes"] = "not in bcase set / not run"

    write_orbit_catalog_xlsx(orbit_catalog_xlsx, catalog, archive=archive)
    print(f"Updated orbit catalog columns in {orbit_catalog_xlsx}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Project orbit prediction error into STT-frame LOS angles."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--td-orbit-name", default=None)
    parser.add_argument(
        "--all-bcase-orbits",
        action="store_true",
        help="Run all unique orbit_case values used by sunface_deltaT_bcase cases 4-6,8-25",
    )
    parser.add_argument(
        "--update-orbit-catalog",
        action="store_true",
        help="Write pat/STT orbit-error method columns into orbit_catalog.xlsx",
    )
    parser.add_argument(
        "--orbit-catalog-xlsx",
        type=Path,
        default=REPO_ROOT / "cases" / "orbit_catalog.xlsx",
    )
    parser.add_argument(
        "--case-matrix-xlsx",
        type=Path,
        default=REPO_ROOT / "cases" / "case_matrix.xlsx",
    )
    parser.add_argument(
        "--timeseries-csv",
        type=Path,
        default=REPO_ROOT
        / "results/orbit/sentinel1_tle_vs_pod/orbit_prediction_error_timeseries.csv",
    )
    parser.add_argument("--n-orbits", type=float, default=3.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.all_bcase_orbits and not args.td_orbit_name:
        args.td_orbit_name = DEFAULT_ORBIT_NAME

    config = _load_config(args.config)
    analysis = config.get("analysis", {})
    sample_interval_s = float(analysis.get("sample_interval_s", 60.0))

    timeseries_path = (
        args.timeseries_csv
        if args.timeseries_csv.is_absolute()
        else REPO_ROOT / args.timeseries_csv
    )
    if not timeseries_path.exists():
        raise FileNotFoundError(
            f"Missing {timeseries_path}. Run src/orbit/run_orbit_prediction_error.py first."
        )
    timeseries = pd.read_csv(timeseries_path)

    print("Loading POD / GP (for attitude only; position errors from CSV)...")
    ephemeris_records = _load_ephemeris_records(config)
    pod_states = _load_pod_states(config, ephemeris_records)
    positions, velocities, pod_sampled = _match_pod_to_timeseries(
        timeseries, pod_states, sample_interval_s
    )

    output_dir = _resolve_path(config["output"]["output_dir"])
    assert output_dir is not None

    if args.all_bcase_orbits:
        orbit_names = list_bcase_orbit_names(args.case_matrix_xlsx)
    else:
        orbit_names = [args.td_orbit_name]

    print(f"Orbits to run ({len(orbit_names)}): {orbit_names}")
    summaries: list[dict] = []
    for name in orbit_names:
        summaries.append(
            run_one_orbit(
                td_orbit_name=name,
                config=config,
                timeseries=timeseries,
                positions=positions,
                velocities=velocities,
                pod_sampled=pod_sampled,
                orbit_catalog_xlsx=args.orbit_catalog_xlsx,
                output_dir=output_dir,
                n_orbits=args.n_orbits,
            )
        )

    summary_csv = output_dir / "orbit_error_stt_summary.csv"
    pd.DataFrame(summaries).to_csv(summary_csv, index=False, encoding="utf-8-sig")
    print(f"Summary: {summary_csv}")

    unrealistic = [s for s in summaries if not s["realistic_link"]]
    if unrealistic:
        print("Unrealistic link geometry (still computed):")
        for s in unrealistic:
            print(f"  - {s['td_orbit_name']}: {s['partner_notes']}")

    if args.update_orbit_catalog:
        update_orbit_catalog_columns(
            args.orbit_catalog_xlsx,
            summaries,
            bcase_orbit_names=set(list_bcase_orbit_names(args.case_matrix_xlsx)),
        )


if __name__ == "__main__":
    main()
