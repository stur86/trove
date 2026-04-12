# Document Library Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full backend for the document library — folder/document CRUD, Markitdown conversion, AI summarisation with context-length guard, filesystem storage, and Pydantic AI tool injection for gem runs.

**Architecture:** New `backend/documents/` domain (models, repository, service, router) following the existing feature-grouped pattern. `UserTask` gains two new JSON columns. The runner builds a document-aware `Agent` with two injected tool functions when documents are in scope. The run endpoint resolves the gem's document access list before calling the runner.

**Tech Stack:** Python/FastAPI, SQLite (`backend/db.get_db`), Markitdown, Pydantic AI `Agent` with plain-function tools, pytest with `data_dir` + `config_dir` fixtures from `tests/conftest.py`.

---

## File Map

**Create:**
- `backend/documents/__init__.py`
- `backend/documents/models.py`
- `backend/documents/repository.py`
- `backend/documents/service.py`
- `backend/documents/router.py`
- `tests/test_documents.py`

**Modify:**
- `pyproject.toml` — add `markitdown` dependency
- `backend/tasks/models.py` — add `doc_folder_ids`, `doc_ids` to `UserTask`
- `backend/tasks/repository.py` — save/load new columns; `ALTER TABLE` guard
- `backend/tasks/runner.py` — `_build_document_tools`, `_make_agent`, `documents` param on both functions
- `backend/tasks/router.py` — resolve documents before calling `stream_task`
- `backend/app/router.py` — include documents router
- `tests/test_task_models.py` — `UserTask` doc field round-trip
- `tests/test_task_runner.py` — tool injection tests
- `tests/test_gems_router.py` — run endpoint resolves documents

---

## Task 1: Add markitdown dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add markitdown to dependencies**

In `pyproject.toml`, add `"markitdown>=0.1"` to the `dependencies` list (after `jinja2`):

```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "pydantic>=2.10",
    "psutil>=6.1",
    "sse-starlette>=2.2",
    "python-dotenv>=1.0",
    "typer>=0.12",
    "jinja2>=3.1",
    "markitdown>=0.1",
    "pydantic-ai>=0.0.54",
]
```

- [ ] **Step 2: Sync dependencies**

```bash
uv sync --group dev
```

Expected: resolves without error, `markitdown` appears in `uv.lock`.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add markitdown dependency"
```

---

## Task 2: Document models

**Files:**
- Create: `backend/documents/__init__.py`
- Create: `backend/documents/models.py`
- Test: `tests/test_documents.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_documents.py`:

```python
"""Tests for the document library domain."""
from datetime import datetime, timezone

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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_documents.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.documents'`

- [ ] **Step 3: Create the module files**

Create `backend/documents/__init__.py`:

```python
"""Document library domain for Trove."""
```

Create `backend/documents/models.py`:

```python
"""Data models for the Trove document library.

Folder groups related documents under a human-readable name.
Document represents a single processed file with AI-generated metadata.
Both are immutable Pydantic models — the repository owns persistence.
"""
from datetime import datetime

from pydantic import BaseModel


class Folder(BaseModel, frozen=True):
    """A named folder grouping related documents in the library."""

    id: str
    """Slug identifier, e.g. 'hr-policies'."""
    name: str
    """Human-readable folder name, e.g. 'HR Policies'."""


class Document(BaseModel, frozen=True):
    """A processed document stored in the library.

    The markdown content is stored on disk at
    $XDG_DATA_HOME/trove/documents/<folder_id>/<id>.md.
    This model holds only the metadata.
    """

    id: str
    """Slug derived from the original filename, e.g. 'leave-policy-2024'."""
    folder_id: str
    """ID of the folder this document belongs to."""
    name: str
    """Original filename, used for display purposes."""
    description: str
    """AI-generated one-liner, or admin-supplied description if the document
    is too long for the model's context window."""
    mime_type: str
    """MIME type of the original uploaded file."""
    created_at: datetime
    """Timestamp when this document was added to the library."""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_documents.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/documents/ tests/test_documents.py
git commit -m "feat: add document library models"
```

---

## Task 3: Document repository

**Files:**
- Create: `backend/documents/repository.py`
- Test: `tests/test_documents.py` (extend)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_documents.py`:

```python
import pytest
from backend.documents.repository import (
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
)


# ── Folder CRUD ───────────────────────────────────────────────────────────────

def test_save_and_get_folder(data_dir):
    f = Folder(id="hr", name="HR")
    save_folder(f)
    assert get_folder("hr") == f


def test_get_folder_missing_raises(data_dir):
    with pytest.raises(KeyError):
        get_folder("does-not-exist")


def test_list_folders_empty(data_dir):
    assert list_folders() == []


def test_list_folders_returns_all_ordered(data_dir):
    save_folder(Folder(id="b", name="Beta"))
    save_folder(Folder(id="a", name="Alpha"))
    names = [f.name for f in list_folders()]
    assert names == ["Alpha", "Beta"]


def test_delete_folder_removes_folder_and_documents(data_dir):
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


# ── Document CRUD ─────────────────────────────────────────────────────────────

