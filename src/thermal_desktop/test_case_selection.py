"""Unit tests for TD case-number parsing (no OpenTD required)."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.thermal_desktop.case_selection import (
    case_number_from_name,
    parse_case_spec,
    select_cases,
)


class ParseCaseSpecTests(unittest.TestCase):
    def test_list(self) -> None:
        self.assertEqual(parse_case_spec("7,8,9"), [7, 8, 9])

    def test_range(self) -> None:
        self.assertEqual(parse_case_spec("10-15"), [10, 11, 12, 13, 14, 15])

    def test_mixed(self) -> None:
        self.assertEqual(parse_case_spec("7,10-12,15"), [7, 10, 11, 12, 15])

    def test_whitespace(self) -> None:
        self.assertEqual(parse_case_spec(" 8 , 9 "), [8, 9])


class SelectCasesTests(unittest.TestCase):
    def test_select_by_group_and_number(self) -> None:
        cases = [
            SimpleNamespace(Name="01_A", GroupName="transient", SindaFilenames="01_A"),
            SimpleNamespace(Name="08_B", GroupName="transient", SindaFilenames="08_B"),
            SimpleNamespace(Name="08_C", GroupName="other", SindaFilenames="08_C"),
            SimpleNamespace(Name="09_D", GroupName="transient", SindaFilenames="09_D"),
        ]
        selected = select_cases(cases, group="transient", numbers=[8, 9])
        self.assertEqual([c.name for c in selected], ["08_B", "09_D"])
        self.assertEqual([c.index for c in selected], [1, 3])

    def test_missing_raises(self) -> None:
        cases = [
            SimpleNamespace(Name="08_B", GroupName="transient", SindaFilenames="08_B"),
        ]
        with self.assertRaises(ValueError):
            select_cases(cases, group="transient", numbers=[8, 9])

    def test_case_number_from_name(self) -> None:
        self.assertEqual(case_number_from_name("08_LTAN06_x"), 8)
        self.assertIsNone(case_number_from_name("no_prefix"))


if __name__ == "__main__":
    unittest.main()
