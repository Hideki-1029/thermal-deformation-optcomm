"""
Aggregate per-case compo-local Ridge coefficients into a cross-case comparison CSV.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pat_acquisition.models.sunface_compo_local_los.dataset import (  # noqa: E402
    DEFAULT_OUTPUT_ROOT,
)
from thermal_desktop.case_selection import case_number_from_name  # noqa: E402

DEFAULT_COMPARISON_CSV = DEFAULT_OUTPUT_ROOT / "compo_local_coefficients_comparison.csv"
DEFAULT_COMPARISON_DISPLAY_CSV = (
    DEFAULT_OUTPUT_ROOT / "compo_local_coefficients_comparison_display.csv"
)
DISPLAY_FLOAT_FORMAT = "%.3g"

COEF_COLUMNS = {
    "intercept": "intercept_urad",
    "t_sunface_minus_opposite_c": "coef_t_sunface_minus_opposite_c_urad",
    "t_prop_attach_minus_py_center_c": "coef_t_prop_attach_minus_py_center_c_urad",
    "t_pcdu_attach_minus_my_center_c": "coef_t_pcdu_attach_minus_my_center_c_urad",
}

FILE_STEM = "compo_local"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build cross-case sunface-compo-local coefficient comparison CSV."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_COMPARISON_CSV)
    return parser.parse_args()


def _read_case_metadata(case_dir: Path, case_tag: str) -> dict[str, str]:
    predictions_path = case_dir / f"{case_tag}_{FILE_STEM}_predictions.csv"
    if not predictions_path.exists():
        return {"case_id": "", "sun_face": "", "dominant_axis": ""}
    head = pd.read_csv(predictions_path, nrows=1)
    return {
        "case_id": str(head["case_id"].iloc[0]),
        "sun_face": str(head["sun_direction"].iloc[0]),
        "dominant_axis": str(head["dominant_axis"].iloc[0]),
    }


def _read_test_metrics(case_dir: Path, case_tag: str, dominant_axis: str) -> dict[str, float]:
    metrics_path = case_dir / f"{case_tag}_{FILE_STEM}_metrics.csv"
    if not metrics_path.exists():
        return {}

    metrics_df = pd.read_csv(metrics_path)
    model_rows = metrics_df[
        (metrics_df["split"] == "test")
        & (metrics_df["model"].astype(str).str.startswith("compo_local_"))
    ]
    if model_rows.empty:
        return {}

    row = model_rows.iloc[0]
    dom_col = "rmse_x_urad" if dominant_axis == "x" else "rmse_y_urad"
    return {
        "test_rmse_norm_urad": float(row["rmse_norm_urad"]),
        "test_rmse_dominant_urad": float(row[dom_col]),
        "test_mae_norm_urad": float(row["mae_norm_urad"]),
        "test_p95_error_norm_urad": float(row["p95_error_norm_urad"]),
    }


def build_coefficients_comparison(input_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for case_dir in sorted(input_dir.glob("case*_within_case")):
        case_tag = case_dir.name.replace("_within_case", "")
        coef_paths = sorted(case_dir.glob(f"{case_tag}_{FILE_STEM}_coefficients.csv"))
        if not coef_paths:
            continue

        coef_df = pd.read_csv(coef_paths[0])
        coef_map = dict(
            zip(coef_df["feature"].astype(str), coef_df["coef_dominant_axis_urad"])
        )

        meta = _read_case_metadata(case_dir, case_tag)
        case_id = meta["case_id"]
        case_number = case_number_from_name(case_id) if case_id else None
        if case_number is None:
            prefix = case_tag.removeprefix("case")
            case_number = int(prefix) if prefix.isdigit() else None

        row: dict[str, object] = {
            "case_number": case_number,
            "case_id": case_id,
            "sun_face": meta["sun_face"],
            "dominant_axis": meta["dominant_axis"],
        }
        for feature, column in COEF_COLUMNS.items():
            row[column] = coef_map.get(feature)

        row.update(_read_test_metrics(case_dir, case_tag, meta["dominant_axis"]))
        rows.append(row)

    if not rows:
        return pd.DataFrame(
            columns=[
                "case_number",
                "case_id",
                "sun_face",
                "dominant_axis",
                *COEF_COLUMNS.values(),
                "test_rmse_norm_urad",
                "test_rmse_dominant_urad",
                "test_mae_norm_urad",
                "test_p95_error_norm_urad",
            ]
        )

    out = pd.DataFrame(rows)
    return out.sort_values("case_number", kind="stable").reset_index(drop=True)


def write_coefficients_comparison(
    input_dir: Path = DEFAULT_OUTPUT_ROOT,
    output_path: Path = DEFAULT_COMPARISON_CSV,
    display_output_path: Path | None = None,
) -> Path:
    comparison_df = build_coefficients_comparison(input_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    if display_output_path is None:
        if output_path == DEFAULT_COMPARISON_CSV:
            display_output_path = DEFAULT_COMPARISON_DISPLAY_CSV
        else:
            display_output_path = output_path.with_name(
                f"{output_path.stem}_display{output_path.suffix}"
            )
    display_output_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_df.to_csv(
        display_output_path,
        index=False,
        encoding="utf-8-sig",
        float_format=DISPLAY_FLOAT_FORMAT,
    )
    return output_path


def main() -> None:
    args = parse_args()
    output_path = write_coefficients_comparison(args.input_dir, args.output)
    comparison_df = pd.read_csv(output_path)
    display_path = (
        DEFAULT_COMPARISON_DISPLAY_CSV
        if args.output == DEFAULT_COMPARISON_CSV
        else args.output.with_name(f"{args.output.stem}_display{args.output.suffix}")
    )
    print(f"Cases: {len(comparison_df)}")
    print(f"Comparison CSV: {output_path}")
    print(f"Display CSV ({DISPLAY_FLOAT_FORMAT}): {display_path}")
    if not comparison_df.empty:
        print(comparison_df.to_string(index=False, float_format=DISPLAY_FLOAT_FORMAT))


if __name__ == "__main__":
    main()