def test_save_and_get_document(data_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    doc = Document(id="doc1", folder_id="f1", name="doc1.pdf",
                   description="A doc", mime_type="application/pdf", created_at=now)
    save_document(doc)
    loaded = get_document("doc1")
    assert loaded.id == "doc1"
    assert loaded.folder_id == "f1"


def test_get_document_missing_raises(data_dir):
    with pytest.raises(KeyError):
        get_document("missing")


def test_list_documents_empty(data_dir):
    save_folder(Folder(id="f1", name="F1"))
    assert list_documents("f1") == []


def test_list_documents_filtered_by_folder(data_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_folder(Folder(id="f2", name="F2"))
    save_document(Document(id="d1", folder_id="f1", name="d1", description="", mime_type="text/plain", created_at=now))
    save_document(Document(id="d2", folder_id="f2", name="d2", description="", mime_type="text/plain", created_at=now))
    assert [d.id for d in list_documents("f1")] == ["d1"]
    assert [d.id for d in list_documents("f2")] == ["d2"]


def test_delete_document_returns_folder_id(data_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="d1", description="", mime_type="text/plain", created_at=now))
    folder_id = delete_document("d1")
    assert folder_id == "f1"
    with pytest.raises(KeyError):
        get_document("d1")


def test_delete_document_missing_returns_none(data_dir):
    assert delete_document("missing") is None


def test_document_id_exists(data_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="d1", description="", mime_type="text/plain", created_at=now))
    assert document_id_exists("d1") is True
    assert document_id_exists("nope") is False


# ── resolve_documents ─────────────────────────────────────────────────────────

def test_resolve_documents_empty_inputs(data_dir):
    assert resolve_documents([], []) == []


def test_resolve_documents_by_folder(data_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="Alpha", description="", mime_type="text/plain", created_at=now))
    save_document(Document(id="d2", folder_id="f1", name="Beta", description="", mime_type="text/plain", created_at=now))
    docs = resolve_documents(["f1"], [])
    assert {d.id for d in docs} == {"d1", "d2"}


def test_resolve_documents_by_id(data_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="d1", description="", mime_type="text/plain", created_at=now))
    save_document(Document(id="d2", folder_id="f1", name="d2", description="", mime_type="text/plain", created_at=now))
    docs = resolve_documents([], ["d1"])
    assert [d.id for d in docs] == ["d1"]


def test_resolve_documents_deduplicates_overlap(data_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="d1", description="", mime_type="text/plain", created_at=now))
    # d1 appears in both a folder grant and an individual grant
    docs = resolve_documents(["f1"], ["d1"])
    assert len(docs) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_documents.py -v -k "folder or document or resolve"
```

Expected: `ImportError` on `backend.documents.repository`.

- [ ] **Step 3: Implement the repository**

Create `backend/documents/repository.py`:

```python
"""SQLite repository for the Trove document library.

Owns the 'folders' and 'documents' tables in trove.db.
Uses backend.db.get_db() for connections.
"""
from datetime import datetime

from backend.db import get_db
from backend.documents.models import Document, Folder

_CREATE_TABLES = """\
CREATE TABLE IF NOT EXISTS folders (
    id    TEXT PRIMARY KEY,
    name  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
    id          TEXT PRIMARY KEY,
    folder_id   TEXT NOT NULL REFERENCES folders(id),
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    mime_type   TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
"""


def _ensure_tables(conn) -> None:
    """Create folders and documents tables if they do not exist."""
    conn.executescript(_CREATE_TABLES)


def _row_to_folder(row) -> Folder:
    return Folder(id=row["id"], name=row["name"])


