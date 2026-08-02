"""Inkbound — local PDF → EPUB web app for e-ink readers."""

from __future__ import annotations

import re
import uuid
from dataclasses import replace
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.converter import convert_pdf_to_epub
from app.converter.options import READER_PROFILES, ConvertOptions
from app.converter.pdf_extract import tesseract_available, tesseract_languages

ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = ROOT / "uploads"
OUTPUT_DIR = ROOT / "output"
STATIC_DIR = Path(__file__).resolve().parent / "static"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OCR_LANG_LABELS = {
    "eng": "English",
    "fra": "French",
    "deu": "German",
    "spa": "Spanish",
    "ita": "Italian",
    "por": "Portuguese",
    "nld": "Dutch",
    "pol": "Polish",
    "tur": "Turkish",
    "rus": "Russian",
    "chi_sim": "Chinese (Simplified)",
    "chi_tra": "Chinese (Traditional)",
    "jpn": "Japanese",
    "kor": "Korean",
}

BOOK_LANGS = [
    ("en", "English"),
    ("fr", "French"),
    ("de", "German"),
    ("es", "Spanish"),
    ("it", "Italian"),
    ("pt", "Portuguese"),
    ("nl", "Dutch"),
    ("pl", "Polish"),
    ("tr", "Turkish"),
    ("ru", "Russian"),
    ("zh", "Chinese"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
]

app = FastAPI(title="Inkbound", description="Local PDF → EPUB for e-ink")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

_jobs: dict[str, dict] = {}
_batches: dict[str, dict] = {}


def _truthy(val: str | None) -> bool:
    return str(val or "").lower() in {"1", "true", "yes", "on"}


def _ocr_lang_choices() -> list[dict]:
    installed = set(tesseract_languages())
    # Always show common options; mark which are installed
    codes = list(dict.fromkeys([*OCR_LANG_LABELS.keys(), *sorted(installed)]))
    out = []
    for code in codes:
        out.append(
            {
                "code": code,
                "label": OCR_LANG_LABELS.get(code, code),
                "installed": code in installed,
            }
        )
    return out


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    profiles = [
        {"id": key, "label": val["label"], "hint": val["hint"], "defaults": val["defaults"]}
        for key, val in READER_PROFILES.items()
    ]
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "ocr_available": tesseract_available(),
            "ocr_langs": _ocr_lang_choices(),
            "book_langs": BOOK_LANGS,
            "reader_profiles": profiles,
        },
    )


@app.get("/api/capabilities")
async def capabilities():
    return {
        "ocr": tesseract_available(),
        "ocr_langs": _ocr_lang_choices(),
        "book_langs": [{"code": c, "label": l} for c, l in BOOK_LANGS],
        "reader_profiles": [
            {"id": key, "label": val["label"], "hint": val["hint"], "defaults": val["defaults"]}
            for key, val in READER_PROFILES.items()
        ],
    }


async def _save_upload(upload: UploadFile, dest: Path) -> None:
    with dest.open("wb") as out:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


def _looks_like_pdf(path: Path) -> bool:
    """True if file starts with PDF magic bytes."""
    try:
        with path.open("rb") as fh:
            head = fh.read(5)
        return head.startswith(b"%PDF")
    except OSError:
        return False


def _safe_stem(filename: str | None) -> str:
    stem = Path(filename or "document").stem
    stem = re.sub(r"[^\w\s.\-]+", "", stem, flags=re.UNICODE)
    stem = re.sub(r"\s+", " ", stem).strip(" ._")[:60]
    return stem or "document"


