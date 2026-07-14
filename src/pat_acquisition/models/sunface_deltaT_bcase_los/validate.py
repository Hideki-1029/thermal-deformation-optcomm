"""
Hierarchical sunface ΔT validation:

  Level 1: LOS(t) ≈ b_case + a(sun_face) · ΔT(t)
  Level 2: b_case ≈ b0(sun) + c_prop·I_prop + c_pcdu·I_pcdu

Fits Level-2 across cases, reports b_emp vs b_pred (in-sample + LOO),
and dominant-axis RMSE with predicted b + shared a.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

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
    evaluate_case_timeseries_with_b,
    run_bcase_pipeline,
)

DISPLAY_FLOAT_FORMAT = "%.3g"
FILE_STEM = "bcase"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate hierarchical sunface ΔT: "
            "LOS ≈ b_case + a(sun)·ΔT, "
            "b_case ≈ b0(sun)+c_prop·I_prop+c_pcdu·I_pcdu."
        )
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--cases",
        help="Case numbers, e.g. 4,5,6 or 4-21 (0-padding optional).",
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
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--orbit-period-s", type=float, default=6052.0)
    parser.add_argument("--train-orbits", type=float, default=1.0)
    parser.add_argument("--ridge-lam", type=float, default=1e-3)
    parser.add_argument(
        "--level2-ridge-lam",
        type=float,
        default=0.0,
        help="Ridge on Level-2 heat coeffs only (0 = OLS).",
    )
    parser.add_argument(
        "--heat-faces",
        default="MY,PY",
        help="Sun faces where I_prop/I_pcdu apply (comma list or 'all').",
    )
    return parser.parse_args()


def _write_display_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", float_format=DISPLAY_FLOAT_FORMAT)


def main() -> None:
    args = parse_args()

    if args.list_cases:
        if not args.dataset.exists():
            raise FileNotFoundError(f"Dataset not found: {args.dataset}")
        print(f"Cases in {args.dataset}:")
        for number, case_id, sun_face, supported in list_numbered_cases(args.dataset):
            flag = "supported" if supported else "skipped (not MX/MY/PX/PY)"
            print(f"  {number:>3d}  {case_id}  sun={sun_face}  ({flag})")
        return

    case_ids, skipped = resolve_sunface_case_ids(
        args.dataset,
        cases=args.cases,
        case=args.case,
        case_ids=args.case_id,
    )
    heat_faces = parse_heat_faces(args.heat_faces)
    config = BCaseConfig(
        ridge_lam=args.ridge_lam,
        heat_faces=heat_faces,
        orbit_period_s=args.orbit_period_s,
        train_orbits=args.train_orbits,
        level2_ridge_lam=args.level2_ridge_lam,
    )

    result = run_bcase_pipeline(
        dataset_path=args.dataset,
        case_ids=case_ids,
        config=config,
    )
    case_table: pd.DataFrame = result["case_table"]
    coef_table: pd.DataFrame = result["level2_coef_table"]
    a_shared: dict[str, float] = result["a_shared"]

    # Per-case LOS metrics: oracle (b_emp,a_emp) vs hierarchical (b_pred, a_shared).
    metric_rows: list[dict[str, float | str | int]] = []
    for row in case_table.itertuples(index=False):
        case_df = load_case_frame(args.dataset, str(row.case_id))
        a_s = float(a_shared[str(row.sun_face)])

        oracle = evaluate_case_timeseries_with_b(
            case_df,
            b_urad=float(row.b_emp_urad),
            a_urad_per_c=float(row.a_emp_urad_per_c),
            config=config,
        )
        shared_a_emp_b = evaluate_case_timeseries_with_b(
            case_df,
            b_urad=float(row.b_emp_urad),
            a_urad_per_c=a_s,
            config=config,
        )
        insample = evaluate_case_timeseries_with_b(
            case_df,
            b_urad=float(row.b_pred_insample_urad),
            a_urad_per_c=a_s,
            config=config,
        )
        loo_b = float(row.b_pred_loo_urad)
        loo = None
        if np.isfinite(loo_b):
            loo = evaluate_case_timeseries_with_b(
                case_df,
                b_urad=loo_b,
                a_urad_per_c=a_s,
                config=config,
            )

        for model_name, ev in (
            ("oracle_b_emp_a_emp", oracle),
            ("b_emp_a_shared", shared_a_emp_b),
            ("b_pred_insample_a_shared", insample),
            ("b_pred_loo_a_shared", loo),
        ):
            if ev is None:
                continue
            metric_rows.append(
                {
                    "case_id": row.case_id,
                    "sun_face": row.sun_face,
                    "i_prop": int(row.i_prop),
                    "i_pcdu": int(row.i_pcdu),
                    "model": model_name,
                    "rmse_dom_train_urad": ev["rmse_dom_train_urad"],
                    "rmse_dom_test_urad": ev["rmse_dom_test_urad"],
                    "rmse_dom_all_urad": ev["rmse_dom_all_urad"],
                }
            )

    metrics_df = pd.DataFrame(metric_rows)
    a_shared_df = pd.DataFrame(
        [{"sun_face": k, "a_shared_urad_per_c": v} for k, v in sorted(a_shared.items())]
    )

    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    case_path = out_dir / f"{FILE_STEM}_case_table.csv"
    case_display = out_dir / f"{FILE_STEM}_case_table_display.csv"
    coef_path = out_dir / f"{FILE_STEM}_level2_coefficients.csv"
    coef_display = out_dir / f"{FILE_STEM}_level2_coefficients_display.csv"
    a_path = out_dir / f"{FILE_STEM}_a_shared.csv"
    metrics_path = out_dir / f"{FILE_STEM}_los_metrics.csv"
    metrics_display = out_dir / f"{FILE_STEM}_los_metrics_display.csv"

    case_table.to_csv(case_path, index=False, encoding="utf-8-sig")
    _write_display_csv(case_table, case_display)
    coef_table.to_csv(coef_path, index=False, encoding="utf-8-sig")
    _write_display_csv(coef_table, coef_display)
    a_shared_df.to_csv(a_path, index=False, encoding="utf-8-sig")
    metrics_df.to_csv(metrics_path, index=False, encoding="utf-8-sig")
    _write_display_csv(metrics_df, metrics_display)

    print(f"Cases: {len(case_table)}")
    print(f"Heat faces (I_prop/I_pcdu active): {', '.join(heat_faces)}")
    print()
    print("--- Level-2 coefficients [urad] ---")
    print(coef_table.to_string(index=False, float_format=DISPLAY_FLOAT_FORMAT))
    print()
    print("--- Shared a by sun face [urad/C] ---")
    print(a_shared_df.to_string(index=False, float_format=DISPLAY_FLOAT_FORMAT))
    print()
    print("--- Case table (b_emp vs b_pred) ---")
    show_cols = [
        "case_id",
        "sun_face",
        "i_prop",
        "i_pcdu",
        "b_emp_urad",
        "b_pred_insample_urad",
        "b_pred_loo_urad",
        "a_emp_urad_per_c",
        "a_shared_urad_per_c",
    ]
    print(case_table[show_cols].to_string(index=False, float_format=DISPLAY_FLOAT_FORMAT))
    print()

    # Compact test RMSE summary by model.
    test_sub = metrics_df.pivot_table(
        index="case_id",
        columns="model",
        values="rmse_dom_test_urad",
        aggfunc="first",
    )
    print("--- Dominant-axis test RMSE [urad] ---")
    print(test_sub.to_string(float_format=DISPLAY_FLOAT_FORMAT))
    print()

    b_resid = case_table["b_resid_insample_urad"].to_numpy(dtype=float)
    loo_resid = case_table["b_resid_loo_urad"].to_numpy(dtype=float)
    loo_ok = np.isfinite(loo_resid)
    print(
        f"b_emp - b_pred (in-sample):  "
        f"RMSE={np.sqrt(np.mean(b_resid**2)):.3g} urad, "
        f"max|d|={np.max(np.abs(b_resid)):.3g} urad"
    )
    if np.any(loo_ok):
        print(
            f"b_emp - b_pred (LOO):        "
            f"RMSE={np.sqrt(np.mean(loo_resid[loo_ok]**2)):.3g} urad, "
            f"max|d|={np.max(np.abs(loo_resid[loo_ok])):.3g} urad "
            f"(n={int(loo_ok.sum())})"
        )
    print()
    print(f"Wrote: {case_path}")
    print(f"Wrote: {coef_path}")
    print(f"Wrote: {a_path}")
    print(f"Wrote: {metrics_path}")
    if skipped:
        print(f"Skipped unsupported cases: {', '.join(skipped)}")


if __name__ == "__main__":
    main()
