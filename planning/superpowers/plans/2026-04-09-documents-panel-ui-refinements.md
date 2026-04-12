# DocumentsPanel UI Refinements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refine the admin DocumentsPanel with a three-column layout, inline folder rename, a document properties card with auto-save, move-to-folder support, and modal-based upload flows, backed by two new PATCH endpoints.

**Architecture:** Backend gains `update_folder` / `update_document` in the repository and two PATCH router endpoints; the document move handler also moves the markdown file on disk. Frontend adds a `patch` HTTP helper, new API methods, new locale keys, and a full rewrite of `DocumentsPanel.tsx` into a three-column layout with modals for uploading.

**Tech Stack:** Python/FastAPI (backend), React/TypeScript/Flowbite React (frontend), SQLite via `backend.db.get_db()`, pytest with `data_dir` / `config_dir` fixtures.

---

## File Map

| File | Change |
|---|---|
| `backend/documents/repository.py` | Add `update_folder`, `update_document` |
| `backend/documents/router.py` | Add PATCH /admin/folders/{id}, PATCH /admin/documents/{id}; add `name` Form field to upload |
| `tests/test_documents.py` | Add tests for new repo functions and router endpoints |
| `frontend/src/api/client.ts` | Add `patch<T>` helper |
| `frontend/src/api/documents.ts` | Add `renameFolder`, `updateDocument`; update `uploadFile` to accept `name` |
| `frontend/src/api/mock/documents.ts` | Mirror API additions in mock |
| `locales/en.json` | Add 15 new keys |
| `locales/it.json` | Add same 15 keys in Italian |
| `frontend/src/pages/DocumentsPanel.tsx` | Full rewrite — three-column layout |

---

### Task 1: Repository — update_folder

**Files:**
- Modify: `backend/documents/repository.py`
- Test: `tests/test_documents.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_documents.py` after the existing `delete_folder` tests, updating the import block at the top to also import `update_folder`:

```python
# In the existing repository imports block, add update_folder:
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
    update_folder,
)
```

Then add the tests:

```python
# ── update_folder ─────────────────────────────────────────────────────────────

def test_update_folder_changes_name(data_dir):
    save_folder(Folder(id="hr", name="HR"))
    updated = update_folder("hr", name="Human Resources")
    assert updated.id == "hr"
    assert updated.name == "Human Resources"
    # Persisted
    assert get_folder("hr").name == "Human Resources"


def test_update_folder_not_found_raises(data_dir):
    with pytest.raises(KeyError):
        update_folder("missing", name="Anything")
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /home/gan_hope326/Projects/trove
uv run pytest tests/test_documents.py::test_update_folder_changes_name tests/test_documents.py::test_update_folder_not_found_raises -v
```

Expected: ImportError or FAILED (update_folder does not exist yet).

- [ ] **Step 3: Implement update_folder in repository.py**

Add after `delete_folder`:

```python
def update_folder(folder_id: str, *, name: str) -> Folder:
    """Update a folder's name. Returns the updated Folder. Raises KeyError if not found."""
    with get_db() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT * FROM folders WHERE id = ?", (folder_id,)
        ).fetchone()
        if row is None:
            raise KeyError(folder_id)
        conn.execute(
            "UPDATE folders SET name = ? WHERE id = ?", (name, folder_id)
        )
        row = conn.execute(
            "SELECT * FROM folders WHERE id = ?", (folder_id,)
        ).fetchone()
    return _row_to_folder(row)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_documents.py::test_update_folder_changes_name tests/test_documents.py::test_update_folder_not_found_raises -v
```

Expected: PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/documents/repository.py tests/test_documents.py
git commit -m "feat: add update_folder to document repository"
```

---

### Task 2: Repository — update_document

**Files:**
- Modify: `backend/documents/repository.py`
- Test: `tests/test_documents.py`

- [ ] **Step 1: Write the failing tests**

Add `update_document` to the repository import block (same block as Task 1), then add:

```python
# ── update_document ───────────────────────────────────────────────────────────

def test_update_document_name(data_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="old.txt",
                           description="x", mime_type="text/plain", created_at=now))
    updated = update_document("d1", name="new.txt")
    assert updated.name == "new.txt"
    assert updated.description == "x"  # unchanged
    assert get_document("d1").name == "new.txt"


def test_update_document_description(data_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="doc.txt",
                           description="old desc", mime_type="text/plain", created_at=now))
    updated = update_document("d1", description="new desc")
    assert updated.description == "new desc"
    assert updated.name == "doc.txt"  # unchanged


