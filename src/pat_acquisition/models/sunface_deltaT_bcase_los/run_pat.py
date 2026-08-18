"""Run PAT coarse acquisition with hierarchical sunface ΔT (bcase) correction."""

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

from pat_acquisition.models.sunface_deltaT_bcase_los.dataset import (  # noqa: E402
    DEFAULT_DATASET,
    DEFAULT_OUTPUT_ROOT,
    list_numbered_cases,
    load_case_frame,
    resolve_sunface_case_ids,
)
from pat_acquisition.models.sunface_deltaT_bcase_los.features import (  # noqa: E402
    parse_heat_faces,
)
from pat_acquisition.models.sunface_deltaT_bcase_los.model import (  # noqa: E402
    BCaseConfig,
    predict_bcase_xy,
    resolve_operational_params,
    run_bcase_pipeline,
)
from pat_acquisition.models.sunface_deltaT_bcase_los.plots import (  # noqa: E402
    plot_pat_summary,
)
from pat_acquisition.runners.pat_common import (  # noqa: E402
    BCASE_MODEL_NAMES,
    BCASE_PLOT_LABELS,
    DEFAULT_BCASE_PAT_OUTPUT_DIR,
    DEFAULT_CONFIG_PATH,
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
            "PAT coarse acquisition with hierarchical sunface ΔT correction: "
            "LOS ≈ b_case + a_shared(sun)·ΔT (Level-2 b from sun face + heat flags)."
        )
    )
    add_common_pat_arguments(parser)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--cases",
        help="Case numbers, e.g. 4,5,6 or 4-6,8-21 (0-padding optional).",
    )
    parser.add_argument(
        "--case",
        default=None,
        help="Single case number (4 or 04). Alternative to --case-id.",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        default=None,
        help="Full case id. Repeatable.",
    )
    parser.add_argument(
        "--list-cases",
        action="store_true",
        help="List numbered cases in the dataset and exit.",
    )
    parser.add_argument("--orbit-period-s", type=float, default=None)
    parser.add_argument("--train-orbits", type=float, default=1.0)
    parser.add_argument("--ridge-lam", type=float, default=1e-3)
    parser.add_argument("--level2-ridge-lam", type=float, default=0.0)
    parser.add_argument(
        "--heat-faces",
        default="MY,PY",
        help="Sun faces where I_prop/I_pcdu apply (comma list or 'all').",
    )
    parser.add_argument(
        "--b-mode",
        choices=("loo", "insample"),
        default="loo",
        help="Use leave-one-case-out or in-sample Level-2 b for PAT (default: loo).",
    )
    return parser.parse_args()


