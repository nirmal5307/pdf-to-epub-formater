"""CLI: convert PDF(s) to EPUB without the web UI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.converter import convert_pdf_to_epub  # noqa: E402
from app.converter.options import READER_PROFILES, ConvertOptions  # noqa: E402
from app.converter.pdf_extract import OcrUnavailableError, tesseract_available  # noqa: E402


def collect_pdfs(paths: list[Path], *, recursive: bool = False) -> list[Path]:
    """Expand file and folder paths into a de-duplicated list of PDF files."""
    found: list[Path] = []
    seen: set[Path] = set()

    def add(pdf: Path) -> None:
        key = pdf.resolve()
        if key in seen:
            return
        seen.add(key)
        found.append(pdf)

    for raw in paths:
        path = Path(raw)
        if path.is_file():
            if path.suffix.lower() != ".pdf":
                raise ValueError(f"Not a PDF: {path}")
            add(path)
            continue
        if path.is_dir():
            pattern = "**/*.pdf" if recursive else "*.pdf"
            matches = sorted(p for p in path.glob(pattern) if p.is_file())
            if not matches:
                raise ValueError(f"No PDF files found in folder: {path}")
            for pdf in matches:
                add(pdf)
            continue
        raise ValueError(f"Path not found: {path}")

    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert PDF(s) or folders of PDFs into e-ink-friendly EPUB(s)."
    )
    parser.add_argument(
        "pdf",
        type=Path,
        nargs="+",
        help="Input PDF path(s) and/or folder(s) containing PDFs",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output EPUB path (single file only)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for EPUB outputs (folder / multi-file convert)",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Include PDFs in subfolders when a folder is given",
    )
    parser.add_argument("--title", default=None, help="Override book title (single file)")
    parser.add_argument("--author", default=None, help="Override author")
    parser.add_argument("--language", default="en", help="EPUB language code (default: en)")
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="OCR scanned / image-only pages (requires Tesseract)",
    )
    parser.add_argument("--ocr-lang", default="eng", help="Tesseract language (default: eng)")
    parser.add_argument(
        "--margin-crop",
        type=float,
        default=0.0,
        help="Crop page margins by this percent (0–20)",
    )
    parser.add_argument(
        "--no-eink-images",
        action="store_true",
        help="Keep original colour/size images",
    )
    parser.add_argument(
        "--cover",
        type=Path,
        default=None,
        help="Custom cover image (single file only)",
    )
    parser.add_argument(
        "--reader-profile",
        choices=sorted(READER_PROFILES.keys()),
        default="universal",
        help="E-ink reader preset (default: universal)",
    )
    parser.add_argument(
        "--body-size",
        choices=["small", "medium", "large"],
        default=None,
        help="Body text size override",
    )
    parser.add_argument(
        "--line-height",
        type=float,
        default=None,
        help="Line height override (1.2–2.0)",
    )
    parser.add_argument(
        "--text-align",
        choices=["justify", "left"],
        default=None,
        help="Paragraph alignment",
    )
    parser.add_argument(
        "--font-stack",
        choices=["serif", "sans"],
        default=None,
        help="Preferred font stack",
    )
    parser.add_argument(
        "--embed-fonts",
        action="store_true",
        help="Embed a Latin font subset (helps stubborn readers that ignore CSS stacks)",
    )
    parser.add_argument(
        "--page-margin",
        choices=["tight", "compact", "normal", "roomy"],
        default=None,
        help="Page padding preset",
    )
    parser.add_argument(
        "--image-max-edge",
        type=int,
        default=None,
        help="Max image edge in pixels after e-ink pass",
    )
    parser.add_argument(
        "--chapter-break",
        choices=["page", "space"],
        default=None,
        dest="chapter_break_style",
        help="Chapter break style",
    )
    parser.add_argument(
        "--no-hyphenate",
        action="store_true",
        help="Disable CSS hyphenation",
    )
    parser.add_argument(
        "--no-indent",
        action="store_true",
        help="Disable paragraph first-line indent",
    )
    args = parser.parse_args(argv)

    if args.ocr and not tesseract_available():
        print(
            "OCR requested but Tesseract was not found on PATH.\n"
            "Install with: brew install tesseract",
            file=sys.stderr,
        )
        return 2

    try:
        pdfs = collect_pdfs(list(args.pdf), recursive=args.recursive)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.output and len(pdfs) > 1:
        print("Use -o only with a single input PDF.", file=sys.stderr)
        return 2
    if args.output and args.output_dir:
        print("Use either -o or --output-dir, not both.", file=sys.stderr)
        return 2

    cover_bytes = None
    cover_ext = "jpeg"
    if args.cover:
        if len(pdfs) > 1:
            print("Custom --cover only works with a single PDF.", file=sys.stderr)
            return 2
        cover_bytes = args.cover.read_bytes()
        cover_ext = args.cover.suffix.lstrip(".").lower() or "jpeg"

    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    profile = READER_PROFILES.get(args.reader_profile, READER_PROFILES["universal"])
    defaults = dict(profile["defaults"])

    def pick(cli_val, key, cast=lambda x: x):
        if cli_val is not None:
            return cast(cli_val)
        return cast(defaults[key])

    def progress(current: int, total: int, stage: str) -> None:
        pct = int(100 * current / max(total, 1))
        print(f"\r[{stage}] {pct}% ({current}/{total})", end="", flush=True)

    failures = 0
    single = len(pdfs) == 1
    try:
        for index, pdf in enumerate(pdfs, start=1):
            if len(pdfs) > 1:
                print(f"\n[{index}/{len(pdfs)}] {pdf.name}", flush=True)
            opts = ConvertOptions(
                title=args.title if single else None,
                author=args.author,
                language=args.language,
                ocr=args.ocr,
                ocr_lang=args.ocr_lang,
                margin_crop=args.margin_crop,
                eink_images=not args.no_eink_images,
                custom_cover=cover_bytes,
                custom_cover_ext=cover_ext,
                reader_profile=args.reader_profile,
                body_size=pick(args.body_size, "body_size"),
                line_height=pick(args.line_height, "line_height", float),
                text_align=pick(args.text_align, "text_align"),
                paragraph_indent=False if args.no_indent else bool(defaults["paragraph_indent"]),
                hyphenate=False if args.no_hyphenate else bool(defaults["hyphenate"]),
                page_break_chapters=bool(defaults["page_break_chapters"]),
                font_stack=pick(args.font_stack, "font_stack"),
                embed_fonts=bool(args.embed_fonts),
                page_margin=pick(args.page_margin, "page_margin"),
                image_max_edge=pick(args.image_max_edge, "image_max_edge", int),
                chapter_break_style=args.chapter_break_style or "page",
            ).normalized()
            if args.output is not None:
                out = args.output
            elif args.output_dir is not None:
                out = args.output_dir / f"{pdf.stem}.epub"
            else:
                out = pdf.with_suffix(".epub")
            try:
                result = convert_pdf_to_epub(
                    pdf,
                    output_path=out,
                    progress=progress,
                    options=opts,
                )
            except OcrUnavailableError:
                raise
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"\nFailed {pdf}: {exc}", file=sys.stderr)
                continue
            print(f"\nWrote {result.path}")
            for warning in result.warnings:
                print(f"Note: {warning}", file=sys.stderr)
    except OcrUnavailableError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 2

    if failures:
        print(f"\nFinished with {failures} failure(s).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