def _parse_options(
    *,
    title: str,
    author: str,
    language: str,
    ocr: str,
    ocr_lang: str,
    margin_crop: str,
    eink_images: str,
    cover_bytes: bytes | None,
    cover_ext: str,
    reader_profile: str = "universal",
    body_size: str = "medium",
    line_height: str = "1.45",
    text_align: str = "justify",
    paragraph_indent: str = "true",
    hyphenate: str = "true",
    page_break_chapters: str = "true",
    font_stack: str = "serif",
    page_margin: str = "normal",
    image_max_edge: str = "1200",
    chapter_break_style: str = "page",
) -> ConvertOptions:
    use_ocr = _truthy(ocr)
    if use_ocr and not tesseract_available():
        raise HTTPException(
            status_code=400,
            detail="OCR requires Tesseract. Install with `brew install tesseract`.",
        )
    try:
        crop = float(margin_crop or "0")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid margin crop") from exc
    try:
        lh = float(line_height or "1.45")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid line height") from exc
    try:
        edge = int(float(image_max_edge or "1200"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid image max edge") from exc

    return ConvertOptions(
        title=title.strip() or None,
        author=author.strip() or None,
        language=(language or "en").strip() or "en",
        ocr=use_ocr,
        ocr_lang=(ocr_lang or "eng").strip() or "eng",
        margin_crop=max(0.0, min(crop, 20.0)),
        eink_images=_truthy(eink_images) if eink_images != "" else True,
        custom_cover=cover_bytes,
        custom_cover_ext=cover_ext,
        reader_profile=reader_profile or "universal",
        body_size=body_size or "medium",
        line_height=lh,
        text_align=text_align or "justify",
        paragraph_indent=_truthy(paragraph_indent) if paragraph_indent != "" else True,
        hyphenate=_truthy(hyphenate) if hyphenate != "" else True,
        page_break_chapters=_truthy(page_break_chapters)
        if page_break_chapters != ""
        else True,
        font_stack=font_stack or "serif",
        page_margin=page_margin or "normal",
        image_max_edge=edge,
        chapter_break_style=chapter_break_style or "page",
    ).normalized()


@app.post("/api/convert")
async def convert(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] | None = File(None),
    file: UploadFile | None = File(None),
    title: str = Form(""),
    author: str = Form(""),
    language: str = Form("en"),
    ocr: str = Form("false"),
    ocr_lang: str = Form("eng"),
    margin_crop: str = Form("0"),
    eink_images: str = Form("true"),
    reader_profile: str = Form("universal"),
    body_size: str = Form("medium"),
    line_height: str = Form("1.45"),
    text_align: str = Form("justify"),
    paragraph_indent: str = Form("true"),
    hyphenate: str = Form("true"),
    page_break_chapters: str = Form("true"),
    font_stack: str = Form("serif"),
    page_margin: str = Form("normal"),
    image_max_edge: str = Form("1200"),
    chapter_break_style: str = Form("page"),
    cover: UploadFile | None = File(None),
):
    uploads: list[UploadFile] = []
    if files:
        uploads.extend([f for f in files if f and f.filename])
    if file and file.filename:
        uploads.append(file)
    if not uploads:
        raise HTTPException(status_code=400, detail="Please upload at least one PDF.")

    for up in uploads:
        if not up.filename or not up.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"Not a PDF: {up.filename}")

    cover_bytes = None
    cover_ext = "jpeg"
    if cover and cover.filename:
        cover_bytes = await cover.read()
        cover_ext = Path(cover.filename).suffix.lstrip(".").lower() or "jpeg"

    opts = _parse_options(
        title=title,
        author=author,
        language=language,
        ocr=ocr,
        ocr_lang=ocr_lang,
        margin_crop=margin_crop,
        eink_images=eink_images,
        cover_bytes=cover_bytes,
        cover_ext=cover_ext,
        reader_profile=reader_profile,
        body_size=body_size,
        line_height=line_height,
        text_align=text_align,
        paragraph_indent=paragraph_indent,
        hyphenate=hyphenate,
        page_break_chapters=page_break_chapters,
        font_stack=font_stack,
        page_margin=page_margin,
        image_max_edge=image_max_edge,
        chapter_break_style=chapter_break_style,
    )

    batch_id = uuid.uuid4().hex[:12]
    job_ids: list[str] = []
    single = len(uploads) == 1
    prepared: list[tuple[str, str, Path, Path, ConvertOptions]] = []

    try:
        for up in uploads:
            job_id = uuid.uuid4().hex[:12]
            safe_stem = _safe_stem(up.filename)
            pdf_path = UPLOAD_DIR / f"{job_id}_{safe_stem}.pdf"
            epub_path = OUTPUT_DIR / f"{job_id}_{safe_stem}.epub"
            await _save_upload(up, pdf_path)

            if not _looks_like_pdf(pdf_path):
                pdf_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=400,
                    detail=f"File is not a valid PDF: {up.filename}",
                )

            job_opts = replace(
                opts,
                title=opts.title if single else None,
                author=opts.author if single else None,
                custom_cover=opts.custom_cover if single else None,
            )
            prepared.append((job_id, up.filename or safe_stem, pdf_path, epub_path, job_opts))
    except Exception:
        for _, _, pdf_path, _, _ in prepared:
            pdf_path.unlink(missing_ok=True)
        raise

    for job_id, filename, pdf_path, epub_path, job_opts in prepared:
        safe_stem = _safe_stem(filename)
        _jobs[job_id] = {
            "id": job_id,
            "batch_id": batch_id,
            "status": "queued",
            "stage": "queued",
            "progress": 0,
            "filename": filename,
            "epub_name": f"{safe_stem}.epub",
            "error": None,
            "pdf_path": str(pdf_path),
            "epub_path": str(epub_path),
        }
        job_ids.append(job_id)
        background_tasks.add_task(_run_convert, job_id, pdf_path, epub_path, job_opts)

    _batches[batch_id] = {"id": batch_id, "job_ids": job_ids}
    return {"batch_id": batch_id, "job_ids": job_ids, "job_id": job_ids[0]}


