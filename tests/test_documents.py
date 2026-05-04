"""Tests for the document library domain."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.documents.models import Document, Folder


def test_folder_has_id_and_name():
    f = Folder(id="hr-policies", name="HR Policies")
    assert f.id == "hr-policies"
    assert f.name == "HR Policies"


def test_folder_is_immutable():
    f = Folder(id="hr-policies", name="HR Policies")
    try:
        f.id = "changed"  # type: ignore[misc]
        assert False, "Should have raised"
    except Exception:
        pass


def test_document_has_all_fields():
    now = datetime.now(timezone.utc)
    doc = Document(
        id="leave-policy",
        folder_id="hr-policies",
        name="leave-policy.pdf",
        description="Covers employee leave entitlements.",
        mime_type="application/pdf",
        created_at=now,
    )
    assert doc.id == "leave-policy"
    assert doc.folder_id == "hr-policies"
    assert doc.name == "leave-policy.pdf"
    assert doc.description == "Covers employee leave entitlements."
    assert doc.mime_type == "application/pdf"
    assert doc.created_at == now


def test_document_is_immutable():
    doc = Document(
        id="x", folder_id="f", name="n", description="d",
        mime_type="text/plain", created_at=datetime.now(timezone.utc),
    )
    try:
        doc.id = "changed"  # type: ignore[misc]
        assert False, "Should have raised"
    except Exception:
        pass


# ── Repository imports (added in Task 3) ─────────────────────────────────────

from backend.documents.repository import (  # noqa: E402
    delete_document,
    delete_folder,
    document_id_exists,
    get_document,
    get_folder,
    list_documents,
    list_folders,
    resolve_documents,
    save_document,
    save_folder,
    update_document,
    update_folder,
)


# ── Folder CRUD ───────────────────────────────────────────────────────────────

def test_save_and_get_folder(config_dir):
    f = Folder(id="hr", name="HR")
    save_folder(f)
    assert get_folder("hr") == f


def test_get_folder_missing_raises(config_dir):
    with pytest.raises(KeyError):
        get_folder("does-not-exist")


def test_list_folders_empty(config_dir):
    assert list_folders() == []


def test_list_folders_returns_all_ordered(config_dir):
    save_folder(Folder(id="b", name="Beta"))
    save_folder(Folder(id="a", name="Alpha"))
    names = [f.name for f in list_folders()]
    assert names == ["Alpha", "Beta"]


def test_delete_folder_removes_folder_and_documents(config_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="d1.txt",
                           description="x", mime_type="text/plain", created_at=now))
    save_document(Document(id="d2", folder_id="f1", name="d2.txt",
                           description="y", mime_type="text/plain", created_at=now))
    deleted_ids = delete_folder("f1")
    assert set(deleted_ids) == {"d1", "d2"}
    with pytest.raises(KeyError):
        get_folder("f1")
    assert list_documents("f1") == []


# ── update_folder ─────────────────────────────────────────────────────────────

def test_update_folder_changes_name(config_dir):
    save_folder(Folder(id="hr", name="HR"))
    updated = update_folder("hr", name="Human Resources")
    assert updated.id == "hr"
    assert updated.name == "Human Resources"
    # Persisted
    assert get_folder("hr").name == "Human Resources"


def test_update_folder_not_found_raises(config_dir):
    with pytest.raises(KeyError):
        update_folder("missing", name="Anything")


# ── update_document ───────────────────────────────────────────────────────────

def test_update_document_name(config_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="old.txt",
                           description="x", mime_type="text/plain", created_at=now))
    updated = update_document("d1", name="new.txt")
    assert updated.name == "new.txt"
    assert updated.description == "x"  # unchanged
    assert get_document("d1").name == "new.txt"


def test_update_document_description(config_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="doc.txt",
                           description="old desc", mime_type="text/plain", created_at=now))
    updated = update_document("d1", description="new desc")
    assert updated.description == "new desc"
    assert updated.name == "doc.txt"  # unchanged


def test_update_document_folder_id(config_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_folder(Folder(id="f2", name="F2"))
    save_document(Document(id="d1", folder_id="f1", name="doc.txt",
                           description="", mime_type="text/plain", created_at=now))
    updated = update_document("d1", folder_id="f2")
    assert updated.folder_id == "f2"
    assert list_documents("f2")[0].id == "d1"


def test_update_document_not_found_raises(config_dir):
    with pytest.raises(KeyError):
        update_document("missing", name="anything")


# ── Document CRUD ─────────────────────────────────────────────────────────────

def test_save_and_get_document(config_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    doc = Document(id="doc1", folder_id="f1", name="doc1.pdf",
                   description="A doc", mime_type="application/pdf", created_at=now)
    save_document(doc)
    loaded = get_document("doc1")
    assert loaded.id == "doc1"
    assert loaded.folder_id == "f1"


def test_get_document_missing_raises(config_dir):
    with pytest.raises(KeyError):
        get_document("missing")


def test_list_documents_empty(config_dir):
    save_folder(Folder(id="f1", name="F1"))
    assert list_documents("f1") == []


def test_list_documents_filtered_by_folder(config_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_folder(Folder(id="f2", name="F2"))
    save_document(Document(id="d1", folder_id="f1", name="d1", description="",
                           mime_type="text/plain", created_at=now))
    save_document(Document(id="d2", folder_id="f2", name="d2", description="",
                           mime_type="text/plain", created_at=now))
    assert [d.id for d in list_documents("f1")] == ["d1"]
    assert [d.id for d in list_documents("f2")] == ["d2"]


def test_delete_document_returns_folder_id(config_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="d1", description="",
                           mime_type="text/plain", created_at=now))
    folder_id = delete_document("d1")
    assert folder_id == "f1"
    with pytest.raises(KeyError):
        get_document("d1")


def test_delete_document_missing_returns_none(config_dir):
    assert delete_document("missing") is None


def test_document_id_exists(config_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="d1", description="",
                           mime_type="text/plain", created_at=now))
    assert document_id_exists("d1") is True
    assert document_id_exists("nope") is False


# ── resolve_documents ─────────────────────────────────────────────────────────

def test_resolve_documents_empty_inputs(config_dir):
    assert resolve_documents([], []) == []


def test_resolve_documents_by_folder(config_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="Alpha", description="",
                           mime_type="text/plain", created_at=now))
    save_document(Document(id="d2", folder_id="f1", name="Beta", description="",
                           mime_type="text/plain", created_at=now))
    docs = resolve_documents(["f1"], [])
    assert {d.id for d in docs} == {"d1", "d2"}


def test_resolve_documents_by_id(config_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="d1", description="",
                           mime_type="text/plain", created_at=now))
    save_document(Document(id="d2", folder_id="f1", name="d2", description="",
                           mime_type="text/plain", created_at=now))
    docs = resolve_documents([], ["d1"])
    assert [d.id for d in docs] == ["d1"]


def test_resolve_documents_deduplicates_overlap(config_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="d1", description="",
                           mime_type="text/plain", created_at=now))
    docs = resolve_documents(["f1"], ["d1"])
    assert len(docs) == 1


# ── Service tests (Task 4) ────────────────────────────────────────────────────

from backend.documents.service import (  # noqa: E402
    DocumentTooLongError,
    _unique_id,
    process_document,
    slugify,
)


# ── slugify ───────────────────────────────────────────────────────────────────

def test_slugify_strips_extension():
    assert slugify("leave-policy.pdf") == "leave-policy"


def test_slugify_lowercases_and_hyphenates():
    assert slugify("HR Policy 2024.docx") == "hr-policy-2024"


def test_slugify_removes_special_chars():
    assert slugify("Report (Final)!.txt") == "report-final"


def test_slugify_empty_stem_returns_document():
    # Path(".").stem == "." — all non-alphanumeric → slug is empty → fallback
    assert slugify(".") == "document"


# ── _unique_id ────────────────────────────────────────────────────────────────

def test_unique_id_no_collision(config_dir):
    assert _unique_id("new-doc") == "new-doc"


def test_unique_id_collision_appends_suffix(config_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="my-doc", folder_id="f1", name="my-doc.pdf",
                           description="", mime_type="application/pdf", created_at=now))
    assert _unique_id("my-doc") == "my-doc-2"


def test_unique_id_multiple_collisions(config_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    for suffix in ["my-doc", "my-doc-2"]:
        save_document(Document(id=suffix, folder_id="f1", name=f"{suffix}.pdf",
                               description="", mime_type="application/pdf", created_at=now))
    assert _unique_id("my-doc") == "my-doc-3"


# ── process_document ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_document_short_doc_uses_ai_summary(config_dir):
    from backend.config.service import save_config
    from backend.config.models import TroveConfig
    save_config(TroveConfig(num_ctx=8192))
    save_folder(Folder(id="f1", name="F1"))

    with patch("backend.documents.service._ai_summary", new=AsyncMock(return_value="An AI summary.")):
        doc = await process_document(
            content="Short content with few words.",
            name="test-doc.txt",
            folder_id="f1",
            mime_type="text/plain",
        )

    assert doc.id == "test-doc"
    assert doc.description == "An AI summary."
    md_path = config_dir / "documents" / "f1" / "test-doc.md"
    assert md_path.exists()
    assert md_path.read_text() == "Short content with few words."


@pytest.mark.asyncio
async def test_process_document_supplied_description_skips_ai(config_dir):
    from backend.config.service import save_config
    from backend.config.models import TroveConfig
    save_config(TroveConfig(num_ctx=512))  # minimum valid; 300 words × 2 = 600 > 512
    save_folder(Folder(id="f1", name="F1"))

    long_content = "word " * 300

    with patch("backend.documents.service._ai_summary", new=AsyncMock()) as mock_ai:
        doc = await process_document(
            content=long_content,
            name="big.txt",
            folder_id="f1",
            mime_type="text/plain",
            description="Admin wrote this.",
        )
    mock_ai.assert_not_called()
    assert doc.description == "Admin wrote this."


@pytest.mark.asyncio
async def test_process_document_too_long_raises(config_dir):
    from backend.config.service import save_config
    from backend.config.models import TroveConfig
    save_config(TroveConfig(num_ctx=512))  # 300 words × 2 = 600 > 512
    save_folder(Folder(id="f1", name="F1"))

    long_content = "word " * 300

    with pytest.raises(DocumentTooLongError) as exc_info:
        await process_document(
            content=long_content,
            name="big.txt",
            folder_id="f1",
            mime_type="text/plain",
        )
    assert exc_info.value.word_count == 300
    assert exc_info.value.num_ctx == 512


@pytest.mark.asyncio
async def test_process_document_ai_failure_falls_back_to_name(config_dir):
    from backend.config.service import save_config
    from backend.config.models import TroveConfig
    save_config(TroveConfig(num_ctx=8192))
    save_folder(Folder(id="f1", name="F1"))

    with patch("backend.tasks.runner.run_task", new=AsyncMock(side_effect=RuntimeError("Ollama down"))):
        doc = await process_document(
            content="Some content.",
            name="my-file.pdf",
            folder_id="f1",
            mime_type="application/pdf",
        )
    assert doc.description == "my-file.pdf"


# ── Router tests (Task 5) ─────────────────────────────────────────────────────

import io  # noqa: E402
import zipfile  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def doc_client(config_dir, monkeypatch, session_token, admin_token):
    """App-mode TestClient with admin cookie pre-set."""
    monkeypatch.setenv("TROVE_FAKE_OLLAMA", "1")
    monkeypatch.setenv("TROVE_FAKE_SYSTEM", "1")
    from backend.config.service import save_config
    from backend.config.models import TroveConfig
    from backend.app.auth import hash_password
    save_config(TroveConfig(admin_username="admin", admin_password=hash_password("pass"), num_ctx=8192))
    from backend.main import create_app_app
    client = TestClient(create_app_app(), headers={"X-Trove-Session": session_token})
    client.cookies.set("admin_auth", admin_token)
    return client


def test_list_folders_api_empty(doc_client):
    res = doc_client.get("/api/app/admin/folders")
    assert res.status_code == 200
    assert res.json() == []


def test_create_folder(doc_client):
    res = doc_client.post("/api/app/admin/folders", json={"name": "HR Policies"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "HR Policies"
    assert data["id"] == "hr-policies"


def test_delete_folder_not_found(doc_client):
    res = doc_client.delete("/api/app/admin/folders/missing")
    assert res.status_code == 404


def test_delete_folder_removes_it(doc_client):
    doc_client.post("/api/app/admin/folders", json={"name": "My Folder"})
    res = doc_client.delete("/api/app/admin/folders/my-folder")
    assert res.status_code == 204
    assert doc_client.get("/api/app/admin/folders").json() == []


def test_list_documents_api_empty(doc_client):
    doc_client.post("/api/app/admin/folders", json={"name": "F1"})
    res = doc_client.get("/api/app/admin/documents?folder_id=f1")
    assert res.status_code == 200
    assert res.json() == []


def test_upload_unsupported_extension_returns_422(doc_client):
    doc_client.post("/api/app/admin/folders", json={"name": "F1"})
    res = doc_client.post(
        "/api/app/admin/documents/upload",
        files={"file": ("report.jpg", io.BytesIO(b"some content"), "image/jpeg")},
        data={"folder_id": "f1"},
    )
    assert res.status_code == 422
    assert "not supported" in res.json()["detail"].lower()


def test_upload_txt_file_returns_ok(doc_client, monkeypatch):
    """Upload a .txt file — mock markitdown and process_document."""
    doc_client.post("/api/app/admin/folders", json={"name": "F1"})
    now = datetime.now(timezone.utc)
    fake_doc = Document(id="my-doc", folder_id="f1", name="my-doc.txt",
                        description="A summary.", mime_type="text/plain", created_at=now)

    mock_md = MagicMock()
    mock_md.convert.return_value.text_content = "Plain text content"

    with patch("markitdown.MarkItDown", return_value=mock_md), \
         patch("backend.documents.router.process_document", new=AsyncMock(return_value=fake_doc)):
        res = doc_client.post(
            "/api/app/admin/documents/upload",
            files={"file": ("my-doc.txt", io.BytesIO(b"Plain text content"), "text/plain")},
            data={"folder_id": "f1"},
        )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["document"]["id"] == "my-doc"


def test_upload_too_long_returns_needs_description(doc_client):
    doc_client.post("/api/app/admin/folders", json={"name": "F1"})
    mock_md = MagicMock()
    mock_md.convert.return_value.text_content = "word " * 1000

    with patch("markitdown.MarkItDown", return_value=mock_md), \
         patch("backend.documents.router.process_document",
               new=AsyncMock(side_effect=DocumentTooLongError(1000, 512))):
        res = doc_client.post(
            "/api/app/admin/documents/upload",
            files={"file": ("big.txt", io.BytesIO(b"word " * 1000), "text/plain")},
            data={"folder_id": "f1"},
        )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "needs_description"
    assert data["word_count"] == 1000
    assert data["num_ctx"] == 512


def test_upload_from_url_returns_ok(doc_client):
    doc_client.post("/api/app/admin/folders", json={"name": "F1"})
    now = datetime.now(timezone.utc)
    fake_doc = Document(id="wiki-page", folder_id="f1", name="Wikipedia",
                        description="An encyclopaedia article.", mime_type="text/html", created_at=now)
    mock_md = MagicMock()
    mock_md.convert.return_value.text_content = "Article content"

    with patch("markitdown.MarkItDown", return_value=mock_md), \
         patch("backend.documents.router.process_document", new=AsyncMock(return_value=fake_doc)):
        res = doc_client.post(
            "/api/app/admin/documents/from-url",
            json={"url": "https://en.wikipedia.org/wiki/Python", "folder_id": "f1", "name": "Wikipedia"},
        )
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_delete_document_not_found(doc_client):
    res = doc_client.delete("/api/app/admin/documents/missing")
    assert res.status_code == 404


def test_delete_document_removes_it(doc_client, config_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="d1.txt",
                           description="", mime_type="text/plain", created_at=now))
    # Create the markdown file
    doc_dir = config_dir / "documents" / "f1"
    doc_dir.mkdir(parents=True)
    (doc_dir / "d1.md").write_text("content")

    res = doc_client.delete("/api/app/admin/documents/d1")
    assert res.status_code == 204
    assert not (doc_dir / "d1.md").exists()


# ── PATCH /admin/folders/{folder_id} ─────────────────────────────────────────

def test_rename_folder_returns_updated(doc_client):
    doc_client.post("/api/app/admin/folders", json={"name": "Original"})
    folders = doc_client.get("/api/app/admin/folders").json()
    fid = folders[0]["id"]
    res = doc_client.patch(f"/api/app/admin/folders/{fid}", json={"name": "Renamed"})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == fid
    assert data["name"] == "Renamed"


def test_rename_folder_persisted(doc_client):
    doc_client.post("/api/app/admin/folders", json={"name": "Before"})
    folders = doc_client.get("/api/app/admin/folders").json()
    fid = folders[0]["id"]
    doc_client.patch(f"/api/app/admin/folders/{fid}", json={"name": "After"})
    folders2 = doc_client.get("/api/app/admin/folders").json()
    assert folders2[0]["name"] == "After"


def test_rename_folder_not_found(doc_client):
    res = doc_client.patch("/api/app/admin/folders/missing", json={"name": "X"})
    assert res.status_code == 404


# ── PATCH /admin/documents/{doc_id} ──────────────────────────────────────────

def _upload_fake_doc(doc_client, folder_id: str, doc_id: str, name: str, config_dir):
    """Helper: insert a document record and create its .md file on disk."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    save_folder(Folder(id=folder_id, name=folder_id.upper()))
    save_document(Document(id=doc_id, folder_id=folder_id, name=name,
                           description="desc", mime_type="text/plain", created_at=now))
    md_dir = config_dir / "documents" / folder_id
    md_dir.mkdir(parents=True, exist_ok=True)
    (md_dir / f"{doc_id}.md").write_text("content")


