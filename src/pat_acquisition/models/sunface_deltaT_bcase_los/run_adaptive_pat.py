"""PAT coarse acquisition with hierarchical bcase FF + adaptive δb / slow b_adapt."""

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
    run_bcase_pipeline,
)
import matplotlib.pyplot as plt  # noqa: E402

from pat_acquisition.runners.pat_common import (  # noqa: E402
    REPO_ROOT,
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

DEFAULT_ADAPTIVE_PAT_OUTPUT_DIR = (
    REPO_ROOT
    / "results"
    / "pat_acquisition"
    / "sunface_deltaT_bcase_los_model"
    / "pat_adaptive"
)

ADAPTIVE_MODEL_NAMES = (
    "no_correction",
    "bcase_correction",
    "bcase_correction_with_nonthermal",
    "bcase_delta_b",
    "bcase_delta_b_with_nonthermal",
    "bcase_delta_b_slow_b",
    "bcase_delta_b_slow_b_with_nonthermal",
)

ADAPTIVE_PLOT_LABELS = {
    "no_correction": "no correction",
    "bcase_correction": "FF bcase",
    "bcase_correction_with_nonthermal": "FF bcase + nonthermal",
    "bcase_delta_b": "FF + δb (Toy-1)",
    "bcase_delta_b_with_nonthermal": "FF + δb + nonthermal",
    "bcase_delta_b_slow_b": "FF + δb + slow b (Toy-2)",
    "bcase_delta_b_slow_b_with_nonthermal": "FF + δb + slow b + nonthermal",
}


def plot_adaptive_pat_summary(summary_df: pd.DataFrame, out_png: Path) -> None:
    focus = (
        "bcase_correction_with_nonthermal",
        "bcase_delta_b_with_nonthermal",
        "bcase_delta_b_slow_b_with_nonthermal",
    )
    labels = {
        "bcase_correction_with_nonthermal": "FF + nonthermal",
        "bcase_delta_b_with_nonthermal": "FF+δb + nonthermal",
        "bcase_delta_b_slow_b_with_nonthermal": "FF+δb+slow b + nonthermal",
    }
    colors = {
        "bcase_correction_with_nonthermal": "#1f77b4",
        "bcase_delta_b_with_nonthermal": "#d62728",
        "bcase_delta_b_slow_b_with_nonthermal": "#2ca02c",
    }
    sub = summary_df[summary_df["model"].isin(focus)].copy()
    if sub.empty:
        return

    def _short(case_id: str) -> str:
        prefix = str(case_id).split("_", 1)[0]
        return prefix if prefix.isdigit() else str(case_id)[:10]

    sub["case_label"] = sub["case_id"].map(_short)
    case_order = (
        sub.drop_duplicates("case_id")
        .assign(_n=lambda d: pd.to_numeric(d["case_label"], errors="coerce"))
        .sort_values(["_n", "case_id"])["case_id"]
        .tolist()
    )
    x = np.arange(len(case_order))
    width = 0.25
    offsets = {
        focus[0]: -width,
        focus[1]: 0.0,
        focus[2]: width,
    }
    fig, ax = plt.subplots(figsize=(max(8.5, 0.55 * len(case_order) + 3), 4.6))
    for model in focus:
        msub = sub[sub["model"] == model].set_index("case_id")
        vals = [
            float(msub.loc[c, "mean_acquisition_time_s"]) if c in msub.index else np.nan
            for c in case_order
        ]
        vals = [max(v, 0.1) if np.isfinite(v) else np.nan for v in vals]
        ax.bar(x + offsets[model], vals, width, label=labels[model], color=colors[model])
    ax.set_xticks(x)
    ax.set_xticklabels([_short(c) for c in case_order], fontsize=8)
    ax.set_ylabel("Mean acquisition time [s]")
    ax.set_xlabel("Case")
    ax.set_yscale("log")
    ax.set_ylim(0.08, None)
    ax.set_title("Adaptive toy: FF vs δb vs δb+slow b (with nonthermal)")
    ax.grid(True, axis="y", which="both", alpha=0.3)
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "PAT with bcase FF + adaptive toy (mode-wise δb; optional slow b_adapt "
            "gated by sun-face geometry)."
        )
    )
    add_common_pat_arguments(parser)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--cases", help="Case numbers, e.g. 4,5,6 or 4-6,8-21.")
    parser.add_argument("--case", default=None, help="Single case number.")
    parser.add_argument("--case-id", action="append", default=None)
    parser.add_argument("--list-cases", action="store_true")
    parser.add_argument("--orbit-period-s", type=float, default=None)
    parser.add_argument("--train-orbits", type=float, default=1.0)
    parser.add_argument("--ridge-lam", type=float, default=1e-3)
    parser.add_argument("--level2-ridge-lam", type=float, default=0.0)
    parser.add_argument("--heat-faces", default="MY,PY")
    parser.add_argument(
        "--b-mode",
        choices=("loo", "insample"),
        default="loo",
    )
    parser.add_argument("--gamma-fast", type=float, default=0.4)
    parser.add_argument("--gamma-slow", type=float, default=0.05)
    parser.add_argument(
        "--residual-noise-urad",
        type=float,
        default=5.0,
        help="1σ noise on orbit-mean innovation used for updates.",
    )
    parser.add_argument("--adaptive-seed", type=int, default=0)
    parser.add_argument(
        "--share-tables-across-cases",
        action="store_true",
        help="Keep δb / b_adapt tables across cases (same mode accumulates).",
    )
    return parser.parse_args()


