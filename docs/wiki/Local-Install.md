# Local install (fully offline)

Best when you want PDFs to stay on your machine.

## Requirements

- Python 3.11+  
- Optional: [Tesseract](https://github.com/tesseract-ocr/tesseract) for OCR  

## Setup

```bash
git clone https://github.com/nirmal5307/pdf-to-epub-formater.git
cd pdf-to-epub-formater
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
./run.sh
```

Open **http://127.0.0.1:8765**

## CLI

```bash
source .venv/bin/activate
python -m app.cli book.pdf -o book.epub
python -m app.cli book.pdf --reader-profile kobo --body-size large
python -m app.cli scan.pdf --ocr --ocr-lang eng
```

## Prefer no install?

Use [[Codespaces]] instead — the app auto-starts after loading.
