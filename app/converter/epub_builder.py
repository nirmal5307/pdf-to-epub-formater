"""Build an EPUB3 package optimized for e-ink readers."""

from __future__ import annotations

import html
import uuid
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from ebooklib import epub

from .options import BODY_SIZES, MARGIN_PRESETS, ConvertOptions
from .pdf_extract import ExtractedBook

SERIF_STACK = (
    '"Palatino Linotype", "Book Antiqua", Palatino, Georgia, "Times New Roman", serif'
)
SANS_STACK = (
    '"Helvetica Neue", Helvetica, Arial, "Noto Sans", sans-serif'
)


def build_eink_css(options: ConvertOptions | None = None) -> str:
    opts = (options or ConvertOptions()).normalized()
    font = SERIF_STACK if opts.font_stack == "serif" else SANS_STACK
    size = BODY_SIZES.get(opts.body_size, "1em")
    padding = MARGIN_PRESETS.get(opts.page_margin, MARGIN_PRESETS["normal"])
    align = "justify" if opts.text_align == "justify" else "left"
    indent = "1.2em" if opts.paragraph_indent else "0"
    hyphens = "auto" if opts.hyphenate else "manual"
    chapter_break = (
        "page-break-before: always; break-before: page;"
        if opts.page_break_chapters and opts.chapter_break_style == "page"
        else "margin-top: 2.2em;"
    )

    return f"""
@charset "UTF-8";

html {{
  -webkit-text-size-adjust: 100%;
}}

body {{
  margin: 0;
  padding: {padding};
  font-family: {font};
  font-size: {size};
  line-height: {opts.line_height};
  color: #000;
  background: #fff;
  text-align: {align};
  hyphens: {hyphens};
  -webkit-hyphens: {hyphens};
  widows: 2;
  orphans: 2;
}}

h1, h2, h3, h4 {{
  font-family: {font};
  font-weight: bold;
  color: #000;
  text-align: left;
  page-break-after: avoid;
  break-after: avoid;
  line-height: 1.25;
  margin: 1.4em 0 0.6em;
}}

h1 {{ font-size: 1.55em; margin-top: 0; }}
h2 {{ font-size: 1.3em; }}
h3 {{ font-size: 1.12em; }}

p {{
  margin: 0 0 0.75em;
  text-indent: {indent};
}}

p.first, h1 + p, h2 + p, h3 + p, .no-indent {{
  text-indent: 0;
}}

img, .figure img {{
  display: block;
  max-width: 100%;
  height: auto;
  margin: 1em auto;
  page-break-inside: avoid;
  break-inside: avoid;
}}

.figure {{
  margin: 1.1em 0;
  text-align: center;
  page-break-inside: avoid;
}}

.caption {{
  font-size: 0.9em;
  font-style: italic;
  text-align: center;
  text-indent: 0;
  margin: 0.3em 0 1em;
}}

.title-page {{
  text-align: center;
  margin-top: 30%;
}}

.title-page h1 {{
  font-size: 1.8em;
  text-align: center;
  margin-bottom: 0.6em;
}}

.title-page .author {{
  font-size: 1.15em;
  font-style: italic;
  text-indent: 0;
}}

.cover {{
  margin: 0;
  padding: 0;
  text-align: center;
}}

.cover img {{
  display: block;
  width: 100%;
  max-width: 100%;
  height: auto;
  margin: 0 auto;
}}

.chapter-title {{
  {chapter_break}
}}

a {{
  color: #000;
  text-decoration: underline;
}}
"""


def _block_to_html(block, first_para: bool) -> tuple[str, bool]:
    text = html.escape(block.text)
    if block.kind == "h1":
        return f"<h1>{text}</h1>\n", True
    if block.kind == "h2":
        return f"<h2>{text}</h2>\n", True
    if block.kind == "h3":
        return f"<h3>{text}</h3>\n", True

    cls = ' class="first"' if first_para else ""
    return f"<p{cls}>{text}</p>\n", False


def _make_chapter(
    uid: str,
    title: str,
    file_name: str,
    body: str,
    css_item: epub.EpubItem,
    lang: str = "en",
) -> epub.EpubHtml:
    chapter = epub.EpubHtml(
        title=title[:200] or "Chapter",
        file_name=file_name,
        lang=lang or "en",
        uid=uid,
    )
    chapter.set_content(body.encode("utf-8"))
    chapter.add_item(css_item)
    return chapter


