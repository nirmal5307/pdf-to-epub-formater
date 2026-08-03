"""Tests for image-only page detection and OCR suggestions."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from app.converter.pdf_extract import _needs_ocr, extract_book, tesseract_available


def _image_only_pdf(tmp_path: Path, pages: int = 2) -> Path:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=400, height=500)
        # Solid pixmap as a fake scanned page (no text layer)
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 200, 250), 0)
        pix.set_rect(pix.irect, (40 + i * 20, 60, 90))
        page.insert_image(page.rect, pixmap=pix)
    path = tmp_path / "scan-like.pdf"
    doc.save(path)
    doc.close()
    return path


def test_needs_ocr_true_for_image_only_page(tmp_path: Path):
    pdf = _image_only_pdf(tmp_path, pages=1)
    doc = fitz.open(pdf)
    try:
        assert _needs_ocr(doc[0]) is True
    finally:
        doc.close()


def test_needs_ocr_false_for_text_page(tmp_pdf):
    pdf = tmp_pdf(
        [[("body", "Enough native text that OCR should not be suggested for this page.")]],
        "texty.pdf",
    )
    doc = fitz.open(pdf)
    try:
        assert _needs_ocr(doc[0]) is False
    finally:
        doc.close()


def test_extract_suggests_ocr_when_disabled(tmp_path: Path):
    pdf = _image_only_pdf(tmp_path, pages=2)
    book = extract_book(str(pdf), ocr=False)
    assert book.image_only_pages >= 1
    assert book.warnings
    assert any("ocr" in w.lower() for w in book.warnings)
    assert any("image-only" in w.lower() or "scanned" in w.lower() for w in book.warnings)


def test_extract_text_pdf_no_ocr_suggestion(tmp_pdf):
    pdf = tmp_pdf(
        [
            [("title", "Readable Book"), ("body", "Chapter prose with a real text layer.")],
            [("h1", "Chapter 1"), ("body", "More body text so this is not treated as a scan.")],
        ],
        "readable.pdf",
    )
    book = extract_book(str(pdf), ocr=False)
    assert book.image_only_pages == 0
    assert not any("ocr" in w.lower() for w in book.warnings)


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract not installed")
def test_extract_with_ocr_skips_enable_suggestion(tmp_path: Path):
    pdf = _image_only_pdf(tmp_path, pages=2)
    book = extract_book(str(pdf), ocr=True)
    assert not any("enable ocr" in w.lower() for w in book.warnings)
    assert not any("install tesseract" in w.lower() for w in book.warnings)
