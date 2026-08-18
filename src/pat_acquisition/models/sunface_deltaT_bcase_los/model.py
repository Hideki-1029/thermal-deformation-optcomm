"""Two-level model: LOS ≈ b_case + a(sun)·ΔT,  b_case ≈ b0(sun)+c_p·I_prop+c_c·I_pcdu.

Both axes are predicted from pre-launch thermal analysis only:

  dominant axis:     b_dom(sun, flags) + a_shared(sun) · ΔT(t)
  non-dominant axis: b_nd(sun, flags)   (constant DC)

Heat flags affect the y-axis LOS, so the Level-2 design gates I_prop/I_pcdu
on sun faces MY/PY for the dominant axis and on MX/PX for the non-dominant
axis (where the non-dominant component is the y axis).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from pat_acquisition.models._common.ridge import ridge_fit_with_intercept
from pat_acquisition.models._common.targets import extract_targets
from pat_acquisition.models.sunface_deltaT_bcase_los.dataset import (
    load_case_frame,
    within_case_split_mask,
)
from pat_acquisition.models.sunface_deltaT_bcase_los.features import (
    DEFAULT_HEAT_FACES,
    build_bcase_design_matrix,
    case_heat_flags,
)
from pat_acquisition.models.sunface_deltaT_los.features import (
    DeltaTFeatureConfig,
    build_deltaT_features,
    normalize_sun_direction,
    resolve_dominant_axis,
)

__all__ = [
    "BCaseConfig",
    "BCaseLevel2Model",
    "estimate_case_deltaT_params",
    "evaluate_case_timeseries_with_b",
    "fit_bcase_level2",
    "predict_bcase",
    "predict_bcase_xy",
    "resolve_operational_params",
    "run_bcase_pipeline",
]


@dataclass(frozen=True)
class BCaseConfig:
    ridge_lam: float = 1e-3
    heat_faces: tuple[str, ...] = DEFAULT_HEAT_FACES
    # Sun faces where heat flags apply for the non-dominant-axis Level-2.
    # Flags act on the y-axis LOS, which is non-dominant for MX/PX sun.
    nd_heat_faces: tuple[str, ...] = ("MX", "PX")
    orbit_period_s: float = 6052.0
    train_orbits: float = 1.0
    # Level-2 uses ordinary least squares (no ridge) unless lam > 0.
    level2_ridge_lam: float = 0.0


@dataclass(frozen=True)
class BCaseLevel2Model:
    feature_names: tuple[str, ...]
    coef: np.ndarray  # shape (n_features,) — no separate intercept; b0_* are intercepts
    heat_faces: tuple[str, ...]

    def predict(self, sun_faces, i_prop, i_pcdu) -> np.ndarray:
        x, names = build_bcase_design_matrix(
            sun_faces, i_prop, i_pcdu, heat_faces=self.heat_faces
        )
        if tuple(names) != self.feature_names:
            raise ValueError("Design matrix feature names do not match fitted model")
        return x @ self.coef


def estimate_case_deltaT_params(
    case_df: pd.DataFrame,
    config: BCaseConfig,
) -> dict[str, float | str | int]:
    """Within-case train-orbit fit of LOS_dom ≈ b + a·ΔT."""
    sun_direction = case_df["case_sun_direction_body"].iloc[0]
    sun_face = normalize_sun_direction(sun_direction)
    dominant_axis = resolve_dominant_axis(sun_face)
    i_prop, i_pcdu = case_heat_flags(case_df)

    x_all, _names, _feat, _ = build_deltaT_features(
        case_df, sun_direction, DeltaTFeatureConfig(ridge_lam=config.ridge_lam)
    )
    y_all = extract_targets(case_df)
    times_s = case_df["time_s"].to_numpy(dtype=float)
    train_mask = within_case_split_mask(times_s, config.orbit_period_s, config.train_orbits)
    if not np.any(train_mask):
        raise ValueError("Empty train split for case deltaT fit")

    axis_idx = 0 if dominant_axis == "x" else 1
    coef = ridge_fit_with_intercept(
        x_all[train_mask],
        y_all[train_mask, axis_idx].reshape(-1, 1),
        lam=config.ridge_lam,
    )[:, 0]
    b_emp = float(coef[0])
    a_emp = float(coef[1])

    # Non-dominant axis: train-orbit DC mean (Level-1 target for b_nd).
    nd_axis_idx = 1 - axis_idx
    b_nd_emp = float(np.mean(y_all[train_mask, nd_axis_idx]))

    # Also report mean residual with this fit on all times (diagnostics).
    y_hat = b_emp + a_emp * x_all[:, 0]
    resid = y_all[:, axis_idx] - y_hat

    return {
        "sun_face": sun_face,
        "dominant_axis": dominant_axis,
        "i_prop": int(i_prop),
        "i_pcdu": int(i_pcdu),
        "b_emp_urad": b_emp,
        "b_nd_emp_urad": b_nd_emp,
        "a_emp_urad_per_c": a_emp,
        "train_samples": int(train_mask.sum()),
        "resid_std_urad": float(np.std(resid)),
        "power_mode": str(case_df["case_power_mode"].iloc[0])
        if "case_power_mode" in case_df.columns
        else "",
    }


def fit_bcase_level2(
    case_table: pd.DataFrame,
    config: BCaseConfig,
    *,
    target_col: str = "b_emp_urad",
    heat_faces: tuple[str, ...] | None = None,
) -> BCaseLevel2Model:
    """Fit Level-2: b_emp ~ design(sun, I_prop, I_pcdu)."""
    required = {"sun_face", "i_prop", "i_pcdu", target_col}
    missing = required.difference(case_table.columns)
    if missing:
        raise ValueError(f"case_table missing columns: {sorted(missing)}")

    effective_heat_faces = config.heat_faces if heat_faces is None else heat_faces
    x, names = build_bcase_design_matrix(
        case_table["sun_face"],
        case_table["i_prop"],
        case_table["i_pcdu"],
        heat_faces=effective_heat_faces,
    )
    y = case_table[target_col].to_numpy(dtype=float)
    if config.level2_ridge_lam > 0.0:
        # Regularize only heat coefficients; keep b0_* unpenalized via diag mask.
        xtx = x.T @ x
        reg = config.level2_ridge_lam * np.eye(x.shape[1])
        for i, name in enumerate(names):
            if name.startswith("b0_"):
                reg[i, i] = 0.0
        coef = np.linalg.solve(xtx + reg, x.T @ y)
    else:
        coef, *_ = np.linalg.lstsq(x, y, rcond=None)

    return BCaseLevel2Model(
        feature_names=tuple(names),
        coef=np.asarray(coef, dtype=float),
        heat_faces=tuple(effective_heat_faces),
    )


def predict_bcase(
    model: BCaseLevel2Model,
    sun_face: str,
    i_prop: int,
    i_pcdu: int,
) -> float:
    return float(model.predict([sun_face], [i_prop], [i_pcdu])[0])


def resolve_operational_params(
    row: pd.Series,
    a_shared: dict[str, float],
    b_mode: str = "loo",
) -> tuple[float, float, float]:
    """Per-case (b_dom, b_nd, a) from a pipeline case_table row.

    With ``b_mode="loo"`` the nested leave-one-case-out predictions are used,
    so all parameters are fully out-of-sample for the case. Falls back to the
    in-sample fit when LOO was skipped (e.g. too few training cases).
    """
    if b_mode == "insample":
        return (
            float(row["b_pred_insample_urad"]),
            float(row["b_nd_pred_insample_urad"]),
            float(a_shared[str(row["sun_face"])]),
        )
    b = float(row["b_pred_loo_urad"])
    if not np.isfinite(b):
        b = float(row["b_pred_insample_urad"])
    b_nd = float(row["b_nd_pred_loo_urad"])
    if not np.isfinite(b_nd):
        b_nd = float(row["b_nd_pred_insample_urad"])
    a = float(row["a_shared_loo_urad_per_c"])
    if not np.isfinite(a):
        a = float(a_shared[str(row["sun_face"])])
    return b, b_nd, a


def shared_a_by_sun_face(case_table: pd.DataFrame) -> dict[str, float]:
    """Median within-case a for each sun face."""
    out: dict[str, float] = {}
    for face, group in case_table.groupby("sun_face"):
        out[str(face)] = float(np.median(group["a_emp_urad_per_c"].to_numpy(dtype=float)))
    return out


def run_bcase_pipeline(
    *,
    dataset_path,
    case_ids: list[str],
    config: BCaseConfig,
) -> dict[str, pd.DataFrame | BCaseLevel2Model | dict[str, float]]:
    """
    Estimate per-case (a,b), fit Level-2 on all cases, and LOO predict b.

    Returns dict with:
      case_table, level2_model, level2_coef_table, a_shared, loo_table
    """
    rows: list[dict[str, float | str | int]] = []
    for case_id in case_ids:
        case_df = load_case_frame(dataset_path, case_id)
        params = estimate_case_deltaT_params(case_df, config)
        params["case_id"] = case_id
        rows.append(params)

    case_table = pd.DataFrame(rows)
    if case_table.empty:
        raise RuntimeError("No cases processed")

    level2 = fit_bcase_level2(case_table, config)
    level2_nd = fit_bcase_level2(
        case_table, config, target_col="b_nd_emp_urad", heat_faces=config.nd_heat_faces
    )
    case_table["b_pred_insample_urad"] = level2.predict(
        case_table["sun_face"], case_table["i_prop"], case_table["i_pcdu"]
    )
    case_table["b_resid_insample_urad"] = (
        case_table["b_emp_urad"] - case_table["b_pred_insample_urad"]
    )
    case_table["b_nd_pred_insample_urad"] = level2_nd.predict(
        case_table["sun_face"], case_table["i_prop"], case_table["i_pcdu"]
    )
    case_table["b_nd_resid_insample_urad"] = (
        case_table["b_nd_emp_urad"] - case_table["b_nd_pred_insample_urad"]
    )

    a_shared = shared_a_by_sun_face(case_table)

    # Nested leave-one-case-out: Level-2 (both axes) and a_shared are all
    # refit without the held-out case, so predictions are fully out-of-sample.
    loo_b = np.full(len(case_table), np.nan, dtype=float)
    loo_b_nd = np.full(len(case_table), np.nan, dtype=float)
    loo_a = np.full(len(case_table), np.nan, dtype=float)
    for i in range(len(case_table)):
        train = case_table.drop(index=case_table.index[i])
        if train["sun_face"].nunique() < 1 or len(train) < 3:
            continue
        # Need each sun face present in train for that face's b0; if held-out
        # face has no other case, fall back to insample b0 by skipping LOO.
        face = str(case_table.iloc[i]["sun_face"])
        if (train["sun_face"] == face).sum() < 1:
            continue
        model_i = fit_bcase_level2(train, config)
        model_nd_i = fit_bcase_level2(
            train, config, target_col="b_nd_emp_urad", heat_faces=config.nd_heat_faces
        )
        loo_b[i] = predict_bcase(
            model_i,
            face,
            int(case_table.iloc[i]["i_prop"]),
            int(case_table.iloc[i]["i_pcdu"]),
        )
        loo_b_nd[i] = predict_bcase(
            model_nd_i,
            face,
            int(case_table.iloc[i]["i_prop"]),
            int(case_table.iloc[i]["i_pcdu"]),
        )
        loo_a[i] = shared_a_by_sun_face(train)[face]

    case_table["b_pred_loo_urad"] = loo_b
    case_table["b_resid_loo_urad"] = case_table["b_emp_urad"] - case_table["b_pred_loo_urad"]
    case_table["b_nd_pred_loo_urad"] = loo_b_nd
    case_table["b_nd_resid_loo_urad"] = (
        case_table["b_nd_emp_urad"] - case_table["b_nd_pred_loo_urad"]
    )
    case_table["a_shared_urad_per_c"] = case_table["sun_face"].map(a_shared)
    case_table["a_shared_loo_urad_per_c"] = loo_a

    coef_table = pd.DataFrame(
        {
            "feature": list(level2.feature_names),
            "coef_urad": level2.coef,
        }
    )
    coef_nd_table = pd.DataFrame(
        {
            "feature": list(level2_nd.feature_names),
            "coef_urad": level2_nd.coef,
        }
    )

    return {
        "case_table": case_table.sort_values("case_id").reset_index(drop=True),
        "level2_model": level2,
        "level2_coef_table": coef_table,
        "level2_nd_model": level2_nd,
        "level2_nd_coef_table": coef_nd_table,
        "a_shared": a_shared,
    }


def evaluate_case_timeseries_with_b(
    case_df: pd.DataFrame,
    *,
    b_urad: float,
    a_urad_per_c: float,
    config: BCaseConfig,
) -> dict[str, float | str]:
    """Apply fixed (b,a) on within-case test split; return dominant-axis RMSE."""
    sun_direction = case_df["case_sun_direction_body"].iloc[0]
    sun_face = normalize_sun_direction(sun_direction)
    dominant_axis = resolve_dominant_axis(sun_face)
    x_all, _, _, _ = build_deltaT_features(
        case_df, sun_direction, DeltaTFeatureConfig(ridge_lam=config.ridge_lam)
    )
    y_all = extract_targets(case_df)
    times_s = case_df["time_s"].to_numpy(dtype=float)
    train_mask = within_case_split_mask(times_s, config.orbit_period_s, config.train_orbits)
    test_mask = ~train_mask
    axis_idx = 0 if dominant_axis == "x" else 1

    y_hat = b_urad + a_urad_per_c * x_all[:, 0]
    err = y_all[:, axis_idx] - y_hat

    def _rmse(mask: np.ndarray) -> float:
        if not np.any(mask):
            return float("nan")
        return float(np.sqrt(np.mean(err[mask] ** 2)))

    return {
        "sun_face": sun_face,
        "dominant_axis": dominant_axis,
        "rmse_dom_train_urad": _rmse(train_mask),
        "rmse_dom_test_urad": _rmse(test_mask),
        "rmse_dom_all_urad": _rmse(np.ones(len(case_df), dtype=bool)),
    }


def predict_bcase_xy(
    case_df: pd.DataFrame,
    *,
    b_urad: float,
    a_urad_per_c: float,
    b_nd_urad: float,
    config: BCaseConfig,
) -> dict[str, np.ndarray | str | float]:
    """
    Build 2-axis LOS prediction for PAT:

      dominant:     b + a · ΔT(t)
      non-dominant: b_nd (constant DC from Level-2)

    Both are predicted from case-level information only (sun face, heat
    flags); no on-orbit LOS measurement is required.
    """
    sun_direction = case_df["case_sun_direction_body"].iloc[0]
    sun_face = normalize_sun_direction(sun_direction)
    dominant_axis = resolve_dominant_axis(sun_face)
    x_all, _, _, _ = build_deltaT_features(
        case_df, sun_direction, DeltaTFeatureConfig(ridge_lam=config.ridge_lam)
    )

    pred = np.full((len(case_df), 2), float(b_nd_urad), dtype=float)
    axis_idx = 0 if dominant_axis == "x" else 1
    pred[:, axis_idx] = b_urad + a_urad_per_c * x_all[:, 0]

    return {
        "bcase": pred,
        "sun_face": sun_face,
        "dominant_axis": dominant_axis,
        "b_urad": float(b_urad),
        "b_nd_urad": float(b_nd_urad),
        "a_urad_per_c": float(a_urad_per_c),
    }
