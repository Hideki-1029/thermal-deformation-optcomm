"""PAT: hierarchical bcase FF + residual Fourier on post-FF innovation."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib.pyplot as plt
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

DEFAULT_OUTPUT_DIR = (
    REPO_ROOT
    / "results"
    / "pat_acquisition"
    / "sunface_deltaT_bcase_los_model"
    / "pat_residual_fourier"
)

MODEL_NAMES = (
    "bcase_correction",
    "bcase_correction_with_nonthermal",
    "bcase_delta_b_with_nonthermal",
    "bcase_residual_fourier",
    "bcase_residual_fourier_with_nonthermal",
)

PLOT_LABELS = {
    "bcase_correction": "FF bcase",
    "bcase_correction_with_nonthermal": "FF + nonthermal",
    "bcase_delta_b_with_nonthermal": "FF+δb + nonthermal",
    "bcase_residual_fourier": "FF + resid Fourier",
    "bcase_residual_fourier_with_nonthermal": "FF + resid Fourier + nonthermal",
}


def plot_summary(summary_df: pd.DataFrame, out_png: Path) -> None:
    focus = (
        "bcase_correction_with_nonthermal",
        "bcase_delta_b_with_nonthermal",
        "bcase_residual_fourier_with_nonthermal",
    )
    labels = {
        "bcase_correction_with_nonthermal": "FF + nonthermal",
        "bcase_delta_b_with_nonthermal": "FF+δb + nonthermal",
        "bcase_residual_fourier_with_nonthermal": "FF+resid Fourier + nonthermal",
    }
    colors = {
        "bcase_correction_with_nonthermal": "#1f77b4",
        "bcase_delta_b_with_nonthermal": "#d62728",
        "bcase_residual_fourier_with_nonthermal": "#2ca02c",
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
    offsets = {focus[0]: -width, focus[1]: 0.0, focus[2]: width}
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
    ax.set_title("Post-FF residual Fourier vs FF / δb (with nonthermal)")
    ax.grid(True, axis="y", which="both", alpha=0.3)
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "PAT with bcase FF + Fourier on post-FF innovation "
            "r=(thermal+nonthermal)-θ_ff."
        )
    )
    add_common_pat_arguments(parser)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--cases", help="Case numbers, e.g. 13,16")
    parser.add_argument("--case", default=None)
    parser.add_argument("--case-id", action="append", default=None)
    parser.add_argument("--list-cases", action="store_true")
    parser.add_argument("--orbit-period-s", type=float, default=None)
    parser.add_argument("--train-orbits", type=float, default=1.0)
    parser.add_argument("--ridge-lam", type=float, default=1e-3)
    parser.add_argument("--level2-ridge-lam", type=float, default=0.0)
    parser.add_argument("--heat-faces", default="MY,PY")
    parser.add_argument("--b-mode", choices=("loo", "insample"), default="loo")
    parser.add_argument("--fourier-order", type=int, default=2)
    parser.add_argument("--fourier-ridge-lam", type=float, default=1e-3)
    parser.add_argument(
        "--fit-mode",
        choices=("causal", "batch"),
        default="causal",
        help="causal: fit orbit n → apply n+1; batch: fit all (analysis upper bound)",
    )
    parser.add_argument("--gamma-fast", type=float, default=0.4)
    parser.add_argument("--adaptive-seed", type=int, default=0)
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
    fourier_cfg: ResidualFourierConfig,
    adaptive_cfg: AdaptiveConfig,
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

    # Toy-1 δb reference (nonthermal path only for the comparison arm).
    sim_db = simulate_adaptive_theta_hat(
        pred_bcase=pred_bcase,
        theta_thermal_true=theta_thermal_true,
        nonthermal_error=nonthermal_error,
        times_s=times_s,
        orbit_period_s=bcase_config.orbit_period_s,
        mode=mode,
        tables=AdaptiveTables(),
        config=adaptive_cfg,
    )
    pred_db = np.asarray(sim_db["theta_hat"], dtype=float)

    cfg_th = ResidualFourierConfig(
        orbit_period_s=fourier_cfg.orbit_period_s,
        fourier_order=fourier_cfg.fourier_order,
        ridge_lam=fourier_cfg.ridge_lam,
        fit_mode=fourier_cfg.fit_mode,
        residual_noise_1sigma_urad=fourier_cfg.residual_noise_1sigma_urad,
        seed=fourier_cfg.seed,
    )
    cfg_nt = ResidualFourierConfig(
        orbit_period_s=fourier_cfg.orbit_period_s,
        fourier_order=fourier_cfg.fourier_order,
        ridge_lam=fourier_cfg.ridge_lam,
        fit_mode=fourier_cfg.fit_mode,
        residual_noise_1sigma_urad=fourier_cfg.residual_noise_1sigma_urad,
        seed=fourier_cfg.seed + 1,
    )
    sim_f_th = simulate_residual_fourier_theta_hat(
        pred_bcase=pred_bcase,
        theta_thermal_true=theta_thermal_true,
        nonthermal_error=zero_error,
        times_s=times_s,
        config=cfg_th,
    )
    sim_f_nt = simulate_residual_fourier_theta_hat(
        pred_bcase=pred_bcase,
        theta_thermal_true=theta_thermal_true,
        nonthermal_error=nonthermal_error,
        times_s=times_s,
        config=cfg_nt,
    )
    pred_f_th = np.asarray(sim_f_th["theta_hat"], dtype=float)
    pred_f_nt = np.asarray(sim_f_nt["theta_hat"], dtype=float)

    model_specs = {
        "bcase_correction": {"theta_hat": pred_bcase, "nonthermal": zero_error},
        "bcase_correction_with_nonthermal": {
            "theta_hat": pred_bcase,
            "nonthermal": nonthermal_error,
        },
        "bcase_delta_b_with_nonthermal": {
            "theta_hat": pred_db,
            "nonthermal": nonthermal_error,
        },
        "bcase_residual_fourier": {"theta_hat": pred_f_th, "nonthermal": zero_error},
        "bcase_residual_fourier_with_nonthermal": {
            "theta_hat": pred_f_nt,
            "nonthermal": nonthermal_error,
        },
    }
    model_specs = {name: model_specs[name] for name in MODEL_NAMES}
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
            "bcase_delta_b": pred_db,
            "residual_fourier": pred_f_nt,
        },
        title=(
            f"PAT residual Fourier (sun={sun_face}, fit={fourier_cfg.fit_mode}, "
            f"order={fourier_cfg.fourier_order}, b={b_urad:.2g})"
        ),
        plot_labels=PLOT_LABELS,
    )

    hist_th = pd.DataFrame(sim_f_th["history"])
    hist_th["layer"] = "fourier_thermal"
    hist_nt = pd.DataFrame(sim_f_nt["history"])
    hist_nt["layer"] = "fourier_nonthermal"
    history = pd.concat([hist_th, hist_nt], ignore_index=True)
    history.insert(0, "case_id", case_id)
    history.insert(1, "sun_face", sun_face)
    case_dir = Path(output_dir) / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    history.to_csv(
        case_dir / "residual_fourier_history.csv", index=False, encoding="utf-8-sig"
    )

    # Save residual timeseries for inspection.
    r_nt = np.asarray(sim_f_nt["r_true"], dtype=float)
    r_hat = np.asarray(sim_f_nt["r_hat"], dtype=float)
    pd.DataFrame(
        {
            "time_s": times_s,
            "r_x_urad": r_nt[:, 0],
            "r_y_urad": r_nt[:, 1],
            "r_norm_urad": np.linalg.norm(r_nt, axis=1),
            "r_hat_x_urad": r_hat[:, 0],
            "r_hat_y_urad": r_hat[:, 1],
            "r_hat_norm_urad": np.linalg.norm(r_hat, axis=1),
        }
    ).to_csv(case_dir / "residual_fourier_timeseries.csv", index=False, encoding="utf-8-sig")

    rows = summary_rows_for_models(
        case_id, theta_thermal_true, zero_error, model_specs, results_by_model
    )
    return rows, history


def main() -> None:
    args = parse_args()
    yaml_config = load_yaml_config(args.config)

    if args.list_cases:
        if not args.dataset.exists():
            raise FileNotFoundError(f"Dataset not found: {args.dataset}")
        for number, case_id, sun_face, supported in list_numbered_cases(args.dataset):
            flag = "supported" if supported else "skipped"
            print(f"  {number:>3d}  {case_id}  sun={sun_face}  ({flag})")
        return

    output_dir = config_path_value(
        yaml_config,
        "input",
        "bcase_residual_fourier_output_dir",
        args.output_dir,
        DEFAULT_OUTPUT_DIR,
    )
    config = build_scan_config(yaml_config, args)
    nonthermal_config = build_nonthermal_config(yaml_config, args)
    case_metadata_paths = build_case_metadata_paths(yaml_config, args)

    if not args.dataset.exists():
        raise FileNotFoundError(f"Dataset not found: {args.dataset}")

    case_ids, skipped = resolve_sunface_case_ids(
        args.dataset,
        cases=args.cases,
        case=args.case,
        case_ids=args.case_id,
        default_all_supported=not args.cases and not args.case and not args.case_id,
    )
    heat_faces = parse_heat_faces(args.heat_faces)
    default_period = float(
        config_value(yaml_config, "lightweight_model", "orbit_period_s", None, 6050.0)
    )
    fit_orbit_period_s = (
        float(args.orbit_period_s)
        if args.orbit_period_s is not None
        else resolve_orbit_period_s(
            case_ids[0], case_metadata_paths, default_period_s=default_period
        )
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
        f"(fit_mode={args.fit_mode}, order={args.fourier_order})..."
    )
    pipeline = run_bcase_pipeline(
        dataset_path=args.dataset, case_ids=case_ids, config=bcase_config
    )
    case_table: pd.DataFrame = pipeline["case_table"]
    a_shared: dict[str, float] = pipeline["a_shared"]
    case_lookup = case_table.set_index("case_id")

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    case_table.to_csv(
        Path(output_dir) / "bcase_pat_case_table.csv", index=False, encoding="utf-8-sig"
    )

    summary_rows: list[dict[str, object]] = []
    histories: list[pd.DataFrame] = []
    for case_id in case_ids:
        case_df = load_case_frame(args.dataset, case_id)
        orbit_period_s = (
            float(args.orbit_period_s)
            if args.orbit_period_s is not None
            else resolve_orbit_period_s(
                case_id, case_metadata_paths, default_period_s=default_period
            )
        )
        case_config = BCaseConfig(
            ridge_lam=bcase_config.ridge_lam,
            heat_faces=bcase_config.heat_faces,
            orbit_period_s=orbit_period_s,
            train_orbits=bcase_config.train_orbits,
            level2_ridge_lam=bcase_config.level2_ridge_lam,
        )
        fourier_cfg = ResidualFourierConfig(
            orbit_period_s=orbit_period_s,
            fourier_order=args.fourier_order,
            ridge_lam=args.fourier_ridge_lam,
            fit_mode=args.fit_mode,
            seed=args.adaptive_seed,
        )
        adaptive_cfg = AdaptiveConfig(
            gamma_fast=args.gamma_fast,
            enable_slow_b=False,
            seed=args.adaptive_seed,
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
            fourier_cfg=fourier_cfg,
            adaptive_cfg=adaptive_cfg,
        )
        summary_rows.extend(rows)
        histories.append(history)

    write_summary_csv(Path(output_dir) / "summary.csv", summary_rows)
    summary_plot = Path(output_dir) / "pat_model_comparison.png"
    plot_summary(pd.DataFrame(summary_rows), summary_plot)
    if histories:
        pd.concat(histories, ignore_index=True).to_csv(
            Path(output_dir) / "residual_fourier_history.csv",
            index=False,
            encoding="utf-8-sig",
        )

    print(f"Processed {len(case_ids)} cases")
    print(f"Output: {output_dir}")
    print(f"fit_mode={args.fit_mode}, order={args.fourier_order}")
    if skipped:
        print(f"Skipped: {', '.join(skipped)}")
    print_summary_rows(summary_rows)


if __name__ == "__main__":
    main()
