"""FastAPI router for the document library admin API.

All endpoints require admin cookie authentication. Markitdown is imported
inside the upload handlers to keep it out of the module-level import chain
(avoiding slow startup if markitdown has heavy dependencies).
"""
import io
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from backend.app.auth import require_admin_cookie
from backend.db import get_data_dir
from backend.documents.models import Document, Folder
from backend.documents.repository import (
    delete_document,
    delete_folder,
    get_document,
    get_folder,
    list_documents,
    list_folders,
    save_folder,
    update_document,
    update_folder,
)
from backend.documents.service import DocumentTooLongError, slugify, process_document

router = APIRouter(tags=["documents"])

# Extensions accepted for file upload. URL uploads are not extension-checked.
ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {".pdf", ".docx", ".pptx", ".xlsx", ".txt", ".md", ".html", ".htm"}
)

# User-agent sent with URL fetch requests. Many sites (including Wikipedia)
# block the default Python requests user-agent, so we identify as a browser.
_FETCH_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def _make_markitdown():
    """Return a MarkItDown instance with a browser-like requests session."""
    import requests
    from markitdown import MarkItDown
    md = MarkItDown()
    session = requests.Session()
    session.headers["User-Agent"] = _FETCH_USER_AGENT
    md._requests_session = session
    return md


class CreateFolderRequest(BaseModel):
    """Request body for creating a new folder."""

    name: str
    """Human-readable folder name. The id is derived from this via slugification."""


class UrlUploadRequest(BaseModel):
    """Request body for uploading a document from a URL."""

    url: str
    """The URL to fetch and convert."""
    folder_id: str
    """Destination folder id."""
    name: str
    """Display name for the document (used as slug base and description fallback)."""
    description: str = ""
    """Optional admin-supplied description. Non-empty bypasses AI summary."""


# ── Folders ────────────────────────────────────────────────────────────────────

@router.get("/admin/folders", dependencies=[Depends(require_admin_cookie)])
def get_folders() -> list[Folder]:
    """List all document library folders."""
    return list_folders()


@router.post(
    "/admin/folders",
    dependencies=[Depends(require_admin_cookie)],
    status_code=201,
)
def create_folder(req: CreateFolderRequest) -> Folder:
    """Create a new folder. The id is derived from the name via slugification."""
    folder = Folder(id=slugify(req.name) or "folder", name=req.name)
    save_folder(folder)
    return folder