def _row_to_document(row) -> Document:
    return Document(
        id=row["id"],
        folder_id=row["folder_id"],
        name=row["name"],
        description=row["description"],
        mime_type=row["mime_type"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


# ── Folder CRUD ────────────────────────────────────────────────────────────────

def save_folder(folder: Folder) -> None:
    """Insert or replace a folder record."""
    with get_db() as conn:
        _ensure_tables(conn)
        conn.execute(
            "INSERT OR REPLACE INTO folders (id, name) VALUES (?, ?)",
            (folder.id, folder.name),
        )


def get_folder(folder_id: str) -> Folder:
    """Load a folder by id. Raises KeyError if not found."""
    with get_db() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT * FROM folders WHERE id = ?", (folder_id,)
        ).fetchone()
    if row is None:
        raise KeyError(folder_id)
    return _row_to_folder(row)


def list_folders() -> list[Folder]:
    """Return all folders ordered by name."""
    with get_db() as conn:
        _ensure_tables(conn)
        rows = conn.execute("SELECT * FROM folders ORDER BY name").fetchall()
    return [_row_to_folder(r) for r in rows]


def delete_folder(folder_id: str) -> list[str]:
    """Delete a folder and all its documents. Returns list of deleted document IDs."""
    with get_db() as conn:
        _ensure_tables(conn)
        doc_rows = conn.execute(
            "SELECT id FROM documents WHERE folder_id = ?", (folder_id,)
        ).fetchall()
        doc_ids = [r["id"] for r in doc_rows]
        conn.execute("DELETE FROM documents WHERE folder_id = ?", (folder_id,))
        conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
    return doc_ids


# ── Document CRUD ──────────────────────────────────────────────────────────────

def save_document(doc: Document) -> None:
    """Insert or replace a document record."""
    with get_db() as conn:
        _ensure_tables(conn)
        conn.execute(
            """INSERT OR REPLACE INTO documents
               (id, folder_id, name, description, mime_type, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                doc.id,
                doc.folder_id,
                doc.name,
                doc.description,
                doc.mime_type,
                doc.created_at.isoformat(),
            ),
        )


def get_document(doc_id: str) -> Document:
    """Load a document by id. Raises KeyError if not found."""
    with get_db() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    if row is None:
        raise KeyError(doc_id)
    return _row_to_document(row)


def list_documents(folder_id: str | None = None) -> list[Document]:
    """List documents, optionally filtered by folder_id, ordered by name."""
    with get_db() as conn:
        _ensure_tables(conn)
        if folder_id is not None:
            rows = conn.execute(
                "SELECT * FROM documents WHERE folder_id = ? ORDER BY name",
                (folder_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM documents ORDER BY name"
            ).fetchall()
    return [_row_to_document(r) for r in rows]


def delete_document(doc_id: str) -> str | None:
    """Delete a document by id. Returns its folder_id for filesystem cleanup, or None if not found."""
    with get_db() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT folder_id FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    return row["folder_id"]


def document_id_exists(doc_id: str) -> bool:
    """Return True if a document with the given id already exists."""
    with get_db() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT 1 FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    return row is not None


def resolve_documents(folder_ids: list[str], doc_ids: list[str]) -> list[Document]:
    """Return the union of all documents in the given folders and individual doc IDs.

    Deduplicates by document ID. Results are ordered by name.

    Args:
        folder_ids: IDs of folders whose entire contents are accessible.
        doc_ids: IDs of individually accessible documents.

    Returns:
        Deduplicated list of Documents, ordered by name.
    """
    if not folder_ids and not doc_ids:
        return []
    seen: dict[str, Document] = {}
    with get_db() as conn:
        _ensure_tables(conn)
        if folder_ids:
            placeholders = ",".join("?" * len(folder_ids))
            rows = conn.execute(
                f"SELECT * FROM documents WHERE folder_id IN ({placeholders}) ORDER BY name",
                folder_ids,
            ).fetchall()
            for r in rows:
                doc = _row_to_document(r)
                seen[doc.id] = doc
        if doc_ids:
            placeholders = ",".join("?" * len(doc_ids))
            rows = conn.execute(
                f"SELECT * FROM documents WHERE id IN ({placeholders}) ORDER BY name",
                doc_ids,
            ).fetchall()
            for r in rows:
                doc = _row_to_document(r)
                seen[doc.id] = doc
    return sorted(seen.values(), key=lambda d: d.name)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_documents.py -v -k "folder or document or resolve"
```

Expected: all 17 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/documents/repository.py tests/test_documents.py
git commit -m "feat: add document library repository"
```

---

## Task 4: Document service

**Files:**
- Create: `backend/documents/service.py`
- Test: `tests/test_documents.py` (extend)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_documents.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.documents.service import (
    DocumentTooLongError,
    _slugify,
    _unique_id,
    process_document,
)


# ── _slugify ──────────────────────────────────────────────────────────────────

def test_slugify_strips_extension():
    assert _slugify("leave-policy.pdf") == "leave-policy"


def test_slugify_lowercases_and_hyphenates():
    assert _slugify("HR Policy 2024.docx") == "hr-policy-2024"


def test_slugify_removes_special_chars():
    assert _slugify("Report (Final)!.txt") == "report-final"


def test_slugify_empty_stem_returns_document():
    assert _slugify(".hidden") == "document"


# ── _unique_id ────────────────────────────────────────────────────────────────

def test_unique_id_no_collision(data_dir):
    assert _unique_id("new-doc") == "new-doc"


def test_unique_id_collision_appends_suffix(data_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="my-doc", folder_id="f1", name="my-doc.pdf",
                           description="", mime_type="application/pdf", created_at=now))
    assert _unique_id("my-doc") == "my-doc-2"


def test_unique_id_multiple_collisions(data_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    for suffix in ["my-doc", "my-doc-2"]:
        save_document(Document(id=suffix, folder_id="f1", name=f"{suffix}.pdf",
                               description="", mime_type="application/pdf", created_at=now))
    assert _unique_id("my-doc") == "my-doc-3"


# ── process_document ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_document_short_doc_uses_ai_summary(data_dir, config_dir, monkeypatch):
    """Short document → AI summary called, document saved to disk and DB."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir.parent))
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
    md_path = data_dir / "documents" / "f1" / "test-doc.md"
    assert md_path.exists()
    assert md_path.read_text() == "Short content with few words."


@pytest.mark.asyncio
async def test_process_document_supplied_description_skips_ai(data_dir, config_dir, monkeypatch):
    """Admin-supplied description bypasses length check and AI summary entirely."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir.parent))
    from backend.config.service import save_config
    from backend.config.models import TroveConfig
    save_config(TroveConfig(num_ctx=10))  # very small context window
    save_folder(Folder(id="f1", name="F1"))

    # content that would exceed num_ctx if checked
    long_content = "word " * 100

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
async def test_process_document_too_long_raises(data_dir, config_dir, monkeypatch):
    """Document exceeding context window with no description raises DocumentTooLongError."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir.parent))
    from backend.config.service import save_config
    from backend.config.models import TroveConfig
    save_config(TroveConfig(num_ctx=10))
    save_folder(Folder(id="f1", name="F1"))

    long_content = "word " * 100  # 100 words × 2 = 200 estimated tokens > 10

    with pytest.raises(DocumentTooLongError) as exc_info:
        await process_document(
            content=long_content,
            name="big.txt",
            folder_id="f1",
            mime_type="text/plain",
        )
    assert exc_info.value.word_count == 100
    assert exc_info.value.num_ctx == 10


@pytest.mark.asyncio
async def test_process_document_ai_failure_falls_back_to_name(data_dir, config_dir, monkeypatch):
    """When AI summary raises, description falls back to the filename."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir.parent))
    from backend.config.service import save_config
    from backend.config.models import TroveConfig
    save_config(TroveConfig(num_ctx=8192))
    save_folder(Folder(id="f1", name="F1"))

    # Patch run_task (used inside _ai_summary) to raise — _ai_summary catches it
    # and returns the fallback. This tests the full fallback chain.
    with patch("backend.tasks.runner.run_task", new=AsyncMock(side_effect=RuntimeError("Ollama down"))):
        doc = await process_document(
            content="Some content.",
            name="my-file.pdf",
            folder_id="f1",
            mime_type="application/pdf",
        )
    assert doc.description == "my-file.pdf"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_documents.py -v -k "slugify or unique_id or process_document"
```

Expected: `ImportError` on `backend.documents.service`.

- [ ] **Step 3: Implement the service**

Create `backend/documents/service.py`:

```python
"""Upload pipeline for the Trove document library.

Handles slug derivation, context-length guard, AI summary generation,
markdown file writing, and database persistence. Both upload paths
(file and URL) call process_document() after content is retrieved.
"""
import re
from datetime import datetime, timezone
from pathlib import Path

from backend.config.service import load_config
from backend.db import get_data_dir
from backend.documents.models import Document
from backend.documents.repository import document_id_exists, save_document


class DocumentTooLongError(Exception):
    """Raised when a document exceeds the model's context window and no description was supplied.

    The router catches this and returns a needs_description response so the
    frontend can prompt the admin for a manual description.
    """

    def __init__(self, word_count: int, num_ctx: int) -> None:
        self.word_count = word_count
        self.num_ctx = num_ctx
        super().__init__(
            f"Document has ~{word_count * 2} estimated tokens; context window is {num_ctx}."
        )


def _slugify(name: str) -> str:
    """Derive a lowercase hyphenated slug from a filename, stripping the extension.

    Examples:
        'HR Policy 2024.docx' → 'hr-policy-2024'
        '.hidden'             → 'document'
    """
    stem = Path(name).stem
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return slug or "document"


def _unique_id(base: str) -> str:
    """Return base if available, otherwise base-2, base-3, … until unique."""
    if not document_id_exists(base):
        return base
    n = 2
    while document_id_exists(f"{base}-{n}"):
        n += 1
    return f"{base}-{n}"


async def _ai_summary(content: str, fallback: str) -> str:
    """Generate a one-sentence AI summary of content.

    Imports run_task at call time to avoid a circular import at module load
    (service → runner → documents.models is fine; service → runner at module
    level would cause an import cycle with runner → service for the summary task).

    Falls back to the filename on any failure (Ollama unavailable, timeout, etc.).
    """
    from backend.tasks.models import StringArg, Task
    from backend.tasks.runner import run_task

    summary_task = Task(
        template=(
            "In one sentence, describe what this document is about:\n\n{{ content }}"
        ),
        args=(StringArg(name="content"),),
    )
    try:
        return await run_task(summary_task, {"content": content})
    except Exception:
        return fallback


async def process_document(
    content: str,
    name: str,
    folder_id: str,
    mime_type: str,
    description: str = "",
) -> Document:
    """Convert, summarise, and persist a document.

    Steps:
      1. Derive a unique slug from the filename.
      2. If no description was supplied, check content length against num_ctx.
         Raises DocumentTooLongError if content exceeds the context window.
      3. If no description supplied and content is short enough, run AI summary.
      4. Write markdown content to disk.
      5. Insert metadata row into the database.

    Args:
        content:     Full markdown text of the document (post-Markitdown).
        name:        Original filename — used for slug and as description fallback.
        folder_id:   ID of the destination folder (must already exist in DB).
        mime_type:   MIME type of the original file.
        description: Admin-supplied description. Non-empty values bypass length
                     check and AI summary entirely.

    Raises:
        DocumentTooLongError: When content is too long and no description given.
    """
    doc_id = _unique_id(_slugify(name))

    if not description:
        word_count = len(content.split())
        config = load_config()
        if word_count * 2 > config.num_ctx:
            raise DocumentTooLongError(word_count, config.num_ctx)
        description = await _ai_summary(content, name)

    # Write markdown to disk
    doc_dir = get_data_dir() / "documents" / folder_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / f"{doc_id}.md").write_text(content, encoding="utf-8")

    # Persist metadata
    doc = Document(
        id=doc_id,
        folder_id=folder_id,
        name=name,
        description=description,
        mime_type=mime_type,
        created_at=datetime.now(timezone.utc),
    )
    save_document(doc)
    return doc
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_documents.py -v -k "slugify or unique_id or process_document"
```

Expected: 11 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/documents/service.py tests/test_documents.py
git commit -m "feat: add document service with context-length guard and AI summary"
```

---

## Task 5: Document router

**Files:**
- Create: `backend/documents/router.py`
- Test: `tests/test_documents.py` (extend)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_documents.py`:

```python
import io
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def doc_client(config_dir, data_dir, monkeypatch):
    """App-mode TestClient with admin cookie pre-set."""
    monkeypatch.setenv("TROVE_FAKE_OLLAMA", "1")
    monkeypatch.setenv("TROVE_FAKE_SYSTEM", "1")
    from backend.config.service import save_config
    from backend.config.models import TroveConfig
    save_config(TroveConfig(admin_username="admin", admin_password="pass", num_ctx=8192))
    from backend.main import create_app_app
    client = TestClient(create_app_app())
    client.cookies.set("admin_auth", "true")
    return client


def test_list_folders_empty(doc_client):
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


def test_list_documents_empty(doc_client):
    doc_client.post("/api/app/admin/folders", json={"name": "F1"})
    res = doc_client.get("/api/app/admin/documents?folder_id=f1")
    assert res.status_code == 200
    assert res.json() == []


def test_upload_unsupported_extension_returns_422(doc_client):
    doc_client.post("/api/app/admin/folders", json={"name": "F1"})
    file_bytes = b"some content"
    res = doc_client.post(
        "/api/app/admin/documents/upload",
        files={"file": ("report.jpg", io.BytesIO(file_bytes), "image/jpeg")},
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

    with patch("backend.documents.router.MarkItDown", return_value=mock_md), \
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


def test_upload_too_long_returns_needs_description(doc_client, monkeypatch):
    doc_client.post("/api/app/admin/folders", json={"name": "F1"})
    mock_md = MagicMock()
    mock_md.convert.return_value.text_content = "word " * 1000

    with patch("backend.documents.router.MarkItDown", return_value=mock_md), \
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

    with patch("backend.documents.router.MarkItDown", return_value=mock_md), \
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


def test_delete_document_removes_it(doc_client, data_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="d1.txt",
                           description="", mime_type="text/plain", created_at=now))
    # Create the markdown file
    doc_dir = data_dir / "documents" / "f1"
    doc_dir.mkdir(parents=True)
    (doc_dir / "d1.md").write_text("content")

    res = doc_client.delete("/api/app/admin/documents/d1")
    assert res.status_code == 204
    assert not (doc_dir / "d1.md").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_documents.py -v -k "doc_client or folders or documents"
```

Expected: fixture/import errors.

- [ ] **Step 3: Implement the router**

Create `backend/documents/router.py`:

```python
"""FastAPI router for the document library admin API.

All endpoints require admin cookie authentication. Markitdown is imported
inside the upload handlers to keep it out of the module-level import chain
(avoiding slow startup if markitdown has heavy dependencies).
"""
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.app.auth import require_admin_cookie
from backend.db import get_data_dir
from backend.documents.models import Document, Folder
from backend.documents.repository import (
    delete_document,
    delete_folder,
    get_folder,
    list_documents,
    list_folders,
    save_folder,
)
from backend.documents.service import DocumentTooLongError, _slugify, process_document

router = APIRouter(tags=["documents"])

# Extensions accepted for file upload. URL uploads are not extension-checked.
ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {".pdf", ".docx", ".pptx", ".xlsx", ".txt", ".md", ".html", ".htm"}
)


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
    folder = Folder(id=_slugify(req.name) or "folder", name=req.name)
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


# ── Documents ──────────────────────────────────────────────────────────────────

@router.get("/admin/documents", dependencies=[Depends(require_admin_cookie)])
def get_documents(folder_id: str | None = None) -> list[Document]:
    """List all documents, optionally filtered by folder_id."""
    return list_documents(folder_id)


@router.post("/admin/documents/upload", dependencies=[Depends(require_admin_cookie)])
async def upload_document(
    file: UploadFile = File(...),
    folder_id: str = Form(...),
    description: str = Form(""),
) -> dict:
    """Upload a file and process it into the document library.

    The file extension is checked against the supported whitelist.
    Markitdown converts the file to markdown. An AI summary is generated
    unless the document is too long or a description was supplied.

    Returns:
        {"status": "ok", "document": {...}} on success.
        {"status": "needs_description", "word_count": N, "num_ctx": N} when
        the document exceeds the context window and no description was given.
    """
    from markitdown import MarkItDown

    filename = file.filename or "document"
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
        result = MarkItDown().convert(str(tmp_path))
        content = result.text_content
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not process file: {exc}")
    finally:
        tmp_path.unlink(missing_ok=True)

    try:
        doc = await process_document(
            content=content,
            name=filename,
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
    from markitdown import MarkItDown

    try:
        result = MarkItDown().convert(req.url)
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
```

- [ ] **Step 4: Mount the router in `backend/app/router.py`**

At the bottom of `backend/app/router.py`, after the existing `gems_router` include, add:

```python
from backend.documents.router import router as documents_router  # noqa: E402
router.include_router(documents_router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_documents.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/documents/router.py backend/app/router.py tests/test_documents.py
git commit -m "feat: add document library router and mount in app"
```

---

## Task 6: UserTask model + repository changes

**Files:**
- Modify: `backend/tasks/models.py`
- Modify: `backend/tasks/repository.py`
- Test: `tests/test_task_models.py` (extend)
- Test: `tests/test_task_repository.py` (extend)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_task_models.py`:

```python
from backend.tasks.models import UserTask, GemHue


def test_user_task_defaults_to_empty_doc_fields():
    task = UserTask(id="t1", name="T1", template="Hello")
    assert task.doc_folder_ids == ()
    assert task.doc_ids == ()


def test_user_task_accepts_doc_fields():
    task = UserTask(
        id="t1", name="T1", template="Hello",
        doc_folder_ids=("hr", "finance"),
        doc_ids=("policy-doc",),
    )
    assert task.doc_folder_ids == ("hr", "finance")
    assert task.doc_ids == ("policy-doc",)
```

Append to `tests/test_task_repository.py`:

```python
from backend.tasks.models import UserTask
from backend.tasks.repository import save_task, load_task


def test_save_and_load_task_with_doc_fields(data_dir):
    task = UserTask(
        id="t1",
        name="T1",
        template="Hello",
        doc_folder_ids=("hr", "finance"),
        doc_ids=("policy-doc",),
    )
    save_task(task)
    loaded = load_task("t1")
    assert loaded.doc_folder_ids == ("hr", "finance")
    assert loaded.doc_ids == ("policy-doc",)


def test_existing_task_without_doc_fields_loads_with_defaults(data_dir):
    """Tasks saved before doc columns existed default to empty tuples."""
    import sqlite3
    from backend.db import get_db_path
    from backend.tasks.repository import _ensure_table

    # Simulate old-style task without doc columns by inserting directly
    with sqlite3.connect(str(get_db_path())) as conn:
        conn.row_factory = sqlite3.Row
        # Ensure table exists first
        _ensure_table(conn)
        conn.execute(
            "INSERT INTO tasks (id, name, description, hue, template, args, has_image, has_audio, output_mode)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("legacy", "Legacy", "", "indigo", "Hi", "[]", 0, 0, "text"),
        )
        conn.commit()

    loaded = load_task("legacy")
    assert loaded.doc_folder_ids == ()
    assert loaded.doc_ids == ()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_task_models.py tests/test_task_repository.py -v -k "doc_field"
```

Expected: attribute errors (fields don't exist yet).

- [ ] **Step 3: Add fields to `UserTask` in `backend/tasks/models.py`**

In `backend/tasks/models.py`, add to the `UserTask` class (after the `hue` field):

```python
    doc_folder_ids: tuple[str, ...] = ()
    """IDs of folders whose entire contents are accessible to this gem."""
    doc_ids: tuple[str, ...] = ()
    """IDs of individually accessible documents (outside of folder grants)."""
```

- [ ] **Step 4: Update `backend/tasks/repository.py`**

Replace the `_CREATE_TABLE` constant and `_ensure_table` function, and update `_row_to_user_task` and `save_task`:

**Replace `_CREATE_TABLE`:**

```python
_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    hue             TEXT NOT NULL DEFAULT 'indigo',
    template        TEXT NOT NULL,
    args            TEXT NOT NULL,
    has_image       INTEGER NOT NULL DEFAULT 0,
    has_audio       INTEGER NOT NULL DEFAULT 0,
    output_mode     TEXT NOT NULL DEFAULT 'text',
    doc_folder_ids  TEXT NOT NULL DEFAULT '[]',
    doc_ids         TEXT NOT NULL DEFAULT '[]'
)
"""

# ADD COLUMN statements are no-ops on databases that already have the columns.
# SQLite does not support IF NOT EXISTS on ALTER TABLE, so we swallow the error.
_ADD_DOC_COLUMNS = [
    "ALTER TABLE tasks ADD COLUMN doc_folder_ids TEXT NOT NULL DEFAULT '[]'",
    "ALTER TABLE tasks ADD COLUMN doc_ids TEXT NOT NULL DEFAULT '[]'",
]
```

**Replace `_ensure_table`:**

```python
def _ensure_table(conn) -> None:
    """Create the tasks table if it does not exist, then add doc columns if missing."""
    conn.execute(_CREATE_TABLE)
    for stmt in _ADD_DOC_COLUMNS:
        try:
            conn.execute(stmt)
        except Exception:
            pass  # Column already exists — safe to ignore
```

**Replace `_row_to_user_task`:**

```python
def _row_to_user_task(row) -> UserTask:
    """Deserialise a sqlite3.Row into a UserTask, reconstructing the args union."""
    args = tuple(_arg_adapter.validate_python(a) for a in json.loads(row["args"]))
    doc_folder_ids = tuple(json.loads(row["doc_folder_ids"] or "[]"))
    doc_ids = tuple(json.loads(row["doc_ids"] or "[]"))
    return UserTask(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        hue=row["hue"],
        template=row["template"],
        args=args,
        has_image=bool(row["has_image"]),
        has_audio=bool(row["has_audio"]),
        output_mode=row["output_mode"],
        doc_folder_ids=doc_folder_ids,
        doc_ids=doc_ids,
    )
```

**Replace `save_task`:**

```python
def save_task(task: UserTask) -> None:
    """Persist a UserTask to the database.

    Uses INSERT OR REPLACE, so calling save_task() with an existing id
    overwrites the previous record.
    """
    args_json = json.dumps([arg.model_dump() for arg in task.args])
    doc_folder_ids_json = json.dumps(list(task.doc_folder_ids))
    doc_ids_json = json.dumps(list(task.doc_ids))
    with get_db() as conn:
        _ensure_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO tasks
               (id, name, description, hue, template, args,
                has_image, has_audio, output_mode, doc_folder_ids, doc_ids)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task.id,
                task.name,
                task.description,
                task.hue.value,
                task.template,
                args_json,
                int(task.has_image),
                int(task.has_audio),
                task.output_mode.value,
                doc_folder_ids_json,
                doc_ids_json,
            ),
        )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_task_models.py tests/test_task_repository.py -v
