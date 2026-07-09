from __future__ import annotations

import numpy as np
import pandas as pd

TARGET_X = "far_field_los_angle_x_urad"
TARGET_Y = "far_field_los_angle_y_urad"


def extract_targets(df: pd.DataFrame) -> np.ndarray:
    required = {TARGET_X, TARGET_Y}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Dataset missing target columns: {sorted(missing)}")
    return df[[TARGET_X, TARGET_Y]].to_numpy(dtype=float)
