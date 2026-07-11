"""Unit tests for PostProcessing dataset path helpers (no OpenTD required)."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.thermal_desktop.run_td_cases import (
    _dataset_name_for_create,
    _is_absolute_path_ref,
    _matching_dataset_entries,
    dataset_lookup_names,
    dataset_ref_for_sav,
)


class DatasetRefTests(unittest.TestCase):
    def test_dataset_ref_prefers_relative_to_dwg(self) -> None:
        dwg_dir = Path(r"C:\TD\model")
        sav_path = Path(r"C:\TD\model\transient\11_case.sav")
        self.assertEqual(
            dataset_ref_for_sav(dwg_dir, sav_path),
            r"transient\11_case.sav",
        )

    def test_dataset_ref_falls_back_to_absolute_outside_dwg(self) -> None:
        dwg_dir = Path(r"C:\TD\model")
        sav_path = Path(r"D:\archive\11_case.sav")
        self.assertEqual(
            dataset_ref_for_sav(dwg_dir, sav_path),
            str(sav_path.resolve()),
        )

    def test_lookup_names_are_relative_only(self) -> None:
        names = dataset_lookup_names(r"transient\11_case.sav", "11_case.sav")
        self.assertEqual(names, [r"transient\11_case.sav", "transient/11_case.sav", "11_case.sav"])
        for name in names:
            self.assertFalse(_is_absolute_path_ref(name))

    def test_create_dataset_name_uses_relative_ref(self) -> None:
        self.assertEqual(
            _dataset_name_for_create(r"transient\12_case.sav"),
            "transient_12_case.sav",
        )

    def test_matching_entries_prefers_relative_path(self) -> None:
        class FakeDataset:
            def __init__(self, name: str) -> None:
                self.Name = name

        datasets = [
            FakeDataset(r"C:\TD\model\transient\11_case.sav"),
            FakeDataset(r"transient\11_case.sav"),
            FakeDataset("11_case.sav"),
        ]
        matches = _matching_dataset_entries(
            datasets,
            sav_ref=r"transient\11_case.sav",
            sav_name="11_case.sav",
        )
        self.assertEqual(matches[0][1], r"transient\11_case.sav")


if __name__ == "__main__":
    unittest.main()
