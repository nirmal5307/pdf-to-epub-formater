"""End-to-end PDF → EPUB conversion."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .eink_images import optimize_book_images, optimize_cover
from .epub_builder import build_epub
from .options import ConvertOptions
from .pdf_extract import ImageAsset, extract_book

ProgressCb = Callable[[int, int, str], None]


@dataclass
class ConvertResult:
    path: Path
    warnings: list[str] = field(default_factory=list)
    multi_column_pages: int = 0
    image_only_pages: int = 0

    def __str__(self) -> str:
        return str(self.path)

    def __fspath__(self) -> str:
        return str(self.path)


def convert_pdf_to_epub(
    pdf_path: str | Path,
    output_path: str | Path | None = None,
    title: str | None = None,
    author: str | None = None,
    progress: ProgressCb | None = None,
    ocr: bool = False,
    *,
    options: ConvertOptions | None = None,
) -> ConvertResult:
    """
    Convert a PDF file into an e-ink-friendly EPUB.

    Pass ``options`` for OCR language, margin crop, e-ink image pass,
    language metadata, custom cover, and reader typography.
    """
    opts = options or ConvertOptions(
        title=title,
        author=author,
        ocr=ocr,
    )
    if title:
        opts.title = title
    if author:
        opts.author = author
    if ocr:
        opts.ocr = True
    opts = opts.normalized()

    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if output_path is None:
        output_path = pdf_path.with_suffix(".epub")
    else:
        output_path = Path(output_path)

    book = extract_book(
        str(pdf_path),
        progress=progress,
        ocr=opts.ocr,
        ocr_lang=opts.ocr_lang,
        margin_crop=opts.margin_crop,
    )
    if opts.title:
        book.title = opts.title.strip() or book.title
    if opts.author:
        book.author = opts.author.strip() or book.author
    book.language = (opts.language or "en").strip() or "en"

    if opts.custom_cover:
        ext = opts.custom_cover_ext.lower().replace("jpg", "jpeg")
        book.cover = ImageAsset(
            id="cover",
            data=opts.custom_cover,
            ext=ext if ext in {"jpeg", "png", "gif", "webp"} else "jpeg",
            width=0,
            height=0,
            page=0,
            y=0.0,
            full_page=True,
        )

    if opts.eink_images:
        if progress:
            progress(0, 1, "eink")
        custom = opts.custom_cover is not None
        book.images = optimize_book_images(
            book.images,
            greyscale=True,
            max_edge=opts.image_max_edge,
        )
        book.cover = optimize_cover(
            book.cover,
            greyscale=not custom,
            max_edge=max(opts.image_max_edge, 1400),
        )

    path = build_epub(book, output_path, progress=progress, options=opts)
    return ConvertResult(
        path=path,
        warnings=list(book.warnings),
        multi_column_pages=book.multi_column_pages,
        image_only_pages=book.image_only_pages,
    )
