"""Extract structured text, headings, and images from a PDF."""

from __future__ import annotations

import hashlib
import re
import shutil
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF


@dataclass
class ImageAsset:
    """An image extracted from the PDF, bytes kept as-is when possible."""

    id: str
    data: bytes
    ext: str  # png, jpeg, etc.
    width: int
    height: int
    page: int
    y: float
    full_page: bool = False


@dataclass
class Block:
    """A content block: paragraph, heading, or image reference."""

    kind: str  # "p" | "h1" | "h2" | "h3" | "img"
    text: str = ""
    image_id: str | None = None
    page: int = 0
    y: float = 0.0
    x: float = 0.0


@dataclass
class Chapter:
    title: str
    blocks: list[Block] = field(default_factory=list)


@dataclass
class ExtractedBook:
    title: str
    author: str
    chapters: list[Chapter]
    images: dict[str, ImageAsset]
    page_count: int
    ocr_pages: int = 0
    cover: ImageAsset | None = None
    language: str = "en"


_HEADER_FOOTER_RE = re.compile(
    r"^(?:\d+|(?:page\s+)?\d+(?:\s*(?:of|/)\s*\d+)?|"
    r"chapter\s+\d+|copyright\s*.*|©.*)$",
    re.IGNORECASE,
)
_CHAPTER_TITLE_RE = re.compile(
    r"^(?:chapter|part|section|book)\s+[\wivxlcdm\d]+(?:\s*[:.\-–—].*)?$",
    re.IGNORECASE,
)
_PART_TITLE_RE = re.compile(
    r"^part\s+(?:one|two|three|four|five|six|seven|eight|nine|ten|[\divxlcdm\d]+)(?:\s*[:.\-–—].*)?$",
    re.IGNORECASE,
)
_SKIP_TOC_RE = re.compile(
    r"^(?:cover|title(?:\s*page)?|half[\s\-]?title|copyright|dedication|"
    r"also by|about the author|image|illustration|photo|plate|"
    r"this page intentionally left blank|blank)$",
    re.IGNORECASE,
)
_BLANK_OR_PROMO_RE = re.compile(
    r"(?:this page intentionally left blank|want to learn more\?|"
    r"mcgraw[\-\s]?hill e ?book|click here\.?$|"
    r"hope you enjoy this .{0,40}ebook)",
    re.IGNORECASE,
)
_JUNK_TITLE_RE = re.compile(
    r"(?:microsoft\s+word|untitled|document\s*\d*|\.docx?$|wallpaper|"
    r"https?://|www\.|check out the most)",
    re.IGNORECASE,
)
_ZLIB_PAREN_RE = re.compile(
    r"\s*\((?:z-library|1lib|z-lib|libgen|annas-archive)[^)]*\)",
    re.IGNORECASE,
)
_DECORATIVE_RE = re.compile(r"^[\W\d_*✰☆★■□▪▫●○•·\-–—…\.]+$", re.UNICODE)
_HOW_TO_RE = re.compile(r"^how\s+to\b.+", re.IGNORECASE)
_NUMBERED_HOW_TO_RE = re.compile(
    r"^\d{1,3}[\.\):\s]+(how\s+to\b.+)$",
    re.IGNORECASE,
)


class OcrUnavailableError(RuntimeError):
    """Raised when OCR was requested but Tesseract is not available."""


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def tesseract_languages() -> list[str]:
    """Installed Tesseract language codes (excluding osd)."""
    if not tesseract_available():
        return []
    import subprocess

    try:
        out = subprocess.check_output(
            ["tesseract", "--list-langs"],
            stderr=subprocess.STDOUT,
            text=True,
        )
    except Exception:
        return ["eng"]
    langs = []
    for line in out.splitlines():
        code = line.strip()
        if not code or code.lower().startswith("list of") or code == "osd":
            continue
        langs.append(code)
    return langs or ["eng"]


