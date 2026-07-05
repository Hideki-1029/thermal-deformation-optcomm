from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

try:
    import yaml
except ImportError as exc:
    raise ImportError(
        "PyYAML is required. Install it with: python -m pip install pyyaml"
    ) from exc

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from orbit.gp_history import load_gp_history_parquet
from orbit.prediction_error import (
    OrbitPredictionErrorResult,
    compute_tle_vs_pod_error,
    summarize_by_tle_age,
)
from orbit.sentinel1_pod import (
    download_s1_orbit_key,
    find_poeorb_key_for_validity_start,
    find_poeorb_key_nearest_to_time,
    load_sentinel1_poeorb,
)
from orbit.tle_sources import fetch_celestrak_tle, load_tle_file

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path(__file__).with_name("orbit_prediction_error_config.yaml")
DEFAULT_GP_HISTORY = REPO_ROOT / "data" / "orbit" / "tle" / "tle_2026.parquet"


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML config must be a mapping: {path}")
    return data


def _resolve_path(value: str | None, default: Path | None = None) -> Path | None:
    if value in (None, "", "null"):
        return default
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _load_ephemeris_records(config: dict) -> list:
    satellite = config["satellite"]
    norad_cat_id = int(satellite["norad_cat_id"])

    gp_path = _resolve_path(
        satellite.get("gp_history_parquet"),
        default=DEFAULT_GP_HISTORY if DEFAULT_GP_HISTORY.exists() else None,
    )
    if gp_path is not None and gp_path.exists():
        print(f"Loading GP history: {gp_path}")
        return load_gp_history_parquet(gp_path, norad_cat_id)

    tle_path = _resolve_path(satellite.get("tle_history_path"))
    if tle_path is not None:
        print(f"Loading TLE history file: {tle_path}")
        return load_tle_file(tle_path)

    print(
        "WARNING: GP history not found; falling back to a single current TLE from CelesTrak. "
        "Forward comparison requires GP/TLE history covering the POD window."
    )
    return [fetch_celestrak_tle(norad_cat_id)]


def _load_pod_states(config: dict, ephemeris_records: list) -> list:
    pod_config = config["pod"]
    local_path = _resolve_path(pod_config.get("local_poeorb_path"))
    cache_dir = REPO_ROOT / "data" / "orbit" / "sentinel1"

    paths: list[Path] = []
    if local_path is not None:
        paths.append(local_path)
    else:
        validity_start_raw = pod_config.get("validity_start_utc")
        if validity_start_raw in (None, "", "null"):
            anchor_time = ephemeris_records[-1].epoch_utc
            key = find_poeorb_key_nearest_to_time(anchor_time)
            if key is None:
                raise FileNotFoundError(
                    f"No POEORB file found near GP history end {anchor_time.isoformat()}"
                )
            print(f"Auto-selected POEORB near GP history: {key}")
            output_path = cache_dir / Path(key).name
            if not output_path.exists():
                print(f"Downloading {key}")
                download_s1_orbit_key(key, output_path)
            paths.append(output_path)
        else:
            validity_starts = [_parse_utc(validity_start_raw)]
            validity_starts.extend(
                _parse_utc(value)
                for value in pod_config.get("extra_validity_starts_utc") or []
            )
            for validity_start in validity_starts:
                key = find_poeorb_key_for_validity_start(validity_start)
                if key is None:
                    raise FileNotFoundError(
                        f"No POEORB file found near {validity_start.isoformat()}"
                    )
                output_path = cache_dir / Path(key).name
                if not output_path.exists():
                    print(f"Downloading {key}")
                    download_s1_orbit_key(key, output_path)
                paths.append(output_path)

    states = []
    for path in paths:
        states.extend(load_sentinel1_poeorb(path))

    states.sort(key=lambda item: item.utc)
    deduped = {state.utc.timestamp(): state for state in states}
    pod_states = [deduped[key] for key in sorted(deduped)]

    earliest_gp = min(record.epoch_utc for record in ephemeris_records)
    latest_gp = max(record.epoch_utc for record in ephemeris_records)
    if pod_states[0].utc < earliest_gp:
        raise ValueError(
            "POD window starts before GP/TLE history coverage. "
            f"POD start={pod_states[0].utc.isoformat()}, earliest GP={earliest_gp.isoformat()}"
        )
    if pod_states[-1].utc > latest_gp + (pod_states[-1].utc - pod_states[0].utc):
        print(
            "WARNING: POD window extends beyond latest GP epoch; "
            "only samples with epoch<=evaluation time are valid."
        )
    return pod_states


