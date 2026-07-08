from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASE_MATRIX = REPO_ROOT / "cases" / "case_matrix.xlsx"
DEFAULT_ORBIT_CATALOG = REPO_ROOT / "cases" / "orbit_catalog.xlsx"
DEFAULT_SYMBOL_DIR = REPO_ROOT / "inputs" / "data_symbols_TD"
DEFAULT_FEMAP_RESULT_DIR = REPO_ROOT / "results" / "femap_deformation"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "pat_acquisition" / "lightweight_dataset"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build lightweight LOS model dataset by merging case metadata, "
            "orbit catalog, TD LOGIC_SUN symbols, representative temperature CSV, and LOS CSV."
        )
    )
    parser.add_argument("--case-matrix", type=Path, default=DEFAULT_CASE_MATRIX)
    parser.add_argument("--case-matrix-sheet", default="case_matrix")
    parser.add_argument("--orbit-catalog", type=Path, default=DEFAULT_ORBIT_CATALOG)
    parser.add_argument("--orbit-catalog-sheet", default="orbit_catalog")
    parser.add_argument("--symbol-dir", type=Path, default=DEFAULT_SYMBOL_DIR)
    parser.add_argument("--femap-result-dir", type=Path, default=DEFAULT_FEMAP_RESULT_DIR)
    parser.add_argument("--temperature-csv-name", default="default_surface_9points_temperatures.csv")
    parser.add_argument("--los-csv-name", default="los_angles.csv")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--train-ratio", type=float, default=0.6)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def normalize_ratio(train_ratio: float, val_ratio: float) -> tuple[float, float, float]:
    if not (0.0 < train_ratio < 1.0):
        raise ValueError(f"train_ratio must be in (0,1), got {train_ratio}")
    if not (0.0 <= val_ratio < 1.0):
        raise ValueError(f"val_ratio must be in [0,1), got {val_ratio}")
    test_ratio = 1.0 - train_ratio - val_ratio
    if test_ratio <= 0.0:
        raise ValueError("train_ratio + val_ratio must be less than 1.0")
    return train_ratio, val_ratio, test_ratio


def select_orbit_row(orbit_catalog: pd.DataFrame, orbit_case: str) -> pd.Series | None:
    names = orbit_catalog["td_orbit_name"].astype(str)
    exact = orbit_catalog[names == orbit_case]
    if len(exact) == 1:
        return exact.iloc[0]
    if len(exact) > 1:
        raise ValueError(f"orbit_case matched multiple rows: {orbit_case}")

    prefix_candidates: list[tuple[int, pd.Series]] = []
    for _, row in orbit_catalog.iterrows():
        name = str(row["td_orbit_name"])
        if orbit_case.startswith(name):
            prefix_candidates.append((len(name), row))
    if not prefix_candidates:
        return None
    return max(prefix_candidates, key=lambda item: item[0])[1]


def _prepare_time_series(df: pd.DataFrame, time_col: str) -> pd.DataFrame:
    cleaned = df.dropna(subset=[time_col]).copy()
    cleaned = cleaned.sort_values(time_col)
    cleaned = cleaned.groupby(time_col, as_index=False).mean(numeric_only=True)
    return cleaned


def interpolate_to_times(
    source: pd.DataFrame,
    source_time_col: str,
    target_times: np.ndarray,
    value_cols: list[str],
) -> pd.DataFrame:
    if source.empty:
        raise ValueError("Cannot interpolate from empty dataframe")
    source = _prepare_time_series(source, source_time_col)

    result = pd.DataFrame({"time_s": target_times})
    for col in value_cols:
        result[col] = np.interp(
            target_times,
            source[source_time_col].to_numpy(dtype=float),
            source[col].to_numpy(dtype=float),
        )
    return result


