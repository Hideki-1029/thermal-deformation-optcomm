"""Prepare research-note PDFs: rasterize to PNG, then OCR to Markdown.

Runs in order:
  1. pdf_to_png.py  -> <dir>/PNG/<name>/page_XXX.png
  2. png_to_md.py   -> <dir>/MD/<name>/content.md

Keeps the two scripts separate; this is the one-shot entry point.

Examples:
  python scripts/prepare_pdf_notes.py docs/research_notes/google_doc/260712_JANUS研究.pdf
  python scripts/prepare_pdf_notes.py docs/research_notes/google_doc
  python scripts/prepare_pdf_notes.py notes.pdf --dpi 144
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pdf_to_png
import png_to_md


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "PDF -> PNG (raster) -> MD (OCR). "
            "Wrapper around pdf_to_png.py then png_to_md.py."
        )
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="Input folder(s) and/or PDF file(s)",
    )
    parser.add_argument(
        "--dpi",
        type=float,
        default=300.0,
        help="PNG rasterization DPI (default: 300)",
    )
    parser.add_argument(
        "--lang",
        default="jpn+eng",
        help="Tesseract languages for OCR (default: jpn+eng)",
    )
    parser.add_argument(
        "--tesseract",
        type=Path,
        default=None,
        help="Path to tesseract.exe (optional)",
    )
    parser.add_argument(
        "--skip-png",
        action="store_true",
        help="Skip rasterization; OCR existing PNG folders only",
    )
    parser.add_argument(
        "--skip-md",
        action="store_true",
        help="Skip OCR; rasterize PNG only",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.skip_png and args.skip_md:
        print("error: both --skip-png and --skip-md set", file=sys.stderr)
        return 2
    if args.dpi <= 0:
        print("error: --dpi must be positive", file=sys.stderr)
        return 2

    jobs = pdf_to_png.collect_pdfs(args.inputs)
    if not jobs:
        print("error: nothing to convert", file=sys.stderr)
        return 1

    png_doc_dirs = [png_root / pdf.stem for pdf, png_root in jobs]

    if not args.skip_png:
        print("=== 1/2 PNG ===")
        png_argv = [str(p) for p in args.inputs] + ["--dpi", str(args.dpi)]
        code = pdf_to_png.main(png_argv)
        if code:
            return code
    else:
        print("=== 1/2 PNG (skipped) ===")

    if not args.skip_md:
        print("=== 2/2 MD (OCR) ===")
        md_argv = [str(p) for p in png_doc_dirs] + ["--lang", args.lang]
        if args.tesseract is not None:
            md_argv += ["--tesseract", str(args.tesseract)]
        code = png_to_md.main(md_argv)
        if code:
            return code
    else:
        print("=== 2/2 MD (skipped) ===")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
