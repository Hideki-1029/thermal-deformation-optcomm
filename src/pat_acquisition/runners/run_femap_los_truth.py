"""Run PAT coarse acquisition using Femap LOS truth baselines only."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np

PAT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PAT_ROOT.parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(PAT_ROOT) not in sys.path:
    sys.path.insert(0, str(PAT_ROOT))

from pat_acquisition.runners.pat_common import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    DEFAULT_TRUTH_OUTPUT_DIR,
    TRUTH_MODEL_NAMES,
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
    summary_rows_for_models,
    write_case_bundle,
    write_summary_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "PAT coarse acquisition with Femap LOS truth baselines "
            "(no lightweight prediction models)."
        )
    )
    add_common_pat_arguments(parser)
    # Allow unknown flags so the combined legacy entry can pass Fourier CLI args.
    args, _unknown = parser.parse_known_args()
    return args


def run_one_case(
    los_csv: Path,
    output_dir: Path,
    los_prefix: str,
    config,
    nonthermal_config,
) -> list[dict[str, object]]:
    case_id = los_csv.parent.name
    times_s, theta_thermal_true = read_femap_los_csv(los_csv, los_prefix)
    nonthermal_error = generate_nonthermal_error(times_s, case_id, nonthermal_config)
    zero_error = np.zeros_like(theta_thermal_true)

    model_specs = {
        "no_correction": {
            "theta_hat": zero_error,
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
        "thermal_truth_correction_with_nonthermal": {
            "theta_hat": theta_thermal_true.copy(),
            "nonthermal": nonthermal_error,
        },
    }
    # Keep a stable order matching TRUTH_MODEL_NAMES.
    model_specs = {name: model_specs[name] for name in TRUTH_MODEL_NAMES}

    results_by_model = evaluate_model_specs(theta_thermal_true, config, model_specs)
    write_case_bundle(
        output_dir,
        case_id,
        times_s,
        theta_thermal_true,
        nonthermal_error,
        results_by_model,
        lightweight_predictions=None,
        title="PAT coarse acquisition with Femap thermal LOS truth",
    )
    return summary_rows_for_models(
        case_id, theta_thermal_true, zero_error, model_specs, results_by_model
    )


def main() -> None:
    args = parse_args()
    yaml_config = load_yaml_config(args.config)

    # Prefer --output-dir; fall back to truth_output_dir / legacy output_dir.
    truth_cli = args.output_dir
    output_dir = config_path_value(
        yaml_config,
        "input",
        "truth_output_dir",
        truth_cli,
        DEFAULT_TRUTH_OUTPUT_DIR,
    )
    if truth_cli is None and output_dir == DEFAULT_TRUTH_OUTPUT_DIR:
        legacy_output = config_value(yaml_config, "input", "output_dir", None, None)
        if legacy_output is not None:
            output_dir = config_path_value(
                yaml_config, "input", "output_dir", None, DEFAULT_TRUTH_OUTPUT_DIR
            )

    los_prefix = resolve_los_prefix(yaml_config, args)
    input_paths = resolve_input_paths(yaml_config, args)
    config = build_scan_config(yaml_config, args)
    nonthermal_config = build_nonthermal_config(yaml_config, args)
    # case_metadata is unused for truth-only, but keep YAML validation path available.
    _ = build_case_metadata_paths(yaml_config, args)

    summary_rows: list[dict[str, object]] = []
    for los_csv in input_paths:
        summary_rows.extend(
            run_one_case(
                los_csv=los_csv,
                output_dir=output_dir,
                los_prefix=los_prefix,
                config=config,
                nonthermal_config=nonthermal_config,
            )
        )

    write_summary_csv(output_dir / "summary.csv", summary_rows)
    print(f"Processed {len(input_paths)} LOS CSV files")
    print(f"Config: {args.config}")
    print(f"Truth output: {output_dir}")
    print_summary_rows(summary_rows)


if __name__ == "__main__":
    main()
