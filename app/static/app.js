(() => {
  const form = document.getElementById("convert-form");
  const fileInput = document.getElementById("pdf-file");
  const dropTarget = document.getElementById("drop-target");
  const fileLabel = document.getElementById("file-label");
  const convertBtn = document.getElementById("convert-btn");
  const clearBtn = document.getElementById("clear-btn");
  const statusEl = document.getElementById("status");
  const statusLabel = document.getElementById("status-label");
  const statusPct = document.getElementById("status-pct");
  const statusDetail = document.getElementById("status-detail");
  const bar = document.getElementById("bar");
  const barFill = document.getElementById("bar-fill");
  const downloadBtn = document.getElementById("download-btn");
  const downloadsEl = document.getElementById("downloads");
  const ocrEl = document.getElementById("ocr");
  const ocrLangEl = document.getElementById("ocr_lang");
  const profileInput = document.getElementById("reader_profile");
  const profileHint = document.getElementById("profile-hint");
  const profileTip = document.getElementById("profile-tip");
  const profileGrid = document.getElementById("profile-grid");
  const savedProfilesEl = document.getElementById("saved-profiles");
  const saveProfileBtn = document.getElementById("save-profile-btn");
  const deleteProfileBtn = document.getElementById("delete-profile-btn");
  const SAVED_KEY = "inkbound.savedProfiles.v1";

  let selectedFiles = [];
  let pollTimer = null;

  let profileDefaults = {};
  try {
    const raw = document.getElementById("profile-defaults");
    const list = raw ? JSON.parse(raw.textContent || "[]") : [];
    list.forEach((p) => {
      profileDefaults[p.id] = p;
    });
  } catch (_) {
    profileDefaults = {};
  }

  function setFieldValue(id, value) {
    const el = document.getElementById(id);
    if (!el || value === undefined || value === null) return;
    if (el.type === "checkbox") {
      el.checked = Boolean(value);
    } else {
      el.value = String(value);
    }
  }

  function readSettings() {
    return {
      reader_profile: profileInput.value || "universal",
      body_size: document.getElementById("body_size").value,
      line_height: document.getElementById("line_height").value,
      text_align: document.getElementById("text_align").value,
      page_margin: document.getElementById("page_margin").value,
      hyphenate: document.getElementById("hyphenate").checked,
      paragraph_indent: document.getElementById("paragraph_indent").checked,
      font_stack: document.getElementById("font_stack").value,
      embed_fonts: document.getElementById("embed_fonts").checked,
      page_break_chapters: document.getElementById("page_break_chapters").checked,
      image_max_edge: document.getElementById("image_max_edge").value,
      chapter_break_style: document.getElementById("chapter_break_style").value,
      eink_images: document.getElementById("eink_images").checked,
      margin_crop: document.getElementById("margin_crop").value,
      language: document.getElementById("language").value,
    };
  }

  function applySettings(settings) {
    if (!settings) return;
    if (settings.reader_profile) applyProfile(settings.reader_profile, false);
    Object.entries(settings).forEach(([key, value]) => {
      if (key === "reader_profile") return;
      setFieldValue(key, value);
    });
  }

  function loadSavedMap() {
    try {
      return JSON.parse(localStorage.getItem(SAVED_KEY) || "{}") || {};
    } catch (_) {
      return {};
    }
  }

  function persistSavedMap(map) {
    localStorage.setItem(SAVED_KEY, JSON.stringify(map));
  }

  function refreshSavedSelect() {
    if (!savedProfilesEl) return;
    const map = loadSavedMap();
    const current = savedProfilesEl.value;
    savedProfilesEl.innerHTML = '<option value="">— load a saved preset —</option>';
    Object.keys(map)
      .sort((a, b) => a.localeCompare(b))
      .forEach((name) => {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        savedProfilesEl.appendChild(opt);
      });
    if (current && map[current]) savedProfilesEl.value = current;
  }

  function applyProfile(id, applyDefaults = true) {
    const profile = profileDefaults[id];
    if (!profile) return;
    profileInput.value = id;
    if (profileHint) profileHint.textContent = profile.hint || "";
    if (profileTip) profileTip.textContent = profile.tip || profile.hint || "";
    if (applyDefaults) {
      const d = profile.defaults || {};
      setFieldValue("body_size", d.body_size);
      setFieldValue("line_height", d.line_height);
      setFieldValue("text_align", d.text_align);
      setFieldValue("page_margin", d.page_margin);
      setFieldValue("hyphenate", d.hyphenate);
      setFieldValue("paragraph_indent", d.paragraph_indent);
      setFieldValue("font_stack", d.font_stack);
      setFieldValue("page_break_chapters", d.page_break_chapters);
      setFieldValue("image_max_edge", d.image_max_edge);
    }
    if (profileGrid) {
      profileGrid.querySelectorAll(".profile-card").forEach((btn) => {
        const active = btn.dataset.profile === id;
        btn.classList.toggle("is-active", active);
        btn.setAttribute("aria-pressed", active ? "true" : "false");
      });
    }
  }

  if (profileGrid) {
    profileGrid.addEventListener("click", (e) => {
      const btn = e.target.closest(".profile-card");
      if (!btn) return;
      applyProfile(btn.dataset.profile);
    });
  }

  if (saveProfileBtn) {
    saveProfileBtn.addEventListener("click", () => {
      const name = window.prompt("Name for these settings (saved in this browser):");
      if (!name || !name.trim()) return;
      const map = loadSavedMap();
      map[name.trim()] = readSettings();
      persistSavedMap(map);
      refreshSavedSelect();
      savedProfilesEl.value = name.trim();
    });
  }

  if (deleteProfileBtn) {
    deleteProfileBtn.addEventListener("click", () => {
      const name = savedProfilesEl && savedProfilesEl.value;
      if (!name) {
        alert("Select a saved preset to delete.");
        return;
      }
      const map = loadSavedMap();
      delete map[name];
      persistSavedMap(map);
      refreshSavedSelect();
    });
  }

  if (savedProfilesEl) {
    savedProfilesEl.addEventListener("change", () => {
      const name = savedProfilesEl.value;
      if (!name) return;
      const map = loadSavedMap();
      if (map[name]) applySettings(map[name]);
    });
    refreshSavedSelect();
  }

  function disableDownload() {
    downloadBtn.classList.add("is-disabled");
    downloadBtn.setAttribute("aria-disabled", "true");
    downloadBtn.removeAttribute("href");
    downloadBtn.removeAttribute("download");
    downloadBtn.tabIndex = -1;
    downloadBtn.hidden = false;
  }

  function enableDownload(url, filename) {
    downloadBtn.classList.remove("is-disabled");
    downloadBtn.setAttribute("aria-disabled", "false");
    downloadBtn.href = url;
    downloadBtn.setAttribute("download", filename || "book.epub");
    downloadBtn.tabIndex = 0;
    downloadBtn.hidden = false;
  }

  function setFiles(fileList) {
    const pdfs = Array.from(fileList || []).filter(
      (f) => !f.type || f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")
    );
    if (!pdfs.length) {
      alert("Please choose one or more PDF files.");
      return;
    }
    selectedFiles = pdfs;
    fileLabel.hidden = false;
    fileLabel.textContent =
      pdfs.length === 1 ? pdfs[0].name : `${pdfs.length} PDFs selected`;
    dropTarget.classList.add("has-file");
    convertBtn.disabled = false;
    clearBtn.hidden = false;
  }

  function resetForm() {
    selectedFiles = [];
    fileInput.value = "";
    const cover = document.getElementById("cover");
    if (cover) cover.value = "";
    fileLabel.hidden = true;
    fileLabel.textContent = "";
    dropTarget.classList.remove("has-file");
    convertBtn.disabled = true;
    clearBtn.hidden = true;
    statusEl.hidden = true;
    statusEl.classList.remove("error");
    downloadsEl.innerHTML = "";
    disableDownload();
    downloadBtn.hidden = true;
    applyProfile("universal");
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  dropTarget.addEventListener("click", () => fileInput.click());
  dropTarget.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files && fileInput.files.length) setFiles(fileInput.files);
  });

  ["dragenter", "dragover"].forEach((evt) => {
    dropTarget.addEventListener(evt, (e) => {
      e.preventDefault();
      dropTarget.classList.add("dragover");
    });
  });
  ["dragleave", "drop"].forEach((evt) => {
    dropTarget.addEventListener(evt, (e) => {
      e.preventDefault();
      dropTarget.classList.remove("dragover");
    });
  });
  dropTarget.addEventListener("drop", (e) => {
    if (e.dataTransfer && e.dataTransfer.files) setFiles(e.dataTransfer.files);
  });

  clearBtn.addEventListener("click", resetForm);

  if (ocrEl && ocrLangEl) {
    const syncOcrLang = () => {
      ocrLangEl.disabled = !ocrEl.checked || ocrEl.disabled;
    };
    ocrEl.addEventListener("change", syncOcrLang);
    syncOcrLang();
  }

  downloadBtn.addEventListener("click", (e) => {
    if (downloadBtn.classList.contains("is-disabled") || !downloadBtn.getAttribute("href")) {
      e.preventDefault();
    }
  });

  function stageCopy(stage, progress) {
    if (stage === "ocr") return `OCR scanning pages… ${progress}%`;
    if (stage === "eink") return `Optimizing images for e-ink…`;
    if (stage === "extracting") return `Reading PDF pages… ${progress}%`;
    if (stage === "building") return `Building EPUB chapters… ${progress}%`;
    if (stage === "done") return "Ready to download.";
    if (stage === "error") return "Conversion failed.";
    if (stage === "partial") return "Finished with some errors.";
    if (stage === "queued" || stage === "running") return "Converting…";
    return stage || "";
  }

  function renderDownloads(jobs) {
    downloadsEl.innerHTML = "";
    const done = (jobs || []).filter((j) => j.status === "done" && j.download_url);
    if (done.length <= 1) return;
    done.forEach((j) => {
      const a = document.createElement("a");
      a.className = "btn ghost download-item";
      a.href = j.download_url;
      a.setAttribute("download", j.epub_name || "book.epub");
      a.textContent = j.epub_name || j.filename || "Download";
      downloadsEl.appendChild(a);
    });
  }

  function collectWarnings(jobs) {
    const notes = [];
    (jobs || []).forEach((j) => {
      (j.warnings || []).forEach((w) => {
        if (w) notes.push(jobs.length > 1 ? `${j.filename}: ${w}` : w);
      });
    });
    return notes;
  }

  function renderBatch(batch) {
    statusEl.hidden = false;
    statusEl.classList.toggle("error", batch.status === "error");
    const jobs = batch.jobs || [];
    const warnings = collectWarnings(jobs);
    statusEl.classList.toggle("warn", Boolean(warnings.length) && batch.status !== "error");
    statusLabel.textContent = batch.status === "done" ? "Done" : batch.status;
    statusPct.textContent = `${batch.progress || 0}%`;
    bar.setAttribute("aria-valuenow", String(batch.progress || 0));
    barFill.style.width = `${batch.progress || 0}%`;

    const detailBits = jobs.map((j) => {
      if (j.status === "done") return `${j.filename}: ready`;
      if (j.status === "error") return `${j.filename}: ${j.error || "failed"}`;
      return `${j.filename}: ${stageCopy(j.stage, j.progress)}`;
    });
    let detail =
      jobs.length > 1
        ? detailBits.join(" · ")
        : batch.status === "error"
          ? (jobs[0] && jobs[0].error) || "Something went wrong."
          : stageCopy(
              (jobs[0] && jobs[0].stage) || batch.status,
              (jobs[0] && jobs[0].progress) || batch.progress
            );
    if (warnings.length && batch.status !== "error") {
      detail = detail ? `${detail} ${warnings.join(" ")}` : warnings.join(" ");
    }
    statusDetail.textContent = detail;

    renderDownloads(jobs);

    const finished = batch.status === "done" || batch.status === "partial" || batch.status === "error";
    if (finished) {
      convertBtn.disabled = false;
      convertBtn.textContent = "Convert to EPUB";
    }

    const firstDone = jobs.find((j) => j.status === "done" && j.download_url);
    if ((batch.status === "done" || batch.status === "partial") && firstDone) {
      enableDownload(firstDone.download_url, firstDone.epub_name);
    } else {
      disableDownload();
    }
  }

  async function poll(batchId) {
    try {
      const res = await fetch(`/api/batches/${batchId}`);
      if (!res.ok) throw new Error("Lost batch status");
      const batch = await res.json();
      renderBatch(batch);
      if (batch.status === "done" || batch.status === "error" || batch.status === "partial") {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    } catch (err) {
      clearInterval(pollTimer);
      pollTimer = null;
      disableDownload();
      renderBatch({
        status: "error",
        progress: 0,
        jobs: [{ status: "error", error: err.message || "Polling failed", filename: "" }],
      });
      convertBtn.disabled = false;
      convertBtn.textContent = "Try again";
    }
  }

  function appendBool(data, name, id, defaultTrue) {
    const el = document.getElementById(id);
    if (!el) {
      data.append(name, defaultTrue ? "true" : "false");
      return;
    }
    data.append(name, el.checked ? "true" : "false");
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!selectedFiles.length) return;

    convertBtn.disabled = true;
    convertBtn.textContent = "Working…";
    downloadsEl.innerHTML = "";
    disableDownload();
    statusEl.classList.remove("error");
    renderBatch({ status: "queued", progress: 0, jobs: [] });

    const data = new FormData();
    selectedFiles.forEach((f) => data.append("files", f, f.name));
    data.append("title", document.getElementById("title").value || "");
    data.append("author", document.getElementById("author").value || "");
    data.append("language", document.getElementById("language").value || "en");
    data.append("ocr", ocrEl && ocrEl.checked ? "true" : "false");
    data.append("ocr_lang", (ocrLangEl && ocrLangEl.value) || "eng");
    data.append("margin_crop", document.getElementById("margin_crop").value || "0");
    appendBool(data, "eink_images", "eink_images", true);
    data.append("reader_profile", profileInput.value || "universal");
    data.append("body_size", document.getElementById("body_size").value || "medium");
    data.append("line_height", document.getElementById("line_height").value || "1.45");
    data.append("text_align", document.getElementById("text_align").value || "justify");
    data.append("font_stack", document.getElementById("font_stack").value || "serif");
    data.append("page_margin", document.getElementById("page_margin").value || "normal");
    data.append("image_max_edge", document.getElementById("image_max_edge").value || "1200");
    data.append(
      "chapter_break_style",
      document.getElementById("chapter_break_style").value || "page"
    );
    appendBool(data, "paragraph_indent", "paragraph_indent", true);
    appendBool(data, "hyphenate", "hyphenate", true);
    appendBool(data, "page_break_chapters", "page_break_chapters", true);
    appendBool(data, "embed_fonts", "embed_fonts", false);

    const coverInput = document.getElementById("cover");
    if (coverInput && coverInput.files && coverInput.files[0] && selectedFiles.length === 1) {
      data.append("cover", coverInput.files[0], coverInput.files[0].name);
    }

    try {
      const res = await fetch("/api/convert", { method: "POST", body: data });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(formatErrorDetail(err.detail) || "Upload failed");
      }
      const body = await res.json();
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = setInterval(() => poll(body.batch_id), 700);
      poll(body.batch_id);
    } catch (err) {
      disableDownload();
      renderBatch({
        status: "error",
        progress: 0,
        jobs: [{ status: "error", error: err.message || "Upload failed", filename: "" }],
      });
      convertBtn.disabled = false;
      convertBtn.textContent = "Try again";
    }
  });

  function formatErrorDetail(detail) {
    if (!detail) return "";
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (!item) return "";
          if (typeof item === "string") return item;
          if (item.msg) return item.msg;
          return JSON.stringify(item);
        })
        .filter(Boolean)
        .join("; ");
    }
    if (typeof detail === "object" && detail.msg) return detail.msg;
    try {
      return JSON.stringify(detail);
    } catch (_) {
      return String(detail);
    }
  }
})();
