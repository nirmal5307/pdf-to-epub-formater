# Inkbound v1.0.0

First public release of **Inkbound** — a local PDF → EPUB converter for e-ink readers.

## Highlights

- Local web UI + CLI (no cloud upload)
- Reader profiles: Universal, Kobo, Kindle, BOOX, Compact
- Typography controls, e-ink image pass, optional OCR
- Smart chaptering (TOC / Part / “How to…” aware)
- EPUB3 + NCX for wide sideload support
- **GitHub Codespaces** — one-click try (auto-starts the web UI)

## Quick start (local)

```bash
git clone https://github.com/nirmal5307/pdf-to-epub-formater.git
cd pdf-to-epub-formater
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

Open http://127.0.0.1:8765

## Try in Codespaces

[Open in GitHub Codespaces](https://codespaces.new/nirmal5307/pdf-to-epub-formater?quickstart=1) — setup installs dependencies and Tesseract, then starts Inkbound on port 8765 automatically.

See [docs/CODESPACES.md](https://github.com/nirmal5307/pdf-to-epub-formater/blob/main/docs/CODESPACES.md).

## License

MIT
