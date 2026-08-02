# Codespaces — try Inkbound with no install

**Yes: after the Codespace finishes loading, Inkbound automatically starts and runs.**  
You do **not** need to run `./run.sh` the first time.

## Open a Codespace

**[Create Codespace / Open Inkbound](https://codespaces.new/nirmal5307/pdf-to-epub-formater?quickstart=1)**

This works for **any signed-in GitHub user**, not only the repo owner. Usage counts against *your* free Codespaces minutes.

## First-time flow

1. Sign in to GitHub.  
2. Click the link above.  
3. Keep the default machine size if asked.  
4. Wait while GitHub builds the container (installs Python deps + Tesseract).  
5. When setup finishes:
   - Inkbound **auto-starts in the background**  
   - Your browser should open the UI on port **8765**  
6. Convert a PDF and download the EPUB.

## If the UI doesn’t open

1. Open the **Ports** tab in the Codespace.  
2. Find port **8765** (Inkbound web UI).  
3. Click the globe / preview link.  

Or in the Terminal:

```bash
bash .devcontainer/start-inkbound.sh
```

Then open port **8765** again.

## Privacy

Codespaces is **cloud**. Uploaded PDFs live in that temporary workspace.  
For fully offline conversion, use [[Local-Install]].

## More detail

Also see [docs/CODESPACES.md](https://github.com/nirmal5307/pdf-to-epub-formater/blob/main/docs/CODESPACES.md) in the repo.
