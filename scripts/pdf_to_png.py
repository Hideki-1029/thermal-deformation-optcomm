"""Render PDF pages to PNG for vision-friendly reading (e.g. Print-to-PDF notes).

Requires: pip install pymupdf

Folder mode (recommended):
  python scripts/pdf_to_png.py docs/research_notes/google_doc
  -> docs/research_notes/google_doc/PNG/<pdf_stem>/page_001.png ...

Single PDF:
  python scripts/pdf_to_png.py path/to/notes.pdf
  -> path/to/PNG/notes/page_001.png ...
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def render_pdf(pdf_path: Path, out_dir: Path, dpi: float) -> list[Path]:
    try:
        import fitz  # pymupdf
    except ImportError as exc:
        raise SystemExit(
            "pymupdf is required. Install with: pip install pymupdf"
        ) from exc

    if not pdf_path.is_file():
        raise FileNotFoundError(pdf_path)

    out_dir.mkdir(parents=True, exist_ok=True)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    saved: list[Path] = []
    with fitz.open(pdf_path) as doc:
        width = max(3, len(str(doc.page_count)))
        for i, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            out_path = out_dir / f"page_{i:0{width}d}.png"
            pix.save(out_path)
            saved.append(out_path)
            text_len = len(page.get_text().strip())
            print(
                f"  page {i}/{doc.page_count}: {out_path.name} "
                f"({pix.width}x{pix.height}, text_chars={text_len})"
            )
    return saved


def collect_pdfs(paths: list[Path]) -> list[tuple[Path, Path]]:
    """Return (pdf_path, png_root) pairs.

    png_root is the directory that will contain <pdf_stem>/ pages.
    For a folder input, png_root is <folder>/PNG.
    For a PDF input, png_root is <pdf.parent>/PNG.
    """
    jobs: list[tuple[Path, Path]] = []
    for raw in paths:
        path = raw.resolve()
        if path.is_dir():
            pdfs = sorted(path.glob("*.pdf")) + sorted(path.glob("*.PDF"))
            # de-dupe on case-insensitive FS
            seen: set[Path] = set()
            unique: list[Path] = []
            for pdf in pdfs:
                key = pdf.resolve()
                if key in seen:
                    continue
                seen.add(key)
                unique.append(pdf)
            if not unique:
                print(f"warning: no PDFs in {path}", file=sys.stderr)
                continue
            png_root = path / "PNG"
            for pdf in unique:
                jobs.append((pdf, png_root))
        elif path.is_file() and path.suffix.lower() == ".pdf":
            jobs.append((path, path.parent / "PNG"))
        elif path.exists():
            raise SystemExit(f"error: not a PDF or directory: {path}")
        else:
            raise SystemExit(f"error: not found: {path}")
    return jobs


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render PDF pages to PNG. "
            "For a folder, writes <folder>/PNG/<pdf_stem>/page_XXX.png for every PDF."
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
        help="Rasterization DPI (default: 300, better for OCR)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dpi <= 0:
        print("error: --dpi must be positive", file=sys.stderr)
        return 2

    jobs = collect_pdfs(args.inputs)
    if not jobs:
        print("error: nothing to convert", file=sys.stderr)
        return 1

    for pdf, png_root in jobs:
        out_dir = png_root / pdf.stem
        print(f"{pdf.name} -> {out_dir}")
        saved = render_pdf(pdf, out_dir, args.dpi)
        print(f"  wrote {len(saved)} page(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