def test_update_document_folder_id(data_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_folder(Folder(id="f2", name="F2"))
    save_document(Document(id="d1", folder_id="f1", name="doc.txt",
                           description="", mime_type="text/plain", created_at=now))
    updated = update_document("d1", folder_id="f2")
    assert updated.folder_id == "f2"
    assert list_documents("f2")[0].id == "d1"


def test_update_document_not_found_raises(data_dir):
    with pytest.raises(KeyError):
        update_document("missing", name="anything")
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_documents.py::test_update_document_name tests/test_documents.py::test_update_document_description tests/test_documents.py::test_update_document_folder_id tests/test_documents.py::test_update_document_not_found_raises -v
```

Expected: ImportError or FAILED.

- [ ] **Step 3: Implement update_document in repository.py**

Add after `update_folder`:

```python
def update_document(
    doc_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    folder_id: str | None = None,
) -> Document:
    """Update document fields. Returns updated Document. Raises KeyError if not found.

    Only the keyword arguments that are not None are written to the database.
    """
    with get_db() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        if row is None:
            raise KeyError(doc_id)
        updates: dict[str, object] = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if folder_id is not None:
            updates["folder_id"] = folder_id
        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [doc_id]
            conn.execute(
                f"UPDATE documents SET {set_clause} WHERE id = ?", values
            )
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    return _row_to_document(row)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_documents.py::test_update_document_name tests/test_documents.py::test_update_document_description tests/test_documents.py::test_update_document_folder_id tests/test_documents.py::test_update_document_not_found_raises -v
```

Expected: PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/documents/repository.py tests/test_documents.py
git commit -m "feat: add update_document to document repository"
```

---

### Task 3: Router — PATCH /admin/folders/{folder_id}

**Files:**
- Modify: `backend/documents/router.py`
- Test: `tests/test_documents.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_documents.py` after the existing router tests:

```python
def test_rename_folder_returns_updated(doc_client):
    doc_client.post("/api/app/admin/folders", json={"name": "Original"})
    # get the id
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_documents.py::test_rename_folder_returns_updated tests/test_documents.py::test_rename_folder_persisted tests/test_documents.py::test_rename_folder_not_found -v
```

Expected: FAILED (404 — endpoint does not exist).

- [ ] **Step 3: Implement the PATCH endpoint in router.py**

Add `update_folder` to the repository import in `router.py`:

```python
from backend.documents.repository import (
    delete_document,
    delete_folder,
    get_folder,
    list_documents,
    list_folders,
    save_folder,
    update_folder,
)
```

Add a request model and endpoint after `remove_folder`:

```python
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
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_documents.py::test_rename_folder_returns_updated tests/test_documents.py::test_rename_folder_persisted tests/test_documents.py::test_rename_folder_not_found -v
```

Expected: PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/documents/router.py tests/test_documents.py
git commit -m "feat: add PATCH /admin/folders/{id} endpoint for folder rename"
```

---

### Task 4: Router — PATCH /admin/documents/{doc_id}

**Files:**
- Modify: `backend/documents/router.py`
- Test: `tests/test_documents.py`

- [ ] **Step 1: Write the failing tests**

Add after the rename folder tests:

```python
def test_patch_document_name(doc_client, data_dir):
    doc_client.post("/api/app/admin/folders", json={"name": "F1"})
    now = datetime.now(timezone.utc)
    mock_md = MagicMock()
    mock_md.convert.return_value.text_content = "content"
    fake_doc = Document(id="mydoc", folder_id="f1", name="old.txt",
                        description="desc", mime_type="text/plain", created_at=now)
    with patch("markitdown.MarkItDown", return_value=mock_md), \
         patch("backend.documents.router.process_document", new=AsyncMock(return_value=fake_doc)):
        doc_client.post(
            "/api/app/admin/documents/upload",
            files={"file": ("old.txt", io.BytesIO(b"content"), "text/plain")},
            data={"folder_id": "f1"},
        )
    res = doc_client.patch("/api/app/admin/documents/mydoc", json={"name": "new.txt"})
    assert res.status_code == 200
    assert res.json()["name"] == "new.txt"
    assert res.json()["description"] == "desc"


def test_patch_document_description(doc_client, data_dir):
    doc_client.post("/api/app/admin/folders", json={"name": "F1"})
    now = datetime.now(timezone.utc)
    mock_md = MagicMock()
    mock_md.convert.return_value.text_content = "content"
    fake_doc = Document(id="mydoc", folder_id="f1", name="doc.txt",
                        description="old", mime_type="text/plain", created_at=now)
    with patch("markitdown.MarkItDown", return_value=mock_md), \
         patch("backend.documents.router.process_document", new=AsyncMock(return_value=fake_doc)):
        doc_client.post(
            "/api/app/admin/documents/upload",
            files={"file": ("doc.txt", io.BytesIO(b"content"), "text/plain")},
            data={"folder_id": "f1"},
        )
    res = doc_client.patch("/api/app/admin/documents/mydoc", json={"description": "new desc"})
    assert res.status_code == 200
    assert res.json()["description"] == "new desc"


def test_patch_document_move(doc_client, data_dir):
    """Moving a document updates folder_id and moves the .md file on disk."""
    doc_client.post("/api/app/admin/folders", json={"name": "F1"})
    doc_client.post("/api/app/admin/folders", json={"name": "F2"})
    now = datetime.now(timezone.utc)
    mock_md = MagicMock()
    mock_md.convert.return_value.text_content = "content"
    fake_doc = Document(id="mydoc", folder_id="f1", name="doc.txt",
                        description="", mime_type="text/plain", created_at=now)
    # Create a real .md file to simulate what process_document would write
    md_dir = data_dir / "documents" / "f1"
    md_dir.mkdir(parents=True, exist_ok=True)
    (md_dir / "mydoc.md").write_text("content")
    with patch("markitdown.MarkItDown", return_value=mock_md), \
         patch("backend.documents.router.process_document", new=AsyncMock(return_value=fake_doc)):
        doc_client.post(
            "/api/app/admin/documents/upload",
            files={"file": ("doc.txt", io.BytesIO(b"content"), "text/plain")},
            data={"folder_id": "f1"},
        )
    res = doc_client.patch("/api/app/admin/documents/mydoc", json={"folder_id": "f2"})
    assert res.status_code == 200
    assert res.json()["folder_id"] == "f2"
    assert not (data_dir / "documents" / "f1" / "mydoc.md").exists()
    assert (data_dir / "documents" / "f2" / "mydoc.md").exists()


def test_patch_document_not_found(doc_client):
    res = doc_client.patch("/api/app/admin/documents/missing", json={"name": "x"})
    assert res.status_code == 404


def test_patch_document_bad_folder(doc_client, data_dir):
    doc_client.post("/api/app/admin/folders", json={"name": "F1"})
    now = datetime.now(timezone.utc)
    mock_md = MagicMock()
    mock_md.convert.return_value.text_content = "content"
    fake_doc = Document(id="mydoc", folder_id="f1", name="doc.txt",
                        description="", mime_type="text/plain", created_at=now)
    with patch("markitdown.MarkItDown", return_value=mock_md), \
         patch("backend.documents.router.process_document", new=AsyncMock(return_value=fake_doc)):
        doc_client.post(
            "/api/app/admin/documents/upload",
            files={"file": ("doc.txt", io.BytesIO(b"content"), "text/plain")},
            data={"folder_id": "f1"},
        )
    res = doc_client.patch("/api/app/admin/documents/mydoc", json={"folder_id": "nonexistent"})
    assert res.status_code == 400
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_documents.py::test_patch_document_name tests/test_documents.py::test_patch_document_description tests/test_documents.py::test_patch_document_move tests/test_documents.py::test_patch_document_not_found tests/test_documents.py::test_patch_document_bad_folder -v
```

Expected: FAILED (404 — endpoint does not exist).

- [ ] **Step 3: Add imports and endpoint to router.py**

Add `update_document` and `get_document` to the repository import:

```python
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
```

Add request model and endpoint after `remove_document`:

```python
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
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_documents.py::test_patch_document_name tests/test_documents.py::test_patch_document_description tests/test_documents.py::test_patch_document_move tests/test_documents.py::test_patch_document_not_found tests/test_documents.py::test_patch_document_bad_folder -v
```

Expected: PASSED.

- [ ] **Step 5: Run the full test suite to catch regressions**

```bash
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/documents/router.py tests/test_documents.py
git commit -m "feat: add PATCH /admin/documents/{id} endpoint for rename/move"
```

---

### Task 5: Router — add name field to upload_document

**Files:**
- Modify: `backend/documents/router.py`
- Test: `tests/test_documents.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_documents.py::test_upload_with_explicit_name_uses_it tests/test_documents.py::test_upload_without_name_falls_back_to_filename -v
```

Expected: `test_upload_with_explicit_name_uses_it` fails (name not used), `test_upload_without_name_falls_back_to_filename` passes (current behaviour).

- [ ] **Step 3: Add name form field to upload_document in router.py**

Find the `upload_document` function signature and add `name: str = Form("")`:

```python
@router.post("/admin/documents/upload", dependencies=[Depends(require_admin_cookie)])
async def upload_document(
    file: UploadFile = File(...),
    folder_id: str = Form(...),
    name: str = Form(""),
    description: str = Form(""),
) -> dict:
```

Then update the line that sets the display name (currently `filename = file.filename or "document"`):

```python
    filename = file.filename or "document"
    display_name = name.strip() or filename
    ext = Path(filename).suffix.lower()
```

And update the `process_document` call to use `display_name`:

```python
        doc = await process_document(
            content=content,
            name=display_name,
            folder_id=folder_id,
            mime_type=file.content_type or "application/octet-stream",
            description=description,
        )
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_documents.py::test_upload_with_explicit_name_uses_it tests/test_documents.py::test_upload_without_name_falls_back_to_filename -v
```

Expected: both PASSED.

- [ ] **Step 5: Run full suite**

```bash
uv run pytest -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/documents/router.py tests/test_documents.py
git commit -m "feat: accept optional display name in file upload endpoint"
```

---

### Task 6: Frontend — patch helper + API additions

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/documents.ts`
- Modify: `frontend/src/api/mock/documents.ts`

- [ ] **Step 1: Add patch helper to client.ts**

Add after the `put` function:

```typescript
/**
 * Make a PATCH request with a JSON body and return the parsed JSON response.
 * @template T Expected response type
 * @param path API path
 * @param body Request body (serialised to JSON)
 */
export async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    credentials: 'include',
  })
  if (!res.ok) throw new Error(`PATCH ${path} failed: ${res.status}`)
  return res.json()
}
```

- [ ] **Step 2: Update documents.ts**

Replace the import line at the top:

```typescript
import { del, get, patch, post } from './client'
```

Update `uploadFile` to accept an optional `name` parameter (add as 4th arg):

```typescript
  uploadFile: async (
    file: File,
    folder_id: string,
    description: string = '',
    name: string = '',
  ): Promise<UploadResult> => {
    const form = new FormData()
    form.append('file', file)
    form.append('folder_id', folder_id)
    if (name) form.append('name', name)
    if (description) form.append('description', description)
    const res = await fetch('/api/app/admin/documents/upload', {
      method: 'POST',
      body: form,
      credentials: 'include',
    })
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
    return res.json()
  },
```

Add `renameFolder` and `updateDocument` before `deleteDocument`:

```typescript
  /** Rename a folder. Returns the updated Folder. */
  renameFolder: (id: string, name: string): Promise<Folder> =>
    patch<Folder>(`/app/admin/folders/${id}`, { name }),

  /**
   * Update a document's name, description, or folder (move).
   * Pass only the fields you want to change.
   */
  updateDocument: (
    id: string,
    updates: Partial<{ name: string; description: string; folder_id: string }>,
  ): Promise<Document> =>
    patch<Document>(`/app/admin/documents/${id}`, updates),
```

- [ ] **Step 3: Update mock/documents.ts**

Update `uploadFile` signature to match (add `name = ''` as 4th arg):

```typescript
  uploadFile: async (
    file: File,
    folder_id: string,
    description: string = '',
    name: string = '',
  ): Promise<UploadResult> => {
    await delay(800)
    const displayName = name || file.name
    const id = displayName
      .replace(/\.[^.]+$/, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
    const doc: Document = {
      id,
      folder_id,
      name: displayName,
      description: description || `Mock summary for ${displayName}.`,
      mime_type: file.type,
      created_at: new Date().toISOString(),
    }
    documents.push(doc)
    return { status: 'ok', document: doc }
  },
```

Add `renameFolder` and `updateDocument` before `deleteDocument`:

```typescript
  renameFolder: async (id: string, name: string): Promise<Folder> => {
    await delay()
    const folder = folders.find(f => f.id === id)
    if (!folder) throw new Error(`Folder ${id} not found`)
    const updated = { ...folder, name }
    folders = folders.map(f => f.id === id ? updated : f)
    return updated
  },

  updateDocument: async (
    id: string,
    updates: Partial<{ name: string; description: string; folder_id: string }>,
  ): Promise<Document> => {
    await delay()
    const doc = documents.find(d => d.id === id)
    if (!doc) throw new Error(`Document ${id} not found`)
    const updated = { ...doc, ...updates }
    documents = documents.map(d => d.id === id ? updated : d)
    return updated
  },
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd /home/gan_hope326/Projects/trove/frontend && bun run build 2>&1 | tail -20
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 5: Commit**

```bash
cd /home/gan_hope326/Projects/trove
git add frontend/src/api/client.ts frontend/src/api/documents.ts frontend/src/api/mock/documents.ts
git commit -m "feat: add patch helper, renameFolder, updateDocument to frontend API"
```

---

### Task 7: Locale additions

**Files:**
- Modify: `locales/en.json`
- Modify: `locales/it.json`

- [ ] **Step 1: Add new keys to en.json**

Add the following entries before the closing `}` of `locales/en.json`:

```json
  "admin.documents.upload_file_modal_title": "Upload a file",
  "admin.documents.from_url_modal_title": "Add from URL",
  "admin.documents.url_label": "URL",
  "admin.documents.name_label": "Display name",
  "admin.documents.name_placeholder_file": "Defaults to file name",
  "admin.documents.name_placeholder_url": "Defaults to last part of URL",
  "admin.documents.description_hint": "Leave blank to auto-generate",
  "admin.documents.move_to_folder": "Move to folder",
  "admin.documents.move_button": "Move",
  "admin.documents.delete_confirm": "Sure?",
  "admin.documents.properties_empty": "Select a document to view its properties.",
  "admin.documents.folder_rename_placeholder": "New folder name",
  "admin.documents.cancel": "Cancel",
  "admin.documents.upload_button": "Upload",
  "admin.documents.add_button": "Add"
