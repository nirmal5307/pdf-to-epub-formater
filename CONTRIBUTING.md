# Contributing to Inkbound

Thanks for helping. Inkbound is **English-first** today; more languages are on the roadmap.

## Highest-impact help

1. **Languages** — UI strings, and chapter heading patterns for your language  
2. **Test data** — freely licensed / public-domain PDFs that stress chaptering, covers, OCR, or columns  
3. **Device proof** — photos of a converted EPUB on a real e-ink reader  
4. **Bugs** — clear steps + what you expected vs what happened  

Do **not** attach copyrighted commercial books to issues or PRs.

## Dev setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
./run.sh
```

Or use [Codespaces](docs/CODESPACES.md) — the app auto-starts after the container loads.

## Pull requests

- Keep changes focused  
- Add or update a test when you change extract/split/API behaviour  
- Synthetic PDFs only under `tests/` (no copyrighted fixtures)

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).
