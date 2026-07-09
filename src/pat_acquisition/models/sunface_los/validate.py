"""
Within-case validation: sun-facing panel temperature -> dominant LOS axis.

Sun direction is treated as known (sun sensor / case metadata).
Evaluation is within-case (first orbit train, remaining orbits test).
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pat_acquisition.models._common.metrics import compute_error_metrics  # noqa: E402
from pat_acquisition.models._common.static_bias import (  # noqa: E402
    predict_no_correction,
    predict_static_bias,
)
from pat_acquisition.models._common.targets import extract_targets  # noqa: E402
from pat_acquisition.models.sunface_los.dataset import (  # noqa: E402
    CASE_PRESETS,
    DEFAULT_DATASET,
    DEFAULT_OUTPUT_ROOT,
    load_case_frame,
    short_case_tag,
    within_case_split_mask,
)
from pat_acquisition.models.sunface_los.features import (  # noqa: E402
    SunfaceFeatureConfig,
    build_sunface_features,
    normalize_sun_direction,
    predict_sunface_case,
    train_sunface_axis_model,
)

DEFAULT_ORBIT_PERIOD_S = 6052.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate sunface temperature -> dominant LOS axis (within-case)."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--case",
        choices=sorted(CASE_PRESETS.keys()),
        default=None,
        help="Short case key (04/05). Alternative to --case-id.",
    )
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--orbit-period-s", type=float, default=DEFAULT_ORBIT_PERIOD_S)
    parser.add_argument(
        "--train-orbits",
        type=float,
        default=1.0,
        help="Number of orbits used for training from the start of the case.",
    )
    parser.add_argument("--t-ref-c", type=float, default=23.9)
    parser.add_argument("--ridge-lam", type=float, default=1e-3)
    parser.add_argument("--no-opposite-diff", action="store_true")
    parser.add_argument("--no-ref-diff", action="store_true")
    return parser.parse_args()


def resolve_case_id(args: argparse.Namespace) -> str:
    if args.case_id:
        return str(args.case_id)
    if args.case:
        return CASE_PRESETS[args.case]
    raise ValueError("Specify --case (04/05) or --case-id.")


def plot_within_case(
    out_png: Path,
    case_tag: str,
    sun_face: str,
    dominant_axis: str,
    times_s: np.ndarray,
    y_true: np.ndarray,
    pred_sunface: np.ndarray,
    pred_static: np.ndarray,
    pred_no: np.ndarray,
    t_sunface: np.ndarray,
    train_mask: np.ndarray,
) -> None:
    t_min = times_s / 60.0
    train_end_min = float(times_s[train_mask][-1] / 60.0) if np.any(train_mask) else t_min[0]
    model_label = f"sunface_{sun_face.lower()}"

    fig, axes = plt.subplots(4, 1, figsize=(11, 10), sharex=True)

    axes[0].plot(t_min, t_sunface, color="#d62728", label=f"T_{sun_face} center")
    axes[0].axvline(train_end_min, color="k", linestyle=":", alpha=0.7, label="train/test split")
    axes[0].set_ylabel(f"T_{sun_face} [C]")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(fontsize=8)

    if dominant_axis == "y":
        dom_idx, other_idx = 1, 0
        dom_name, other_name = "y", "x"
    else:
        dom_idx, other_idx = 0, 1
        dom_name, other_name = "x", "y"

    axes[1].plot(t_min, y_true[:, dom_idx], label=f"true {dom_name}")
    axes[1].plot(t_min, pred_sunface[:, dom_idx], "--", label=f"sunface pred {dom_name}")
    axes[1].plot(t_min, pred_static[:, dom_idx], ":", label=f"static pred {dom_name}")
    axes[1].axvline(train_end_min, color="k", linestyle=":", alpha=0.7)
    axes[1].set_ylabel(f"dtheta {dom_name} [urad]")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(fontsize=8)

    axes[2].plot(t_min, y_true[:, other_idx], label=f"true {other_name}")
    axes[2].plot(
        t_min,
        pred_sunface[:, other_idx],
        "--",
        label=f"sunface pred {other_name} (static)",
    )
    axes[2].axvline(train_end_min, color="k", linestyle=":", alpha=0.7)
    axes[2].set_ylabel(f"dtheta {other_name} [urad]")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(fontsize=8)

    err_no = np.linalg.norm(y_true - pred_no, axis=1)
    err_static = np.linalg.norm(y_true - pred_static, axis=1)
    err_sun = np.linalg.norm(y_true - pred_sunface, axis=1)
    axes[3].plot(t_min, err_no, label="no_correction")
    axes[3].plot(t_min, err_static, label="static_bias")
    axes[3].plot(t_min, err_sun, label=model_label)
    axes[3].axvline(train_end_min, color="k", linestyle=":", alpha=0.7)
    axes[3].set_ylabel("error norm [urad]")
    axes[3].set_xlabel("Time [min]")
    axes[3].grid(True, alpha=0.3)
    axes[3].legend(fontsize=8)

    fig.suptitle(f"{case_tag} within-case: T_{sun_face} -> LOS {dom_name}")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    case_id = resolve_case_id(args)
    case_tag = short_case_tag(case_id)
    output_dir = args.output_dir or (DEFAULT_OUTPUT_ROOT / f"{case_tag}_within_case")

    case_df = load_case_frame(args.dataset, case_id)
    sun_direction = case_df["case_sun_direction_body"].iloc[0]
    sun_face = normalize_sun_direction(sun_direction)

    config = SunfaceFeatureConfig(
        t_ref_c=args.t_ref_c,
        ridge_lam=args.ridge_lam,
        include_opposite_diff=not args.no_opposite_diff,
        include_ref_diff=not args.no_ref_diff,
    )
    x_all, feature_names, features_df, dominant_axis = build_sunface_features(
        case_df, sun_direction, config
    )

    y_all = extract_targets(case_df)
    times_s = case_df["time_s"].to_numpy(dtype=float)
    train_mask = within_case_split_mask(times_s, args.orbit_period_s, args.train_orbits)
    test_mask = ~train_mask
    if not np.any(train_mask) or not np.any(test_mask):
        raise ValueError(
            "Train/test split is empty. Check --orbit-period-s and --train-orbits."
        )

    axis_idx = 0 if dominant_axis == "x" else 1
    x_train = x_all[train_mask]
    y_train = y_all[train_mask]
    axis_model = train_sunface_axis_model(
        x_train=x_train,
        y_axis_train=y_train[:, axis_idx],
        feature_names=feature_names,
        config=config,
    )
    static_bias = np.mean(y_train, axis=0)

    pred_sunface = predict_sunface_case(
        x=x_all,
        dominant_axis=dominant_axis,
        axis_model=axis_model,
        static_bias_xy=static_bias,
    )
    pred_no = predict_no_correction(len(case_df))
    pred_static = predict_static_bias(y_train, len(case_df))
    model_name = f"sunface_{sun_face.lower()}_correction"

    metrics_rows: list[dict[str, float | str]] = []
    for split_name, mask in (
        ("train", train_mask),
        ("test", test_mask),
        ("all", np.ones(len(case_df), dtype=bool)),
    ):
        for name, pred in (
            ("no_correction", pred_no),
            ("static_bias_correction", pred_static),
            (model_name, pred_sunface),
        ):
            m = compute_error_metrics(y_all[mask], pred[mask])
            metrics_rows.append({"split": split_name, "model": name, **m})

    predictions = pd.DataFrame(
        {
            "case_id": case_id,
            "time_s": times_s,
            "split": np.where(train_mask, "train", "test"),
            "sun_direction": sun_face,
            "dominant_axis": dominant_axis,
            "t_sunface_c": features_df["t_sunface_c"].to_numpy(dtype=float),
            "dtheta_x_true_urad": y_all[:, 0],
            "dtheta_y_true_urad": y_all[:, 1],
            "dtheta_x_pred_no_correction_urad": pred_no[:, 0],
            "dtheta_y_pred_no_correction_urad": pred_no[:, 1],
            "dtheta_x_pred_static_bias_urad": pred_static[:, 0],
            "dtheta_y_pred_static_bias_urad": pred_static[:, 1],
            "dtheta_x_pred_sunface_urad": pred_sunface[:, 0],
            "dtheta_y_pred_sunface_urad": pred_sunface[:, 1],
        }
    )
    for name in feature_names:
        predictions[name] = features_df[name].to_numpy(dtype=float)

    coef_df = pd.DataFrame(
        {
            "feature": ["intercept", *axis_model.feature_names],
            "coef_dominant_axis_urad": axis_model.coef[:, 0],
        }
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = output_dir / f"{case_tag}_sunface_predictions.csv"
    metrics_path = output_dir / f"{case_tag}_sunface_metrics.csv"
    coef_path = output_dir / f"{case_tag}_sunface_coefficients.csv"
    plot_path = output_dir / f"{case_tag}_sunface_true_vs_pred.png"

    predictions.to_csv(predictions_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(metrics_rows).to_csv(metrics_path, index=False, encoding="utf-8-sig")
    coef_df.to_csv(coef_path, index=False, encoding="utf-8-sig")
    plot_within_case(
        plot_path,
        case_tag,
        sun_face,
        dominant_axis,
        times_s,
        y_all,
        pred_sunface,
        pred_static,
        pred_no,
        features_df["t_sunface_c"].to_numpy(dtype=float),
        train_mask,
    )

    print(f"Case: {case_id}")
    print(f"Sun direction: {sun_face}")
    print(f"Dominant axis: {dominant_axis}")
    print(f"Features: {', '.join(feature_names)}")
    print(f"Train samples: {int(train_mask.sum())}, Test samples: {int(test_mask.sum())}")
    print(f"Predictions: {predictions_path}")
    print(f"Metrics: {metrics_path}")
    print(f"Coefficients: {coef_path}")
    print(f"Plot: {plot_path}")
    print()
    metrics_df = pd.DataFrame(metrics_rows)
    metric_cols = [
        "model",
        "rmse_x_urad" if dominant_axis == "x" else "rmse_y_urad",
        "rmse_norm_urad",
        "p95_error_norm_urad",
        "max_error_norm_urad",
    ]
    for split in ("train", "test"):
        print(f"--- {split} ---")
        sub = metrics_df[metrics_df["split"] == split][metric_cols]
        print(sub.to_string(index=False))


if __name__ == "__main__":
    main()