def run_one_case(
    case_id: str,
    case_df: pd.DataFrame,
    *,
    row: pd.Series,
    a_shared: dict[str, float],
    output_dir: Path,
    config,
    nonthermal_config,
    bcase_config: BCaseConfig,
    b_mode: str,
) -> list[dict[str, object]]:
    times_s = case_df["time_s"].to_numpy(dtype=float)
    theta_thermal_true = case_df[
        ["far_field_los_angle_x_urad", "far_field_los_angle_y_urad"]
    ].to_numpy(dtype=float)
    nonthermal_error = generate_nonthermal_error(times_s, case_id, nonthermal_config)
    zero_error = np.zeros_like(theta_thermal_true)

    sun_face = str(row["sun_face"])
    b_urad, b_nd_urad, a_urad = resolve_operational_params(row, a_shared, b_mode)
    predictions = predict_bcase_xy(
        case_df,
        b_urad=b_urad,
        a_urad_per_c=a_urad,
        b_nd_urad=b_nd_urad,
        config=bcase_config,
    )
    pred_bcase = np.asarray(predictions["bcase"], dtype=float)

    model_specs = {
        "no_correction": {
            "theta_hat": zero_error,
            "nonthermal": zero_error,
        },
        "bcase_correction": {
            "theta_hat": pred_bcase,
            "nonthermal": zero_error,
        },
        "thermal_truth_correction": {
            "theta_hat": theta_thermal_true.copy(),
            "nonthermal": zero_error,
        },
        "thermal_plus_nonthermal_no_correction": {
            "theta_hat": zero_error,
            "nonthermal": nonthermal_error,
        },
        "bcase_correction_with_nonthermal": {
            "theta_hat": pred_bcase,
            "nonthermal": nonthermal_error,
        },
    }
    model_specs = {name: model_specs[name] for name in BCASE_MODEL_NAMES}

    results_by_model = evaluate_model_specs(theta_thermal_true, config, model_specs)
    write_case_bundle(
        output_dir,
        case_id,
        times_s,
        theta_thermal_true,
        nonthermal_error,
        results_by_model,
        lightweight_predictions={
            "bcase": pred_bcase,
        },
        title=(
            f"PAT with hierarchical bcase "
            f"(sun={sun_face}, b_mode={b_mode}, "
            f"b={b_urad:.2g}, b_nd={b_nd_urad:.2g}, a={a_urad:.2g})"
        ),
        plot_labels=BCASE_PLOT_LABELS,
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
        "bcase_output_dir",
        args.output_dir,
        DEFAULT_BCASE_PAT_OUTPUT_DIR,
    )
    config = build_scan_config(yaml_config, args)
    nonthermal_config = build_nonthermal_config(yaml_config, args)
    case_metadata_paths = build_case_metadata_paths(yaml_config, args)

    if not args.dataset.exists():
        raise FileNotFoundError(
            f"Dataset not found: {args.dataset}. "
            "Build with scripts/build_lightweight_dataset.py first."
        )

    case_ids, skipped = resolve_sunface_case_ids(
        args.dataset,
        cases=args.cases,
        case=args.case,
        case_ids=args.case_id,
        default_all_supported=not args.cases and not args.case and not args.case_id,
    )
    heat_faces = parse_heat_faces(args.heat_faces)

    default_period = float(
        config_value(
            yaml_config,
            "lightweight_model",
            "orbit_period_s",
            None,
            6050.0,
        )
    )
    # Prefer CLI / first case period for the Level-2 fit orbit split.
    if args.orbit_period_s is not None:
        fit_orbit_period_s = float(args.orbit_period_s)
    else:
        fit_orbit_period_s = resolve_orbit_period_s(
            case_ids[0],
            case_metadata_paths,
            default_period_s=default_period,
        )

    bcase_config = BCaseConfig(
        ridge_lam=args.ridge_lam,
        heat_faces=heat_faces,
        orbit_period_s=fit_orbit_period_s,
        train_orbits=args.train_orbits,
        level2_ridge_lam=args.level2_ridge_lam,
    )

    print(
        f"Fitting Level-2 bcase on {len(case_ids)} cases "
        f"(heat faces={', '.join(heat_faces)}, b_mode={args.b_mode})..."
    )
    pipeline = run_bcase_pipeline(
        dataset_path=args.dataset,
        case_ids=case_ids,
        config=bcase_config,
    )
    case_table: pd.DataFrame = pipeline["case_table"]
    a_shared: dict[str, float] = pipeline["a_shared"]
    case_lookup = case_table.set_index("case_id")

    # Persist the fit used for PAT next to PAT outputs.
    fit_dir = Path(output_dir)
    fit_dir.mkdir(parents=True, exist_ok=True)
    case_table.to_csv(fit_dir / "bcase_pat_case_table.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [{"sun_face": k, "a_shared_urad_per_c": v} for k, v in sorted(a_shared.items())]
    ).to_csv(fit_dir / "bcase_pat_a_shared.csv", index=False, encoding="utf-8-sig")
    pipeline["level2_coef_table"].to_csv(
        fit_dir / "bcase_pat_level2_coefficients.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pipeline["level2_nd_coef_table"].to_csv(
        fit_dir / "bcase_pat_level2_nd_coefficients.csv",
        index=False,
        encoding="utf-8-sig",
    )

    summary_rows: list[dict[str, object]] = []
    for case_id in case_ids:
        case_df = load_case_frame(args.dataset, case_id)
        # Per-case orbit period for train split consistency with metadata.
        orbit_period_s = (
            float(args.orbit_period_s)
            if args.orbit_period_s is not None
            else resolve_orbit_period_s(
                case_id,
                case_metadata_paths,
                default_period_s=default_period,
            )
        )
        case_config = BCaseConfig(
            ridge_lam=bcase_config.ridge_lam,
            heat_faces=bcase_config.heat_faces,
            orbit_period_s=orbit_period_s,
            train_orbits=bcase_config.train_orbits,
            level2_ridge_lam=bcase_config.level2_ridge_lam,
        )
        summary_rows.extend(
            run_one_case(
                case_id=case_id,
                case_df=case_df,
                row=case_lookup.loc[case_id],
                a_shared=a_shared,
                output_dir=output_dir,
                config=config,
                nonthermal_config=nonthermal_config,
                bcase_config=case_config,
                b_mode=args.b_mode,
            )
        )

    summary_path = Path(output_dir) / "summary.csv"
    write_summary_csv(summary_path, summary_rows)
    summary_plot = Path(output_dir) / "pat_model_comparison.png"
    plot_pat_summary(pd.DataFrame(summary_rows), summary_plot)

    # Also mirror a short display summary into the model root for the paper note.
    paper_summary = DEFAULT_OUTPUT_ROOT / "bcase_pat_summary_display.csv"
    DEFAULT_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summary_rows).to_csv(
        paper_summary, index=False, encoding="utf-8-sig", float_format="%.3g"
    )

    n_cases = len(case_ids)
    print(f"Processed {n_cases} cases")
    print(f"Config: {args.config}")
    print(f"Dataset: {args.dataset}")
    print(f"b_mode: {args.b_mode}")
    print(f"bcase PAT output: {output_dir}")
    print(f"Summary plot: {summary_plot}")
    if skipped:
        print(f"Skipped unsupported cases: {', '.join(skipped)}")
    print_summary_rows(summary_rows)


if __name__ == "__main__":
    main()
