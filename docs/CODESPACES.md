# Try Inkbound in GitHub Codespaces (easiest path)

**No install. No Python setup. Click one button and wait.**

After the Codespace finishes loading, Inkbound **starts by itself** and the web UI should open in your browser on port **8765**. You do **not** need to run `./run.sh` the first time.

---

## What is Codespaces?

GitHub Codespaces is a ready-made cloud computer in your browser.  
Inkbound’s Codespace is preconfigured to:

1. Install Python dependencies  
2. Install Tesseract (for optional OCR)  
3. **Automatically start** the Inkbound web app  
4. Forward port **8765** and open the UI  

---

## First-time steps (about 2–5 minutes)

1. Sign in to [GitHub](https://github.com/login) (free account is fine).  
2. Open this link:  
   **[Open Inkbound in Codespaces](https://codespaces.new/nirmal5307/pdf-to-epub-formater?quickstart=1)**  
3. If GitHub asks which machine size / region, keep the defaults and continue.  
4. Wait while the page says it’s **Setting up** / building the container.  
   - First launch is slower (downloads packages).  
   - Later launches reuse the machine and are faster.  
5. When setup finishes:
   - Inkbound **auto-starts in the background**  
   - Your browser should open (or offer) the forwarded **8765** page  
6. You should see the Inkbound UI — drop a PDF and convert.

**Yes: after loading completes, it will automatically load and run.** You should land on the converter UI without typing any commands.

---

## If the UI doesn’t open by itself

That’s normal sometimes. Do this:

1. In the Codespace, open the **Ports** tab (usually near Terminal).  
2. Find port **8765** — label looks like **Inkbound web UI**.  
3. Click the globe / preview / forwarded address to open it.  

Still blank? In the Terminal panel run:

```bash
bash .devcontainer/start-inkbound.sh
```

Then open port **8765** again from **Ports**.

---

## Using Inkbound once it’s open

Same as the local app:

1. Drop one or more PDFs  
2. Pick a reader profile (Universal, Kobo, Kindle, BOOX, Compact)  
3. Adjust typography if you want  
4. Convert → download the EPUB  

---

## Privacy note (important)

Codespaces runs **in the cloud**, so files you upload there live in that temporary workspace — not on your laptop.  

For fully offline / private conversion, run locally instead:

```bash
./run.sh
```

---

## Optional: restart / logs (only if something stuck)

```bash
# Start or restart Inkbound
bash .devcontainer/start-inkbound.sh

# Watch the log
tail -f "${TMPDIR:-/tmp}/inkbound.log"

# Stop the server
kill "$(cat "${TMPDIR:-/tmp}/inkbound.pid")" 2>/dev/null || true
```

---

## Free-tier tip

GitHub gives a monthly Codespaces allowance on free accounts. Stop or delete the Codespace when you’re done (Codespaces menu → Stop / Delete) so you don’t use hours while idle.
