"""Paper-oriented plots for hierarchical sunface ΔT (bcase) validation."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pat_acquisition.models._common.targets import extract_targets
from pat_acquisition.models.sunface_deltaT_bcase_los.dataset import (
    load_case_frame,
    within_case_split_mask,
)
from pat_acquisition.models.sunface_deltaT_bcase_los.model import BCaseConfig
from pat_acquisition.models.sunface_deltaT_los.features import (
    DeltaTFeatureConfig,
    SUN_FACE_OPPOSITE,
    build_deltaT_features,
    normalize_sun_direction,
    resolve_dominant_axis,
)

FACE_ORDER = ("MX", "MY", "PX", "PY")
FACE_COLORS = {
    "MX": "#1f77b4",
    "MY": "#ff7f0e",
    "PX": "#2ca02c",
    "PY": "#d62728",
}

# Representative cases for hierarchical true-vs-pred (paper P2).
DEFAULT_TIMESERIES_CASES = (
    "04",  # MY ALL — standard heat
    "08",  # PY ALL — large raw scale
    "09",  # MX ALL
    "15",  # MY STTLCT — no component heat
    "10",  # HOT — Level-2 limitation
    "11",  # Black — higher residual floor
)


def _case_tag(case_id: str) -> str:
    # "04_LTAN..." -> "case04"
    prefix = str(case_id).split("_", 1)[0]
    if prefix.isdigit():
        return f"case{int(prefix):02d}"
    return f"case_{prefix}"


def _short_case_label(case_id: str) -> str:
    prefix = str(case_id).split("_", 1)[0]
    return prefix if prefix.isdigit() else str(case_id)[:12]


def plot_a_emp_by_sunface(
    case_table: pd.DataFrame,
    a_shared: dict[str, float],
    out_png: Path,
) -> None:
    """P3: within-case a_emp vs shared a (cross-case stability)."""
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    rng = np.random.default_rng(0)

    for i, face in enumerate(FACE_ORDER):
        sub = case_table[case_table["sun_face"] == face]
        if sub.empty:
            continue
        a_vals = sub["a_emp_urad_per_c"].to_numpy(dtype=float)
        x = np.full(len(a_vals), i, dtype=float) + rng.uniform(-0.12, 0.12, size=len(a_vals))
        ax.scatter(
            x,
            a_vals,
            color=FACE_COLORS[face],
            s=42,
            alpha=0.85,
            zorder=3,
            label=f"{face} a_emp",
        )
        if face in a_shared:
            ax.hlines(
                a_shared[face],
                i - 0.35,
                i + 0.35,
                colors=FACE_COLORS[face],
                linestyles="--",
                linewidth=1.8,
                zorder=2,
            )

    ax.set_xticks(range(len(FACE_ORDER)))
    ax.set_xticklabels(FACE_ORDER)
    ax.set_ylabel(r"$a$ [µrad/°C]")
    ax.set_xlabel("Sun face")
    ax.set_title(r"Cross-case $a_\mathrm{emp}$ and shared $a$ (median)")
    ax.grid(True, axis="y", alpha=0.3)
    ax.axhline(0.0, color="k", linewidth=0.6, alpha=0.4)
    # Compact legend: one entry explaining dashed = shared
    ax.plot([], [], "k--", label=r"$a_\mathrm{shared}$ (median)")
    ax.legend(fontsize=8, loc="best")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def plot_b_emp_vs_b_pred(case_table: pd.DataFrame, out_png: Path) -> None:
    """P3: Level-2 b_emp vs b_pred (in-sample + LOO)."""
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.4), sharex=True, sharey=True)

    panels = (
        ("b_pred_insample_urad", "In-sample Level-2"),
        ("b_pred_loo_urad", "Leave-one-case-out"),
    )
    for ax, (pred_col, title) in zip(axes, panels):
        for face in FACE_ORDER:
            sub = case_table[case_table["sun_face"] == face]
            if sub.empty:
                continue
            x = sub["b_emp_urad"].to_numpy(dtype=float)
            y = sub[pred_col].to_numpy(dtype=float)
            ok = np.isfinite(x) & np.isfinite(y)
            ax.scatter(
                x[ok],
                y[ok],
                color=FACE_COLORS[face],
                s=48,
                alpha=0.9,
                label=face,
                zorder=3,
            )
            for case_id, xb, yb in zip(
                sub["case_id"].to_numpy()[ok],
                x[ok],
                y[ok],
            ):
                ax.annotate(
                    _short_case_label(str(case_id)),
                    (float(xb), float(yb)),
                    textcoords="offset points",
                    xytext=(3, 3),
                    fontsize=7,
                    alpha=0.75,
                )

        all_b = case_table["b_emp_urad"].to_numpy(dtype=float)
        pred = case_table[pred_col].to_numpy(dtype=float)
        ok = np.isfinite(all_b) & np.isfinite(pred)
        if np.any(ok):
            lo = float(min(all_b[ok].min(), pred[ok].min()))
            hi = float(max(all_b[ok].max(), pred[ok].max()))
            pad = 0.08 * (hi - lo + 1.0)
            lim = (lo - pad, hi + pad)
            ax.plot(lim, lim, "k--", linewidth=1.0, alpha=0.7, label="1:1")
            ax.set_xlim(lim)
            ax.set_ylim(lim)
            rmse = float(np.sqrt(np.mean((all_b[ok] - pred[ok]) ** 2)))
            ax.text(
                0.04,
                0.96,
                f"RMSE = {rmse:.2g} µrad",
                transform=ax.transAxes,
                va="top",
                fontsize=9,
                bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none"},
            )

        ax.set_title(title)
        ax.set_xlabel(r"$b_\mathrm{emp}$ [µrad]")
        ax.set_ylabel(r"$b_\mathrm{pred}$ [µrad]")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, alpha=0.3)

    handles, labels = axes[0].get_legend_handles_labels()
    seen: set[str] = set()
    uniq_handles: list = []
    uniq_labels: list[str] = []
    for handle, label in zip(handles, labels):
        if label in seen:
            continue
        seen.add(label)
        uniq_handles.append(handle)
        uniq_labels.append(label)
    fig.legend(
        uniq_handles,
        uniq_labels,
        loc="upper center",
        ncol=5,
        fontsize=8,
        frameon=False,
        bbox_to_anchor=(0.5, 1.02),
    )
    fig.suptitle(r"Level-2 case bias: $b_\mathrm{emp}$ vs $b_\mathrm{pred}$", y=1.08)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _dominant_series(
    case_df: pd.DataFrame,
    config: BCaseConfig,
) -> tuple[str, str, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    sun_direction = case_df["case_sun_direction_body"].iloc[0]
    sun_face = normalize_sun_direction(sun_direction)
    dominant_axis = resolve_dominant_axis(sun_face)
    x_all, _, feat, _ = build_deltaT_features(
        case_df, sun_direction, DeltaTFeatureConfig(ridge_lam=config.ridge_lam)
    )
    y_all = extract_targets(case_df)
    times_s = case_df["time_s"].to_numpy(dtype=float)
    axis_idx = 0 if dominant_axis == "x" else 1
    return (
        sun_face,
        dominant_axis,
        times_s,
        y_all[:, axis_idx],
        x_all[:, 0],
        feat["t_sunface_c"].to_numpy(dtype=float),
    )


def plot_hierarchical_timeseries(
    case_df: pd.DataFrame,
    *,
    case_id: str,
    b_urad: float,
    a_urad_per_c: float,
    config: BCaseConfig,
    out_png: Path,
    b_label: str = r"$b_\mathrm{pred}$",
) -> dict[str, float]:
    """P2: true vs hierarchical prediction on dominant axis."""
    sun_face, dominant_axis, times_s, y_dom, delta_t, t_sun = _dominant_series(
        case_df, config
    )
    train_mask = within_case_split_mask(
        times_s, config.orbit_period_s, config.train_orbits
    )
    y_hat = b_urad + a_urad_per_c * delta_t
    resid = y_dom - y_hat
    raw_rms = float(np.sqrt(np.mean(y_dom**2)))
    raw_peak = float(np.max(np.abs(y_dom)))
    test_mask = ~train_mask
    rmse_test = (
        float(np.sqrt(np.mean(resid[test_mask] ** 2))) if np.any(test_mask) else float("nan")
    )

    t_min = times_s / 60.0
    train_end_min = float(times_s[train_mask][-1] / 60.0) if np.any(train_mask) else t_min[0]
    opposite = SUN_FACE_OPPOSITE.get(sun_face, "?")
    case_tag = _case_tag(case_id)

    fig, axes = plt.subplots(3, 1, figsize=(10.5, 8.0), sharex=True)

    axes[0].plot(t_min, t_sun, color="#d62728", label=f"T_{sun_face} center")
    axes[0].plot(t_min, delta_t, color="#1f77b4", linestyle="--", label=f"ΔT ({sun_face}-{opposite})")
    axes[0].axvline(train_end_min, color="k", linestyle=":", alpha=0.7, label="train/test")
    axes[0].set_ylabel("T [°C]")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(fontsize=8)

    axes[1].plot(t_min, y_dom, label=f"true {dominant_axis}")
    axes[1].plot(
        t_min,
        y_hat,
        "--",
        label=rf"bcase: {b_label}+$a_\mathrm{{shared}}$·ΔT",
    )
    axes[1].axvline(train_end_min, color="k", linestyle=":", alpha=0.7)
    axes[1].set_ylabel(f"LOS {dominant_axis} [µrad]")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(fontsize=8)

    axes[2].plot(t_min, resid, color="#9467bd", label="residual")
    axes[2].axhline(0.0, color="k", linewidth=0.6, alpha=0.5)
    axes[2].axvline(train_end_min, color="k", linestyle=":", alpha=0.7)
    axes[2].set_ylabel("residual [µrad]")
    axes[2].set_xlabel("Time [min]")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(fontsize=8)

    fig.suptitle(
        f"{case_tag} hierarchical bcase  |  sun={sun_face}  |  "
        f"raw RMS={raw_rms:.0f}, peak={raw_peak:.0f} → test RMSE={rmse_test:.2g} µrad"
    )
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)

    return {
        "raw_rms_dom_urad": raw_rms,
        "raw_peak_dom_urad": raw_peak,
        "rmse_dom_test_urad": rmse_test,
    }


def build_raw_scale_table(
    dataset_path: Path,
    case_table: pd.DataFrame,
    metrics_df: pd.DataFrame,
    config: BCaseConfig,
) -> pd.DataFrame:
    """Raw dominant-axis scale vs hierarchical test RMSE (for P5 / tables)."""
    hier = metrics_df[metrics_df["model"] == "b_pred_insample_a_shared"].set_index("case_id")
    rows: list[dict[str, float | str]] = []
    for row in case_table.itertuples(index=False):
        case_df = load_case_frame(dataset_path, str(row.case_id))
        _sun, _dom, _t, y_dom, _dt, _ts = _dominant_series(case_df, config)
        case_id = str(row.case_id)
        rmse = (
            float(hier.loc[case_id, "rmse_dom_test_urad"])
            if case_id in hier.index
            else float("nan")
        )
        rows.append(
            {
                "case_id": case_id,
                "sun_face": str(row.sun_face),
                "i_prop": int(row.i_prop),
                "i_pcdu": int(row.i_pcdu),
                "raw_rms_dom_urad": float(np.sqrt(np.mean(y_dom**2))),
                "raw_peak_dom_urad": float(np.max(np.abs(y_dom))),
                "rmse_bcase_test_urad": rmse,
                "b_emp_urad": float(row.b_emp_urad),
                "b_pred_insample_urad": float(row.b_pred_insample_urad),
                "a_emp_urad_per_c": float(row.a_emp_urad_per_c),
            }
        )
    return pd.DataFrame(rows)


def plot_raw_vs_model_rmse(scale_table: pd.DataFrame, out_png: Path) -> None:
    """P5: raw dominant RMS vs hierarchical test RMSE (log scale)."""
    # Prefer a compact paper-friendly subset, fall back to all.
    preferred = {"04", "08", "09", "10", "11", "15"}
    labels = scale_table["case_id"].map(_short_case_label)
    mask = labels.isin(preferred)
    plot_df = scale_table.loc[mask].copy() if mask.any() else scale_table.copy()
    plot_df = plot_df.sort_values("case_id").reset_index(drop=True)
    x = np.arange(len(plot_df))
    width = 0.36
    short = plot_df["case_id"].map(_short_case_label)

    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    ax.bar(
        x - width / 2,
        plot_df["raw_rms_dom_urad"],
        width,
        label="raw RMS (dominant)",
        color="#7f7f7f",
    )
    ax.bar(
        x + width / 2,
        plot_df["rmse_bcase_test_urad"],
        width,
        label="bcase test RMSE",
        color="#1f77b4",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{lab}\n{face}" for lab, face in zip(short, plot_df["sun_face"])],
        fontsize=8,
    )
    ax.set_ylabel("µrad")
    ax.set_yscale("log")
    ax.set_title("Order-of-magnitude reduction: raw LOS vs hierarchical bcase")
    ax.grid(True, axis="y", which="both", alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def resolve_timeseries_case_ids(
    case_table: pd.DataFrame,
    requested: tuple[str, ...] | list[str] | None = None,
) -> list[str]:
    wanted = tuple(requested) if requested is not None else DEFAULT_TIMESERIES_CASES
    by_num: dict[str, str] = {}
    for case_id in case_table["case_id"].astype(str):
        prefix = case_id.split("_", 1)[0]
        if prefix.isdigit():
            by_num[f"{int(prefix):02d}"] = case_id
            by_num[str(int(prefix))] = case_id
    out: list[str] = []
    for key in wanted:
        k = key.strip()
        if k in by_num:
            out.append(by_num[k])
        elif k in set(case_table["case_id"].astype(str)):
            out.append(k)
    return out


def plot_pat_summary(summary_df: pd.DataFrame, out_png: Path) -> None:
    """P4: cross-case mean acquisition time for no / static / bcase / truth."""
    focus = (
        "no_correction",
        "static_bias_correction",
        "bcase_correction",
        "thermal_truth_correction",
    )
    labels = {
        "no_correction": "no",
        "static_bias_correction": "static",
        "bcase_correction": "bcase",
        "thermal_truth_correction": "truth",
    }
    colors = {
        "no_correction": "#7f7f7f",
        "static_bias_correction": "#ff7f0e",
        "bcase_correction": "#1f77b4",
        "thermal_truth_correction": "#2ca02c",
    }

    sub = summary_df[summary_df["model"].isin(focus)].copy()
    if sub.empty:
        return

    def _short(case_id: str) -> str:
        prefix = str(case_id).split("_", 1)[0]
        return prefix if prefix.isdigit() else str(case_id)[:10]

    sub["case_label"] = sub["case_id"].map(_short)
    # Stable case order by numeric prefix when possible.
    case_order = (
        sub.drop_duplicates("case_id")
        .assign(_n=lambda d: pd.to_numeric(d["case_label"], errors="coerce"))
        .sort_values(["_n", "case_id"])["case_id"]
        .tolist()
    )
    case_labels = [_short(c) for c in case_order]
    x = np.arange(len(case_order))
    width = 0.2
    offsets = {
        "no_correction": -1.5 * width,
        "static_bias_correction": -0.5 * width,
        "bcase_correction": 0.5 * width,
        "thermal_truth_correction": 1.5 * width,
    }

    fig, ax = plt.subplots(figsize=(max(8.5, 0.55 * len(case_order) + 3), 4.6))
    for model in focus:
        msub = sub[sub["model"] == model].set_index("case_id")
        vals = [
            float(msub.loc[c, "mean_acquisition_time_s"]) if c in msub.index else np.nan
            for c in case_order
        ]
        # Floor for log scale (dwell time is the practical lower bound).
        vals = [max(v, 0.1) if np.isfinite(v) else np.nan for v in vals]
        ax.bar(
            x + offsets[model],
            vals,
            width,
            label=labels[model],
            color=colors[model],
        )

    ax.set_xticks(x)
    ax.set_xticklabels(case_labels, fontsize=8)
    ax.set_ylabel("Mean acquisition time [s]")
    ax.set_xlabel("Case")
    ax.set_yscale("log")
    ax.set_ylim(0.08, None)
    ax.set_title("PAT comparison: no / static / bcase / thermal truth")
    ax.grid(True, axis="y", which="both", alpha=0.3)
    ax.legend(fontsize=8, ncol=4, loc="upper right")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def write_paper_plots(
    *,
    dataset_path: Path,
    case_table: pd.DataFrame,
    metrics_df: pd.DataFrame,
    a_shared: dict[str, float],
    config: BCaseConfig,
    out_dir: Path,
    timeseries_cases: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Path]:
    """Write P2/P3/P5 plots and scale table. Returns output paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    p3_a = out_dir / "bcase_a_emp_by_sunface.png"
    plot_a_emp_by_sunface(case_table, a_shared, p3_a)
    paths["p3_a"] = p3_a

    p3_b = out_dir / "bcase_b_emp_vs_b_pred.png"
    plot_b_emp_vs_b_pred(case_table, p3_b)
    paths["p3_b"] = p3_b

    scale_table = build_raw_scale_table(dataset_path, case_table, metrics_df, config)
    scale_path = out_dir / "bcase_raw_vs_model_scale.csv"
    scale_display = out_dir / "bcase_raw_vs_model_scale_display.csv"
    scale_table.to_csv(scale_path, index=False, encoding="utf-8-sig")
    scale_table.to_csv(
        scale_display, index=False, encoding="utf-8-sig", float_format="%.3g"
    )
    paths["scale_csv"] = scale_path

    p5 = out_dir / "bcase_raw_vs_model_rmse.png"
    plot_raw_vs_model_rmse(scale_table, p5)
    paths["p5"] = p5

    ts_dir = out_dir / "timeseries"
    case_lookup = case_table.set_index("case_id")
    for case_id in resolve_timeseries_case_ids(case_table, timeseries_cases):
        row = case_lookup.loc[case_id]
        case_df = load_case_frame(dataset_path, case_id)
        tag = _case_tag(case_id)
        out_png = ts_dir / f"{tag}_bcase_true_vs_pred.png"
        plot_hierarchical_timeseries(
            case_df,
            case_id=case_id,
            b_urad=float(row["b_pred_insample_urad"]),
            a_urad_per_c=float(a_shared[str(row["sun_face"])]),
            config=config,
            out_png=out_png,
            b_label=r"$b_\mathrm{pred}$",
        )
        paths[f"p2_{tag}"] = out_png

    return paths
