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


# ── import_bundle — Replace mode ──────────────────────────────────────────────

def test_import_replace_wipes_existing_gems(data_dir):
    from backend.bundle.service import export_bundle, import_bundle
    from backend.bundle.models import ImportMode
    _make_folder()
    _make_gem("old-gem")
    bundle = export_bundle()

    # Add a new gem that is NOT in the bundle
    _make_gem("extra-gem")
    result = import_bundle(bundle, ImportMode.REPLACE)

    from backend.tasks.repository import list_tasks
    ids = {g.id for g in list_tasks()}
    assert "old-gem" in ids
    assert "extra-gem" not in ids
    assert result.gems_imported == 1


def test_import_replace_wipes_existing_documents(data_dir):
    from backend.bundle.service import export_bundle, import_bundle
    from backend.bundle.models import ImportMode
    _make_folder()
    _make_document("doc1", "f1", data_dir)
    bundle = export_bundle()

    # Add a document not in the bundle
    _make_document("extra-doc", "f1", data_dir)
    import_bundle(bundle, ImportMode.REPLACE)

    from backend.documents.repository import list_documents
    ids = {d.id for d in list_documents()}
    assert "doc1" in ids
    assert "extra-doc" not in ids


def test_import_replace_restores_md_files(data_dir):
    from backend.bundle.service import export_bundle, import_bundle
    from backend.bundle.models import ImportMode
    _make_folder()
    _make_document("doc1", "f1", data_dir, content="Original content")
    bundle = export_bundle()

    # Overwrite the md file then replace
    (data_dir / "documents" / "f1" / "doc1.md").write_text("corrupted")
    import_bundle(bundle, ImportMode.REPLACE)

    assert (data_dir / "documents" / "f1" / "doc1.md").read_text() == "Original content"


def test_import_replace_returns_correct_counts(data_dir):
    from backend.bundle.service import export_bundle, import_bundle
    from backend.bundle.models import ImportMode
    _make_folder("f1")
    _make_folder("f2")
    _make_document("d1", "f1", data_dir)
    _make_document("d2", "f2", data_dir)
    _make_gem("gem1")
    _make_gem("gem2")
    bundle = export_bundle()
    result = import_bundle(bundle, ImportMode.REPLACE)

    assert result.folders_created == 2
    assert result.documents_imported == 2
    assert result.gems_imported == 2
    assert result.documents_renamed == {}
    assert result.gems_renamed == {}


# ── import_bundle — Add mode ──────────────────────────────────────────────────

def test_import_add_no_conflicts_imports_all(data_dir):
    from backend.bundle.service import export_bundle, import_bundle
    from backend.bundle.models import ImportMode
    _make_folder()
    _make_document("doc1", "f1", data_dir)
    _make_gem("gem1")
    bundle = export_bundle()

    # Clear everything, then import in Add mode into empty state
    from backend.tasks.repository import delete_task
    from backend.documents.repository import delete_folder as df
    delete_task("gem1")
    df("f1")
    import_bundle(bundle, ImportMode.ADD)

    from backend.tasks.repository import list_tasks
    from backend.documents.repository import list_documents
    assert any(g.id == "gem1" for g in list_tasks())
    assert any(d.id == "doc1" for d in list_documents())


def test_import_add_skips_existing_folder(data_dir):
    """If a folder already exists, keep the existing name (don't overwrite)."""
    from backend.bundle.service import export_bundle, import_bundle
    from backend.bundle.models import ImportMode
    _make_folder("f1", "Original Name")
    bundle = export_bundle()

    # Rename the folder, then import — original name should be preserved
    from backend.documents.repository import update_folder
    update_folder("f1", name="Renamed Locally")
    result = import_bundle(bundle, ImportMode.ADD)

    from backend.documents.repository import get_folder as gf
    assert gf("f1").name == "Renamed Locally"
    assert result.folders_created == 0


def test_import_add_renames_document_on_collision(data_dir):
    from backend.bundle.service import export_bundle, import_bundle
    from backend.bundle.models import ImportMode
    _make_folder()
    _make_document("doc1", "f1", data_dir, content="From bundle")
    bundle = export_bundle()

    # doc1 already exists — Add should rename the incoming one
    result = import_bundle(bundle, ImportMode.ADD)

    assert "doc1" in result.documents_renamed
    new_id = result.documents_renamed["doc1"]
    assert new_id == "doc1-2"
    assert (data_dir / "documents" / "f1" / "doc1-2.md").read_text() == "From bundle"


