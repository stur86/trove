"""Tests for the bundle export/import service."""
import io
import json
import zipfile
from datetime import datetime, timezone

import pytest

from backend.documents.models import Document, Folder
from backend.documents.repository import save_document, save_folder
from backend.tasks.models import GemHue, OutputMode, UserTask
from backend.tasks.repository import save_task


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_folder(folder_id: str = "f1", name: str = "F1") -> Folder:
    f = Folder(id=folder_id, name=name)
    save_folder(f)
    return f


def _make_document(
    doc_id: str,
    folder_id: str,
    data_dir,
    content: str = "Some content.",
) -> Document:
    doc = Document(
        id=doc_id,
        folder_id=folder_id,
        name=f"{doc_id}.pdf",
        description="A description.",
        mime_type="application/pdf",
        created_at=datetime.now(timezone.utc),
    )
    save_document(doc)
    doc_dir = data_dir / "documents" / folder_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / f"{doc_id}.md").write_text(content, encoding="utf-8")
    return doc


def _make_gem(gem_id: str, doc_folder_ids=(), doc_ids=()) -> UserTask:
    gem = UserTask(
        id=gem_id,
        name=gem_id.replace("-", " ").title(),
        template="Hello {{ name }}",
        hue=GemHue.INDIGO,
        output_mode=OutputMode.TEXT,
        doc_folder_ids=tuple(doc_folder_ids),
        doc_ids=tuple(doc_ids),
    )
    save_task(gem)
    return gem


# ── export_bundle ─────────────────────────────────────────────────────────────

def test_export_bundle_is_valid_zip(data_dir):
    from backend.bundle.service import export_bundle
    _make_folder()
    zip_bytes = export_bundle()
    assert zipfile.is_zipfile(io.BytesIO(zip_bytes))


def test_export_bundle_contains_manifest(data_dir):
    from backend.bundle.service import export_bundle
    _make_folder()
    zip_bytes = export_bundle()
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        assert "manifest.json" in zf.namelist()
        manifest = json.loads(zf.read("manifest.json"))
    assert manifest["version"] == 1
    assert "exported_at" in manifest


def test_export_bundle_includes_document_content(data_dir):
    from backend.bundle.service import export_bundle
    _make_folder()
    _make_document("doc1", "f1", data_dir, content="Hello world")
    zip_bytes = export_bundle()
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        assert "documents/f1/doc1.md" in zf.namelist()
        assert zf.read("documents/f1/doc1.md").decode() == "Hello world"


def test_export_bundle_manifest_has_gems_and_folders(data_dir):
    from backend.bundle.service import export_bundle
    _make_folder("hr", "HR")
    _make_document("policy", "hr", data_dir)
    _make_gem("summarise", doc_folder_ids=["hr"])
    zip_bytes = export_bundle()
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        manifest = json.loads(zf.read("manifest.json"))
    assert any(f["id"] == "hr" for f in manifest["folders"])
    assert any(d["id"] == "policy" for d in manifest["documents"])
    assert any(g["id"] == "summarise" for g in manifest["gems"])
    assert manifest["gems"][0]["doc_folder_ids"] == ["hr"]
