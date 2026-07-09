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
from pat_acquisition.models.temperature_los.dataset import (  # noqa: E402
    DEFAULT_DATASET,
    DEFAULT_OUTPUT_DIR,
    load_split_frames,
)
from pat_acquisition.models.temperature_los.features import (  # noqa: E402
    TemperatureFeatureConfig,
    build_temperature_features,
    train_ridge_temperature_model,
)
from pat_acquisition.models.temperature_los.model import predict_ridge  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Train/evaluate temperature-based LOS lightweight model "
            "with case_id-level split."
        )
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--t-ref-c", type=float, default=23.9)
    parser.add_argument("--ridge-lam", type=float, default=1e-3)
    parser.add_argument("--no-dtmid-dt", action="store_true")
    parser.add_argument(
        "--plot-splits",
        nargs="*",
        default=["val", "test"],
        help="Splits to generate per-case time-series plots for.",
    )
    return parser.parse_args()


def _collect_predictions(
    source_df: pd.DataFrame,
    y_true: np.ndarray,
    pred_no: np.ndarray,
    pred_static: np.ndarray,
    pred_ridge: np.ndarray,
) -> pd.DataFrame:
    out = source_df.loc[:, ["case_id", "split", "time_s"]].copy()
    out["dtheta_x_true_urad"] = y_true[:, 0]
    out["dtheta_y_true_urad"] = y_true[:, 1]
    out["dtheta_x_pred_no_correction_urad"] = pred_no[:, 0]
    out["dtheta_y_pred_no_correction_urad"] = pred_no[:, 1]
    out["dtheta_x_pred_static_bias_urad"] = pred_static[:, 0]
    out["dtheta_y_pred_static_bias_urad"] = pred_static[:, 1]
    out["dtheta_x_pred_temperature_ridge_urad"] = pred_ridge[:, 0]
    out["dtheta_y_pred_temperature_ridge_urad"] = pred_ridge[:, 1]
    return out


def _evaluate_one_split(
    split_name: str,
    split_df: pd.DataFrame,
    y_train: np.ndarray,
    ridge_pred: np.ndarray,
) -> list[dict[str, float | str]]:
    if split_df.empty:
        return []
    y_true = extract_targets(split_df)
    pred_no = predict_no_correction(len(split_df))
    pred_static = predict_static_bias(y_train, len(split_df))
    evaluations: list[tuple[str, np.ndarray]] = [
        ("no_correction", pred_no),
        ("static_bias_correction", pred_static),
        ("temperature_ridge_correction", ridge_pred),
    ]
    rows: list[dict[str, float | str]] = []
    for model_name, pred in evaluations:
        m = compute_error_metrics(y_true, pred)
        rows.append({"split": split_name, "model": model_name, **m})
    return rows