def _normalize_ws(text: str) -> str:
    text = text.replace("\u00ad", "")
    text = text.replace("\r", " ")
    text = re.sub(r"-\n(?=\w)", "", text)
    text = text.replace("\n", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _title_author_from_filename(pdf_path: str) -> tuple[str, str | None]:
    """Derive title/author from common pirate-site / export filenames."""
    stem = Path(pdf_path).stem
    # Web uploads are stored as "{12-hex-job-id}_{original stem}.pdf"
    stem = re.sub(r"^[0-9a-f]{10,16}_", "", stem, flags=re.IGNORECASE)
    stem = _ZLIB_PAREN_RE.sub("", stem)
    stem = re.sub(r"\s*\(\d+\)\s*$", "", stem)
    stem = re.sub(r"\s{2,}", " ", stem).strip(" -_")

    author = None
    m = re.match(r"^(?P<title>.+?)\s*\((?P<author>[^)]+)\)\s*$", stem)
    if m:
        maybe_author = m.group("author").strip()
        if (
            2 <= len(maybe_author) <= 60
            and not re.search(r"\.(sk|com|net|org)\b", maybe_author, re.I)
            and not re.search(r"\d{5,}", maybe_author)
        ):
            return m.group("title").strip(), maybe_author
    return stem or "Untitled", author


def _is_junk_title(title: str) -> bool:
    t = (title or "").strip()
    if not t or len(t) < 3:
        return True
    if _JUNK_TITLE_RE.search(t):
        return True
    if t.lower() in {"unknown", "none", "null", "document"}:
        return True
    return False


def _is_junk_author(author: str) -> bool:
    a = (author or "").strip()
    if not a:
        return True
    if a.lower() in {"unknown", "none", "null", "admin", "user", "ooza", "n/a"}:
        return True
    if len(a) <= 2:
        return True
    if _JUNK_TITLE_RE.search(a):
        return True
    return False


def _resolve_metadata(meta: dict, pdf_path: str) -> tuple[str, str]:
    file_title, file_author = _title_author_from_filename(pdf_path)
    raw_title = (meta.get("title") or "").strip()
    raw_author = (meta.get("author") or "").strip()

    title = file_title if _is_junk_title(raw_title) else raw_title
    if _is_junk_author(raw_author):
        author = file_author or "Unknown"
    else:
        author = raw_author
    return title, author


def _looks_like_header_footer(text: str) -> bool:
    t = text.strip()
    if not t or len(t) > 90:
        return False
    if _HEADER_FOOTER_RE.match(t):
        return True
    if re.fullmatch(r"\d{1,4}", t):
        return True
    return False


def _is_decorative_text(text: str) -> bool:
    t = text.strip()
    if not t:
        return True
    if _DECORATIVE_RE.match(t):
        return True
    letters = sum(ch.isalpha() for ch in t)
    if letters == 0:
        return True
    if letters / max(len(t), 1) < 0.35 and len(t) < 40:
        return True
    return False


def _is_blank_or_promo(text: str) -> bool:
    t = text.strip()
    if not t:
        return True
    if _BLANK_OR_PROMO_RE.search(t):
        return True
    return False


def _looks_like_garbled(text: str) -> bool:
    """Heuristic for OCR/cover-art junk lines."""
    t = text.strip()
    if len(t) < 12:
        return False
    letters = sum(ch.isalpha() for ch in t)
    if letters < 6:
        return True
    # Lots of isolated single letters / odd punctuation density
    singles = len(re.findall(r"(?:^|\s)[A-Za-z](?=\s|$)", t))
    if singles >= 6 and singles >= letters * 0.35:
        return True
    weird = sum(1 for ch in t if ch in r"\|/\\~^`<>{}[]")
    if weird >= 4 and weird / len(t) > 0.08:
        return True
    return False


def _is_strong_chapter_heading(text: str, book_title: str | None = None) -> bool:
    t = text.strip()
    if not t or _is_decorative_text(t) or _looks_like_garbled(t):
        return False
    if t.count(".") >= 5 or t.count("·") >= 5:
        return False
    # Strip trailing page numbers from TOC-ish lines
    t_clean = re.sub(r"[\.\s·•]+\d{1,4}$", "", t).strip()
    if _CHAPTER_TITLE_RE.match(t_clean) or _PART_TITLE_RE.match(t_clean):
        return True
    if _CHAPTER_TITLE_RE.match(t) or _PART_TITLE_RE.match(t):
        return True

    # Numbered lesson/trick titles — but not running headers like "12 Book Title"
    m = re.match(r"^(\d{1,3})[\.\):\s]+(.+)$", t)
    if m and 12 <= len(t) <= 110:
        rest = m.group(2).strip()
        words = rest.split()
        if not (4 <= len(words) <= 16 and sum(ch.isalpha() for ch in rest) >= 10):
            return False
        if book_title:
            bt = re.sub(r"\s+", " ", book_title).strip().lower()
            rl = re.sub(r"\s+", " ", rest).strip().lower()
            if rl == bt or rl in bt or bt.startswith(rl):
                return False
            # Near-equal titles (headers often omit subtitle)
            if len(rl) >= 12 and rl in bt:
                return False
        return True
    return False


def _short_book_title(book_title: str | None) -> str:
    if not book_title:
        return ""
    # First clause before subtitle-ish numbers / colon
    t = re.sub(r"\s+", " ", book_title).strip().lower()
    t = re.split(r"\s+\d{1,3}\b", t, maxsplit=1)[0].strip()
    return t


def _is_part_heading(text: str) -> bool:
    t = text.strip()
    if not t or _is_decorative_text(t):
        return False
    cleaned = re.sub(r"[\.\s·•]+\d{1,4}$", "", t).strip()
    return bool(
        _CHAPTER_TITLE_RE.match(cleaned)
        or _PART_TITLE_RE.match(cleaned)
        or _CHAPTER_TITLE_RE.match(t)
        or _PART_TITLE_RE.match(t)
    )


def _is_trick_heading(text: str, book_title: str | None = None) -> bool:
    """
    Detect lesson/trick titles common in self-help PDFs without a TOC.

    Examples: "How to Make Your Smile Magically Different"
    Rejects running headers that repeat the book title.
    """
    t = text.strip()
    if not t or _is_decorative_text(t) or _looks_like_garbled(t):
        return False
    if t.count(".") >= 5 or t.count("·") >= 5:
        return False

    rest = t
    m = _NUMBERED_HOW_TO_RE.match(t)
    if m:
        rest = m.group(1).strip()
    elif not _HOW_TO_RE.match(t):
        return False

    words = rest.split()
    if not (4 <= len(words) <= 18):
        return False

    short = _short_book_title(book_title)
    rl = re.sub(r"\s+", " ", rest).strip().lower()
    if short:
        if rl == short or rl in short or short.startswith(rl):
            return False
        # "How to Talk to Anyone" header vs full title containing that phrase
        if len(rl) >= 12 and rl in short:
            return False
    return True


def _is_structural_heading(text: str, book_title: str | None = None) -> bool:
    return _is_part_heading(text) or _is_trick_heading(text, book_title)


def _needs_ocr(page: fitz.Page, min_chars: int = 40) -> bool:
    """True when the page looks like a scan / image-only page."""
    chars = _page_char_count(page)
    if chars >= min_chars:
        return False
    # Almost no text + has images → likely scan
    return bool(page.get_images(full=True)) or chars < 8


def _get_text_dict(
    page: fitz.Page, use_ocr: bool, ocr_lang: str = "eng"
) -> tuple[dict, bool]:
    """Return (text dict, used_ocr)."""
    if not use_ocr:
        return page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE), False

    lang = (ocr_lang or "eng").strip() or "eng"
    try:
        tp = page.get_textpage_ocr(dpi=200, language=lang, full=True)
        data = page.get_text("dict", textpage=tp)
        return data, True
    except Exception as exc:  # noqa: BLE001
        if not tesseract_available():
            raise OcrUnavailableError(
                "OCR requires Tesseract. Install it (e.g. `brew install tesseract`) "
                "or convert without OCR."
            ) from exc
        return page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE), False