def test_import_add_renames_gem_on_collision(data_dir):
    from backend.bundle.service import export_bundle, import_bundle
    from backend.bundle.models import ImportMode
    _make_folder()
    _make_gem("gem1")
    bundle = export_bundle()

    # gem1 already exists — Add should rename the incoming one
    result = import_bundle(bundle, ImportMode.ADD)

    assert "gem1" in result.gems_renamed
    assert result.gems_renamed["gem1"] == "gem1-2"


def test_import_add_rewrites_gem_doc_refs_after_rename(data_dir):
    """When a document is renamed, gems that reference it are updated."""
    from backend.bundle.service import export_bundle, import_bundle
    from backend.bundle.models import ImportMode
    from backend.tasks.repository import list_tasks
    _make_folder()
    _make_document("doc1", "f1", data_dir)
    _make_gem("gem1", doc_ids=["doc1"])
    bundle = export_bundle()

    # doc1 now conflicts — it will be renamed to doc1-2
    result = import_bundle(bundle, ImportMode.ADD)

    renamed_gem_id = result.gems_renamed.get("gem1", "gem1")
    tasks = {g.id: g for g in list_tasks()}
    assert renamed_gem_id in tasks
    assert "doc1-2" in tasks[renamed_gem_id].doc_ids


def test_import_add_md_file_content_preserved(data_dir):
    from backend.bundle.service import export_bundle, import_bundle
    from backend.bundle.models import ImportMode
    _make_folder("new-folder", "New Folder")
    _make_document("new-doc", "new-folder", data_dir, content="Preserved text")
    bundle = export_bundle()

    # Import into a state without new-folder or new-doc
    from backend.documents.repository import delete_folder as df
    from backend.tasks.repository import list_tasks
    df("new-folder")
    import_bundle(bundle, ImportMode.ADD)

    assert (data_dir / "documents" / "new-folder" / "new-doc.md").read_text() == "Preserved text"


# ── Router tests ──────────────────────────────────────────────────────────────

import io as _io  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def bundle_client(config_dir, data_dir, monkeypatch, session_token, admin_token):
    """App-mode TestClient with session + admin cookie pre-set."""
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


def test_export_endpoint_returns_zip(bundle_client, data_dir):
    _make_folder()
    res = bundle_client.get("/api/app/admin/bundle/export")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert zipfile.is_zipfile(_io.BytesIO(res.content))


def test_export_endpoint_requires_admin(bundle_client, data_dir, session_token):
    """Without an admin cookie, export returns 401 or 403."""
    from fastapi.testclient import TestClient
    from backend.main import create_app_app
    client = TestClient(create_app_app(), headers={"X-Trove-Session": session_token})
    res = client.get("/api/app/admin/bundle/export")
    assert res.status_code in (401, 403)


def test_import_endpoint_replace_mode(bundle_client, data_dir):
    """POST a bundle ZIP to the import endpoint in replace mode."""
    _make_folder()
    _make_gem("existing-gem")

    # Export, then add another gem, then replace with the original bundle
    bundle_bytes = bundle_client.get("/api/app/admin/bundle/export").content
    _make_gem("extra-gem")

    res = bundle_client.post(
        "/api/app/admin/bundle/import",
        files={"file": ("bundle.zip", _io.BytesIO(bundle_bytes), "application/zip")},
        data={"mode": "replace"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["gems_imported"] == 1
    assert data["gems_renamed"] == {}


def test_import_endpoint_add_mode(bundle_client, data_dir):
    _make_folder()
    _make_gem("gem-a")
    bundle_bytes = bundle_client.get("/api/app/admin/bundle/export").content

    res = bundle_client.post(
        "/api/app/admin/bundle/import",
        files={"file": ("bundle.zip", _io.BytesIO(bundle_bytes), "application/zip")},
        data={"mode": "add"},
    )
    assert res.status_code == 200
    data = res.json()
    # gem-a already exists; import renames it
    assert "gem-a" in data["gems_renamed"]


def test_import_endpoint_bad_zip_returns_422(bundle_client):
    res = bundle_client.post(
        "/api/app/admin/bundle/import",
        files={"file": ("bad.zip", _io.BytesIO(b"not a zip"), "application/zip")},
        data={"mode": "add"},
    )
    assert res.status_code == 422