```

- [ ] **Step 2: Add new keys to it.json**

Add the same keys with Italian values before the closing `}` of `locales/it.json`:

```json
  "admin.documents.upload_file_modal_title": "Carica un file",
  "admin.documents.from_url_modal_title": "Aggiungi da URL",
  "admin.documents.url_label": "URL",
  "admin.documents.name_label": "Nome visualizzato",
  "admin.documents.name_placeholder_file": "Predefinito: nome del file",
  "admin.documents.name_placeholder_url": "Predefinito: ultima parte dell'URL",
  "admin.documents.description_hint": "Lascia vuoto per generare automaticamente",
  "admin.documents.move_to_folder": "Sposta nella cartella",
  "admin.documents.move_button": "Sposta",
  "admin.documents.delete_confirm": "Sicuro?",
  "admin.documents.properties_empty": "Seleziona un documento per visualizzarne le proprietà.",
  "admin.documents.folder_rename_placeholder": "Nuovo nome della cartella",
  "admin.documents.cancel": "Annulla",
  "admin.documents.upload_button": "Carica",
  "admin.documents.add_button": "Aggiungi"
```

- [ ] **Step 3: Verify JSON is valid**

```bash
python3 -c "import json; json.load(open('locales/en.json')); json.load(open('locales/it.json')); print('OK')"
```

Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add locales/en.json locales/it.json
git commit -m "feat: add locale keys for DocumentsPanel UI refinements"
```