def test_patch_document_name(doc_client, config_dir):
    _upload_fake_doc(doc_client, "f1", "mydoc", "old.txt", config_dir)
    res = doc_client.patch("/api/app/admin/documents/mydoc", json={"name": "new.txt"})
    assert res.status_code == 200
    assert res.json()["name"] == "new.txt"
    assert res.json()["description"] == "desc"


def test_patch_document_description(doc_client, config_dir):
    _upload_fake_doc(doc_client, "f1", "mydoc", "doc.txt", config_dir)
    res = doc_client.patch("/api/app/admin/documents/mydoc", json={"description": "new desc"})
    assert res.status_code == 200
    assert res.json()["description"] == "new desc"


def test_patch_document_move(doc_client, config_dir):
    """Moving a document updates folder_id and moves the .md file on disk."""
    _upload_fake_doc(doc_client, "f1", "mydoc", "doc.txt", config_dir)
    save_folder(Folder(id="f2", name="F2"))
    res = doc_client.patch("/api/app/admin/documents/mydoc", json={"folder_id": "f2"})
    assert res.status_code == 200
    assert res.json()["folder_id"] == "f2"
    assert not (config_dir / "documents" / "f1" / "mydoc.md").exists()
    assert (config_dir / "documents" / "f2" / "mydoc.md").exists()


