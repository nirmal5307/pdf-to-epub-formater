# Inkbound

Local PDF → EPUB converter for e-ink readers (Xteink, Kobo, Kindle, BOOX, PocketBook, and similar).  
Everything runs on your machine — files are never uploaded to the cloud.

---

## How to run (web UI)

### First time setup

```bash
cd pdf-to-epub-formater
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Start the app

```bash
./run.sh
```

Open **http://127.0.0.1:8765**

1. Drop one or more PDFs  
2. Pick a **reader profile** (Universal, Kobo, Kindle, BOOX, Compact)  
3. Tune typography (font, size, line height, alignment, margins, hyphenation, chapter breaks)  
4. Optionally set metadata, OCR, margin crop, and image edge size  
5. Convert → download when ready

If the port is busy:

```bash
kill $(lsof -tiTCP:8765 -sTCP:LISTEN)
./run.sh
```

---

## Features

| Feature | What it does |
|--------|----------------|
| **Reader profiles** | Presets for Universal / Kobo / Kindle / BOOX / Compact screens |
| **Typography** | Font stack, type size, line height, justify/left, indent, hyphenation, margins |
| **Chapter breaks** | Page break or spacing-only between chapters |
| **Smart chaptering** | Prefers Part / “How to…” structure when present; avoids page-chunk spam |
| **Cover** | PDF page 1 (or your custom image) becomes the EPUB cover |
| **E-ink image pass** | Greyscale + downscale figures; configurable max edge |
| **OCR** | Optional Tesseract OCR for scanned pages, with language picker |
| **Margin crop** | Trim page edges (0–20%) before extract |
| **Batch** | Convert multiple PDFs in one go |
| **EPUB3 + NCX** | Wide sideload support across e-ink devices |

---

## CLI

```bash
source .venv/bin/activate

python -m app.cli book.pdf -o book.epub
python -m app.cli a.pdf b.pdf c.pdf
python -m app.cli scan.pdf --ocr --ocr-lang eng --margin-crop 4
python -m app.cli book.pdf --cover cover.jpg --language en --author "Name"
python -m app.cli book.pdf --reader-profile kobo --body-size large
python -m app.cli book.pdf --reader-profile kindle --no-hyphenate --text-align left
python -m app.cli book.pdf --no-eink-images
```

### OCR languages

```bash
brew install tesseract
brew install tesseract-lang   # extra languages
tesseract --list-langs
```

---

## Tests

```bash
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Covers heading/split heuristics, e-ink CSS options, and the convert API with synthetic PDFs.

---

## Tips

- Restart `./run.sh` after pulling code changes so the server loads them  
- On device, replace/remove the old EPUB if the cover looks cached  
- Text PDFs convert best; use OCR for scans  
- Junk PDF metadata (e.g. Word export titles) is ignored in favour of a cleaned filename  
- Books without a TOC no longer explode into hundreds of tiny chapters  
- Self-help / Lowndes-style books prefer Part + trick TOC over page chunks when possible  
