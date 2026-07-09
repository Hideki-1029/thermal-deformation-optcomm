""" Backward-compatible wrapper. Prefer models/sunface_los/validate.py. """

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pat_acquisition.models.sunface_los.validate import main

if __name__ == "__main__":
    main()