@router.delete(
    "/admin/folders/{folder_id}",
    dependencies=[Depends(require_admin_cookie)],
    status_code=204,
)
def remove_folder(folder_id: str) -> None:
    """Delete a folder and all its documents, including markdown files on disk."""
    try:
        get_folder(folder_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Folder '{folder_id}' not found")
    deleted_doc_ids = delete_folder(folder_id)
    data_dir = get_data_dir()
    for doc_id in deleted_doc_ids:
        (data_dir / "documents" / folder_id / f"{doc_id}.md").unlink(missing_ok=True)
    try:
        (data_dir / "documents" / folder_id).rmdir()
    except OSError:
        pass  # Not empty or doesn't exist — ignore


@router.get("/admin/folders/{folder_id}/download", dependencies=[Depends(require_admin_cookie)])
def download_folder(folder_id: str) -> Response:
    """Download all documents in a folder as a ZIP of .md files.

    Each .md file in the archive is named <doc_id>.md (flat structure).
    Requires admin cookie.
    """
    try:
        get_folder(folder_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Folder '{folder_id}' not found")

    docs = list_documents(folder_id)
    data_dir = get_data_dir()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for doc in docs:
            md_path = data_dir / "documents" / folder_id / f"{doc.id}.md"
            if md_path.exists():
                zf.writestr(f"{doc.id}.md", md_path.read_bytes())

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{folder_id}.zip"'},
    )


class RenameFolderRequest(BaseModel):
    """Request body for renaming a folder."""

    name: str
    """New human-readable folder name."""


@router.patch("/admin/folders/{folder_id}", dependencies=[Depends(require_admin_cookie)])
def rename_folder(folder_id: str, req: RenameFolderRequest) -> Folder:
    """Rename an existing folder. Returns the updated Folder or 404."""
    try:
        return update_folder(folder_id, name=req.name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Folder '{folder_id}' not found")


# ── Documents ──────────────────────────────────────────────────────────────────

@router.get("/admin/documents", dependencies=[Depends(require_admin_cookie)])
def get_documents(folder_id: str | None = None) -> list[Document]:
    """List all documents, optionally filtered by folder_id."""
    return list_documents(folder_id)


@router.post("/admin/documents/upload", dependencies=[Depends(require_admin_cookie)])
async def upload_document(
    file: UploadFile = File(...),
    folder_id: str = Form(...),
    name: str = Form(""),
    description: str = Form(""),
) -> dict:
    """Upload a file and process it into the document library.

    The file extension is checked against the supported whitelist.
    Markitdown converts the file to markdown. An AI summary is generated
    unless the document is too long or a description was supplied.

    Args:
        name: Optional display name. Defaults to the uploaded filename if blank.

    Returns:
        {"status": "ok", "document": {...}} on success.
        {"status": "needs_description", "word_count": N, "num_ctx": N} when
        the document exceeds the context window and no description was given.
    """
    filename = file.filename or "document"
    display_name = name.strip() or filename
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"File type '{ext}' is not supported. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        result = _make_markitdown().convert(str(tmp_path))
        content = result.text_content
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not process file: {exc}")
    finally:
        tmp_path.unlink(missing_ok=True)

    try:
        doc = await process_document(
            content=content,
            name=display_name,
            folder_id=folder_id,
            mime_type=file.content_type or "application/octet-stream",
            description=description,
        )
        return {"status": "ok", "document": doc.model_dump(mode="json")}
    except DocumentTooLongError as e:
        return {"status": "needs_description", "word_count": e.word_count, "num_ctx": e.num_ctx}


@router.post("/admin/documents/from-url", dependencies=[Depends(require_admin_cookie)])
async def upload_from_url(req: UrlUploadRequest) -> dict:
    """Fetch a URL and process it into the document library.

    Markitdown handles fetching and conversion. No extension whitelist applies
    to URLs — if Markitdown cannot process the URL, a 422 is returned.

    Returns:
        {"status": "ok", "document": {...}} on success.
        {"status": "needs_description", "word_count": N, "num_ctx": N} when too long.
    """
    try:
        result = _make_markitdown().convert(req.url)
        content = result.text_content
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not fetch or process URL: {exc}")

    try:
        doc = await process_document(
            content=content,
            name=req.name,
            folder_id=req.folder_id,
            mime_type="text/html",
            description=req.description,
        )
        return {"status": "ok", "document": doc.model_dump(mode="json")}
    except DocumentTooLongError as e:
        return {"status": "needs_description", "word_count": e.word_count, "num_ctx": e.num_ctx}


@router.delete(
    "/admin/documents/{doc_id}",
    dependencies=[Depends(require_admin_cookie)],
    status_code=204,
)
def remove_document(doc_id: str) -> None:
    """Delete a document and its markdown file from disk."""
    folder_id = delete_document(doc_id)
    if folder_id is None:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")
    (get_data_dir() / "documents" / folder_id / f"{doc_id}.md").unlink(missing_ok=True)


@router.get("/admin/documents/{doc_id}/download", dependencies=[Depends(require_admin_cookie)])
def download_document(doc_id: str) -> Response:
    """Download a single document as its converted markdown file.

    Requires admin cookie.
    """
    try:
        doc = get_document(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")

    md_path = get_data_dir() / "documents" / doc.folder_id / f"{doc_id}.md"
    if not md_path.exists():
        raise HTTPException(status_code=404, detail=f"Markdown file for '{doc_id}' not found on disk")

    return Response(
        content=md_path.read_bytes(),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{doc_id}.md"'},
    )


class UpdateDocumentRequest(BaseModel):
    """Request body for updating a document's metadata or moving it to another folder."""

    name: str | None = None
    """New display name, or None to leave unchanged."""
    description: str | None = None
    """New description, or None to leave unchanged."""
    folder_id: str | None = None
    """Destination folder id for a move, or None to leave unchanged."""


@router.patch("/admin/documents/{doc_id}", dependencies=[Depends(require_admin_cookie)])
def update_doc(doc_id: str, req: UpdateDocumentRequest) -> Document:
    """Update a document's name, description, or folder.

    If folder_id changes, the markdown file is moved on disk.
    Returns 404 if the document is not found, 400 if the target folder does not exist.
    """
    if req.folder_id is not None:
        try:
            get_folder(req.folder_id)
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Target folder '{req.folder_id}' not found",
            )
    try:
        old_doc = get_document(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")

    updated = update_document(
        doc_id,
        name=req.name,
        description=req.description,
        folder_id=req.folder_id,
    )

    if req.folder_id is not None and req.folder_id != old_doc.folder_id:
        data_dir = get_data_dir()
        old_path = data_dir / "documents" / old_doc.folder_id / f"{doc_id}.md"
        new_dir = data_dir / "documents" / req.folder_id
        new_dir.mkdir(parents=True, exist_ok=True)
        old_path.rename(new_dir / f"{doc_id}.md")

    return updated
