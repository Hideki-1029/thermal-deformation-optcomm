"""PAT comparison: direct Fourier(total) vs hierarchical FF -> residual Fourier.

Reproduces the 260813_post_ff_residual_fourier.md section 4 comparison
under the beacon-class scan geometry (260816_coarse_acquisition_scan_geometry.md).

Arms (all with nonthermal error, causal, order=2):
  - ff_only:        theta_hat = b_case + a*DeltaT
  - resid_fourier:  theta_hat = FF + Fourier(r), r = total - FF
  - fourier_total:  theta_hat = Fourier(thermal + nonthermal)  (no thermal FF)

Level-2 b is leave-one-case-out, fitted on the full main case set
(default 4-6,8-21) so numbers are consistent with the main PAT run.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

PAT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PAT_ROOT.parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(PAT_ROOT) not in sys.path:
    sys.path.insert(0, str(PAT_ROOT))

from pat_acquisition.models.sunface_deltaT_bcase_los.adaptive import (  # noqa: E402
    AdaptiveConfig,
    AdaptiveTables,
    mode_key_from_case,
    simulate_adaptive_theta_hat,
)
from pat_acquisition.models.sunface_deltaT_bcase_los.dataset import (  # noqa: E402
    DEFAULT_DATASET,
    load_case_frame,
    resolve_sunface_case_ids,
)
from pat_acquisition.models.sunface_deltaT_bcase_los.features import (  # noqa: E402
    parse_heat_faces,
)
from pat_acquisition.models.sunface_deltaT_bcase_los.model import (  # noqa: E402
    BCaseConfig,
    predict_bcase_xy,
    run_bcase_pipeline,
)
from pat_acquisition.models.sunface_deltaT_bcase_los.residual_fourier import (  # noqa: E402
    ResidualFourierConfig,
    simulate_residual_fourier_theta_hat,
)
from pat_acquisition.runners.pat_common import (  # noqa: E402
    REPO_ROOT,
    add_common_pat_arguments,
    build_case_metadata_paths,
    build_nonthermal_config,
    build_scan_config,
    evaluate_model_specs,
    generate_nonthermal_error,
    load_yaml_config,
    resolve_orbit_period_s,
    summarize_acquisition,
)

DEFAULT_OUTPUT_DIR = (
    REPO_ROOT
    / "results"
    / "pat_acquisition"
    / "sunface_deltaT_bcase_los_model"
    / "pat_direct_vs_residual_fourier"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_pat_arguments(parser)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--fit-cases",
        default="4-6,8-21",
        help="Case set for Level-2 LOO fit (main PAT set).",
    )
    parser.add_argument(
        "--eval-cases",
        default="13,16",
        help="Cases to evaluate the direct-Fourier comparison on.",
    )
    parser.add_argument("--train-orbits", type=float, default=1.0)
    parser.add_argument("--ridge-lam", type=float, default=1e-3)
    parser.add_argument("--level2-ridge-lam", type=float, default=0.0)
    parser.add_argument("--heat-faces", default="MY,PY")
    parser.add_argument("--fourier-order", type=int, default=2)
    parser.add_argument("--fourier-ridge-lam", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def orbit_split_stats(
    result: np.ndarray, orbit_idx: np.ndarray
) -> dict[str, float]:
    """Overall + orbit-0 / orbit>=1 acquisition-time stats."""
    out = summarize_acquisition(result)
    tacq = result[:, 1]
    for label, mask in (
        ("orbit0", orbit_idx == 0),
        ("orbit1p", orbit_idx >= 1),
    ):
        if np.count_nonzero(mask):
            out[f"mean_tacq_{label}_s"] = float(np.nanmean(tacq[mask]))
            out[f"success_rate_{label}"] = float(np.mean(result[mask, 0]))
        else:
            out[f"mean_tacq_{label}_s"] = float("nan")
            out[f"success_rate_{label}"] = float("nan")
    return out


def main() -> None:
    args = parse_args()
    yaml_config = load_yaml_config(args.config)
    scan_config = build_scan_config(yaml_config, args)
    nonthermal_config = build_nonthermal_config(yaml_config, args)
    case_metadata_paths = build_case_metadata_paths(yaml_config, args)

    fit_case_ids, _ = resolve_sunface_case_ids(args.dataset, cases=args.fit_cases)
    eval_case_ids, _ = resolve_sunface_case_ids(args.dataset, cases=args.eval_cases)

    default_period = 6050.0
    fit_period = resolve_orbit_period_s(
        fit_case_ids[0], case_metadata_paths, default_period_s=default_period
    )
    bcase_config = BCaseConfig(
        ridge_lam=args.ridge_lam,
        heat_faces=parse_heat_faces(args.heat_faces),
        orbit_period_s=fit_period,
        train_orbits=args.train_orbits,
        level2_ridge_lam=args.level2_ridge_lam,
    )
    print(f"Fitting Level-2 bcase on {len(fit_case_ids)} cases (LOO)...")
    pipeline = run_bcase_pipeline(
        dataset_path=args.dataset, case_ids=fit_case_ids, config=bcase_config
    )
    case_lookup = pipeline["case_table"].set_index("case_id")
    a_shared: dict[str, float] = pipeline["a_shared"]

    rows: list[dict[str, object]] = []
    for case_id in eval_case_ids:
        case_df = load_case_frame(args.dataset, case_id)
        times_s = case_df["time_s"].to_numpy(dtype=float)
        theta_thermal_true = case_df[
            ["far_field_los_angle_x_urad", "far_field_los_angle_y_urad"]
        ].to_numpy(dtype=float)
        nonthermal_error = generate_nonthermal_error(
            times_s, case_id, nonthermal_config
        )
        orbit_period_s = resolve_orbit_period_s(
            case_id, case_metadata_paths, default_period_s=default_period
        )

        row = case_lookup.loc[case_id]
        sun_face = str(row["sun_face"])
        b_loo = float(row["b_pred_loo_urad"])
        b_urad = (
            b_loo if np.isfinite(b_loo) else float(row["b_pred_insample_urad"])
        )
        pred_bcase = np.asarray(
            predict_bcase_xy(
                case_df,
                b_urad=b_urad,
                a_urad_per_c=float(a_shared[sun_face]),
                config=BCaseConfig(
                    ridge_lam=args.ridge_lam,
                    heat_faces=parse_heat_faces(args.heat_faces),
                    orbit_period_s=orbit_period_s,
                    train_orbits=args.train_orbits,
                    level2_ridge_lam=args.level2_ridge_lam,
                ),
            )["bcase"],
            dtype=float,
        )

        fourier_cfg = ResidualFourierConfig(
            orbit_period_s=orbit_period_s,
            fourier_order=args.fourier_order,
            ridge_lam=args.fourier_ridge_lam,
            fit_mode="causal",
            seed=args.seed,
        )
        theta_hat_resid = np.asarray(
            simulate_residual_fourier_theta_hat(
                pred_bcase=pred_bcase,
                theta_thermal_true=theta_thermal_true,
                nonthermal_error=nonthermal_error,
                times_s=times_s,
                config=fourier_cfg,
            )["theta_hat"],
            dtype=float,
        )
        theta_hat_total = np.asarray(
            simulate_residual_fourier_theta_hat(
                pred_bcase=np.zeros_like(pred_bcase),
                theta_thermal_true=theta_thermal_true,
                nonthermal_error=nonthermal_error,
                times_s=times_s,
                config=fourier_cfg,
            )["theta_hat"],
            dtype=float,
        )
        theta_hat_db = np.asarray(
            simulate_adaptive_theta_hat(
                pred_bcase=pred_bcase,
                theta_thermal_true=theta_thermal_true,
                nonthermal_error=nonthermal_error,
                times_s=times_s,
                orbit_period_s=orbit_period_s,
                mode=mode_key_from_case(case_df, sun_face=sun_face),
                tables=AdaptiveTables(),
                config=AdaptiveConfig(
                    gamma_fast=0.4, enable_slow_b=False, seed=args.seed
                ),
            )["theta_hat"],
            dtype=float,
        )

        model_specs = {
            "ff_only": {"theta_hat": pred_bcase, "nonthermal": nonthermal_error},
            "ff_delta_b": {
                "theta_hat": theta_hat_db,
                "nonthermal": nonthermal_error,
            },
            "resid_fourier": {
                "theta_hat": theta_hat_resid,
                "nonthermal": nonthermal_error,
            },
            "fourier_total": {
                "theta_hat": theta_hat_total,
                "nonthermal": nonthermal_error,
            },
        }
        results_by_model = evaluate_model_specs(
            theta_thermal_true, scan_config, model_specs
        )

        orbit_idx = np.floor(times_s / orbit_period_s).astype(int)
        for model_name, result in results_by_model.items():
            stats = orbit_split_stats(result, orbit_idx)
            stats.update(
                {
                    "case_id": case_id,
                    "model": model_name,
                    "sun_face": sun_face,
                    "orbit_period_s": orbit_period_s,
                }
            )
            rows.append(stats)

    out_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = pd.DataFrame(rows)
    summary.to_csv(out_dir / "summary.csv", index=False, encoding="utf-8-sig")

    print(f"\nScan: range=±{scan_config.max_range_urad} urad, "
          f"step={scan_config.step_urad} urad, "
          f"detect={scan_config.detect_radius_urad} urad, "
          f"dwell={scan_config.dwell_time_s} s")
    print(f"Output: {out_dir}\n")
    for case_id in eval_case_ids:
        print(f"== {case_id} ==")
        for model_name in (
            "ff_only",
            "ff_delta_b",
            "fourier_total",
            "resid_fourier",
        ):
            r = next(
                x for x in rows if x["case_id"] == case_id and x["model"] == model_name
            )
            print(
                f"  {model_name:<15s} all={r['mean_acquisition_time_s']:6.2f}s "
                f"(success {r['success_rate'] * 100:5.1f}%) | "
                f"orbit0={r['mean_tacq_orbit0_s']:6.2f}s | "
                f"orbit1+={r['mean_tacq_orbit1p_s']:6.2f}s "
                f"(success {r['success_rate_orbit1p'] * 100:5.1f}%)"
            )


if __name__ == "__main__":
    main()