def _plot_case_timeseries(case_df: pd.DataFrame, out_png: Path) -> None:
    case_df = case_df.sort_values("time_s")
    t_min = case_df["time_s"].to_numpy(dtype=float) / 60.0

    true_x = case_df["dtheta_x_true_urad"].to_numpy(dtype=float)
    true_y = case_df["dtheta_y_true_urad"].to_numpy(dtype=float)
    pred_rx = case_df["dtheta_x_pred_temperature_ridge_urad"].to_numpy(dtype=float)
    pred_ry = case_df["dtheta_y_pred_temperature_ridge_urad"].to_numpy(dtype=float)
    pred_nx = case_df["dtheta_x_pred_no_correction_urad"].to_numpy(dtype=float)
    pred_ny = case_df["dtheta_y_pred_no_correction_urad"].to_numpy(dtype=float)
    pred_sx = case_df["dtheta_x_pred_static_bias_urad"].to_numpy(dtype=float)
    pred_sy = case_df["dtheta_y_pred_static_bias_urad"].to_numpy(dtype=float)

    err_no = np.linalg.norm(np.column_stack([true_x - pred_nx, true_y - pred_ny]), axis=1)
    err_static = np.linalg.norm(np.column_stack([true_x - pred_sx, true_y - pred_sy]), axis=1)
    err_ridge = np.linalg.norm(np.column_stack([true_x - pred_rx, true_y - pred_ry]), axis=1)

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

    axes[0].plot(t_min, true_x, label="true x")
    axes[0].plot(t_min, pred_rx, "--", label="ridge pred x")
    axes[0].set_ylabel("dtheta x [urad]")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(fontsize=8)

    axes[1].plot(t_min, true_y, label="true y")
    axes[1].plot(t_min, pred_ry, "--", label="ridge pred y")
    axes[1].set_ylabel("dtheta y [urad]")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(fontsize=8)

    axes[2].plot(t_min, err_no, label="no_correction")
    axes[2].plot(t_min, err_static, label="static_bias")
    axes[2].plot(t_min, err_ridge, label="temperature_ridge")
    axes[2].set_ylabel("error norm [urad]")
    axes[2].set_xlabel("Time [min]")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(fontsize=8)

    case_id = str(case_df["case_id"].iloc[0])
    split = str(case_df["split"].iloc[0])
    fig.suptitle(f"{case_id} ({split})")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    df, train_df, val_df, test_df = load_split_frames(args.dataset)

    config = TemperatureFeatureConfig(
        t_ref_c=args.t_ref_c,
        ridge_lam=args.ridge_lam,
        include_dtmid_dt=not args.no_dtmid_dt,
    )

    x_all, feature_names, feature_df = build_temperature_features(df, config)
    df_features = pd.concat([df.reset_index(drop=True), feature_df.reset_index(drop=True)], axis=1)

    split_mask = {
        "train": (df_features["split"] == "train").to_numpy(),
        "val": (df_features["split"] == "val").to_numpy(),
        "test": (df_features["split"] == "test").to_numpy(),
    }

    x_train = x_all[split_mask["train"]]
    y_train = extract_targets(train_df)
    ridge_model = train_ridge_temperature_model(
        x_train=x_train,
        y_train=y_train,
        feature_names=feature_names,
        config=config,
    )

    y_all = extract_targets(df_features)
    pred_ridge_all = predict_ridge(ridge_model, x_all)
    pred_no_all = predict_no_correction(len(df_features))
    pred_static_all = predict_static_bias(y_train, len(df_features))

    predictions_df = _collect_predictions(
        source_df=df_features,
        y_true=y_all,
        pred_no=pred_no_all,
        pred_static=pred_static_all,
        pred_ridge=pred_ridge_all,
    )

    metrics_rows: list[dict[str, float | str]] = []
    for split_name in ("train", "val", "test"):
        mask = split_mask[split_name]
        split_subset = df_features.loc[mask]
        if split_subset.empty:
            continue
        metrics_rows.extend(
            _evaluate_one_split(
                split_name=split_name,
                split_df=split_subset,
                y_train=y_train,
                ridge_pred=pred_ridge_all[mask],
            )
        )
    metrics_df = pd.DataFrame(metrics_rows)

    coef_df = pd.DataFrame(
        {
            "feature": ["intercept", *ridge_model.feature_names],
            "coef_x_urad": ridge_model.coef[:, 0],
            "coef_y_urad": ridge_model.coef[:, 1],
        }
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = args.output_dir / "temperature_los_predictions.csv"
    metrics_path = args.output_dir / "temperature_los_metrics.csv"
    coefficients_path = args.output_dir / "temperature_los_coefficients.csv"

    predictions_df.to_csv(predictions_path, index=False, encoding="utf-8-sig")
    metrics_df.to_csv(metrics_path, index=False, encoding="utf-8-sig")
    coef_df.to_csv(coefficients_path, index=False, encoding="utf-8-sig")

    plots_dir = args.output_dir / "timeseries_plots"
    plot_splits = {s.strip().lower() for s in args.plot_splits}
    plot_df = predictions_df[predictions_df["split"].isin(plot_splits)]
    for (split, case_id), group in plot_df.groupby(["split", "case_id"]):
        out_png = plots_dir / split / f"{case_id}_true_vs_pred.png"
        _plot_case_timeseries(group, out_png)

    print(f"Dataset: {args.dataset}")
    print(f"Output directory: {args.output_dir}")
    print(f"Feature count: {len(feature_names)}")
    print(f"Features: {', '.join(feature_names)}")
    print(f"Predictions CSV: {predictions_path}")
    print(f"Metrics CSV: {metrics_path}")
    print(f"Coefficients CSV: {coefficients_path}")
    if not plot_df.empty:
        print(f"Time-series plots: {plots_dir}")


if __name__ == "__main__":
    main()