---

### Task 8: DocumentsPanel.tsx — full rewrite

**Files:**
- Modify: `frontend/src/pages/DocumentsPanel.tsx`

- [ ] **Step 1: Replace the file with the new implementation**

Write the following complete file to `frontend/src/pages/DocumentsPanel.tsx`:

```tsx
/**
 * DocumentsPanel — admin UI for the document library.
 *
 * Three-column layout: folders (left, 192px), document list (centre, flex-1),
 * properties card (right, 288px). Folder rename is inline (click pencil icon).
 * Documents show name only; clicking selects the document and populates the
 * properties card. Name and description auto-save on blur. Folder selector shows
 * a Move button when the selection changes; Move switches the active folder and
 * keeps the document selected. Upload File and Add from URL open separate modals.
 */
import { useEffect, useRef, useState } from 'react'
import {
  Alert,
  Button,
  Label,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  Select,
  Spinner,
  Textarea,
  TextInput,
} from 'flowbite-react'
import { documentsApi, type Document, type Folder } from '../api/documents'
import { useTranslation } from '../i18n'

export default function DocumentsPanel() {
  const { t } = useTranslation()

  // ── Folder panel ──────────────────────────────────────────────────────────
  const [folders, setFolders] = useState<Folder[]>([])
  const [selectedFolder, setSelectedFolder] = useState<Folder | null>(null)
  const [loadingFolders, setLoadingFolders] = useState(true)
  const [newFolderName, setNewFolderName] = useState('')
  const [creatingFolder, setCreatingFolder] = useState(false)
  const [renamingFolderId, setRenamingFolderId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [folderToDelete, setFolderToDelete] = useState<Folder | null>(null)
  const [folderError, setFolderError] = useState<string | null>(null)

  // ── Document list ─────────────────────────────────────────────────────────
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null)
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [pendingSelectDocId, setPendingSelectDocId] = useState<string | null>(null)
  const [docError, setDocError] = useState<string | null>(null)

  // ── Properties card ───────────────────────────────────────────────────────
  const [propName, setPropName] = useState('')
  const [propDescription, setPropDescription] = useState('')
  const [propFolderId, setPropFolderId] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [propSaving, setPropSaving] = useState(false)
  // Move button shows when folder selector differs from the document's current folder
  const movePending = selectedDoc !== null && propFolderId !== selectedDoc.folder_id

  // ── Upload file modal ─────────────────────────────────────────────────────
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadName, setUploadName] = useState('')
  const [uploadDescription, setUploadDescription] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadNeedsDesc, setUploadNeedsDesc] = useState<{
    wordCount: number
    numCtx: number
  } | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // ── Add from URL modal ────────────────────────────────────────────────────
  const [urlModalOpen, setUrlModalOpen] = useState(false)
  const [urlInput, setUrlInput] = useState('')
  const [urlName, setUrlName] = useState('')
  const [urlDescription, setUrlDescription] = useState('')
  const [urlUploading, setUrlUploading] = useState(false)
  const [urlNeedsDesc, setUrlNeedsDesc] = useState<{
    wordCount: number
    numCtx: number
  } | null>(null)
  const [urlError, setUrlError] = useState<string | null>(null)

  // ── Load folders on mount ─────────────────────────────────────────────────
  useEffect(() => {
    documentsApi.listFolders().then(setFolders).finally(() => setLoadingFolders(false))
  }, [])

  // ── Load documents when selected folder changes ───────────────────────────
  useEffect(() => {
    if (!selectedFolder) {
      setDocuments([])
      setSelectedDoc(null)
      return
    }
    setLoadingDocs(true)
    documentsApi
      .listDocuments(selectedFolder.id)
      .then(docs => {
        setDocuments(docs)
        // After a move, auto-select the moved document in the new folder
        if (pendingSelectDocId) {
          const doc = docs.find(d => d.id === pendingSelectDocId)
          if (doc) setSelectedDoc(doc)
          setPendingSelectDocId(null)
        }
      })
      .finally(() => setLoadingDocs(false))
  }, [selectedFolder]) // pendingSelectDocId intentionally omitted — read synchronously

  // ── Sync properties card fields when a different document is selected ─────
  useEffect(() => {
    if (!selectedDoc) return
    setPropName(selectedDoc.name)
    setPropDescription(selectedDoc.description)
    setPropFolderId(selectedDoc.folder_id)
    setDeleteConfirm(false)
    setDocError(null)
  }, [selectedDoc])

  // ── Folder handlers ───────────────────────────────────────────────────────

  async function handleCreateFolder() {
    if (!newFolderName.trim()) return
    setCreatingFolder(true)
    setFolderError(null)
    try {
      const folder = await documentsApi.createFolder(newFolderName.trim())
      setFolders(prev => [...prev, folder].sort((a, b) => a.name.localeCompare(b.name)))
      setNewFolderName('')
    } catch (e) {
      setFolderError(String(e))
    } finally {
      setCreatingFolder(false)
    }
  }

  function startRename(folder: Folder) {
    setRenamingFolderId(folder.id)
    setRenameValue(folder.name)
  }

  async function commitRename(folderId: string) {
    const trimmed = renameValue.trim()
    setRenamingFolderId(null)
    if (!trimmed) return
    try {
      const updated = await documentsApi.renameFolder(folderId, trimmed)
      setFolders(prev =>
        prev.map(f => f.id === folderId ? updated : f).sort((a, b) => a.name.localeCompare(b.name))
      )
      if (selectedFolder?.id === folderId) setSelectedFolder(updated)
    } catch (e) {
      setFolderError(String(e))
    }
  }

  async function handleDeleteFolder(folder: Folder) {
    setFolderToDelete(null)
    setFolderError(null)
    try {
      await documentsApi.deleteFolder(folder.id)
      setFolders(prev => prev.filter(f => f.id !== folder.id))
      if (selectedFolder?.id === folder.id) setSelectedFolder(null)
    } catch (e) {
      setFolderError(String(e))
    }
  }

  // ── Properties card handlers ──────────────────────────────────────────────

  async function handlePropNameBlur() {
    if (!selectedDoc || propName.trim() === selectedDoc.name) return
    setPropSaving(true)
    try {
      const updated = await documentsApi.updateDocument(selectedDoc.id, { name: propName.trim() })
      setDocuments(prev => prev.map(d => d.id === updated.id ? updated : d))
      setSelectedDoc(updated)
    } catch (e) {
      setPropName(selectedDoc.name)
      setDocError(String(e))
    } finally {
      setPropSaving(false)
    }
  }

  async function handlePropDescriptionBlur() {
    if (!selectedDoc || propDescription === selectedDoc.description) return
    setPropSaving(true)
    try {
      const updated = await documentsApi.updateDocument(selectedDoc.id, {
        description: propDescription,
      })
      setDocuments(prev => prev.map(d => d.id === updated.id ? updated : d))
      setSelectedDoc(updated)
    } catch (e) {
      setPropDescription(selectedDoc.description)
      setDocError(String(e))
    } finally {
      setPropSaving(false)
    }
  }

  async function handleMove() {
    if (!selectedDoc || !movePending) return
    setDocError(null)
    try {
      const updated = await documentsApi.updateDocument(selectedDoc.id, {
        folder_id: propFolderId,
      })
      const destFolder = folders.find(f => f.id === propFolderId)
      if (destFolder) {
        setPendingSelectDocId(updated.id)
        setSelectedFolder(destFolder)
      }
    } catch (e) {
      setPropFolderId(selectedDoc.folder_id)
      setDocError(String(e))
    }
  }

  async function handleDeleteDocument() {
    if (!selectedDoc) return
    if (!deleteConfirm) {
      setDeleteConfirm(true)
      return
    }
    try {
      await documentsApi.deleteDocument(selectedDoc.id)
      setDocuments(prev => prev.filter(d => d.id !== selectedDoc.id))
      setSelectedDoc(null)
    } catch (e) {
      setDocError(String(e))
    }
  }

  // ── Upload file modal handlers ────────────────────────────────────────────

  function closeUploadModal() {
    setUploadModalOpen(false)
    setUploadFile(null)
    setUploadName('')
    setUploadDescription('')
    setUploading(false)
    setUploadNeedsDesc(null)
    setUploadError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  async function handleUpload() {
    if (!uploadFile || !selectedFolder) return
    setUploading(true)
    setUploadError(null)
    const name = uploadName.trim() || uploadFile.name
    try {
      const result = await documentsApi.uploadFile(
        uploadFile,
        selectedFolder.id,
        uploadDescription.trim(),
        name,
      )
      if (result.status === 'ok') {
        setDocuments(prev =>
          [...prev, result.document].sort((a, b) => a.name.localeCompare(b.name))
        )
        closeUploadModal()
      } else {
        setUploadNeedsDesc({ wordCount: result.word_count, numCtx: result.num_ctx })
      }
    } catch (e) {
      setUploadError(String(e))
    } finally {
      setUploading(false)
    }
  }

  // ── Add from URL modal handlers ───────────────────────────────────────────

  function closeUrlModal() {
    setUrlModalOpen(false)
    setUrlInput('')
    setUrlName('')
    setUrlDescription('')
    setUrlUploading(false)
    setUrlNeedsDesc(null)
    setUrlError(null)
  }

  async function handleUrlUpload() {
    if (!urlInput.trim() || !selectedFolder) return
    setUrlUploading(true)
    setUrlError(null)
    const url = urlInput.trim()
    const name = urlName.trim() || url.split('/').filter(Boolean).pop() || url
    try {
      const result = await documentsApi.uploadUrl(
        url,
        selectedFolder.id,
        name,
        urlDescription.trim(),
      )
      if (result.status === 'ok') {
        setDocuments(prev =>
          [...prev, result.document].sort((a, b) => a.name.localeCompare(b.name))
        )
        closeUrlModal()
      } else {
        setUrlNeedsDesc({ wordCount: result.word_count, numCtx: result.num_ctx })
      }
    } catch (e) {
      setUrlError(String(e))
    } finally {
      setUrlUploading(false)
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="pt-4 flex gap-4">

      {/* ── Folder column ────────────────────────────────────────────────── */}
      <div className="w-48 flex-shrink-0 flex flex-col gap-2">
        {folderError && (
          <Alert color="failure" className="text-xs p-2">{folderError}</Alert>
        )}

        {/* New folder input */}
        <div className="flex gap-1">
          <TextInput
            sizing="sm"
            placeholder={t('admin.documents.folder_name_placeholder')}
            value={newFolderName}
            onChange={e => setNewFolderName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleCreateFolder()}
            className="flex-1"
          />
          <Button
            size="sm"
            onClick={handleCreateFolder}
            disabled={creatingFolder || !newFolderName.trim()}
          >
            {creatingFolder ? <Spinner size="sm" /> : '+'}
          </Button>
        </div>

        {/* Folder list */}
        {loadingFolders ? (
          <Spinner />
        ) : (
          <div className="flex flex-col gap-0.5">
            {folders.map(folder => (
              <div
                key={folder.id}
                className={`group flex items-center gap-1 px-2 py-1.5 rounded cursor-pointer text-sm ${
                  selectedFolder?.id === folder.id
                    ? 'bg-blue-50 text-blue-700 font-medium'
                    : 'hover:bg-gray-100 text-gray-700'
                }`}
                onClick={() => renamingFolderId !== folder.id && setSelectedFolder(folder)}
              >
                {renamingFolderId === folder.id ? (
                  <TextInput
                    sizing="sm"
                    autoFocus
                    value={renameValue}
                    placeholder={t('admin.documents.folder_rename_placeholder')}
                    onChange={e => setRenameValue(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') commitRename(folder.id)
                      if (e.key === 'Escape') setRenamingFolderId(null)
                    }}
                    onBlur={() => commitRename(folder.id)}
                    onClick={e => e.stopPropagation()}
                    className="flex-1"
                  />
                ) : (
                  <>
                    <span className="flex-1 truncate">{folder.name}</span>
                    <button
                      className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-blue-500 transition-opacity text-base leading-none"
                      onClick={e => { e.stopPropagation(); startRename(folder) }}
                      title="Rename"
                    >
                      ✎
                    </button>
                    <button
                      className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-opacity text-lg leading-none"
                      onClick={e => { e.stopPropagation(); setFolderToDelete(folder) }}
                      title={t('admin.documents.delete_folder')}
                    >
                      ×
                    </button>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Document list column ─────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col gap-3 min-w-0">
        {/* Upload controls */}
        <div className="flex gap-2">
          <Button
            size="sm"
            disabled={!selectedFolder}
            onClick={() => setUploadModalOpen(true)}
          >
            {t('admin.documents.upload_file')}
          </Button>
          <Button
            size="sm"
            color="light"
            disabled={!selectedFolder}
            onClick={() => setUrlModalOpen(true)}
          >
            {t('admin.documents.add_from_url')}
          </Button>
        </div>

        {!selectedFolder ? (
          <p className="text-gray-500 text-sm">{t('admin.documents.no_folder_selected')}</p>
        ) : loadingDocs ? (
          <Spinner />
        ) : documents.length === 0 ? (
          <p className="text-gray-500 text-sm">{t('admin.documents.no_documents')}</p>
        ) : (
          <div className="flex flex-col gap-0.5">
            {documents.map(doc => (
              <div
                key={doc.id}
                className={`px-3 py-2 rounded cursor-pointer text-sm truncate ${
                  selectedDoc?.id === doc.id
                    ? 'bg-blue-50 text-blue-700 font-medium'
                    : 'hover:bg-gray-100 text-gray-700'
                }`}
                onClick={() => { setSelectedDoc(doc); setDeleteConfirm(false) }}
              >
                {doc.name}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Properties card ──────────────────────────────────────────────── */}
      <div className="w-72 flex-shrink-0 flex flex-col gap-3">
        {docError && (
          <Alert color="failure" className="text-xs p-2">{docError}</Alert>
        )}

        {!selectedDoc ? (
          <p className="text-gray-400 text-sm italic">
            {t('admin.documents.properties_empty')}
          </p>
        ) : (
          <>
            <div>
              <Label className="text-xs text-gray-500 mb-1 block">
                {t('admin.documents.name_label')}
              </Label>
              <TextInput
                sizing="sm"
                value={propName}
                onChange={e => setPropName(e.target.value)}
                onBlur={handlePropNameBlur}
                disabled={propSaving}
              />
            </div>

            <div>
              <Label className="text-xs text-gray-500 mb-1 block">
                {t('admin.documents.description_label')}
              </Label>
              <Textarea
                rows={4}
                value={propDescription}
                onChange={e => setPropDescription(e.target.value)}
                onBlur={handlePropDescriptionBlur}
                disabled={propSaving}
                className="text-sm"
              />
            </div>

            <div>
              <Label className="text-xs text-gray-500 mb-1 block">
                {t('admin.documents.move_to_folder')}
              </Label>
              <div className="flex gap-2 items-center">
                <Select
                  sizing="sm"
                  className="flex-1"
                  value={propFolderId}
                  onChange={e => setPropFolderId(e.target.value)}
                >
                  {folders.map(f => (
                    <option key={f.id} value={f.id}>{f.name}</option>
                  ))}
                </Select>
                {movePending && (
                  <Button size="sm" onClick={handleMove}>
                    {t('admin.documents.move_button')}
                  </Button>
                )}
              </div>
            </div>

            <div className="pt-2 border-t border-gray-100">
              <Button size="sm" color="failure" onClick={handleDeleteDocument}>
                {deleteConfirm
                  ? t('admin.documents.delete_confirm')
                  : t('admin.documents.delete_document')}
              </Button>
            </div>
          </>
        )}
      </div>

      {/* ── Upload File modal ─────────────────────────────────────────────── */}
      <Modal show={uploadModalOpen} onClose={closeUploadModal} size="md">
        <ModalHeader>{t('admin.documents.upload_file_modal_title')}</ModalHeader>
        <ModalBody>
          <div className="flex flex-col gap-4">
            {uploadError && <Alert color="failure">{uploadError}</Alert>}

            {uploadNeedsDesc ? (
              /* Too-long flow — description required before retrying */
              <Alert color="warning">
                <p className="font-semibold">{t('admin.documents.too_long_title')}</p>
                <p className="text-sm mt-1">
                  {t('admin.documents.too_long_body')
                    .replace('{{words}}', uploadNeedsDesc.wordCount.toLocaleString())
                    .replace('{{tokens}}', (uploadNeedsDesc.wordCount * 2).toLocaleString())
                    .replace('{{ctx}}', uploadNeedsDesc.numCtx.toLocaleString())}
                </p>
                <div className="mt-2">
                  <TextInput
                    sizing="sm"
                    placeholder={t('admin.documents.description_placeholder')}
                    value={uploadDescription}
                    onChange={e => setUploadDescription(e.target.value)}
                  />
                </div>
              </Alert>
            ) : (
              <>
                <div>
                  <Label className="mb-1 block">{t('admin.documents.upload_file')}</Label>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx,.pptx,.xlsx,.txt,.md,.html,.htm"
                    className="block w-full text-sm text-gray-500 file:mr-4 file:py-1 file:px-3 file:rounded file:border-0 file:text-sm file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200"
                    onChange={e => setUploadFile(e.target.files?.[0] ?? null)}
                  />
                </div>
                <div>
                  <Label className="mb-1 block">{t('admin.documents.name_label')}</Label>
                  <TextInput
                    sizing="sm"
                    placeholder={t('admin.documents.name_placeholder_file')}
                    value={uploadName}
                    onChange={e => setUploadName(e.target.value)}
                  />
                </div>
                <div>
                  <Label className="mb-1 block">{t('admin.documents.description_label')}</Label>
                  <TextInput
                    sizing="sm"
                    placeholder={t('admin.documents.description_hint')}
                    value={uploadDescription}
                    onChange={e => setUploadDescription(e.target.value)}
                  />
                </div>
              </>
            )}
          </div>
        </ModalBody>
        <ModalFooter>
          <Button
            onClick={handleUpload}
            disabled={
              !uploadFile ||
              uploading ||
              (uploadNeedsDesc !== null && !uploadDescription.trim())
            }
          >
            {uploading ? (
              <Spinner size="sm" />
            ) : uploadNeedsDesc ? (
              t('admin.documents.submit_with_description')
            ) : (
              t('admin.documents.upload_button')
            )}
          </Button>
          <Button color="gray" onClick={closeUploadModal}>
            {t('admin.documents.cancel')}
          </Button>
        </ModalFooter>
      </Modal>

      {/* ── Add from URL modal ────────────────────────────────────────────── */}
      <Modal show={urlModalOpen} onClose={closeUrlModal} size="md">
        <ModalHeader>{t('admin.documents.from_url_modal_title')}</ModalHeader>
        <ModalBody>
          <div className="flex flex-col gap-4">
            {urlError && <Alert color="failure">{urlError}</Alert>}

            {urlNeedsDesc ? (
              <Alert color="warning">
                <p className="font-semibold">{t('admin.documents.too_long_title')}</p>
                <p className="text-sm mt-1">
                  {t('admin.documents.too_long_body')
                    .replace('{{words}}', urlNeedsDesc.wordCount.toLocaleString())
                    .replace('{{tokens}}', (urlNeedsDesc.wordCount * 2).toLocaleString())
                    .replace('{{ctx}}', urlNeedsDesc.numCtx.toLocaleString())}
                </p>
                <div className="mt-2">
                  <TextInput
                    sizing="sm"
                    placeholder={t('admin.documents.description_placeholder')}
                    value={urlDescription}
                    onChange={e => setUrlDescription(e.target.value)}
                  />
                </div>
              </Alert>
            ) : (
              <>
                <div>
                  <Label className="mb-1 block">{t('admin.documents.url_label')}</Label>
                  <TextInput
                    sizing="sm"
                    placeholder="https://..."
                    value={urlInput}
                    onChange={e => setUrlInput(e.target.value)}
                  />
                </div>
                <div>
                  <Label className="mb-1 block">{t('admin.documents.name_label')}</Label>
                  <TextInput
                    sizing="sm"
                    placeholder={t('admin.documents.name_placeholder_url')}
                    value={urlName}
                    onChange={e => setUrlName(e.target.value)}
                  />
                </div>
                <div>
                  <Label className="mb-1 block">{t('admin.documents.description_label')}</Label>
                  <TextInput
                    sizing="sm"
                    placeholder={t('admin.documents.description_hint')}
                    value={urlDescription}
                    onChange={e => setUrlDescription(e.target.value)}
                  />
                </div>
              </>
            )}
          </div>
        </ModalBody>
        <ModalFooter>
          <Button
            onClick={handleUrlUpload}
            disabled={
              !urlInput.trim() ||
              urlUploading ||
              (urlNeedsDesc !== null && !urlDescription.trim())
            }
          >
            {urlUploading ? (
              <Spinner size="sm" />
            ) : urlNeedsDesc ? (
              t('admin.documents.submit_with_description')
            ) : (
              t('admin.documents.add_button')
            )}
          </Button>
          <Button color="gray" onClick={closeUrlModal}>
            {t('admin.documents.cancel')}
          </Button>
        </ModalFooter>
      </Modal>

      {/* ── Delete folder confirmation modal ──────────────────────────────── */}
      <Modal show={!!folderToDelete} onClose={() => setFolderToDelete(null)} size="sm">
        <ModalHeader>{t('admin.documents.delete_folder')}</ModalHeader>
        <ModalBody>
          <p>{t('admin.documents.delete_folder_confirm')}</p>
        </ModalBody>
        <ModalFooter>
          <Button
            color="failure"
            onClick={() => folderToDelete && handleDeleteFolder(folderToDelete)}
          >
            {t('admin.documents.delete_folder')}
          </Button>
          <Button color="gray" onClick={() => setFolderToDelete(null)}>
            {t('admin.documents.cancel')}
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  )
}
```