```

Expected: all tests pass (including the legacy task test).

- [ ] **Step 6: Commit**

```bash
git add backend/tasks/models.py backend/tasks/repository.py tests/test_task_models.py tests/test_task_repository.py
git commit -m "feat: add doc_folder_ids and doc_ids to UserTask"
```

---

## Task 7: Runner — document tool injection

**Files:**
- Modify: `backend/tasks/runner.py`
- Test: `tests/test_task_runner.py` (extend)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_task_runner.py`:

```python
from datetime import datetime, timezone
from backend.documents.models import Document
from backend.tasks.runner import _build_document_tools


def _make_doc(doc_id: str, folder_id: str = "f1", description: str = "A doc") -> Document:
    return Document(
        id=doc_id, folder_id=folder_id, name=f"{doc_id}.txt",
        description=description, mime_type="text/plain",
        created_at=datetime.now(timezone.utc),
    )


def test_build_document_tools_returns_two_callables():
    tools = _build_document_tools([_make_doc("d1")])
    assert len(tools) == 2
    assert callable(tools[0])
    assert callable(tools[1])


def test_get_table_of_contents_lists_all_docs():
    docs = [
        _make_doc("d1", description="First document."),
        _make_doc("d2", description="Second document."),
    ]
    toc_fn, _ = _build_document_tools(docs)
    result = toc_fn()
    assert "[d1]" in result
    assert "First document." in result
    assert "[d2]" in result
    assert "Second document." in result


def test_get_document_returns_file_content(data_dir):
    doc_dir = data_dir / "documents" / "f1"
    doc_dir.mkdir(parents=True)
    (doc_dir / "d1.md").write_text("# Hello\nThis is the content.")

    _, get_fn = _build_document_tools([_make_doc("d1")])
    result = get_fn("d1")
    assert "This is the content." in result


def test_get_document_out_of_scope_returns_error_string(data_dir):
    _, get_fn = _build_document_tools([_make_doc("d1")])
    result = get_fn("not-in-scope")
    assert "not" in result.lower() or "error" in result.lower()


@pytest.mark.asyncio
async def test_stream_task_with_documents_runs_without_error(data_dir):
    """Documents param accepted — agent runs normally (tool calls not asserted here)."""
    doc = _make_doc("d1")
    task = Task(template="Answer the question")
    agent = Agent(TestModel(custom_output_text="The answer"))
    chunks = []
    async for chunk in stream_task(task, {}, documents=[doc], _agent=agent):
        chunks.append(chunk)
    assert "The answer" in "".join(chunks)


@pytest.mark.asyncio
async def test_run_task_with_documents_runs_without_error(data_dir):
    doc = _make_doc("d1")
    task = Task(template="Answer")
    agent = Agent(TestModel(custom_output_text="42"))
    result = await run_task(task, {}, documents=[doc], _agent=agent)
    assert result == "42"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_task_runner.py -v -k "document_tools or documents"
```

