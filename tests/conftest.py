"""Shared helpers for Inkbound tests."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest


@pytest.fixture
def tmp_pdf(tmp_path: Path):
    """Factory: write a simple multi-page PDF and return its path."""

    def _make(pages: list[list[tuple[str, str]]], name: str = "sample.pdf") -> Path:
        """
        pages: list of pages; each page is list of (style, text)
        style: "title" | "h1" | "body"
        """
        doc = fitz.open()
        for page_blocks in pages:
            page = doc.new_page(width=595, height=842)
            y = 96.0
            for style, text in page_blocks:
                size = {"title": 20, "h1": 16, "body": 11}.get(style, 11)
                height = 120.0 if style == "body" else 36.0
                rect = fitz.Rect(72, y, 520, y + height)
                page.insert_textbox(rect, text, fontsize=size, fontname="helv")
                y = rect.y1 + 12
        path = tmp_path / name
        doc.save(path)
        doc.close()
        return path

    return _make


@pytest.fixture
def lowndes_like_pdf(tmp_pdf) -> Path:
    """Synthetic PDF with Parts + How-to tricks (no TOC)."""
    pages: list[list[tuple[str, str]]] = [
        [
            ("title", "How to Talk to Anyone"),
            ("body", "A practical book of social tricks for everyday conversations."),
        ],
        [
            ("h1", "Part One"),
            ("body", "The first section introduces basic habits for confidence and warmth."),
        ],
    ]
    for i in range(1, 10):
        pages.append(
            [
                ("h1", f"How to Master Social Trick Number {i}"),
                (
                    "body",
                    "This lesson explains a concrete technique with enough prose so the "
                    "chapter is not considered tiny when chapters are merged later on.",
                ),
            ]
        )
    pages.append(
        [
            ("h1", "Part Two"),
            ("body", "The second part covers advanced conversation patterns and posture."),
        ]
    )
    for i in range(10, 18):
        pages.append(
            [
                ("h1", f"How to Master Social Trick Number {i}"),
                (
                    "body",
                    "More advice with substantial paragraph text for chapter merging and "
                    "stable EPUB navigation across e-ink readers.",
                ),
            ]
        )
    return tmp_pdf(pages, "How to Talk to Anyone.pdf")
