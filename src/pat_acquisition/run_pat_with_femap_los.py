"""
Backward-compatible entry point.

Runs both:
  - runners/run_femap_los_truth.py  -> results/.../femap_los_truth/
  - models/fourier_los/run_pat.py   -> results/.../fourier_los_model/

Prefer calling those scripts directly. This wrapper always uses the YAML
output directories (ignores --output-dir) so the two runs do not collide.
"""

from __future__ import annotations

from pathlib import Path
import sys

PAT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PAT_ROOT.parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(PAT_ROOT) not in sys.path:
    sys.path.insert(0, str(PAT_ROOT))

from pat_acquisition.models.fourier_los.run_pat import main as run_fourier_main
from pat_acquisition.runners.run_femap_los_truth import main as run_truth_main


def _without_output_dir_args(argv: list[str]) -> list[str]:
    cleaned: list[str] = []
    skip_next = False
    for i, arg in enumerate(argv):
        if skip_next:
            skip_next = False
            continue
        if arg in {"--output-dir", "--truth-output-dir", "--fourier-output-dir"}:
            skip_next = True
            continue
        if arg.startswith("--output-dir=") or arg.startswith("--truth-output-dir="):
            continue
        if arg.startswith("--fourier-output-dir="):
            continue
        cleaned.append(arg)
    return cleaned


def main() -> None:
    original = list(sys.argv)
    sys.argv = _without_output_dir_args(original)
    try:
        print("=== Femap LOS truth baselines ===")
        run_truth_main()
        print()
        print("=== Fourier lightweight LOS model ===")
        run_fourier_main()
    finally:
        sys.argv = original


if __name__ == "__main__":
    main()