def _run_convert(
    job_id: str,
    pdf_path: Path,
    epub_path: Path,
    opts: ConvertOptions,
) -> None:
    job = _jobs.get(job_id)
    if not job:
        return
    job["status"] = "running"

    def progress(current: int, total: int, stage: str) -> None:
        job["stage"] = stage
        job["progress"] = int(100 * current / max(total, 1))

    try:
        convert_pdf_to_epub(
            pdf_path,
            output_path=epub_path,
            progress=progress,
            options=opts,
        )
        job["status"] = "done"
        job["progress"] = 100
        job["stage"] = "done"
    except Exception as exc:  # noqa: BLE001
        job["status"] = "error"
        job["error"] = str(exc)
        job["stage"] = "error"
    finally:
        try:
            pdf_path.unlink(missing_ok=True)
        except OSError:
            pass


def _job_payload(job: dict) -> dict:
    return {
        "id": job["id"],
        "batch_id": job.get("batch_id"),
        "status": job["status"],
        "stage": job["stage"],
        "progress": job["progress"],
        "filename": job["filename"],
        "epub_name": job["epub_name"],
        "error": job["error"],
        "download_url": f"/api/download/{job['id']}" if job["status"] == "done" else None,
    }


@app.get("/api/jobs/{job_id}")
async def job_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_payload(job)


@app.get("/api/batches/{batch_id}")
async def batch_status(batch_id: str):
    batch = _batches.get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    jobs = [_job_payload(_jobs[jid]) for jid in batch["job_ids"] if jid in _jobs]
    statuses = {j["status"] for j in jobs}
    if statuses == {"done"}:
        status = "done"
    elif "error" in statuses and statuses <= {"done", "error"}:
        status = "error" if statuses == {"error"} else "partial"
    elif statuses & {"queued", "running"}:
        status = "running"
    else:
        status = "running"
    progress = int(sum(j["progress"] for j in jobs) / max(len(jobs), 1))
    return {"id": batch_id, "status": status, "progress": progress, "jobs": jobs}


@app.get("/api/download/{job_id}")
async def download(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "done":
        raise HTTPException(status_code=409, detail="Conversion not finished")
    path = Path(job["epub_path"])
    if not path.is_file():
        raise HTTPException(status_code=404, detail="EPUB file missing")
    return FileResponse(
        path,
        media_type="application/epub+zip",
        filename=job["epub_name"],
    )


@app.post("/api/cleanup")
async def cleanup():
    active = [
        j
        for j in _jobs.values()
        if j.get("status") in {"queued", "running"}
    ]
    if active:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cleanup while {len(active)} job(s) are still running.",
        )
    for folder in (UPLOAD_DIR, OUTPUT_DIR):
        if folder.exists():
            for p in folder.iterdir():
                if p.is_file() and p.name != ".gitkeep":
                    p.unlink(missing_ok=True)
    _jobs.clear()
    _batches.clear()
    return {"ok": True}


def run() -> None:
    import os

    import uvicorn

    # Local default stays loopback; Codespaces/containers need 0.0.0.0 for port forward.
    if os.environ.get("INKBOUND_HOST"):
        host = os.environ["INKBOUND_HOST"]
    elif os.environ.get("CODESPACES") == "true":
        host = "0.0.0.0"
    else:
        host = "127.0.0.1"
    port = int(os.environ.get("INKBOUND_PORT", "8765"))

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    run()
