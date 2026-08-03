"""Shared conversion options for e-ink export."""

from __future__ import annotations

from dataclasses import dataclass


READER_PROFILES = {
    "universal": {
        "label": "Universal e-ink",
        "hint": "Safe defaults for Xteink, Kobo, Kindle, Boox, PocketBook",
        "tip": "Best starting point. Justifies text, medium type, and balanced image size for most sideload apps.",
        "defaults": {
            "body_size": "medium",
            "line_height": "1.45",
            "text_align": "justify",
            "page_margin": "normal",
            "hyphenate": True,
            "paragraph_indent": True,
            "font_stack": "serif",
            "page_break_chapters": True,
            "image_max_edge": "1200",
        },
    },
    "kobo": {
        "label": "Kobo",
        "hint": "Comfortable margins and hyphenation for Kobo EPUB",
        "tip": "Roomier margins + hyphenation — works well with Kobo’s reflow and sideloaded EPUB.",
        "defaults": {
            "body_size": "medium",
            "line_height": "1.5",
            "text_align": "justify",
            "page_margin": "roomy",
            "hyphenate": True,
            "paragraph_indent": True,
            "font_stack": "serif",
            "page_break_chapters": True,
            "image_max_edge": "1200",
        },
    },
    "kindle": {
        "label": "Kindle",
        "hint": "Simpler CSS tuned for Kindle EPUB sideload",
        "tip": "Left-aligned, no hyphenation, slightly smaller images — kinder to Kindle’s EPUB engine.",
        "defaults": {
            "body_size": "medium",
            "line_height": "1.4",
            "text_align": "left",
            "page_margin": "normal",
            "hyphenate": False,
            "paragraph_indent": True,
            "font_stack": "serif",
            "page_break_chapters": True,
            "image_max_edge": "1000",
        },
    },
    "boox": {
        "label": "BOOX / Android",
        "hint": "Slightly larger type for Android e-ink devices",
        "tip": "Larger type and bigger image budget for Android e-ink apps (NeoReader, etc.).",
        "defaults": {
            "body_size": "large",
            "line_height": "1.5",
            "text_align": "justify",
            "page_margin": "normal",
            "hyphenate": True,
            "paragraph_indent": True,
            "font_stack": "serif",
            "page_break_chapters": True,
            "image_max_edge": "1400",
        },
    },
    "tolino": {
        "label": "Tolino",
        "hint": "Comfortable German/EU Tolino EPUB defaults",
        "tip": "Justify + hyphenation with roomy margins — a solid default for Tolino sideload.",
        "defaults": {
            "body_size": "medium",
            "line_height": "1.5",
            "text_align": "justify",
            "page_margin": "roomy",
            "hyphenate": True,
            "paragraph_indent": True,
            "font_stack": "serif",
            "page_break_chapters": True,
            "image_max_edge": "1200",
        },
    },
    "compact": {
        "label": "Compact / small screens",
        "hint": "Tighter margins for smaller panels",
        "tip": "Tighter margins and smaller type for Xteink-class / small panels — more words per page.",
        "defaults": {
            "body_size": "small",
            "line_height": "1.35",
            "text_align": "justify",
            "page_margin": "tight",
            "hyphenate": True,
            "paragraph_indent": False,
            "font_stack": "serif",
            "page_break_chapters": True,
            "image_max_edge": "900",
        },
    },
    "comfort": {
        "label": "Large type / comfort",
        "hint": "Bigger type and spacing for easier reading",
        "tip": "One-click comfort: large type, roomy margins, open line height — great for long sessions.",
        "defaults": {
            "body_size": "large",
            "line_height": "1.6",
            "text_align": "left",
            "page_margin": "roomy",
            "hyphenate": False,
            "paragraph_indent": False,
            "font_stack": "sans",
            "page_break_chapters": True,
            "image_max_edge": "1100",
        },
    },
}

BODY_SIZES = {
    "small": "0.95em",
    "medium": "1em",
    "large": "1.15em",
}

MARGIN_PRESETS = {
    "tight": "0.4em 0.5em 0.9em",
    "normal": "0.6em 0.8em 1.2em",
    "roomy": "0.9em 1.1em 1.5em",
}


@dataclass
class ConvertOptions:
    title: str | None = None
    author: str | None = None
    language: str = "en"
    ocr: bool = False
    ocr_lang: str = "eng"
    margin_crop: float = 0.0
    eink_images: bool = True
    custom_cover: bytes | None = None
    custom_cover_ext: str = "jpeg"

    reader_profile: str = "universal"
    body_size: str = "medium"
    line_height: float = 1.45
    text_align: str = "justify"
    paragraph_indent: bool = True
    hyphenate: bool = True
    page_break_chapters: bool = True
    font_stack: str = "serif"
    embed_fonts: bool = False
    page_margin: str = "normal"
    image_max_edge: int = 1200
    chapter_break_style: str = "page"

    def normalized(self) -> "ConvertOptions":
        """Return a copy with clamped/validated fields."""
        profile = self.reader_profile if self.reader_profile in READER_PROFILES else "universal"
        return ConvertOptions(
            title=self.title,
            author=self.author,
            language=(self.language or "en").strip() or "en",
            ocr=self.ocr,
            ocr_lang=(self.ocr_lang or "eng").strip() or "eng",
            margin_crop=max(0.0, min(float(self.margin_crop or 0), 20.0)),
            eink_images=self.eink_images,
            custom_cover=self.custom_cover,
            custom_cover_ext=self.custom_cover_ext or "jpeg",
            reader_profile=profile,
            body_size=self.body_size if self.body_size in BODY_SIZES else "medium",
            line_height=max(1.2, min(float(self.line_height or 1.45), 2.0)),
            text_align=self.text_align if self.text_align in {"justify", "left"} else "justify",
            paragraph_indent=bool(self.paragraph_indent),
            hyphenate=bool(self.hyphenate),
            page_break_chapters=bool(self.page_break_chapters),
            font_stack=self.font_stack if self.font_stack in {"serif", "sans"} else "serif",
            embed_fonts=bool(self.embed_fonts),
            page_margin=self.page_margin if self.page_margin in MARGIN_PRESETS else "normal",
            image_max_edge=max(600, min(int(self.image_max_edge or 1200), 2000)),
            chapter_break_style=self.chapter_break_style
            if self.chapter_break_style in {"page", "space"}
            else "page",
        )