def test_patch_document_not_found(doc_client):
    res = doc_client.patch("/api/app/admin/documents/missing", json={"name": "x"})
    assert res.status_code == 404


def test_patch_document_bad_folder(doc_client, config_dir):
    _upload_fake_doc(doc_client, "f1", "mydoc", "doc.txt", config_dir)
    res = doc_client.patch("/api/app/admin/documents/mydoc", json={"folder_id": "nonexistent"})
    assert res.status_code == 400


# ── upload name field ─────────────────────────────────────────────────────────

def test_upload_with_explicit_name_uses_it(doc_client):
    doc_client.post("/api/app/admin/folders", json={"name": "F1"})
    now = datetime.now(timezone.utc)
    mock_md = MagicMock()
    mock_md.convert.return_value.text_content = "content"

    async def fake_process(content, name, folder_id, mime_type, description=''):
        return Document(id="doc", folder_id=folder_id, name=name,
                        description="x", mime_type=mime_type, created_at=now)

    with patch("markitdown.MarkItDown", return_value=mock_md), \
         patch("backend.documents.router.process_document", new=fake_process):
        res = doc_client.post(
            "/api/app/admin/documents/upload",
            files={"file": ("file.txt", io.BytesIO(b"content"), "text/plain")},
            data={"folder_id": "f1", "name": "My Custom Name"},
        )
    assert res.status_code == 200
    assert res.json()["document"]["name"] == "My Custom Name"


