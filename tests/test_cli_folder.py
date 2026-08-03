"""Tests for CLI folder PDF collection and convert."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.cli import collect_pdfs, main


def test_collect_pdfs_from_folder(tmp_path: Path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "b.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "notes.txt").write_text("nope", encoding="utf-8")
    found = collect_pdfs([tmp_path])
    assert [p.name for p in found] == ["a.pdf", "b.pdf"]


def test_collect_pdfs_recursive(tmp_path: Path):
    nested = tmp_path / "nested"
    nested.mkdir()
    (tmp_path / "top.pdf").write_bytes(b"%PDF-1.4")
    (nested / "deep.pdf").write_bytes(b"%PDF-1.4")
    assert [p.name for p in collect_pdfs([tmp_path])] == ["top.pdf"]
    names = {p.name for p in collect_pdfs([tmp_path], recursive=True)}
    assert names == {"top.pdf", "deep.pdf"}


def test_collect_pdfs_empty_folder_errors(tmp_path: Path):
    with pytest.raises(ValueError, match="No PDF"):
        collect_pdfs([tmp_path])


def test_cli_folder_convert(tmp_path, tmp_pdf):
    folder = tmp_path / "library"
    out_dir = tmp_path / "epubs"
    folder.mkdir()
    pdf_a = tmp_pdf(
        [[("title", "Book A"), ("body", "Body text for book A conversion.")]],
        "book-a.pdf",
    )
    pdf_b = tmp_pdf(
        [[("title", "Book B"), ("body", "Body text for book B conversion.")]],
        "book-b.pdf",
    )
    # Copy into folder (tmp_pdf writes under tmp_path root)
    target_a = folder / "book-a.pdf"
    target_b = folder / "book-b.pdf"
    target_a.write_bytes(pdf_a.read_bytes())
    target_b.write_bytes(pdf_b.read_bytes())

    code = main(
        [
            str(folder),
            "--output-dir",
            str(out_dir),
            "--reader-profile",
            "universal",
            "--no-eink-images",
        ]
    )
    assert code == 0
    assert (out_dir / "book-a.epub").is_file()
    assert (out_dir / "book-b.epub").is_file()
