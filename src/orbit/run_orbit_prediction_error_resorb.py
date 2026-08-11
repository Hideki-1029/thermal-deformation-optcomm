"""Evaluate AUX_RESORB vs AUX_POEORB as a GPS/GNSS-grade orbit error proxy."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from orbit.prediction_error import (  # noqa: E402
    compute_resorb_vs_pod_error,
    summarize_overall,
)
from orbit.run_orbit_prediction_error import (  # noqa: E402
    DEFAULT_GP_HISTORY,
    _load_config,
    _load_ephemeris_records,
    _load_pod_states,
    _resolve_path,
    plot_results,
    plot_results_n_orbits,
    write_summary_csv,
    write_timeseries_csv,
)
from orbit.sentinel1_pod import (  # noqa: E402
    download_s1_orbit_key,
    find_resorb_keys_covering,
    load_sentinel1_eof,
    parse_orbit_key_validity,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path(__file__).with_name("orbit_prediction_error_resorb_config.yaml")


def _load_resorb_states(
    config: dict,
    t_start: datetime,
    t_stop: datetime,
) -> tuple[list, np.ndarray]:
    """
    Download/load RESORB EOF files covering [t_start, t_stop].

    Returns stitched OrbitState list and per-OSV validity-start unix times
    (used to build product-age on the POEORB sample grid).
    """
    pred = config.get("prediction", {})
    local_dir = _resolve_path(pred.get("local_resorb_dir"))
    cache_dir = REPO_ROOT / "data" / "orbit" / "sentinel1" / "resorb"

    keys = find_resorb_keys_covering(t_start, t_stop)
    if not keys:
        raise FileNotFoundError(
            "No AUX_RESORB keys covering "
            f"{t_start.isoformat()} -> {t_stop.isoformat()}. "
            "RESORB on AWS is a rolling archive; the window may have aged out."
        )
    print(f"RESORB keys covering window: {len(keys)}")

    states = []
    validity_by_osv_time: dict[float, float] = {}
    for key in keys:
        window = parse_orbit_key_validity(key)
        if window is None:
            continue
        validity_start_s = window[0].timestamp()
        filename = Path(key).name
        if local_dir is not None:
            path = local_dir / filename
        else:
            path = cache_dir / filename
            if not path.exists():
                print(f"Downloading {key}")
                download_s1_orbit_key(key, path)
        file_states = load_sentinel1_eof(path)
        for state in file_states:
            ts = state.utc.timestamp()
            # Prefer the newest product that still covers this OSV when overlapping.
            prev = validity_by_osv_time.get(ts)
            if prev is None or validity_start_s >= prev:
                validity_by_osv_time[ts] = validity_start_s
        states.extend(file_states)

    if not states:
        raise ValueError("RESORB files downloaded but no OSV states parsed")

    states.sort(key=lambda item: item.utc)
    deduped = {state.utc.timestamp(): state for state in states}
    ordered_times = sorted(deduped)
    ordered_states = [deduped[ts] for ts in ordered_times]
    validity_starts = np.array(
        [validity_by_osv_time[ts] for ts in ordered_times], dtype=float
    )
    print(
        "RESORB coverage: "
        f"{ordered_states[0].utc.isoformat()} -> {ordered_states[-1].utc.isoformat()} "
        f"({len(ordered_states)} OSVs)"
    )
    return ordered_states, validity_starts


def _validity_starts_on_grid(
    resorb_states: list,
    resorb_validity_starts_s: np.ndarray,
    query_times_s: np.ndarray,
) -> np.ndarray:
    """Nearest-OSV validity start for each query time (left searchsorted)."""
    resorb_times = np.array([s.utc.timestamp() for s in resorb_states], dtype=float)
    indices = np.searchsorted(resorb_times, query_times_s, side="right") - 1
    indices = np.clip(indices, 0, len(resorb_times) - 1)
    return resorb_validity_starts_s[indices]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate RESORB vs POEORB orbit error (GPS/GNSS-grade proxy) "
            "and write PAT-compatible timeseries."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = _load_config(args.config)

    # Reuse TLE runner POD loader (needs GP history only for coverage checks).
    if not (REPO_ROOT / "data/orbit/tle/tle_2026.parquet").exists():
        # Soften: allow POD load without GP by injecting a tiny dummy window check skip.
        # Prefer real GP if present (same as TLE baseline).
        pass
    ephemeris_records = _load_ephemeris_records(config)
    pod_states = _load_pod_states(config, ephemeris_records)

    analysis = config.get("analysis", {})
    pred = config.get("prediction", {})
    sample_interval_s = float(analysis.get("sample_interval_s", 60.0))

    # Sample grid matches compute_* internals; precompute for age mapping.
    from orbit.prediction_error import _sample_pod_states

    times_s, _, _, _ = _sample_pod_states(pod_states, sample_interval_s)
    t_start = datetime.fromtimestamp(float(times_s[0]), tz=timezone.utc)
    t_stop = datetime.fromtimestamp(float(times_s[-1]), tz=timezone.utc)

    resorb_states, resorb_validity_osv = _load_resorb_states(config, t_start, t_stop)
    validity_on_grid = _validity_starts_on_grid(
        resorb_states, resorb_validity_osv, times_s
    )

    result = compute_resorb_vs_pod_error(
        pod_states=pod_states,
        resorb_states=resorb_states,
        isl_range_m=float(analysis.get("isl_range_km", 800.0)) * 1000.0,
        sample_interval_s=sample_interval_s,
        max_gap_s=float(pred.get("max_gap_s", 120.0)),
        resorb_validity_starts_s=validity_on_grid,
    )

    output_dir = _resolve_path(config["output"]["output_dir"])
    if output_dir is None:
        raise ValueError("output.output_dir must be set")

    write_timeseries_csv(output_dir / "orbit_prediction_error_timeseries.csv", result)
    summary_rows = summarize_overall(result)
    write_summary_csv(output_dir / "orbit_prediction_error_summary.csv", summary_rows)

    # Reuse TLE plotters; titles still say TLE — overwrite with RESORB-specific plots.
    plot_results(output_dir / "orbit_prediction_error.png", result)
    orbit_period_s = float(analysis.get("orbit_period_s", 6050.0))
    n_orbits = float(analysis.get("plot_n_orbits", 3.0))
    plot_results_n_orbits(
        output_dir / "orbit_prediction_error_3orbits.png",
        result,
        orbit_period_s=orbit_period_s,
        n_orbits=n_orbits,
    )
    _retitle_plots(output_dir, result, orbit_period_s=orbit_period_s, n_orbits=n_orbits)

    print(f"POD window: {pod_states[0].utc.isoformat()} -> {pod_states[-1].utc.isoformat()}")
    print(
        "RESORB product age [days]: "
        f"median={result.tle_age_median_days:.4f}, max={result.tle_age_max_days:.4f}"
    )
    print(f"Samples: {len(result.unix_times_s)}")
    print(f"Position RMS: {np.sqrt(np.mean(result.position_error_norm_m**2)):.4f} m")
    print(
        "ISL angle RMS: "
        f"{np.sqrt(np.mean(result.isl_angle_error_norm_urad**2)):.4f} urad"
    )
    print(f"Output: {output_dir}")


def _retitle_plots(
    output_dir: Path,
    result,
    *,
    orbit_period_s: float,
    n_orbits: float,
) -> None:
    """Rewrite plot titles for RESORB (shared plot helpers are TLE-labeled)."""
    import matplotlib.pyplot as plt

    for path, title, xlabel_hours in [
        (
            output_dir / "orbit_prediction_error.png",
            (
                "Sentinel-1 AUX_RESORB vs AUX_POEORB (GNSS-grade proxy)\n"
                f"RESORB age median={result.tle_age_median_days:.4f} d, "
                f"max={result.tle_age_max_days:.4f} d"
            ),
            True,
        ),
        (
            output_dir / "orbit_prediction_error_3orbits.png",
            (
                "Sentinel-1 RESORB vs POEORB — first "
                f"{n_orbits:g} orbits (Torb={orbit_period_s:.0f} s)\n"
                "Same window as typical thermal/PAT span; dashed = orbit boundaries"
            ),
            False,
        ),
    ]:
        # Regenerated below with correct labels.
        _ = path, title, xlabel_hours

    # Full window
    elapsed = result.elapsed_time_s / 3600.0
    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    axes[0].plot(elapsed, result.position_error_norm_m, label="|delta r|")
    axes[0].plot(elapsed, np.abs(result.position_error_rtn_m[:, 1]), label="|along-track|")
    axes[0].set_ylabel("Position error [m]")
    axes[0].grid(True)
    axes[0].legend()
    axes[1].plot(elapsed, result.isl_angle_error_urad[:, 0], label="ISL angle x")
    axes[1].plot(elapsed, result.isl_angle_error_urad[:, 1], label="ISL angle y")
    axes[1].plot(
        elapsed, result.isl_angle_error_norm_urad, label="ISL angle norm", linewidth=2
    )
    axes[1].set_ylabel("ISL angle error [urad]")
    axes[1].grid(True)
    axes[1].legend()
    axes[2].plot(elapsed, result.tle_age_days, label="RESORB product age")
    axes[2].set_xlabel("Elapsed time [h]")
    axes[2].set_ylabel("RESORB age [days]")
    axes[2].grid(True)
    axes[2].legend()
    fig.suptitle(
        "Sentinel-1 AUX_RESORB vs AUX_POEORB (GNSS-grade proxy)\n"
        f"RESORB age median={result.tle_age_median_days:.4f} d, "
        f"max={result.tle_age_max_days:.4f} d"
    )
    fig.tight_layout()
    fig.savefig(output_dir / "orbit_prediction_error.png", dpi=200)
    plt.close(fig)

    # First N orbits
    t_max_s = float(n_orbits) * float(orbit_period_s)
    mask = result.elapsed_time_s <= t_max_s
    t_min = result.elapsed_time_s[mask] / 60.0
    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    axes[0].plot(t_min, result.position_error_norm_m[mask], label="|delta r|")
    axes[0].plot(
        t_min, np.abs(result.position_error_rtn_m[mask, 1]), label="|along-track|"
    )
    axes[0].set_ylabel("Position error [m]")
    axes[0].grid(True)
    axes[0].legend()
    axes[1].plot(t_min, result.isl_angle_error_urad[mask, 0], label="ISL angle x")
    axes[1].plot(t_min, result.isl_angle_error_urad[mask, 1], label="ISL angle y")
    axes[1].plot(
        t_min,
        result.isl_angle_error_norm_urad[mask],
        label="ISL angle norm",
        linewidth=2,
    )
    axes[1].set_ylabel("ISL angle error [urad]")
    axes[1].grid(True)
    axes[1].legend()
    axes[2].plot(t_min, result.tle_age_days[mask], label="RESORB product age")
    axes[2].set_xlabel("Time [min]")
    axes[2].set_ylabel("RESORB age [days]")
    axes[2].grid(True)
    axes[2].legend()
    for axis in axes:
        for k in range(1, int(np.floor(n_orbits)) + 1):
            axis.axvline(
                k * orbit_period_s / 60.0,
                color="0.7",
                linestyle="--",
                linewidth=0.8,
                zorder=0,
            )
    fig.suptitle(
        "Sentinel-1 RESORB vs POEORB — first "
        f"{n_orbits:g} orbits (Torb={orbit_period_s:.0f} s)\n"
        "Same window as typical thermal/PAT span; dashed = orbit boundaries"
    )
    fig.tight_layout()
    fig.savefig(output_dir / "orbit_prediction_error_3orbits.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    main()