def _apply_margin_crop(page: fitz.Page, margin_pct: float) -> None:
    """Inset the page cropbox by margin_pct percent of the shorter side."""
    if margin_pct <= 0:
        return
    pct = min(margin_pct, 20.0) / 100.0
    r = page.rect
    inset = min(r.width, r.height) * pct
    if inset * 2 >= min(r.width, r.height):
        return
    page.set_cropbox(
        fitz.Rect(r.x0 + inset, r.y0 + inset, r.x1 - inset, r.y1 - inset)
    )


def _font_stats(doc: fitz.Document) -> tuple[float, float]:
    """Return (median body size, heading size threshold)."""
    sizes: list[float] = []
    sample_pages = min(len(doc), 40)
    for i in range(sample_pages):
        page = doc[i]
        data = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        for block in data.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    s = float(span.get("size", 0))
                    if s > 0 and span.get("text", "").strip():
                        sizes.append(s)
    if not sizes:
        return 11.0, 16.0
    sizes.sort()
    median = sizes[len(sizes) // 2]
    # Stricter than before — avoid promoting body emphasis to headings
    heading = median * 1.45
    return median, heading


def _heading_level(
    size: float,
    body: float,
    heading_min: float,
    flags: int,
    text: str,
) -> str | None:
    """Classify a text block as heading — short, strong signals only."""
    if _is_decorative_text(text) or _looks_like_garbled(text) or _is_blank_or_promo(text):
        return None

    words = text.split()
    if len(text) > 120 or len(words) > 16:
        return None
    if len(words) < 2 and not _is_strong_chapter_heading(text):
        return None
    if text.endswith(".") and len(words) > 8:
        return None
    # TOC dotted leaders
    if text.count(".") >= 5 or text.count("·") >= 5:
        return None

    bold = bool(flags & (1 << 4))
    ratio = size / max(body, 1.0)
    strong = _is_strong_chapter_heading(text)

    if strong:
        return "h1" if ratio >= 1.2 or bold else "h2"

    # All-caps display lines — only if clearly larger than body
    if text.isupper() and 2 <= len(words) <= 10 and len(text) < 80 and ratio >= 1.5:
        return "h2"

    if size < heading_min:
        return None
    if ratio >= 1.85 or (ratio >= 1.6 and bold):
        return "h1"
    if ratio >= 1.5:
        return "h2"
    # Mild emphasis stays body text (do not emit h3 for splitting)
    return None


def _detect_repeated_chrome(doc: fitz.Document, sample: int = 25) -> set[str]:
    """Find short lines that repeat across pages (running headers/footers)."""
    counts: Counter[str] = Counter()
    n = min(len(doc), sample)
    if n < 3:
        return set()
    for i in range(n):
        page = doc[i]
        height = float(page.rect.height)
        data = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        seen_on_page: set[str] = set()
        for block in data.get("blocks", []):
            if block.get("type") != 0:
                continue
            y0 = float(block.get("bbox", (0, 0, 0, 0))[1])
            if not (y0 < height * 0.12 or y0 > height * 0.88):
                continue
            parts = []
            for line in block.get("lines", []):
                parts.append("".join(s.get("text", "") for s in line.get("spans", [])))
            text = _normalize_ws("\n".join(parts))
            if not text or len(text) > 70:
                continue
            # Numbered lesson titles are content, not chrome
            if (
                _is_part_heading(text)
                or _HOW_TO_RE.match(text)
                or _NUMBERED_HOW_TO_RE.match(text)
            ):
                continue
            # Normalize page numbers out so "Chapter 1" headers still match
            key = re.sub(r"\d+", "#", text).lower()
            if key not in seen_on_page:
                seen_on_page.add(key)
                counts[key] += 1
    threshold = max(3, n // 3)
    return {k for k, c in counts.items() if c >= threshold}


def _is_chrome(text: str, y0: float, page_height: float, repeated: set[str]) -> bool:
    # Never strip Part / Chapter / "How to…" lesson titles as running headers
    if _is_part_heading(text) or _HOW_TO_RE.match(text) or _NUMBERED_HOW_TO_RE.match(text):
        return False
    key = re.sub(r"\d+", "#", text).lower()
    in_band = y0 < page_height * 0.10 or y0 > page_height * 0.90
    # Keep real chapter titles even when they sit in the header band
    if _CHAPTER_TITLE_RE.match(text) or (
        text.isupper() and 2 <= len(text.split()) <= 12 and len(text) < 90
    ):
        if y0 < page_height * 0.18:
            return False
    if key in repeated and in_band:
        return True
    if _looks_like_header_footer(text) and in_band:
        return True
    if y0 < page_height * 0.05 or y0 > page_height * 0.96:
        if len(text) < 70 and not _CHAPTER_TITLE_RE.match(text):
            return True
    return False


def _column_key(x0: float, page_width: float, two_col: bool) -> int:
    if not two_col:
        return 0
    return 0 if x0 < page_width * 0.48 else 1


def _detect_two_column(raw_blocks: list[tuple[float, float, Block]], page_width: float) -> bool:
    """Heuristic: enough left and right blocks with a gap in the middle."""
    if len(raw_blocks) < 6:
        return False
    left = sum(1 for x, _, _ in raw_blocks if x < page_width * 0.40)
    right = sum(1 for x, _, _ in raw_blocks if x > page_width * 0.52)
    mid = sum(1 for x, _, b in raw_blocks if page_width * 0.40 <= x <= page_width * 0.52 and b.kind == "p")
    return left >= 3 and right >= 3 and mid <= max(2, (left + right) // 6)


def _merge_paragraphs(blocks: list[Block]) -> list[Block]:
    """Join consecutive body paragraphs that look like wrapped fragments."""
    if not blocks:
        return blocks
    out: list[Block] = []
    for b in blocks:
        if (
            out
            and out[-1].kind == "p"
            and b.kind == "p"
            and out[-1].page == b.page
            and abs(out[-1].x - b.x) < 18
            and out[-1].text
            and b.text
            and not out[-1].text.endswith((".", "!", "?", ":", '"', "”"))
            and b.text[0:1].islower()
        ):
            out[-1].text = f"{out[-1].text} {b.text}"
        else:
            out.append(b)
    return out


def _extract_cover(doc: fitz.Document) -> ImageAsset | None:
    """
    Capture the PDF cover for the EPUB by rendering page 1.

    Rendering matches what you see in a PDF viewer (vectors, text, and art),
    which is more reliable than hoping for a single full-page embedded image.
    """
    if len(doc) == 0:
        return None

    page = doc[0]

    # Prefer a large embedded image when it clearly is the cover art
    page_area = abs(float(page.rect.width * page.rect.height)) or 1.0
    best: tuple[float, bytes, str, int, int] | None = None
    for info in page.get_images(full=True):
        xref = info[0]
        try:
            extracted = doc.extract_image(xref)
        except Exception:
            continue
        if not extracted or not extracted.get("image"):
            continue
        data: bytes = extracted["image"]
        ext = (extracted.get("ext") or "png").lower()
        if ext == "jpg":
            ext = "jpeg"
        w = int(extracted.get("width") or 0)
        h = int(extracted.get("height") or 0)
        if w < 120 or h < 120:
            continue
        cover_ratio = 0.0
        try:
            rects = page.get_image_rects(xref)
            if rects:
                cover_ratio = max(abs(r.width * r.height) / page_area for r in rects)
        except Exception:
            pass
        if cover_ratio >= 0.85 and (best is None or w * h > best[3] * best[4]):
            best = (cover_ratio, data, ext, w, h)

    if best is not None:
        _, data, ext, w, h = best
        return ImageAsset(
            id="cover",
            data=data,
            ext=ext,
            width=w,
            height=h,
            page=0,
            y=0.0,
            full_page=True,
        )

    # Always fall back to a high-quality render of the first page
    try:
        # Clamp very large pages so cover stays portable for e-ink
        zoom = 180 / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        # Cap long edge ~1600px for readers
        long_edge = max(pix.width, pix.height)
        if long_edge > 1600:
            scale = 1600 / long_edge
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom * scale, zoom * scale), alpha=False)
        data = pix.tobytes("jpeg")
        return ImageAsset(
            id="cover",
            data=data,
            ext="jpeg",
            width=int(pix.width),
            height=int(pix.height),
            page=0,
            y=0.0,
            full_page=True,
        )
    except Exception:
        return None


def _extract_images_on_page(
    doc: fitz.Document,
    page: fitz.Page,
    page_index: int,
    images: dict[str, ImageAsset],
    seen_xrefs: set[int],
    skip_full_page: bool,
) -> list[Block]:
    blocks: list[Block] = []
    page_area = abs(float(page.rect.width * page.rect.height)) or 1.0

    for info in page.get_images(full=True):
        xref = info[0]
        if xref in seen_xrefs:
            continue
        try:
            extracted = doc.extract_image(xref)
        except Exception:
            continue
        if not extracted or not extracted.get("image"):
            continue

        data: bytes = extracted["image"]
        ext = (extracted.get("ext") or "png").lower()
        if ext == "jpg":
            ext = "jpeg"

        digest = hashlib.sha1(data).hexdigest()[:12]
        image_id = f"img-{page_index + 1}-{digest}"
        if image_id in images:
            seen_xrefs.add(xref)
            continue

        y = float(page.rect.height)
        x = 0.0
        cover = 0.0
        try:
            rects = page.get_image_rects(xref)
            if rects:
                y = float(min(r.y0 for r in rects))
                x = float(min(r.x0 for r in rects))
                cover = max((abs(r.width * r.height) / page_area) for r in rects)
        except Exception:
            pass

        w = int(extracted.get("width") or 0)
        h = int(extracted.get("height") or 0)
        if w and h and (w < 40 or h < 40):
            continue

        full_page = cover >= 0.70
        if full_page and skip_full_page:
            seen_xrefs.add(xref)
            continue

        images[image_id] = ImageAsset(
            id=image_id,
            data=data,
            ext=ext,
            width=w,
            height=h,
            page=page_index,
            y=y,
            full_page=full_page,
        )
        seen_xrefs.add(xref)
        blocks.append(Block(kind="img", image_id=image_id, page=page_index, y=y, x=x))
    return blocks


def _page_text_blocks(
    data: dict,
    page_index: int,
    body_size: float,
    heading_min: float,
    page_width: float,
    page_height: float,
    repeated_chrome: set[str],
) -> list[Block]:
    """Extract text blocks in reading order, tagging headings."""
    staged: list[tuple[float, float, Block]] = []

    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        bbox = block.get("bbox", (0, 0, 0, 0))
        x0 = float(bbox[0])
        y0 = float(bbox[1])

        line_parts: list[str] = []
        max_size = 0.0
        flags_acc = 0
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            line_parts.append("".join(s.get("text", "") for s in spans))
            for s in spans:
                sz = float(s.get("size", 0))
                if sz > max_size:
                    max_size = sz
                flags_acc |= int(s.get("flags", 0))

        text = _normalize_ws("\n".join(line_parts))
        if not text:
            continue
        if _is_blank_or_promo(text) or _looks_like_garbled(text):
            continue
        if _is_chrome(text, y0, page_height, repeated_chrome):
            continue

        level = _heading_level(max_size, body_size, heading_min, flags_acc, text)
        if level is None and _is_strong_chapter_heading(text):
            level = "h2"

        kind = level or "p"
        staged.append((x0, y0, Block(kind=kind, text=text, page=page_index, y=y0, x=x0)))

    two_col = _detect_two_column(staged, page_width)
    staged.sort(key=lambda t: (_column_key(t[0], page_width, two_col), t[1], t[0]))
    return [b for _, _, b in staged]


def _chapters_from_toc(doc: fitz.Document) -> list[tuple[str, int]] | None:
    toc = doc.get_toc(simple=True)
    if not toc or len(toc) < 2:
        return None
    chapters: list[tuple[str, int]] = []
    seen_pages: set[int] = set()
    for level, title, page in toc:
        if level > 2:
            continue
        title = _normalize_ws(str(title))
        if not title or _SKIP_TOC_RE.match(title) or _is_decorative_text(title):
            continue
        page_idx = max(0, int(page) - 1)
        # Skip duplicate page targets and cover page TOC rows
        if page_idx == 0 and re.search(r"cover|title", title, re.I):
            continue
        if page_idx in seen_pages and chapters and chapters[-1][1] == page_idx:
            continue
        seen_pages.add(page_idx)
        chapters.append((title, page_idx))
    return chapters if len(chapters) >= 2 else None


def _chapter_text_len(chapter: Chapter) -> int:
    return sum(len(b.text) for b in chapter.blocks if b.kind != "img")


def _merge_tiny_chapters(chapters: list[Chapter], min_chars: int = 120) -> list[Chapter]:
    if not chapters:
        return chapters
    merged: list[Chapter] = [chapters[0]]
    for ch in chapters[1:]:
        if _chapter_text_len(ch) < min_chars and merged:
            merged[-1].blocks.extend(ch.blocks)
        else:
            merged.append(ch)
    return [c for c in merged if c.blocks]


def _chunk_by_pages(all_blocks: list[Block], fallback_title: str, chunk_size: int = 20) -> list[Chapter]:
    if not all_blocks:
        return [Chapter(title=fallback_title, blocks=[])]
    max_page = max(b.page for b in all_blocks)
    chapters: list[Chapter] = []
    for start in range(0, max_page + 1, chunk_size):
        end = start + chunk_size - 1
        chunk = [b for b in all_blocks if start <= b.page <= end]
        if chunk:
            chapters.append(Chapter(title=f"Pages {start + 1}–{end + 1}", blocks=chunk))
    return chapters or [Chapter(title=fallback_title, blocks=all_blocks)]


def _split_on_headings(
    all_blocks: list[Block],
    fallback_title: str,
    *,
    strong_only: bool,
    book_title: str | None = None,
    parts_only: bool = False,
    structural: bool = False,
) -> list[Chapter]:
    chapters: list[Chapter] = []
    current = Chapter(title=fallback_title)
    title_for_match = book_title or fallback_title
    for b in all_blocks:
        is_split = False
        if b.kind == "img":
            current.blocks.append(b)
            continue

        if structural:
            is_split = _is_structural_heading(b.text, title_for_match)
        elif b.kind in ("h1", "h2") and len(b.text) < 120:
            if parts_only:
                is_split = _is_part_heading(b.text)
            elif strong_only:
                is_split = _is_strong_chapter_heading(b.text, title_for_match)
            else:
                is_split = True
        elif parts_only:
            is_split = _is_part_heading(b.text)
        elif strong_only:
            # Also catch strong chapter lines mistagged as body text
            is_split = _is_strong_chapter_heading(b.text, title_for_match)

        if is_split:
            if current.blocks:
                chapters.append(current)
            current = Chapter(title=b.text)
            current.blocks.append(b)
        else:
            current.blocks.append(b)
    if current.blocks:
        chapters.append(current)
    return chapters


def _count_structural(all_blocks: list[Block], book_title: str) -> tuple[int, int]:
    parts = 0
    tricks = 0
    seen_tricks: set[str] = set()
    for b in all_blocks:
        if b.kind == "img" or not b.text:
            continue
        if _is_part_heading(b.text):
            parts += 1
        elif _is_trick_heading(b.text, book_title):
            key = re.sub(r"^\d{1,3}[\.\):\s]+", "", b.text).strip().lower()
            if key not in seen_tricks:
                seen_tricks.add(key)
                tricks += 1
    return parts, tricks


def _split_into_chapters(
    all_blocks: list[Block],
    toc: list[tuple[str, int]] | None,
    fallback_title: str,
    page_count: int,
) -> list[Chapter]:
    max_chapters = max(80, min(150, page_count // 2 + 15))

    if toc:
        starts = [p for _, p in toc]
        chapters: list[Chapter] = [Chapter(title=t) for t, _ in toc]
        preface: list[Block] = []
        for b in all_blocks:
            assigned = False
            for i in range(len(starts) - 1, -1, -1):
                if b.page >= starts[i]:
                    chapters[i].blocks.append(b)
                    assigned = True
                    break
            if not assigned:
                preface.append(b)
        preface = [b for b in preface if not (b.page == 0 and b.kind != "img")]
        if preface and _chapter_text_len(Chapter(title="x", blocks=preface)) >= 80:
            chapters.insert(0, Chapter(title="Front matter", blocks=preface))
        chapters = [c for c in chapters if c.blocks]
        chapters = _merge_tiny_chapters(chapters, min_chars=80)
        return chapters or [Chapter(title=fallback_title, blocks=all_blocks)]

    parts_n, tricks_n = _count_structural(all_blocks, fallback_title)

    # Prefer Part + "How to…" lesson structure (Lowndes-style) over page chunks
    if parts_n >= 2 or tricks_n >= 8:
        structural = _split_on_headings(
            all_blocks,
            fallback_title,
            strong_only=False,
            book_title=fallback_title,
            structural=True,
        )
        structural = _merge_tiny_chapters(structural, min_chars=100)
        if 3 <= len(structural) <= max_chapters:
            return structural
        # Fall back to Parts only when tricks explode
        if parts_n >= 2:
            part_chapters = _split_on_headings(
                all_blocks,
                fallback_title,
                strong_only=False,
                book_title=fallback_title,
                parts_only=True,
            )
            part_chapters = _merge_tiny_chapters(part_chapters, min_chars=200)
            if 2 <= len(part_chapters) <= max_chapters:
                return part_chapters

    chapters = _split_on_headings(
        all_blocks, fallback_title, strong_only=False, book_title=fallback_title
    )
    chapters = _merge_tiny_chapters(chapters)

    if len(chapters) > max_chapters:
        chapters = _split_on_headings(
            all_blocks, fallback_title, strong_only=True, book_title=fallback_title
        )
        chapters = _merge_tiny_chapters(chapters)

    if len(chapters) > max_chapters:
        chapters = _split_on_headings(
            all_blocks,
            fallback_title,
            strong_only=True,
            book_title=fallback_title,
            parts_only=True,
        )
        chapters = _merge_tiny_chapters(chapters, min_chars=200)

    if len(chapters) > max_chapters or len(chapters) <= 1:
        if page_count > 40 and (len(chapters) > max_chapters or len(chapters) <= 1):
            return _chunk_by_pages(all_blocks, fallback_title, chunk_size=20)

    return chapters or [Chapter(title=fallback_title, blocks=all_blocks)]


def extract_book(
    pdf_path: str,
    progress: Any | None = None,
    ocr: bool = False,
    ocr_lang: str = "eng",
    margin_crop: float = 0.0,
) -> ExtractedBook:
    """
    Parse a PDF into structured chapters + image assets.

    When ``ocr`` is True, pages with little native text are run through
    Tesseract via PyMuPDF. Full-page scan images are then skipped so the
    EPUB keeps OCR text instead of duplicating the page raster.
    """
    if ocr and not tesseract_available():
        raise OcrUnavailableError(
            "OCR requires Tesseract on your PATH. "
            "Install with `brew install tesseract` (macOS) or disable OCR."
        )

    doc = fitz.open(pdf_path)
    try:
        meta = doc.metadata or {}
        title, author = _resolve_metadata(meta, pdf_path)

        if margin_crop > 0:
            for i in range(len(doc)):
                _apply_margin_crop(doc[i], margin_crop)

        body_size, heading_min = _font_stats(doc)
        repeated = _detect_repeated_chrome(doc)
        images: dict[str, ImageAsset] = {}
        seen_xrefs: set[int] = set()
        all_blocks: list[Block] = []
        total = len(doc)
        ocr_pages = 0

        cover = _extract_cover(doc)

        for i in range(total):
            page = doc[i]
            page_width = float(page.rect.width)
            page_height = float(page.rect.height)

            # Cover page: keep the rendered cover only — skip text/OCR junk
            if i == 0 and cover is not None:
                img_blocks = _extract_images_on_page(
                    doc, page, i, images, seen_xrefs, skip_full_page=True
                )
                all_blocks.extend(img_blocks)
                if progress:
                    progress(i + 1, total, "extracting")
                continue

            page_text = (page.get_text("text") or "").strip()
            if _is_blank_or_promo(page_text) and len(page_text) < 220:
                # Still pull non-full-page images from mostly-blank pages
                img_blocks = _extract_images_on_page(
                    doc, page, i, images, seen_xrefs, skip_full_page=False
                )
                all_blocks.extend(img_blocks)
                if progress and (i % 3 == 0 or i == total - 1):
                    progress(i + 1, total, "extracting")
                continue

            use_ocr = bool(ocr and _needs_ocr(page))
            data, used_ocr = _get_text_dict(page, use_ocr, ocr_lang=ocr_lang)
            if used_ocr:
                ocr_pages += 1
                if progress:
                    progress(i + 1, total, "ocr")

            text_blocks = _page_text_blocks(
                data,
                i,
                body_size if not used_ocr else max(body_size, 11.0),
                heading_min if not used_ocr else max(heading_min, 13.0),
                page_width,
                page_height,
                repeated,
            )
            text_blocks = _merge_paragraphs(text_blocks)

            skip_full = bool(
                used_ocr and any(b.kind != "img" and b.text for b in text_blocks)
            )
            img_blocks = _extract_images_on_page(
                doc, page, i, images, seen_xrefs, skip_full_page=skip_full
            )

            page_blocks = text_blocks + img_blocks
            two_col = _detect_two_column(
                [(b.x, b.y, b) for b in text_blocks], page_width
            )
            page_blocks.sort(
                key=lambda b: (
                    _column_key(b.x, page_width, two_col),
                    b.y,
                    0 if b.kind != "img" else 1,
                    b.x,
                )
            )
            all_blocks.extend(page_blocks)

            if progress and (i % 3 == 0 or i == total - 1):
                progress(i + 1, total, "ocr" if used_ocr else "extracting")

        toc = _chapters_from_toc(doc)
        chapters = _split_into_chapters(all_blocks, toc, title, page_count=total)

        return ExtractedBook(
            title=title,
            author=author,
            chapters=chapters,
            images=images,
            page_count=total,
            ocr_pages=ocr_pages,
            cover=cover,
        )
    finally:
        doc.close()