Expected: `ImportError` on `_build_document_tools`.

- [ ] **Step 3: Update `backend/tasks/runner.py`**

Add `from __future__ import annotations` at the top (to allow `list[Document]` annotation without a circular import at module load):

```python
from __future__ import annotations
```

Add the following imports (after existing imports):

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.documents.models import Document
```

Replace `_default_agent` with `_make_agent` and add `_build_document_tools`:

```python
_DOC_SYSTEM_PROMPT = (
    "You have access to a document library. "
    "Call get_table_of_contents() to see what is available, "
    "then get_document(id) to read a specific document."
)


def _build_document_tools(documents: list[Document]) -> list:
    """Create the two document-access tool functions for a gem run.

    Returns a list of two plain callables:
      [0] get_table_of_contents() → str
      [1] get_document(doc_id: str) → str

    Both close over the permitted document list so they can enforce
    access control and read from the correct filesystem paths.

    Args:
        documents: The full list of documents accessible to this run.
    """
    from backend.db import get_data_dir

    doc_map = {doc.id: doc for doc in documents}
    data_dir = get_data_dir()

    def get_table_of_contents() -> str:
        """Return a list of all accessible documents with their one-line descriptions."""
        lines = [
            f"[{doc.id}] {doc.name} — {doc.description}"
            for doc in documents
        ]
        return "\n".join(lines)

    def get_document(doc_id: str) -> str:
        """Return the full markdown content of a document by its ID."""
        if doc_id not in doc_map:
            return (
                f"Error: document '{doc_id}' is not in the permitted document set. "
                f"Call get_table_of_contents() to see available documents."
            )
        doc = doc_map[doc_id]
        path = data_dir / "documents" / doc.folder_id / f"{doc.id}.md"
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            return f"Error: could not read document '{doc_id}': {exc}"

    return [get_table_of_contents, get_document]


