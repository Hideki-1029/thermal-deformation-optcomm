"""Run PAT coarse acquisition with sunface temperature LOS correction."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np

PAT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PAT_ROOT.parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(PAT_ROOT) not in sys.path:
    sys.path.insert(0, str(PAT_ROOT))

from pat_acquisition.models.sunface_los.dataset import (  # noqa: E402
    DEFAULT_DATASET,
    list_numbered_cases,
    load_case_frame,
    resolve_sunface_case_ids,
)
from pat_acquisition.models.sunface_los.features import SunfaceFeatureConfig  # noqa: E402
from pat_acquisition.models.sunface_los.model import fit_sunface_predictions  # noqa: E402
from pat_acquisition.runners.pat_common import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    DEFAULT_SUNFACE_PAT_OUTPUT_DIR,
    SUNFACE_MODEL_NAMES,
    add_common_pat_arguments,
    build_case_metadata_paths,
    build_nonthermal_config,
    build_scan_config,
    config_path_value,
    config_value,
    evaluate_model_specs,
    generate_nonthermal_error,
    load_yaml_config,
    print_summary_rows,
    resolve_orbit_period_s,
    summary_rows_for_models,
    write_case_bundle,
    write_summary_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "PAT coarse acquisition with sunface temperature LOS correction "
            "(within-case train on first orbit(s))."
        )
    )
    add_common_pat_arguments(parser)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--cases",
        help="Case numbers, e.g. 4,5,6 or 4-6 (0-padding optional; same syntax as TD/Femap).",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        default=None,
        help="Case id to evaluate. Repeatable. Default: all MX/MY/PX/PY cases in dataset.",
    )
    parser.add_argument(
        "--list-cases",
        action="store_true",
        help="List numbered cases in the dataset and exit.",
    )
    parser.add_argument("--orbit-period-s", type=float, default=None)
    parser.add_argument(
        "--train-orbits",
        type=float,
        default=1.0,
        help="Number of orbits used for training from the start of each case.",
    )
    parser.add_argument("--t-ref-c", type=float, default=23.9)
    parser.add_argument("--ridge-lam", type=float, default=1e-3)
    parser.add_argument("--no-opposite-diff", action="store_true")
    parser.add_argument("--no-ref-diff", action="store_true")
    return parser.parse_args()


def run_one_case(
    case_id: str,
    dataset_path: Path,
    output_dir: Path,
    config,
    nonthermal_config,
    feature_config: SunfaceFeatureConfig,
    orbit_period_s: float,
    train_orbits: float,
) -> list[dict[str, object]]:
    case_df = load_case_frame(dataset_path, case_id)
    times_s = case_df["time_s"].to_numpy(dtype=float)
    theta_thermal_true = case_df[
        ["far_field_los_angle_x_urad", "far_field_los_angle_y_urad"]
    ].to_numpy(dtype=float)
    nonthermal_error = generate_nonthermal_error(times_s, case_id, nonthermal_config)

    predictions = fit_sunface_predictions(
        case_df=case_df,
        config=feature_config,
        orbit_period_s=orbit_period_s,
        train_orbits=train_orbits,
    )
    zero_error = np.zeros_like(theta_thermal_true)
    pred_static = np.asarray(predictions["static_bias"], dtype=float)
    pred_sunface = np.asarray(predictions["sunface"], dtype=float)

    model_specs = {
        "static_bias_correction": {
            "theta_hat": pred_static,
            "nonthermal": zero_error,
        },
        "sunface_correction": {
            "theta_hat": pred_sunface,
            "nonthermal": zero_error,
        },
        "sunface_correction_with_nonthermal": {
            "theta_hat": pred_sunface,
            "nonthermal": nonthermal_error,
        },
    }
    model_specs = {name: model_specs[name] for name in SUNFACE_MODEL_NAMES}

    results_by_model = evaluate_model_specs(theta_thermal_true, config, model_specs)
    write_case_bundle(
        output_dir,
        case_id,
        times_s,
        theta_thermal_true,
        nonthermal_error,
        results_by_model,
        lightweight_predictions={
            "static_bias": pred_static,
            "sunface": pred_sunface,
        },
        title=(
            "PAT coarse acquisition with sunface LOS model "
            f"(T_{predictions['sun_face']} -> {predictions['dominant_axis']})"
        ),
    )
    return summary_rows_for_models(
        case_id, theta_thermal_true, zero_error, model_specs, results_by_model
    )


def main() -> None:
    args = parse_args()
    yaml_config = load_yaml_config(args.config)

    if args.list_cases:
        if not args.dataset.exists():
            raise FileNotFoundError(f"Dataset not found: {args.dataset}")
        print(f"Cases in {args.dataset}:")
        for number, case_id, sun_face, supported in list_numbered_cases(args.dataset):
            flag = "supported" if supported else "skipped (not MX/MY/PX/PY)"
            print(f"  {number:>3d}  {case_id}  sun={sun_face}  ({flag})")
        return

    output_dir = config_path_value(
        yaml_config,
        "input",
        "sunface_output_dir",
        args.output_dir,
        DEFAULT_SUNFACE_PAT_OUTPUT_DIR,
    )
    config = build_scan_config(yaml_config, args)
    nonthermal_config = build_nonthermal_config(yaml_config, args)
    case_metadata_paths = build_case_metadata_paths(yaml_config, args)

    feature_config = SunfaceFeatureConfig(
        t_ref_c=args.t_ref_c,
        ridge_lam=args.ridge_lam,
        include_opposite_diff=not args.no_opposite_diff,
        include_ref_diff=not args.no_ref_diff,
    )

    if not args.dataset.exists():
        raise FileNotFoundError(
            f"Dataset not found: {args.dataset}. "
            "Build with scripts/build_lightweight_dataset.py first."
        )

    case_ids, skipped = resolve_sunface_case_ids(
        args.dataset,
        cases=args.cases,
        case_ids=args.case_id,
        default_all_supported=not args.cases and not args.case_id,
    )

    default_period = float(
        config_value(
            yaml_config,
            "lightweight_model",
            "orbit_period_s",
            None,
            6050.0,
        )
    )

    summary_rows: list[dict[str, object]] = []
    for case_id in case_ids:
        orbit_period_s = (
            float(args.orbit_period_s)
            if args.orbit_period_s is not None
            else resolve_orbit_period_s(
                case_id,
                case_metadata_paths,
                default_period_s=default_period,
            )
        )
        summary_rows.extend(
            run_one_case(
                case_id=case_id,
                dataset_path=args.dataset,
                output_dir=output_dir,
                config=config,
                nonthermal_config=nonthermal_config,
                feature_config=feature_config,
                orbit_period_s=orbit_period_s,
                train_orbits=args.train_orbits,
            )
        )

    write_summary_csv(output_dir / "summary.csv", summary_rows)
    n_cases = len(case_ids)
    print(f"Processed {n_cases} cases")
    print(f"Config: {args.config}")
    print(f"Dataset: {args.dataset}")
    print(f"Sunface PAT output: {output_dir}")
    if skipped:
        print(f"Skipped unsupported cases: {', '.join(skipped)}")
    print_summary_rows(summary_rows)


if __name__ == "__main__":
    main()