def read_logic_sun(symbol_path: Path) -> pd.DataFrame:
    if not symbol_path.exists():
        raise FileNotFoundError(f"LOGIC_SUN source file not found: {symbol_path}")
    xls = pd.ExcelFile(symbol_path)
    if not xls.sheet_names:
        raise ValueError(f"No sheet in symbol file: {symbol_path}")
    df = pd.read_excel(symbol_path, sheet_name=xls.sheet_names[0])
    required = {"Times", "LOGIC_SUN"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"{symbol_path} missing columns: {sorted(missing)}")
    out = df.loc[:, ["Times", "LOGIC_SUN"]].rename(columns={"Times": "time_s", "LOGIC_SUN": "logic_sun"})
    return out


def read_representative_temperatures(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Representative temperature CSV not found: {path}")
    df = pd.read_csv(path)
    required = {"time_s", "probe_name"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")

    temperature_col = "temperature_c" if "temperature_c" in df.columns else "temperature"
    if temperature_col not in df.columns:
        raise ValueError(f"{path} missing temperature column (temperature_c/temperature)")

    table = (
        df.loc[:, ["time_s", "probe_name", temperature_col]]
        .pivot_table(index="time_s", columns="probe_name", values=temperature_col, aggfunc="mean")
        .reset_index()
    )
    table.columns = ["time_s"] + [f"temp_{str(c)}_c" for c in table.columns[1:]]
    return table


def read_los(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"LOS CSV not found: {path}")
    df = pd.read_csv(path)
    required = {"time_s", "far_field_los_angle_x_urad", "far_field_los_angle_y_urad"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
    selected = [
        "time_s",
        "far_field_los_angle_x_urad",
        "far_field_los_angle_y_urad",
    ]
    if "far_field_los_angle_magnitude_urad" in df.columns:
        selected.append("far_field_los_angle_magnitude_urad")
    return df.loc[:, selected].copy()


def explicit_split_from_use_for_model(use_for_model: str) -> str | None:
    value = str(use_for_model).strip().lower()
    mapping = {
        "train": "train",
        "validation": "val",
        "valid": "val",
        "val": "val",
        "test": "test",
    }
    return mapping.get(value)


def assign_case_splits(
    cases: list[str],
    train_ratio: float,
    val_ratio: float,
    seed: int,
) -> dict[str, str]:
    _, _, _ = normalize_ratio(train_ratio, val_ratio)
    rng = np.random.default_rng(seed)
    shuffled = list(cases)
    rng.shuffle(shuffled)
    n = len(shuffled)
    if n == 0:
        return {}
    if n == 1:
        return {shuffled[0]: "train"}
    if n == 2:
        return {shuffled[0]: "train", shuffled[1]: "test"}

    n_train = max(1, int(round(n * train_ratio)))
    n_val = max(1, int(round(n * val_ratio)))
    if n_train + n_val >= n:
        n_val = max(1, n - n_train - 1)
    n_test = n - n_train - n_val
    if n_test < 1:
        n_test = 1
        if n_train > n_val:
            n_train -= 1
        else:
            n_val -= 1

    out: dict[str, str] = {}
    for idx, case_id in enumerate(shuffled):
        if idx < n_train:
            out[case_id] = "train"
        elif idx < n_train + n_val:
            out[case_id] = "val"
        else:
            out[case_id] = "test"
    return out


def main() -> None:
    args = parse_args()
    normalize_ratio(args.train_ratio, args.val_ratio)

    case_matrix = pd.read_excel(args.case_matrix, sheet_name=args.case_matrix_sheet)
    orbit_catalog = pd.read_excel(args.orbit_catalog, sheet_name=args.orbit_catalog_sheet)
    if "case_id" not in case_matrix.columns:
        raise ValueError(f"{args.case_matrix} does not have case_id column")

    rows: list[pd.DataFrame] = []
    explicit_case_split: dict[str, str] = {}
    unresolved_cases: set[str] = set()

    for _, case_row in case_matrix.iterrows():
        case_id = str(case_row.get("case_id", "")).strip()
        if not case_id:
            continue

        use_for_model = case_row.get("use_for_model", "")
        explicit = explicit_split_from_use_for_model(str(use_for_model))
        if explicit is not None:
            explicit_case_split[case_id] = explicit
        else:
            unresolved_cases.add(case_id)

        los_path = Path(str(case_row.get("python_result_path", "")))
        if not los_path.is_file():
            los_path = args.femap_result_dir / case_id / args.los_csv_name
        temp_path = args.femap_result_dir / case_id / args.temperature_csv_name
        symbol_path = args.symbol_dir / f"{case_id}.xlsx"

        if not (los_path.exists() and temp_path.exists() and symbol_path.exists()):
            print(
                f"Skip {case_id}: missing input "
                f"(los={los_path.exists()}, temp={temp_path.exists()}, logic_sun={symbol_path.exists()})"
            )
            continue

        los = read_los(los_path)
        temperature = read_representative_temperatures(temp_path)
        logic_sun = read_logic_sun(symbol_path)

        time_s = los["time_s"].to_numpy(dtype=float)
        temp_interp = interpolate_to_times(
            temperature,
            source_time_col="time_s",
            target_times=time_s,
            value_cols=[c for c in temperature.columns if c != "time_s"],
        )
        sun_interp = interpolate_to_times(
            logic_sun,
            source_time_col="time_s",
            target_times=time_s,
            value_cols=["logic_sun"],
        )
        sun_interp["logic_sun"] = (sun_interp["logic_sun"] >= 0.5).astype(int)

        merged = los.copy()
        merged = merged.merge(temp_interp, on="time_s", how="left")
        merged = merged.merge(sun_interp, on="time_s", how="left")
        merged["case_id"] = case_id

        for col in case_matrix.columns:
            if col == "case_id":
                continue
            merged[f"case_{col}"] = case_row[col]

        orbit_case = str(case_row.get("orbit_case", "")).strip()
        if orbit_case and "td_orbit_name" in orbit_catalog.columns:
            orbit_row = select_orbit_row(orbit_catalog, orbit_case)
            if orbit_row is not None:
                for col in orbit_catalog.columns:
                    merged[f"orbit_{col}"] = orbit_row[col]

        rows.append(merged)

    if not rows:
        raise RuntimeError("No merged rows were produced. Check input paths and file names.")

    dataset = pd.concat(rows, ignore_index=True)

    auto_case_split = assign_case_splits(
        sorted(set(dataset["case_id"].astype(str))),
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        seed=args.seed,
    )
    final_case_split = auto_case_split | explicit_case_split
    dataset["split"] = dataset["case_id"].map(final_case_split).fillna("train")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = args.output_dir / "lightweight_dataset_all.csv"
    train_path = args.output_dir / "lightweight_dataset_train.csv"
    val_path = args.output_dir / "lightweight_dataset_val.csv"
    test_path = args.output_dir / "lightweight_dataset_test.csv"
    stats_path = args.output_dir / "lightweight_dataset_stats.csv"

    dataset.to_csv(dataset_path, index=False, encoding="utf-8-sig")
    dataset[dataset["split"] == "train"].to_csv(train_path, index=False, encoding="utf-8-sig")
    dataset[dataset["split"] == "val"].to_csv(val_path, index=False, encoding="utf-8-sig")
    dataset[dataset["split"] == "test"].to_csv(test_path, index=False, encoding="utf-8-sig")

    stats = (
        dataset.groupby(["split", "case_id"], as_index=False)
        .agg(
            samples=("time_s", "count"),
            logic_sun_mean=("logic_sun", "mean"),
            los_x_std_urad=("far_field_los_angle_x_urad", "std"),
            los_y_std_urad=("far_field_los_angle_y_urad", "std"),
        )
        .sort_values(["split", "case_id"])
    )
    stats.to_csv(stats_path, index=False, encoding="utf-8-sig")

    print(f"Built dataset rows: {len(dataset)}")
    print(f"Cases used: {dataset['case_id'].nunique()}")
    print(f"All  : {dataset_path}")
    print(f"Train: {train_path} ({(dataset['split'] == 'train').sum()} rows)")
    print(f"Val  : {val_path} ({(dataset['split'] == 'val').sum()} rows)")
    print(f"Test : {test_path} ({(dataset['split'] == 'test').sum()} rows)")
    print(f"Stats: {stats_path}")


if __name__ == "__main__":
    main()