- [ ] **Step 2: Verify the TypeScript build passes**

```bash
cd /home/gan_hope326/Projects/trove/frontend && bun run build 2>&1 | tail -30
```

Expected: build succeeds, zero TypeScript errors.

- [ ] **Step 3: Run full backend test suite to confirm nothing broken**

```bash
cd /home/gan_hope326/Projects/trove && uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
cd /home/gan_hope326/Projects/trove
git add frontend/src/pages/DocumentsPanel.tsx
git commit -m "feat: rewrite DocumentsPanel with three-column layout, modals, and properties card"
```

---

## Self-Review Notes

- All 9 spec requirements covered: folder rename ✓, document rename ✓, name-only list ✓, properties card ✓, auto-save on blur ✓, Move button ✓, move switches folder + keeps selection ✓, Upload File modal ✓, Add from URL modal ✓.
- `pendingSelectDocId` is read synchronously inside the `selectedFolder` useEffect — no stale closure issue because `setPendingSelectDocId` happens before `setSelectedFolder`.
- The `movePending` derived value recalculates on every render — no separate state needed.
- `commitRename` clears `renamingFolderId` before the async call so the input disappears immediately; error is shown in folderError.
- The `patch` import in `documents.ts` does not conflict with the `updates` parameter name used in `updateDocument`.
