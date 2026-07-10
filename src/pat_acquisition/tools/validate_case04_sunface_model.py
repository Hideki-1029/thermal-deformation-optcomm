""" Backward-compatible wrapper for Case 04 sunface within-case validation. """

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pat_acquisition.models.sunface_los.validate import main as _main


if __name__ == "__main__":
    if "--case" not in sys.argv and "--case-id" not in sys.argv and "--cases" not in sys.argv:
        sys.argv.extend(["--case", "04"])
    _main()
