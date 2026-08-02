# Inkbound — Local PDF to EPUB Converter for E-Ink Readers

**Inkbound** is a free, open-source, **offline PDF to EPUB converter** built for e-ink devices.  
Convert PDF books into reflowable **EPUB3** files tuned for **Kobo, Kindle, BOOX, PocketBook, Xteink X4**, and other e-readers — with **no cloud upload**.

Drop a PDF → pick a reader profile → download an e-ink-friendly EPUB.  
Also works from the command line for batch conversion.

[![License: MIT](https://img.shields.io/badge/License-MIT-teal.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Runs locally](https://img.shields.io/badge/privacy-100%25%20local-success.svg)](#why-inkbound)
[![EPUB3](https://img.shields.io/badge/output-EPUB3%20%2B%20NCX-informational.svg)](#features)

![Inkbound web UI — PDF to EPUB for e-ink](docs/screenshots/inkbound-home.jpg)

> Looking for a **PDF to EPUB** tool that keeps books private, preserves covers, supports OCR for scans, and exports CSS that looks good on e-ink? Inkbound is built for that.

---

## Why Inkbound?

| Need | Inkbound |
|------|----------|
| Convert **PDF to EPUB** for sideloading | Yes — EPUB3 + NCX for wide device support |
| Keep files **offline / private** | Yes — nothing leaves your machine |
| Optimize for **e-ink readers** | Yes — greyscale images, typography presets |
| Support **Kobo / Kindle / BOOX / PocketBook / Xteink** | Yes — reader profiles with sensible defaults |
| Handle **scanned PDFs** | Optional local **Tesseract OCR** |
| Batch convert many PDFs | Web UI + CLI |

**Keywords people search for:** pdf to epub, pdf to ebook, epub converter, e-ink epub, kobo epub sideload, kindle epub, boox converter, pocketbook epub, offline pdf converter, local ebook converter, tesseract ocr pdf, reflowable epub from pdf.

---

## Features

- **Reader profiles** — Universal, Kobo, Kindle, BOOX / Android, Compact (small screens)
- **Typography controls** — serif/sans, type size, line height, justify/left, indent, hyphenation, margins, chapter breaks
- **Smart chaptering** — uses TOC when available; prefers Part / “How to…” structure; avoids exploding into page chunks
- **Cover extraction** — PDF page 1 (or a custom cover image) becomes the EPUB cover
- **E-ink image pass** — greyscale + downscale figures; configurable max image edge
- **OCR for scans** — optional Tesseract OCR with language picker
- **Margin crop** — trim page edges (0–20%) before extract
- **Batch mode** — convert multiple PDFs in one go
- **CLI + local web UI** — `./run.sh` or `python -m app.cli`

---

## Screenshots

### Web UI

![Inkbound homepage with reader profiles and typography controls](docs/screenshots/inkbound-home.jpg)

> Tip: drop your own screenshots into `docs/screenshots/` (device photos, before/after EPUB, Kobo/Kindle sideload) and open a PR or commit them — real device shots help discovery a lot.

---

## Quick start (web UI)

### Requirements

- macOS / Linux / Windows (WSL fine)
- Python 3.11+
- Optional: [Tesseract](https://github.com/tesseract-ocr/tesseract) for OCR (`brew install tesseract`)

### Install & run

```bash
git clone https://github.com/nirmal5307/pdf-to-epub-formater.git
cd pdf-to-epub-formater
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
./run.sh
```

Open **http://127.0.0.1:8765**

1. Drop one or more PDFs  
2. Pick a **reader profile** (Universal, Kobo, Kindle, BOOX, Compact)  
3. Tune typography (font, size, line height, alignment, margins, hyphenation, chapter breaks)  
4. Optionally set metadata, OCR, margin crop, and image max edge  
5. Convert → download the EPUB when ready  

If the port is busy:

```bash
kill $(lsof -tiTCP:8765 -sTCP:LISTEN)
./run.sh
```

---

## CLI — batch PDF to EPUB

```bash
source .venv/bin/activate

# Single file
python -m app.cli book.pdf -o book.epub

# Batch
python -m app.cli a.pdf b.pdf c.pdf

# Scanned PDF → OCR
python -m app.cli scan.pdf --ocr --ocr-lang eng --margin-crop 4

# Metadata + cover
python -m app.cli book.pdf --cover cover.jpg --language en --author "Name"

# Reader presets
python -m app.cli book.pdf --reader-profile kobo --body-size large
python -m app.cli book.pdf --reader-profile kindle --no-hyphenate --text-align left

# Keep original colour images
python -m app.cli book.pdf --no-eink-images
```

### OCR languages

```bash
brew install tesseract
brew install tesseract-lang   # extra languages
tesseract --list-langs
```

---

## Who is this for?

- E-ink owners who **sideload EPUBs** to Kobo, Kindle, BOOX, PocketBook, Xteink, Remarkable-adjacent workflows, etc.
- Readers who want **reflowable text** instead of zooming a fixed PDF page
- Anyone who wants a **private, local PDF → EPUB** pipeline with no SaaS upload

---

## How it works (short)

1. **Extract** text, headings, images, and cover from the PDF (PyMuPDF)  
2. **Split** into chapters using TOC / Part / lesson headings when possible  
3. **Optimize** images for e-ink (optional greyscale + resize)  
4. **Build** an EPUB3 package with NCX + CSS tuned for e-readers  

---

## Tests

```bash
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Covers heading/split heuristics, e-ink CSS options, and the convert API with synthetic PDFs.

---

## Tips for better EPUBs

- Restart `./run.sh` after pulling code so the server loads changes  
- On device, replace/remove the old EPUB if the cover looks cached  
- Text-based PDFs convert best; use OCR for image-only scans  
- Junk PDF metadata (e.g. Word export titles) is ignored in favour of a cleaned filename  
- Books without a TOC no longer explode into hundreds of tiny chapters  
- Self-help / “How to…” books prefer Part + trick TOC over page chunks when possible  

---

## Roadmap ideas

- More reader presets (Remarkable-friendly CSS, Tolino, etc.)
- Optional embedded fonts for stubborn devices
- Better multi-column academic PDF handling

Issues and PRs welcome.

---

## License

[MIT](LICENSE) — free to use, modify, and share.

---

## Repository topics / search terms

`pdf-to-epub` · `epub-converter` · `ebook-converter` · `e-ink` · `kobo` · `kindle` · `boox` · `pocketbook` · `xteink` · `pdf` · `epub` · `epub3` · `ocr` · `tesseract` · `fastapi` · `python` · `offline` · `local-first` · `sideload`