def _make_agent(documents: list[Document] | None = None) -> Agent:
    """Create a Pydantic AI Agent backed by the local trove_model Ollama model.

    When documents are provided, the agent is configured with two tool functions
    (get_table_of_contents and get_document) and a system prompt instructing the
    model to use them.

    Args:
        documents: Documents in scope for this run. None or empty → no tools injected.
    """
    model = OpenAIChatModel(
        "trove_model",
        provider=OllamaProvider(base_url=_OLLAMA_BASE_URL),
    )
    if not documents:
        return Agent(model)
    tools = _build_document_tools(documents)
    return Agent(model, tools=tools, system_prompt=_DOC_SYSTEM_PROMPT)
```

Remove the old `_default_agent` function entirely.

Update `stream_task` signature and replace `_default_agent()` call:

```python
async def stream_task(
    task: Task,
    values: dict[str, str],
    *,
    media: MediaInput | None = None,
    documents: list[Document] | None = None,
    _agent: Agent | None = None,
) -> AsyncIterator[str]:
    """
    Stream text tokens for a task, filtering out thinking tokens.

    Args:
        task: The task to run (Task or UserTask).
        values: Argument values keyed by arg name.
        media: Optional image and/or audio bytes to include in the message.
        documents: Documents accessible to this run. When non-empty, two tool
                   functions are injected into the agent.
        _agent: Optional Agent override for testing without a real Ollama instance.

    Yields:
        Filtered text chunks suitable for streaming to the client.
    """
    prompt = render_prompt(task, values)
    parts = _build_parts(prompt, media)
    agent = _agent or _make_agent(documents)
    filt = _ThinkFilter()

    async with agent.run_stream(parts) as response:
        async for chunk in response.stream_text(delta=True):
            filtered = filt.feed(chunk)
            if filtered:
                yield filtered

    tail = filt.flush()
    if tail:
        yield tail
