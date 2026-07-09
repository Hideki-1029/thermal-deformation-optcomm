"""Run PAT coarse acquisition with Fourier / static-bias lightweight LOS models."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import sys

import numpy as np

PAT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PAT_ROOT.parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(PAT_ROOT) not in sys.path:
    sys.path.insert(0, str(PAT_ROOT))

from pat_acquisition.models.fourier_los.model import (  # noqa: E402
    FourierLosConfig,
    estimate_orbit_period_s,
    fit_fourier_predictions,
)
from pat_acquisition.runners.pat_common import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    DEFAULT_FOURIER_OUTPUT_DIR,
    FOURIER_MODEL_NAMES,
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
    read_femap_los_csv,
    resolve_input_paths,
    resolve_los_prefix,
    resolve_orbit_period_s,
    summary_rows_for_models,
    write_case_bundle,
    write_summary_csv,
)


def build_fourier_config(
    yaml_config: dict,
    args: argparse.Namespace,
) -> FourierLosConfig:
    return FourierLosConfig(
        orbit_period_s=float(
            config_value(
                yaml_config,
                "lightweight_model",
                "orbit_period_s",
                args.orbit_period_s,
                6050.0,
            )
        ),
        auto_orbit_period=bool(
            config_value(
                yaml_config,
                "lightweight_model",
                "auto_orbit_period",
                args.auto_orbit_period,
                False,
            )
        ),
        train_fraction=float(
            config_value(
                yaml_config,
                "lightweight_model",
                "train_fraction",
                args.lightweight_train_fraction,
                1.0,
            )
        ),
        fourier_order=int(
            config_value(
                yaml_config,
                "lightweight_model",
                "fourier_order",
                args.lightweight_fourier_order,
                2,
            )
        ),
        include_drift=bool(
            config_value(
                yaml_config,
                "lightweight_model",
                "include_drift",
                args.lightweight_include_drift,
                False,
            )
        ),
        ridge_lam=float(
            config_value(
                yaml_config,
                "lightweight_model",
                "ridge_lam",
                args.lightweight_ridge_lam,
                1e-3,
            )
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "PAT coarse acquisition with Fourier / static-bias lightweight "
            "LOS correction models."
        )
    )
    add_common_pat_arguments(parser)
    parser.add_argument("--orbit-period-s", type=float, default=None)
    parser.add_argument(
        "--auto-orbit-period", action=argparse.BooleanOptionalAction, default=None
    )
    parser.add_argument("--lightweight-train-fraction", type=float, default=None)
    parser.add_argument("--lightweight-fourier-order", type=int, default=None)
    parser.add_argument(
        "--lightweight-include-drift",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument("--lightweight-ridge-lam", type=float, default=None)
    return parser.parse_args()


def run_one_case(
    los_csv: Path,
    output_dir: Path,
    los_prefix: str,
    config,
    nonthermal_config,
    fourier_config: FourierLosConfig,
    case_metadata_paths,
) -> list[dict[str, object]]:
    case_id = los_csv.parent.name
    times_s, theta_thermal_true = read_femap_los_csv(los_csv, los_prefix)
    nonthermal_error = generate_nonthermal_error(times_s, case_id, nonthermal_config)

    if fourier_config.auto_orbit_period:
        orbit_period_s = estimate_orbit_period_s(times_s, theta_thermal_true)
    else:
        orbit_period_s = resolve_orbit_period_s(
            case_id,
            case_metadata_paths,
            default_period_s=fourier_config.orbit_period_s,
        )

    resolved_config = replace(fourier_config, orbit_period_s=orbit_period_s)
    predictions = fit_fourier_predictions(
        times_s, theta_thermal_true, resolved_config
    )
    zero_error = np.zeros_like(theta_thermal_true)

    model_specs = {
        "static_bias_correction": {
            "theta_hat": predictions["static_bias"],
            "nonthermal": zero_error,
        },
        "fourier_ff_correction": {
            "theta_hat": predictions["fourier_ff"],
            "nonthermal": zero_error,
        },
        "fourier_plus_drift_correction": {
            "theta_hat": predictions["fourier_plus_drift"],
            "nonthermal": zero_error,
        },
        "fourier_ff_correction_with_nonthermal": {
            "theta_hat": predictions["fourier_ff"],
            "nonthermal": nonthermal_error,
        },
    }
    model_specs = {name: model_specs[name] for name in FOURIER_MODEL_NAMES}

    results_by_model = evaluate_model_specs(theta_thermal_true, config, model_specs)
    write_case_bundle(
        output_dir,
        case_id,
        times_s,
        theta_thermal_true,
        nonthermal_error,
        results_by_model,
        lightweight_predictions=predictions,
        title="PAT coarse acquisition with Fourier lightweight LOS model",
    )
    return summary_rows_for_models(
        case_id, theta_thermal_true, zero_error, model_specs, results_by_model
    )


def main() -> None:
    args = parse_args()
    yaml_config = load_yaml_config(args.config)

    output_dir = config_path_value(
        yaml_config,
        "input",
        "fourier_output_dir",
        args.output_dir,
        DEFAULT_FOURIER_OUTPUT_DIR,
    )
    los_prefix = resolve_los_prefix(yaml_config, args)
    input_paths = resolve_input_paths(yaml_config, args)
    config = build_scan_config(yaml_config, args)
    nonthermal_config = build_nonthermal_config(yaml_config, args)
    fourier_config = build_fourier_config(yaml_config, args)
    case_metadata_paths = build_case_metadata_paths(yaml_config, args)

    summary_rows: list[dict[str, object]] = []
    for los_csv in input_paths:
        summary_rows.extend(
            run_one_case(
                los_csv=los_csv,
                output_dir=output_dir,
                los_prefix=los_prefix,
                config=config,
                nonthermal_config=nonthermal_config,
                fourier_config=fourier_config,
                case_metadata_paths=case_metadata_paths,
            )
        )

    write_summary_csv(output_dir / "summary.csv", summary_rows)
    print(f"Processed {len(input_paths)} LOS CSV files")
    print(f"Config: {args.config}")
    print(f"Fourier output: {output_dir}")
    print_summary_rows(summary_rows)


if __name__ == "__main__":
    main()