def _resolve_b_urad(row: pd.Series, b_mode: str) -> float:
    if b_mode == "insample":
        return float(row["b_pred_insample_urad"])
    loo = float(row["b_pred_loo_urad"])
    if np.isfinite(loo):
        return loo
    return float(row["b_pred_insample_urad"])


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
    adaptive_config_base: AdaptiveConfig,
    tables: dict[str, AdaptiveTables],
) -> tuple[list[dict[str, object]], pd.DataFrame]:
    times_s = case_df["time_s"].to_numpy(dtype=float)
    theta_thermal_true = case_df[
        ["far_field_los_angle_x_urad", "far_field_los_angle_y_urad"]
    ].to_numpy(dtype=float)
    nonthermal_error = generate_nonthermal_error(times_s, case_id, nonthermal_config)
    zero_error = np.zeros_like(theta_thermal_true)

    sun_face = str(row["sun_face"])
    b_urad = _resolve_b_urad(row, b_mode)
    a_urad = float(a_shared[sun_face])
    predictions = predict_bcase_xy(
        case_df,
        b_urad=b_urad,
        a_urad_per_c=a_urad,
        config=bcase_config,
    )
    pred_bcase = np.asarray(predictions["bcase"], dtype=float)
    mode = mode_key_from_case(case_df, sun_face=sun_face)

    def _cfg(*, enable_slow_b: bool, seed: int) -> AdaptiveConfig:
        return AdaptiveConfig(
            gamma_fast=adaptive_config_base.gamma_fast,
            gamma_slow=adaptive_config_base.gamma_slow,
            enable_slow_b=enable_slow_b,
            w_my_py=adaptive_config_base.w_my_py,
            w_px=adaptive_config_base.w_px,
            w_other=adaptive_config_base.w_other,
            residual_noise_1sigma_urad=adaptive_config_base.residual_noise_1sigma_urad,
            seed=seed,
        )

    def _sim(
        key: str,
        *,
        enable_slow_b: bool,
        nonthermal: np.ndarray,
        seed: int,
    ) -> dict:
        return simulate_adaptive_theta_hat(
            pred_bcase=pred_bcase,
            theta_thermal_true=theta_thermal_true,
            nonthermal_error=nonthermal,
            times_s=times_s,
            orbit_period_s=bcase_config.orbit_period_s,
            mode=mode,
            tables=tables[key],
            config=_cfg(enable_slow_b=enable_slow_b, seed=seed),
        )

    seed0 = adaptive_config_base.seed
    sim_fast_th = _sim("fast_th", enable_slow_b=False, nonthermal=zero_error, seed=seed0)
    sim_fast_nt = _sim(
        "fast_nt", enable_slow_b=False, nonthermal=nonthermal_error, seed=seed0 + 1
    )
    sim_slow_th = _sim("slow_th", enable_slow_b=True, nonthermal=zero_error, seed=seed0 + 2)
    sim_slow_nt = _sim(
        "slow_nt", enable_slow_b=True, nonthermal=nonthermal_error, seed=seed0 + 3
    )

    pred_delta_b = np.asarray(sim_fast_th["theta_hat"], dtype=float)
    pred_delta_b_nt = np.asarray(sim_fast_nt["theta_hat"], dtype=float)
    pred_slow = np.asarray(sim_slow_th["theta_hat"], dtype=float)
    pred_slow_nt = np.asarray(sim_slow_nt["theta_hat"], dtype=float)

    model_specs = {
        "no_correction": {"theta_hat": zero_error, "nonthermal": zero_error},
        "bcase_correction": {"theta_hat": pred_bcase, "nonthermal": zero_error},
        "bcase_correction_with_nonthermal": {
            "theta_hat": pred_bcase,
            "nonthermal": nonthermal_error,
        },
        "bcase_delta_b": {"theta_hat": pred_delta_b, "nonthermal": zero_error},
        "bcase_delta_b_with_nonthermal": {
            "theta_hat": pred_delta_b_nt,
            "nonthermal": nonthermal_error,
        },
        "bcase_delta_b_slow_b": {"theta_hat": pred_slow, "nonthermal": zero_error},
        "bcase_delta_b_slow_b_with_nonthermal": {
            "theta_hat": pred_slow_nt,
            "nonthermal": nonthermal_error,
        },
    }
    model_specs = {name: model_specs[name] for name in ADAPTIVE_MODEL_NAMES}

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
            "bcase_delta_b": pred_delta_b,
            "bcase_delta_b_with_nonthermal": pred_delta_b_nt,
            "bcase_delta_b_slow_b": pred_slow,
            "bcase_delta_b_slow_b_with_nonthermal": pred_slow_nt,
        },
        title=(
            f"PAT adaptive toy (sun={sun_face}, mode={mode}, "
            f"b={b_urad:.2g}, a={a_urad:.2g})"
        ),
        plot_labels=ADAPTIVE_PLOT_LABELS,
    )

    hist_parts = [
        (sim_fast_th, "delta_b_thermal"),
        (sim_fast_nt, "delta_b_nonthermal"),
        (sim_slow_th, "slow_b_thermal"),
        (sim_slow_nt, "slow_b_nonthermal"),
    ]
    frames: list[pd.DataFrame] = []
    for sim, layer in hist_parts:
        hist = pd.DataFrame(sim["history"])
        hist["layer"] = layer
        frames.append(hist)
    history = pd.concat(frames, ignore_index=True)
    history.insert(0, "case_id", case_id)
    history.insert(1, "sun_face", sun_face)
    history.insert(2, "mode", str(mode))

    case_dir = Path(output_dir) / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    history.to_csv(
        case_dir / "adaptive_update_history.csv",
        index=False,
        encoding="utf-8-sig",
    )

    rows = summary_rows_for_models(
        case_id, theta_thermal_true, zero_error, model_specs, results_by_model
    )
    return rows, history