def build_epub(
    book: ExtractedBook,
    output_path: str | Path,
    progress: Any | None = None,
    options: ConvertOptions | None = None,
) -> Path:
    """Write ExtractedBook to an EPUB3 file. Returns output path."""
    opts = (options or ConvertOptions()).normalized()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    epub_book = epub.EpubBook()
    book_id = str(uuid.uuid4())
    epub_book.set_identifier(book_id)
    epub_book.set_title(book.title)
    epub_book.set_language((book.language or opts.language or "en").strip() or "en")
    epub_book.add_author(book.author)
    epub_book.add_metadata("DC", "publisher", "Inkbound (local)")
    epub_book.add_metadata(
        "DC",
        "description",
        f"Converted from PDF ({book.page_count} pages) for e-ink reading "
        f"[{opts.reader_profile}].",
    )

    css_item = epub.EpubItem(
        uid="style_eink",
        file_name="styles/eink.css",
        media_type="text/css",
        content=build_eink_css(opts).encode("utf-8"),
    )
    epub_book.add_item(css_item)

    cover_spine = None
    if book.cover is not None:
        ext = "jpeg" if book.cover.ext in {"jpg", "jpeg"} else book.cover.ext
        if ext not in {"jpeg", "png", "gif"}:
            try:
                from io import BytesIO

                from PIL import Image

                im = Image.open(BytesIO(book.cover.data))
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                buf = BytesIO()
                im.save(buf, format="JPEG", quality=90)
                cover_bytes = buf.getvalue()
                ext = "jpeg"
            except Exception:
                cover_bytes = book.cover.data
                ext = "jpeg"
        else:
            cover_bytes = book.cover.data

        cover_name = f"cover.{ext}"
        epub_book.set_cover(cover_name, cover_bytes, create_page=False)
        cover_body = (
            f'<div class="cover"><img alt="Cover" src="{escape(cover_name)}"/></div>\n'
        )
        cover_spine = _make_chapter(
            "cover-page",
            "Cover",
            "cover.xhtml",
            cover_body,
            css_item,
            lang=book.language,
        )
        epub_book.add_item(cover_spine)

    image_href: dict[str, str] = {}
    mime_map = {
        "png": "image/png",
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
        "tif": "image/tiff",
    }
    for idx, (img_id, asset) in enumerate(book.images.items()):
        ext = asset.ext if asset.ext in mime_map else "png"
        if ext == "jpg":
            ext = "jpeg"
        file_name = f"images/{img_id}.{ext}"
        image_href[img_id] = file_name
        media = mime_map.get(ext, "image/png")
        item = epub.EpubItem(
            uid=f"img_{idx}",
            file_name=file_name,
            media_type=media,
            content=asset.data,
        )
        epub_book.add_item(item)

    title_body = (
        '<div class="title-page">\n'
        f"<h1>{html.escape(book.title)}</h1>\n"
        f'<p class="author">{html.escape(book.author)}</p>\n'
        "</div>\n"
    )
    title_page = _make_chapter(
        "title", "Title", "title.xhtml", title_body, css_item, lang=book.language
    )
    epub_book.add_item(title_page)

    spine_items: list = ["nav"]
    if cover_spine is not None:
        spine_items.append(cover_spine)
    spine_items.append(title_page)
    toc_links: list = []
    total_chapters = max(len(book.chapters), 1)

    for i, chapter in enumerate(book.chapters):
        parts: list[str] = [
            f'<h1 class="chapter-title">{html.escape(chapter.title)}</h1>\n'
        ]
        start = 0
        if (
            chapter.blocks
            and chapter.blocks[0].kind in ("h1", "h2", "h3")
            and chapter.blocks[0].text.strip() == chapter.title.strip()
        ):
            start = 1

        first_para = True
        for block in chapter.blocks[start:]:
            if block.kind == "img" and block.image_id:
                href = image_href.get(block.image_id)
                if not href:
                    continue
                parts.append(
                    f'<div class="figure"><img alt="" src="{escape(href)}"/></div>\n'
                )
                first_para = True
                continue
            if block.kind == "img":
                continue
            html_chunk, resets = _block_to_html(block, first_para)
            parts.append(html_chunk)
            first_para = resets

        body = "".join(parts) or "<p></p>\n"
        chap = _make_chapter(
            f"chap_{i + 1}",
            chapter.title,
            f"chap_{i + 1:04d}.xhtml",
            body,
            css_item,
            lang=book.language,
        )
        epub_book.add_item(chap)
        spine_items.append(chap)
        toc_links.append(chap)

        if progress:
            progress(i + 1, total_chapters, "building")

    if not toc_links:
        toc_links = [title_page]

    epub_book.toc = tuple(toc_links)
    epub_book.add_item(epub.EpubNcx())
    epub_book.add_item(epub.EpubNav())
    epub_book.spine = spine_items

    epub.write_epub(str(output_path), epub_book, {})
    return output_path
