"""Unit tests for heading detection and chapter splitting."""

from __future__ import annotations

from app.converter.pdf_extract import (
    Block,
    _is_part_heading,
    _is_trick_heading,
    _split_into_chapters,
    _title_author_from_filename,
    extract_book,
)


def test_strips_job_id_prefix_from_filename():
    title, author = _title_author_from_filename(
        "/tmp/a1b2c3d4e5f6_How to Talk to Anyone (Leil Lowndes).pdf"
    )
    assert title == "How to Talk to Anyone"
    assert author == "Leil Lowndes"


def test_strips_zlib_suffix():
    title, _ = _title_author_from_filename("Cool Book (z-library.sk).pdf")
    assert "z-library" not in title.lower()
    assert title == "Cool Book"


def test_part_heading_detection():
    assert _is_part_heading("Part One")
    assert _is_part_heading("PART II — Advanced")
    assert _is_part_heading("Chapter 3: Beginnings")
    assert not _is_part_heading("How to smile better")


def test_trick_heading_detection():
    book = "How to Talk to Anyone"
    assert _is_trick_heading("How to Make Your Smile Magically Different", book)
    assert _is_trick_heading("12. How to Win Over Crowds Instantly", book)
    # Running header that repeats the book title should be rejected
    assert not _is_trick_heading("How to Talk to Anyone", book)
    assert not _is_trick_heading("How to", book)


def test_structural_split_prefers_parts_and_tricks():
    book_title = "How to Talk to Anyone"
    blocks: list[Block] = [
        Block(kind="h1", text="Part One", page=1),
        Block(kind="p", text="Intro body " * 20, page=1),
    ]
    for i in range(1, 10):
        blocks.append(Block(kind="h1", text=f"How to Do Amazing Trick {i} Well", page=i + 1))
        blocks.append(Block(kind="p", text="Lesson body text. " * 30, page=i + 1))
    blocks.append(Block(kind="h1", text="Part Two", page=12))
    blocks.append(Block(kind="p", text="Part two intro. " * 20, page=12))
    for i in range(10, 16):
        blocks.append(Block(kind="h1", text=f"How to Do Amazing Trick {i} Well", page=i + 3))
        blocks.append(Block(kind="p", text="More lesson text. " * 30, page=i + 3))

    chapters = _split_into_chapters(blocks, toc=None, fallback_title=book_title, page_count=40)
    titles = [c.title for c in chapters]
    assert any(t.startswith("Part ") for t in titles)
    assert any(t.startswith("How to ") for t in titles)
    assert len(chapters) >= 8
    # Must not fall back to "Pages 1–20" style chunks
    assert not any(t.lower().startswith("pages ") for t in titles)


def test_extract_lowndes_like_pdf(lowndes_like_pdf):
    book = extract_book(str(lowndes_like_pdf))
    titles = [c.title for c in book.chapters]
    assert any("Part" in t for t in titles)
    assert any(t.startswith("How to ") for t in titles)
    assert len(book.chapters) >= 8
