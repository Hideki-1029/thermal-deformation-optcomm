"""Parse CLI case-number specs and match TD Case Sets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable


_CASE_NUM_RE = re.compile(r"^(\d+)_")


def parse_case_spec(spec: str) -> list[int]:
    """
    Parse a case-number spec into a sorted unique list of ints.

    Examples
    --------
    ``"7,8,9"`` → ``[7, 8, 9]``
    ``"10-15"`` → ``[10, 11, 12, 13, 14, 15]``
    ``"7,10-12,15"`` → ``[7, 10, 11, 12, 15]``
    """
    text = (spec or "").strip()
    if not text:
        raise ValueError("Case spec is empty. Example: 7,8,9 or 10-15")

    nums: set[int] = set()
    for raw_part in text.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            start = int(left.strip())
            end = int(right.strip())
            if end < start:
                raise ValueError(f"Invalid range in case spec: {part!r}")
            nums.update(range(start, end + 1))
        else:
            nums.add(int(part))

    if not nums:
        raise ValueError(f"No case numbers parsed from {spec!r}")
    return sorted(nums)


def case_number_from_name(name: str) -> int | None:
    """Extract leading ``NN_`` case number from a Case Set name, else None."""
    match = _CASE_NUM_RE.match(name or "")
    return int(match.group(1)) if match else None


@dataclass(frozen=True)
class SelectedCase:
    """One Case Set selected for run/map."""

    index: int
    name: str
    group_name: str
    number: int
    sinda_filenames: str
    case_set: Any


def select_cases(
    all_cases: Iterable[Any],
    *,
    group: str,
    numbers: Iterable[int],
) -> list[SelectedCase]:
    """
    Filter ``GetCaseSets()`` results by group name and leading case numbers.

    ``index`` is the position in the full Case Set Manager list (needed for
    ``CaseSetManager.Run(indices)``).
    """
    wanted = set(numbers)
    group_key = group.strip().casefold()
    selected: list[SelectedCase] = []
    found_numbers: set[int] = set()

    for index, case in enumerate(all_cases):
        group_name = str(getattr(case, "GroupName", "") or "")
        if group_name.casefold() != group_key:
            continue
        name = str(getattr(case, "Name", "") or "")
        number = case_number_from_name(name)
        if number is None or number not in wanted:
            continue
        sinda = str(getattr(case, "SindaFilenames", "") or "") or name
        selected.append(
            SelectedCase(
                index=index,
                name=name,
                group_name=group_name,
                number=number,
                sinda_filenames=sinda,
                case_set=case,
            )
        )
        found_numbers.add(number)

    missing = sorted(wanted - found_numbers)
    if missing:
        raise ValueError(
            f"Case number(s) not found in group {group!r}: {missing}. "
            "Check Case Set Manager names (expected prefix like 08_...)."
        )

    selected.sort(key=lambda c: c.number)
    return selected
