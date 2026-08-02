# Try Inkbound in GitHub Codespaces

1. Open **[Codespaces → New](https://codespaces.new/nirmal5307/pdf-to-epub-formater?quickstart=1)**  
2. Wait for the container to finish setup (Python deps + Tesseract)  
3. Inkbound **starts automatically** and the browser opens on port **8765**

If the tab doesn’t open: open the **Ports** panel → click the forwarded link for `8765`.

## Useful commands

```bash
# Restart the app
bash .devcontainer/start-inkbound.sh

# Follow logs
tail -f "${TMPDIR:-/tmp}/inkbound.log"

# Stop
kill "$(cat "${TMPDIR:-/tmp}/inkbound.pid")" 2>/dev/null || true
```

Files you upload in Codespaces live in that cloud workspace — use local `./run.sh` when you want everything to stay on your machine.
