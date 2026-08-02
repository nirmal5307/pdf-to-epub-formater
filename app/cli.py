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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert PDF(s) into e-ink-friendly EPUB(s)."
    )
    parser.add_argument("pdf", type=Path, nargs="+", help="Input PDF path(s)")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output EPUB path (single file only)",
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
        "--page-margin",
        choices=["tight", "normal", "roomy"],
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

    if args.output and len(args.pdf) > 1:
        print("Use -o only with a single input PDF.", file=sys.stderr)
        return 2

    cover_bytes = None
    cover_ext = "jpeg"
    if args.cover:
        if len(args.pdf) > 1:
            print("Custom --cover only works with a single PDF.", file=sys.stderr)
            return 2
        cover_bytes = args.cover.read_bytes()
        cover_ext = args.cover.suffix.lstrip(".").lower() or "jpeg"

    profile = READER_PROFILES.get(args.reader_profile, READER_PROFILES["universal"])
    defaults = dict(profile["defaults"])

    def pick(cli_val, key, cast=lambda x: x):
        if cli_val is not None:
            return cast(cli_val)
        return cast(defaults[key])

    def progress(current: int, total: int, stage: str) -> None:
        pct = int(100 * current / max(total, 1))
        print(f"\r[{stage}] {pct}% ({current}/{total})", end="", flush=True)

    try:
        for pdf in args.pdf:
            opts = ConvertOptions(
                title=args.title if len(args.pdf) == 1 else None,
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
                page_margin=pick(args.page_margin, "page_margin"),
                image_max_edge=pick(args.image_max_edge, "image_max_edge", int),
                chapter_break_style=args.chapter_break_style or "page",
            ).normalized()
            out = args.output if len(args.pdf) == 1 else pdf.with_suffix(".epub")
            result = convert_pdf_to_epub(
                pdf,
                output_path=out,
                progress=progress,
                options=opts,
            )
            print(f"\nWrote {result}")
    except OcrUnavailableError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
