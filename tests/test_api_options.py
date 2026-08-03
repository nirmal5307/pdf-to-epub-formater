"""Tests for e-ink CSS options and API surface."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.converter.epub_builder import build_eink_css
from app.converter.options import ConvertOptions
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_css_reflects_kindle_profile_defaults():
    css = build_eink_css(
        ConvertOptions(
            reader_profile="kindle",
            text_align="left",
            hyphenate=False,
            body_size="medium",
        )
    )
    assert "text-align: left" in css
    assert "hyphens: manual" in css


def test_css_roomy_margins_and_indent():
    css = build_eink_css(
        ConvertOptions(page_margin="roomy", paragraph_indent=True, font_stack="sans")
    )
    assert "0.9em 1.1em 1.5em" in css
    assert "text-indent: 1.2em" in css
    assert "Helvetica Neue" in css


def test_capabilities_lists_profiles(client):
    res = client.get("/api/capabilities")
    assert res.status_code == 200
    body = res.json()
    ids = {p["id"] for p in body["reader_profiles"]}
    assert {"universal", "kobo", "kindle", "boox", "compact", "tolino", "comfort"} <= ids
    tips = {p["id"]: p.get("tip") for p in body["reader_profiles"]}
    assert tips["tolino"]
    assert tips["comfort"]


def test_home_renders_profiles(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Inkbound" in res.text
    assert "reader_profile" in res.text
    assert "Kobo" in res.text


def test_convert_rejects_non_pdf(client, tmp_path: Path):
    fake = tmp_path / "notes.txt"
    fake.write_text("not a pdf", encoding="utf-8")
    with fake.open("rb") as fh:
        res = client.post(
            "/api/convert",
            files={"files": ("notes.txt", fh, "text/plain")},
            data={"reader_profile": "universal"},
        )
    assert res.status_code == 400


def test_convert_synthetic_pdf(client, tmp_pdf):
    pdf = tmp_pdf(
        [
            [("title", "Sample Book"), ("body", "Hello chapter one content.")],
            [("h1", "Chapter 1"), ("body", "More content for the first chapter here.")],
            [("h1", "Chapter 2"), ("body", "Second chapter body text for the EPUB.")],
        ],
        "api_sample.pdf",
    )
    with pdf.open("rb") as fh:
        res = client.post(
            "/api/convert",
            files={"files": ("api_sample.pdf", fh, "application/pdf")},
            data={
                "title": "API Sample",
                "author": "Tester",
                "reader_profile": "kobo",
                "body_size": "large",
                "eink_images": "true",
            },
        )
    assert res.status_code == 200, res.text
    batch_id = res.json()["batch_id"]

    deadline = time.time() + 30
    final = None
    while time.time() < deadline:
        status = client.get(f"/api/batches/{batch_id}")
        assert status.status_code == 200
        final = status.json()
        if final["status"] in {"done", "error", "partial"}:
            break
        time.sleep(0.2)

    assert final is not None
    assert final["status"] == "done", final
    job = final["jobs"][0]
    assert job["status"] == "done"
    dl = client.get(job["download_url"])
    assert dl.status_code == 200
    assert dl.content[:4] == b"PK\x03\x04"
