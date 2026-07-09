from __future__ import annotations

from pathlib import Path

import pandas as pd

DEFAULT_DATASET = (
    Path(__file__).resolve().parents[4]
    / "results"
    / "pat_acquisition"
    / "lightweight_dataset"
    / "lightweight_dataset_all.csv"
)
DEFAULT_OUTPUT_DIR = (
    Path(__file__).resolve().parents[4]
    / "results"
    / "pat_acquisition"
    / "temperature_los_model"
)


def validate_case_level_split(df: pd.DataFrame) -> None:
    if "case_id" not in df.columns:
        raise ValueError("dataset must include case_id column")
    if "split" not in df.columns:
        raise ValueError(
            "dataset must include split column. "
            "Build dataset with scripts/build_lightweight_dataset.py first."
        )

    split_counts = df.groupby("case_id")["split"].nunique()
    bad = split_counts[split_counts > 1]
    if len(bad) > 0:
        raise ValueError(
            "split must be case_id-level (one split per case). "
            f"Violating cases: {list(bad.index)}"
        )


def load_split_frames(
    dataset_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(dataset_path)
    validate_case_level_split(df)
    train_df = df[df["split"] == "train"].copy()
    val_df = df[df["split"] == "val"].copy()
    test_df = df[df["split"] == "test"].copy()
    if train_df.empty:
        raise ValueError("train split is empty")
    return df, train_df, val_df, test_df