def write_timeseries_csv(path: Path, result: OrbitPredictionErrorResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "unix_time_s",
                "elapsed_time_s",
                "utc",
                "tle_age_days",
                "pos_err_x_m",
                "pos_err_y_m",
                "pos_err_z_m",
                "pos_err_norm_m",
                "pos_err_radial_m",
                "pos_err_along_track_m",
                "pos_err_cross_track_m",
                "isl_angle_x_urad",
                "isl_angle_y_urad",
                "isl_angle_norm_urad",
            ]
        )
        for index, unix_time in enumerate(result.unix_times_s):
            utc = datetime.fromtimestamp(float(unix_time), tz=timezone.utc).isoformat()
            writer.writerow(
                [
                    unix_time,
                    result.elapsed_time_s[index],
                    utc,
                    result.tle_age_days[index],
                    *result.position_error_ecef_m[index],
                    result.position_error_norm_m[index],
                    *result.position_error_rtn_m[index],
                    *result.isl_angle_error_urad[index],
                    result.isl_angle_error_norm_urad[index],
                ]
            )


def write_summary_csv(path: Path, rows: list[dict[str, float]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot_results(path: Path, result: OrbitPredictionErrorResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    elapsed_hours = result.elapsed_time_s / 3600.0

    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)

    axes[0].plot(elapsed_hours, result.position_error_norm_m, label="|delta r|")
    axes[0].plot(
        elapsed_hours,
        np.abs(result.position_error_rtn_m[:, 1]),
        label="|along-track|",
    )
    axes[0].set_ylabel("Position error [m]")
    axes[0].grid(True)
    axes[0].legend()

    axes[1].plot(elapsed_hours, result.isl_angle_error_urad[:, 0], label="ISL angle x")
    axes[1].plot(elapsed_hours, result.isl_angle_error_urad[:, 1], label="ISL angle y")
    axes[1].plot(
        elapsed_hours,
        result.isl_angle_error_norm_urad,
        label="ISL angle norm",
        linewidth=2,
    )
    axes[1].set_ylabel("ISL angle error [urad]")
    axes[1].grid(True)
    axes[1].legend()

    axes[2].plot(elapsed_hours, result.tle_age_days, label="TLE age")
    axes[2].set_xlabel("Elapsed time [h]")
    axes[2].set_ylabel("TLE age [days]")
    axes[2].grid(True)
    axes[2].legend()

    fig.suptitle(
        "Sentinel-1 TLE-only forward propagation vs AUX_POEORB\n"
        f"TLE age median={result.tle_age_median_days:.3f} d, "
        f"max={result.tle_age_max_days:.3f} d"
    )
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate TLE-only orbit prediction error using forward SGP4 "
            "against Sentinel-1 AUX_POEORB truth."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = _load_config(args.config)

    ephemeris_records = _load_ephemeris_records(config)
    pod_states = _load_pod_states(config, ephemeris_records)
    analysis = config.get("analysis", {})
    result = compute_tle_vs_pod_error(
        pod_states=pod_states,
        ephemeris_records=ephemeris_records,
        isl_range_m=float(analysis.get("isl_range_km", 800.0)) * 1000.0,
        sample_interval_s=float(analysis.get("sample_interval_s", 60.0)),
    )

    output_dir = _resolve_path(config["output"]["output_dir"])
    if output_dir is None:
        raise ValueError("output.output_dir must be set")

    write_timeseries_csv(output_dir / "orbit_prediction_error_timeseries.csv", result)
    summary_rows = summarize_by_tle_age(result)
    write_summary_csv(output_dir / "orbit_prediction_error_summary.csv", summary_rows)
    plot_results(output_dir / "orbit_prediction_error.png", result)

    print(f"POD window: {pod_states[0].utc.isoformat()} -> {pod_states[-1].utc.isoformat()}")
    print(f"TLE age [days]: median={result.tle_age_median_days:.3f}, max={result.tle_age_max_days:.3f}")
    print(f"POD samples: {len(result.unix_times_s)}")
    print(f"Position RMS: {np.sqrt(np.mean(result.position_error_norm_m**2)):.1f} m")
    print(
        "ISL angle RMS: "
        f"{np.sqrt(np.mean(result.isl_angle_error_norm_urad**2)):.1f} urad"
    )
    print(f"Output: {output_dir}")
    for row in summary_rows:
        print(
            f"  age <= {row['max_tle_age_days']:.1f} d: "
            f"pos RMS {row['position_rms_m']:.1f} m, "
            f"ISL RMS {row['isl_angle_rms_urad']:.1f} urad"
        )


if __name__ == "__main__":
    main()