def test_upload_without_name_falls_back_to_filename(doc_client):
    doc_client.post("/api/app/admin/folders", json={"name": "F1"})
    now = datetime.now(timezone.utc)
    mock_md = MagicMock()
    mock_md.convert.return_value.text_content = "content"

    async def fake_process(content, name, folder_id, mime_type, description=''):
        return Document(id="doc", folder_id=folder_id, name=name,
                        description="x", mime_type=mime_type, created_at=now)

    with patch("markitdown.MarkItDown", return_value=mock_md), \
         patch("backend.documents.router.process_document", new=fake_process):
        res = doc_client.post(
            "/api/app/admin/documents/upload",
            files={"file": ("original-file.txt", io.BytesIO(b"content"), "text/plain")},
            data={"folder_id": "f1"},
        )
    assert res.status_code == 200
    assert res.json()["document"]["name"] == "original-file.txt"


# ── Download endpoints (Task 9) ───────────────────────────────────────────────

def test_download_folder_returns_zip(doc_client, config_dir):
    doc_client.post("/api/app/admin/folders", json={"name": "My Folder"})
    # Insert a document and its .md file
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="my-folder", name="My Folder"))
    save_document(Document(id="d1", folder_id="my-folder", name="d1.txt",
                           description="", mime_type="text/plain", created_at=now))
    md_dir = config_dir / "documents" / "my-folder"
    md_dir.mkdir(parents=True, exist_ok=True)
    (md_dir / "d1.md").write_text("hello")

    res = doc_client.get("/api/app/admin/folders/my-folder/download")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
        assert "d1.md" in zf.namelist()
        assert zf.read("d1.md") == b"hello"


def test_download_folder_not_found(doc_client):
    res = doc_client.get("/api/app/admin/folders/missing/download")
    assert res.status_code == 404


def test_download_document_returns_markdown(doc_client, config_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="d1.txt",
                           description="", mime_type="text/plain", created_at=now))
    md_dir = config_dir / "documents" / "f1"
    md_dir.mkdir(parents=True, exist_ok=True)
    (md_dir / "d1.md").write_text("# Document")

    res = doc_client.get("/api/app/admin/documents/d1/download")
    assert res.status_code == 200
    assert "text/markdown" in res.headers["content-type"]
    assert res.content == b"# Document"


def test_download_document_not_found(doc_client):
    res = doc_client.get("/api/app/admin/documents/missing/download")
    assert res.status_code == 404