```

Update `run_task` signature and replace `_default_agent()` call:

```python
async def run_task(
    task: Task,
    values: dict[str, str],
    *,
    media: MediaInput | None = None,
    documents: list[Document] | None = None,
    _agent: Agent | None = None,
) -> str:
    """
    Run a task and return the complete response string.

    Strips thinking tokens from the final response using a regex (safe because
    the full string is available). Used for structured output and internal tasks
    where partial streaming is not appropriate.

    Args:
        task: The task to run (Task or UserTask).
        values: Argument values keyed by arg name.
        media: Optional image and/or audio bytes to include in the message.
        documents: Documents accessible to this run. When non-empty, two tool
                   functions are injected into the agent.
        _agent: Optional Agent override for testing.

    Returns:
        The complete response with thinking tokens removed and whitespace stripped.
    """
    prompt = render_prompt(task, values)
    parts = _build_parts(prompt, media)
    agent = _agent or _make_agent(documents)
    result = await agent.run(parts)
    text: str = result.output
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_task_runner.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/tasks/runner.py tests/test_task_runner.py
git commit -m "feat: inject document tools into agent when documents are in scope"
```

---

## Task 8: Run endpoint — resolve documents

**Files:**
- Modify: `backend/tasks/router.py`
- Test: `tests/test_gems_router.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_gems_router.py`:

```python
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from backend.documents.models import Document
from backend.documents.repository import save_folder, save_document
from backend.documents.models import Folder


