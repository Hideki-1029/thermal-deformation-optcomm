"""OCR PNG page folders into Markdown (companion to pdf_to_png / pdf_to_md).

Requires:
  pip install pytesseract pillow
  Tesseract OCR + Japanese traineddata (jpn)

Install Tesseract (Windows):
  winget install --id UB-Mannheim.TesseractOCR -e

If jpn is missing (common), download once:
  mkdir %LOCALAPPDATA%\\tesseract-ocr\\tessdata
  curl -L -o %LOCALAPPDATA%\\tesseract-ocr\\tessdata\\jpn.traineddata ^
    https://github.com/tesseract-ocr/tessdata_fast/raw/main/jpn.traineddata
  copy "C:\\Program Files\\Tesseract-OCR\\tessdata\\eng.traineddata" ^
    %LOCALAPPDATA%\\tesseract-ocr\\tessdata\\

Examples:
  python scripts/png_to_md.py docs/research_notes/google_doc/PNG/260712_JANUS研究
  python scripts/png_to_md.py docs/research_notes/google_doc/PNG
  python scripts/png_to_md.py docs/research_notes/google_doc
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


PAGE_RE = re.compile(r"^page_(\d+)\.png$", re.IGNORECASE)
DEFAULT_TESSERACT_CANDIDATES = (
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
)


def user_tessdata_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "tesseract-ocr" / "tessdata"
    return Path.home() / "AppData" / "Local" / "tesseract-ocr" / "tessdata"


def configure_tessdata_prefix() -> Path | None:
    """Prefer user tessdata (with jpn) over Program Files (often eng-only)."""
    explicit = os.environ.get("TESSDATA_PREFIX")
    if explicit:
        prefix = Path(explicit)
        if (prefix / "jpn.traineddata").is_file():
            os.environ["TESSDATA_PREFIX"] = str(prefix)
            return prefix
        nested = prefix / "tessdata"
        if (nested / "jpn.traineddata").is_file():
            os.environ["TESSDATA_PREFIX"] = str(nested)
            return nested
        return prefix if prefix.is_dir() else None

    user_dir = user_tessdata_dir()
    if (user_dir / "jpn.traineddata").is_file():
        os.environ["TESSDATA_PREFIX"] = str(user_dir)
        return user_dir

    program_files = Path(r"C:\Program Files\Tesseract-OCR\tessdata")
    if program_files.is_dir():
        os.environ["TESSDATA_PREFIX"] = str(program_files)
        return program_files
    return None


def configure_tesseract(explicit: Path | None) -> str:
    import pytesseract

    configure_tessdata_prefix()

    if explicit is not None:
        exe = explicit
        if not exe.is_file():
            raise SystemExit(f"error: tesseract not found: {exe}")
        pytesseract.pytesseract.tesseract_cmd = str(exe)
        return str(exe)

    env_cmd = os.environ.get("TESSERACT_CMD")
    if env_cmd:
        exe = Path(env_cmd)
        if exe.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(exe)
            return str(exe)

    which = shutil_which("tesseract")
    if which:
        pytesseract.pytesseract.tesseract_cmd = which
        return which

    for candidate in DEFAULT_TESSERACT_CANDIDATES:
        if candidate.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            return str(candidate)

    raise SystemExit(
        "error: Tesseract not found. Install UB-Mannheim Tesseract OCR "
        "(winget install --id UB-Mannheim.TesseractOCR -e), "
        "or pass --tesseract path, or set TESSERACT_CMD."
    )


def shutil_which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


def list_page_pngs(doc_dir: Path) -> list[Path]:
    pages: list[tuple[int, Path]] = []
    for path in doc_dir.iterdir():
        if not path.is_file():
            continue
        match = PAGE_RE.match(path.name)
        if not match:
            continue
        pages.append((int(match.group(1)), path))
    pages.sort(key=lambda item: item[0])
    return [path for _, path in pages]


def resolve_jobs(inputs: list[Path]) -> list[tuple[Path, Path]]:
    """Return (png_doc_dir, md_out_path) jobs."""
    jobs: list[tuple[Path, Path]] = []
    for raw in inputs:
        path = raw.resolve()
        if not path.exists():
            raise SystemExit(f"error: not found: {path}")

        if path.is_dir() and list_page_pngs(path):
            if path.parent.name.upper() == "PNG":
                md_path = path.parent.parent / "MD" / path.name / "content.md"
            else:
                md_path = path.parent / "MD" / path.name / "content.md"
            jobs.append((path, md_path))
            continue

        if path.is_dir() and path.name.upper() == "PNG":
            found = False
            for sub in sorted(p for p in path.iterdir() if p.is_dir()):
                if not list_page_pngs(sub):
                    continue
                md_path = path.parent / "MD" / sub.name / "content.md"
                jobs.append((sub, md_path))
                found = True
            if not found:
                print(f"warning: no page_*.png folders under {path}", file=sys.stderr)
            continue

        png_root = path / "PNG"
        if path.is_dir() and png_root.is_dir():
            jobs.extend(resolve_jobs([png_root]))
            continue

        raise SystemExit(
            f"error: expected a PNG doc folder, PNG/, or parent with PNG/: {path}"
        )
    return jobs


def ocr_image(path: Path, *, lang: str) -> str:
    import pytesseract
    from PIL import Image

    with Image.open(path) as img:
        rgb = img.convert("RGB")
        text = pytesseract.image_to_string(rgb, lang=lang)
    return text.strip()


def build_content_md(
    doc_name: str,
    pages: list[tuple[Path, str]],
) -> str:
    lines = [
        f"# {doc_name}",
        "",
        f"- Source PNG: `../../PNG/{doc_name}/`",
        f"- Pages: {len(pages)}",
        "- Generated by `scripts/png_to_md.py` (Tesseract OCR)",
        "",
        "OCR text may be imperfect. Prefer linked PNG for figures / broken lines.",
        "",
    ]
    for index, (png_path, text) in enumerate(pages, start=1):
        png_rel = f"../../PNG/{doc_name}/{png_path.name}"
        lines.append(f"## Page {index}")
        lines.append("")
        lines.append(f"[PNG page]({png_rel})")
        lines.append("")
        if text:
            lines.append(text)
            lines.append("")
        else:
            lines.append("*(OCR returned no text)*")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def convert_doc(png_dir: Path, md_path: Path, *, lang: str) -> Path:
    page_paths = list_page_pngs(png_dir)
    if not page_paths:
        raise SystemExit(f"error: no page_*.png in {png_dir}")

    pages: list[tuple[Path, str]] = []
    for i, png_path in enumerate(page_paths, start=1):
        text = ocr_image(png_path, lang=lang)
        pages.append((png_path, text))
        print(
            f"  page {i}/{len(page_paths)}: {png_path.name} "
            f"chars={len(text)}"
        )

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(build_content_md(png_dir.name, pages), encoding="utf-8")
    return md_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "OCR page_*.png folders into MD/<name>/content.md "
            "(for Print-to-PDF notes where PDF text extract is empty)."
        )
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="PNG doc folder, PNG/ directory, or parent folder containing PNG/",
    )
    parser.add_argument(
        "--lang",
        default="jpn+eng",
        help="Tesseract languages (default: jpn+eng)",
    )
    parser.add_argument(
        "--tesseract",
        type=Path,
        default=None,
        help="Path to tesseract.exe (optional)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        import pytesseract
    except ImportError as exc:
        raise SystemExit(
            "pytesseract is required. Install with: pip install pytesseract pillow"
        ) from exc

    exe = configure_tesseract(args.tesseract)
    tessdata = os.environ.get("TESSDATA_PREFIX", "")
    print(f"tesseract: {exe}")
    print(f"tessdata: {tessdata or '(default)'}")
    print(f"lang: {args.lang}")

    try:
        available = set(pytesseract.get_languages(config=""))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"error: could not query tesseract languages: {exc}") from exc

    available_norm = {name.split("/")[-1] for name in available}
    needed = {part for part in args.lang.replace("+", " ").split() if part}
    missing = sorted(needed - available_norm)
    if missing:
        hint = user_tessdata_dir()
        raise SystemExit(
            "error: missing Tesseract language data: "
            + ", ".join(missing)
            + f"\ninstalled: {', '.join(sorted(available_norm))}\n"
            f"Put jpn.traineddata in:\n  {hint}\n"
            "Download:\n"
            "  https://github.com/tesseract-ocr/tessdata_fast/raw/main/jpn.traineddata"
        )

    jobs = resolve_jobs(args.inputs)
    if not jobs:
        print("error: nothing to convert", file=sys.stderr)
        return 1

    for png_dir, md_path in jobs:
        print(f"{png_dir.name} -> {md_path}")
        convert_doc(png_dir, md_path, lang=args.lang)
        print(f"  wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