def _fresh_tables() -> dict[str, AdaptiveTables]:
    return {
        "fast_th": AdaptiveTables(),
        "fast_nt": AdaptiveTables(),
        "slow_th": AdaptiveTables(),
        "slow_nt": AdaptiveTables(),
    }


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
        "bcase_adaptive_output_dir",
        args.output_dir,
        DEFAULT_ADAPTIVE_PAT_OUTPUT_DIR,
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
    adaptive_config = AdaptiveConfig(
        gamma_fast=args.gamma_fast,
        gamma_slow=args.gamma_slow,
        residual_noise_1sigma_urad=args.residual_noise_urad,
        seed=args.adaptive_seed,
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

    fit_dir = Path(output_dir)
    fit_dir.mkdir(parents=True, exist_ok=True)
    case_table.to_csv(
        fit_dir / "bcase_pat_case_table.csv", index=False, encoding="utf-8-sig"
    )

    tables = _fresh_tables()
    summary_rows: list[dict[str, object]] = []
    histories: list[pd.DataFrame] = []

    for case_id in case_ids:
        if not args.share_tables_across_cases:
            tables = _fresh_tables()

        case_df = load_case_frame(args.dataset, case_id)
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
        rows, history = run_one_case(
            case_id=case_id,
            case_df=case_df,
            row=case_lookup.loc[case_id],
            a_shared=a_shared,
            output_dir=output_dir,
            config=config,
            nonthermal_config=nonthermal_config,
            bcase_config=case_config,
            b_mode=args.b_mode,
            adaptive_config_base=adaptive_config,
            tables=tables,
        )
        summary_rows.extend(rows)
        histories.append(history)

    summary_path = Path(output_dir) / "summary.csv"
    write_summary_csv(summary_path, summary_rows)
    summary_plot = Path(output_dir) / "pat_model_comparison.png"
    plot_adaptive_pat_summary(pd.DataFrame(summary_rows), summary_plot)

    if histories:
        all_hist = pd.concat(histories, ignore_index=True)
        all_hist.to_csv(
            Path(output_dir) / "adaptive_update_history.csv",
            index=False,
            encoding="utf-8-sig",
        )

    print(f"Processed {len(case_ids)} cases")
    print(f"Adaptive PAT output: {output_dir}")
    print(f"Summary plot: {summary_plot}")
    if skipped:
        print(f"Skipped unsupported cases: {', '.join(skipped)}")
    print_summary_rows(summary_rows)


if __name__ == "__main__":
    main()