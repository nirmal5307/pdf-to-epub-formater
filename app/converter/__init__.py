"""PDF → EPUB conversion pipeline for e-ink readers."""

from .pipeline import ConvertResult, convert_pdf_to_epub

__all__ = ["ConvertResult", "convert_pdf_to_epub"]