def _make_sample_doc(doc_id: str, folder_id: str = "f1") -> Document:
    return Document(
        id=doc_id, folder_id=folder_id, name=f"{doc_id}.txt",
        description="A test doc", mime_type="text/plain",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def gem_with_docs(data_dir):
    """A gem that has doc access, plus the corresponding DB records."""
    save_folder(Folder(id="f1", name="F1"))
    save_document(_make_sample_doc("d1"))
    task = UserTask(
        id="doc-gem",
        name="Doc Gem",
        template="Use docs",
        doc_folder_ids=("f1",),
    )
    save_task(task)
    return task


def test_run_gem_resolves_documents_and_passes_to_stream(authed_client, gem_with_docs):
    """When a gem has doc_folder_ids, stream_task receives the resolved documents."""
    captured = {}

    async def fake_stream(task, values, *, media=None, documents=None):
        captured["documents"] = documents
        yield "ok"

    with patch("backend.tasks.router.stream_task", side_effect=fake_stream):
        res = authed_client.post(
            f"/api/app/gems/doc-gem/run",
            json={"values": {}},
        )
    assert res.status_code == 200
    assert captured.get("documents") is not None
    assert any(d.id == "d1" for d in captured["documents"])
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
pytest tests/test_gems_router.py::test_run_gem_resolves_documents_and_passes_to_stream -v
```

Expected: FAIL — `stream_task` currently called without `documents`.

- [ ] **Step 3: Update the run endpoint in `backend/tasks/router.py`**

Add the import at the top of the file (with the other imports):

```python
from backend.documents.repository import resolve_documents
```

In the `run_gem` endpoint, after `media = _decode_media(req)`, add document resolution:

```python
    # Resolve document access for this gem
    documents = resolve_documents(
        list(gem.doc_folder_ids),
        list(gem.doc_ids),
    ) if (gem.doc_folder_ids or gem.doc_ids) else None
```

Then update the `stream_task` call inside `sse_generator` to pass `documents`:

```python
    async def sse_generator() -> AsyncIterator[str]:
        """Wrap stream_task tokens as SSE data lines."""
        try:
            async for chunk in stream_task(gem, req.values, media=media, documents=documents):
                yield f"data: {chunk}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {exc}\n\n"
        yield "data: [DONE]\n\n"
```

- [ ] **Step 4: Run all tests**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/tasks/router.py tests/test_gems_router.py
git commit -m "feat: resolve and pass documents to stream_task in run endpoint"
```
