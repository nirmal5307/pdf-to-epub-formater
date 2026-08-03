"""Tests for multi-column reading order and caption attachment."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from app.converter.epub_builder import _block_to_html
from app.converter.pdf_extract import (
    Block,
    _attach_captions,
    _detect_two_column,
    extract_book,
)


def _two_column_page(doc: fitz.Document, left_lines: list[str], right_lines: list[str]) -> None:
    page = doc.new_page(width=595, height=842)
    y = 72.0
    for line in left_lines:
        page.insert_textbox(fitz.Rect(36, y, 260, y + 48), line, fontsize=10, fontname="helv")
        y += 52
    y = 72.0
    for line in right_lines:
        page.insert_textbox(fitz.Rect(330, y, 560, y + 48), line, fontsize=10, fontname="helv")
        y += 52


@pytest.fixture
def two_column_pdf(tmp_path: Path) -> Path:
    doc = fitz.open()
    left = [
        "Left column opens with a short lead sentence about layout.",
        "More left text keeps the cluster dense on this side.",
        "A third left paragraph fills the gutters heuristic.",
        "Fourth left block stays clearly under forty percent.",
    ]
    right = [
        "Right column starts far past the page midline here.",
        "Second right paragraph continues the opposite cluster.",
        "Third right block confirms a sparse middle gutter.",
        "Fourth right line finishes the two column sample.",
    ]
    _two_column_page(doc, left, right)
    _two_column_page(doc, left, right)
    path = tmp_path / "two-column.pdf"
    doc.save(path)
    doc.close()
    return path


def test_detect_two_column_with_gutter():
    width = 600.0
    raw = []
    for i in range(4):
        raw.append(
            (80.0, 80.0 + i * 40, Block(kind="p", text=f"Left {i} body", page=0, x=80, y=80 + i * 40))
        )
        raw.append(
            (
                360.0,
                80.0 + i * 40,
                Block(kind="p", text=f"Right {i} body", page=0, x=360, y=80 + i * 40),
            )
        )
    assert _detect_two_column(raw, width) is True


def test_detect_two_column_rejects_indented_single_column():
    width = 600.0
    raw = [
        (
            90.0,
            80.0 + i * 30,
            Block(kind="p", text=f"Body line {i} with indent", page=0, x=90, y=80 + i * 30),
        )
        for i in range(8)
    ]
    assert _detect_two_column(raw, width) is False


def test_attach_captions_moves_figure_label():
    blocks = [
        Block(kind="p", text="Intro paragraph before the figure.", page=1, x=72, y=40),
        Block(kind="img", text="", page=1, x=72, y=100, image_id="img1"),
        Block(kind="p", text="Figure 1. Sample diagram", page=1, x=80, y=180),
        Block(
            kind="p",
            text="Normal prose continues after the caption with a longer sentence.",
            page=1,
            x=72,
            y=220,
        ),
    ]
    out = _attach_captions(blocks)
    kinds = [b.kind for b in out]
    assert kinds[:3] == ["p", "img", "caption"]
    assert out[2].text.startswith("Figure 1")
    assert out[-1].kind == "p"


def test_caption_html_uses_class():
    html, first = _block_to_html(Block(kind="caption", text="Fig. 2 Detail"), True)
    assert 'class="caption"' in html
    assert "Fig. 2 Detail" in html
    assert first is True


def test_extract_two_column_warns(two_column_pdf: Path):
    book = extract_book(str(two_column_pdf))
    assert book.multi_column_pages >= 1
    assert book.warnings
    assert "multi-column" in book.warnings[0].lower()
