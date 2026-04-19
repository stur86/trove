# Import / Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add full bundle export/import (gems + documents as a ZIP), per-folder and per-document downloads, and replace the manual checkbox tree in GemForm with `react-checkbox-tree`.

**Architecture:** A new `backend/bundle/` domain owns the ZIP serialisation and import logic; two download endpoints are added to the existing documents router. The frontend gains a Data section in the Settings tab (export button + import modal), download icon buttons in DocumentsPanel, and a `react-checkbox-tree` component in GemForm that replaces the hand-rolled tree.

**Tech Stack:** Python `zipfile` + `io` (standard library) for ZIP; Pydantic for bundle models; `react-checkbox-tree` + `@types/react-checkbox-tree` on the frontend.

---

## File map

**New files:**
- `backend/bundle/__init__.py` — empty module marker
- `backend/bundle/models.py` — `BundleManifest`, `ImportMode`, `ImportResult`
- `backend/bundle/service.py` — `export_bundle()`, `import_bundle()`
- `backend/bundle/router.py` — GET `/admin/bundle/export`, POST `/admin/bundle/import`
- `tests/test_bundle.py` — service and router tests
- `frontend/src/api/bundle.ts` — `bundleApi` client

**Modified files:**
- `backend/tasks/repository.py` — add `task_id_exists()`
- `backend/documents/router.py` — add folder + document download endpoints
- `backend/app/router.py` — wire in `bundle_router`
- `tests/test_documents.py` — add download endpoint tests
- `frontend/src/api/client.ts` — add `getBlob()` and `postFormData()`
- `frontend/src/api/documents.ts` — add `downloadFolder()` and `downloadDocument()`
- `frontend/src/api/mock/documents.ts` — add no-op stubs for download methods
- `frontend/src/pages/AdminPanel.tsx` — Data section + import modal in Settings tab
- `frontend/src/pages/DocumentsPanel.tsx` — download icon buttons per folder and document
- `frontend/src/pages/GemForm.tsx` — replace manual tree with `react-checkbox-tree`

---

## Task 1: Install react-checkbox-tree

**Files:**
- Modify: `frontend/package.json` (via bun)
- Modify: `frontend/bun.lock` (via bun)

- [ ] **Step 1: Install the package and its types**

```bash
cd frontend && bun add react-checkbox-tree && bun add -D @types/react-checkbox-tree
```

Expected output: `installed react-checkbox-tree@...` — no errors.

- [ ] **Step 2: Verify TypeScript can see the types**

```bash
cd frontend && bun run build 2>&1 | grep -i error || echo "OK"
```

Expected: `OK` (build succeeds).

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/bun.lock
git commit -m "chore: install react-checkbox-tree"
```

---

## Task 2: Add `task_id_exists` to tasks/repository.py

**Files:**
- Modify: `backend/tasks/repository.py`
- Modify: `tests/test_task_repository.py`

- [ ] **Step 1: Write the failing test**

Open `tests/test_task_repository.py` and add at the end:

```python
from backend.tasks.repository import task_id_exists  # add to existing import at top

def test_task_id_exists_false_when_absent(data_dir):
    assert task_id_exists("nonexistent") is False


def test_task_id_exists_true_when_present(data_dir):
    from backend.tasks.models import UserTask, GemHue, OutputMode
    task = UserTask(
        id="my-gem", name="My Gem", template="hi",
        hue=GemHue.INDIGO, output_mode=OutputMode.TEXT,
    )
    save_task(task)
    assert task_id_exists("my-gem") is True
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_task_repository.py::test_task_id_exists_false_when_absent -v
```

Expected: `FAILED` — `ImportError: cannot import name 'task_id_exists'`.

- [ ] **Step 3: Implement in `backend/tasks/repository.py`**

Add after `delete_task`:

```python
def task_id_exists(task_id: str) -> bool:
    """Return True if a task with the given id already exists in the database."""
    with get_db() as conn:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT 1 FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    return row is not None
```

Also add `task_id_exists` to the import in the test file (already done in Step 1).

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_task_repository.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/tasks/repository.py tests/test_task_repository.py
git commit -m "feat: add task_id_exists to tasks repository"
```

---

## Task 3: Create `backend/bundle/` domain — models

**Files:**
- Create: `backend/bundle/__init__.py`
- Create: `backend/bundle/models.py`

- [ ] **Step 1: Create the empty package marker**

Create `backend/bundle/__init__.py` with contents:

```python
"""Bundle export/import domain for Trove."""
```

- [ ] **Step 2: Write the models**

Create `backend/bundle/models.py`:

```python
"""Pydantic models for the Trove bundle export/import format.

The bundle is a ZIP file containing:
  - manifest.json: all metadata (folders, documents, gems) as JSON
  - documents/<folder_id>/<doc_id>.md: converted markdown content per document

BundleManifest is the authoritative representation of manifest.json.
ImportResult is returned by import_bundle() to summarise what changed.
"""
from enum import Enum

from pydantic import BaseModel


class BundleFolder(BaseModel, frozen=True):
    """Folder entry in the bundle manifest."""

    id: str
    name: str


class BundleDocument(BaseModel, frozen=True):
    """Document metadata entry in the bundle manifest.

    The corresponding markdown content is stored at
    documents/<folder_id>/<id>.md inside the ZIP.
    """

    id: str
    folder_id: str
    name: str
    description: str
    mime_type: str
    created_at: str
    """ISO 8601 timestamp string — preserved verbatim from the original."""


class BundleGem(BaseModel, frozen=True):
    """Gem (UserTask) entry in the bundle manifest.

    Args are stored as raw dicts — the discriminated union is reconstructed
    at import time via Pydantic's TypeAdapter.
    """

    id: str
    name: str
    description: str
    hue: str
    template: str
    args: list[dict]
    has_image: bool
    has_audio: bool
    output_mode: str
    doc_folder_ids: list[str]
    doc_ids: list[str]


class BundleManifest(BaseModel, frozen=True):
    """Top-level manifest written as manifest.json inside the bundle ZIP."""

    version: int = 1
    exported_at: str
    """ISO 8601 timestamp of when the bundle was created."""
    folders: list[BundleFolder]
    documents: list[BundleDocument]
    gems: list[BundleGem]


class ImportMode(str, Enum):
    """Controls how imported items are merged with existing data."""

    REPLACE = "replace"
    """Wipe all existing gems, documents, and folders before importing."""
    ADD = "add"
    """Import new items alongside existing ones; rename on ID collision."""


class ImportResult(BaseModel):
    """Summary of what changed during a bundle import operation."""

    folders_created: int
    """Number of folders created (Add mode: skips existing; Replace: always all)."""
    documents_imported: int
    """Total number of documents written (including renamed ones)."""
    documents_renamed: dict[str, str]
    """Mapping of original doc ID → new ID for any renamed documents (Add mode)."""
    gems_imported: int
    """Total number of gems written (including renamed ones)."""
    gems_renamed: dict[str, str]
    """Mapping of original gem ID → new ID for any renamed gems (Add mode)."""
```

- [ ] **Step 3: Verify the module imports cleanly**

```bash
python -c "from backend.bundle.models import BundleManifest, ImportMode, ImportResult; print('OK')"
```

Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add backend/bundle/__init__.py backend/bundle/models.py
git commit -m "feat: add bundle domain models"
```

---

## Task 4: `bundle/service.py` — `export_bundle()`

**Files:**
- Create: `backend/bundle/service.py`
- Create: `tests/test_bundle.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_bundle.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_bundle.py::test_export_bundle_is_valid_zip -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'backend.bundle.service'`.

- [ ] **Step 3: Implement `export_bundle` in `backend/bundle/service.py`**

Create `backend/bundle/service.py`:

```python
"""Bundle export and import service for Trove.

export_bundle() — serialise all gems, folders, and documents into an
                  in-memory ZIP and return the raw bytes.
import_bundle() — parse a ZIP produced by export_bundle() and reconstruct
                  data in two modes:
                    REPLACE: wipe existing data, then import everything.
                    ADD:     import alongside existing data, renaming on
                             any ID collision and rewriting gem references.
"""
import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from backend.bundle.models import (
    BundleDocument,
    BundleFolder,
    BundleGem,
    BundleManifest,
    ImportMode,
    ImportResult,
)
from backend.db import get_data_dir
from backend.documents.models import Document, Folder
from backend.documents.repository import (
    delete_folder,
    document_id_exists,
    get_folder,
    list_documents,
    list_folders,
    save_document,
    save_folder,
)
from backend.tasks.models import GemHue, OutputMode, TaskArg, UserTask
from backend.tasks.repository import (
    delete_task,
    list_tasks,
    save_task,
    task_id_exists,
)
from pydantic import TypeAdapter

_arg_adapter: TypeAdapter[TaskArg] = TypeAdapter(TaskArg)


# ── Export ────────────────────────────────────────────────────────────────────

def export_bundle() -> bytes:
    """Build an in-memory ZIP bundle of all gems, folders, and documents.

    The ZIP contains:
      - manifest.json: all metadata as JSON.
      - documents/<folder_id>/<doc_id>.md: one file per document.

    Returns:
        Raw ZIP bytes suitable for streaming as a file download.
    """
    folders = list_folders()
    documents = list_documents()
    gems = list_tasks()
    data_dir = get_data_dir()

    manifest = BundleManifest(
        version=1,
        exported_at=datetime.now(timezone.utc).isoformat(),
        folders=[BundleFolder(id=f.id, name=f.name) for f in folders],
        documents=[
            BundleDocument(
                id=d.id,
                folder_id=d.folder_id,
                name=d.name,
                description=d.description,
                mime_type=d.mime_type,
                created_at=d.created_at.isoformat(),
            )
            for d in documents
        ],
        gems=[
            BundleGem(
                id=g.id,
                name=g.name,
                description=g.description,
                hue=g.hue.value,
                template=g.template,
                args=[arg.model_dump() for arg in g.args],
                has_image=g.has_image,
                has_audio=g.has_audio,
                output_mode=g.output_mode.value,
                doc_folder_ids=list(g.doc_folder_ids),
                doc_ids=list(g.doc_ids),
            )
            for g in gems
        ],
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", manifest.model_dump_json(indent=2))
        for doc in documents:
            md_path = data_dir / "documents" / doc.folder_id / f"{doc.id}.md"
            if md_path.exists():
                zf.writestr(
                    f"documents/{doc.folder_id}/{doc.id}.md",
                    md_path.read_text(encoding="utf-8"),
                )

    return buf.getvalue()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_bundle.py -k "export" -v
```

Expected: all four export tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/bundle/service.py tests/test_bundle.py
git commit -m "feat: implement export_bundle()"
```

---

## Task 5: `import_bundle()` — Replace mode

**Files:**
- Modify: `backend/bundle/service.py`
- Modify: `tests/test_bundle.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_bundle.py`:

```python
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_bundle.py -k "replace" -v
```

Expected: `FAILED` — `ImportError` (import_bundle not defined yet).

- [ ] **Step 3: Add private helpers and Replace-mode import to `backend/bundle/service.py`**

Append to `backend/bundle/service.py`, after `export_bundle`:

```python
# ── Private helpers ───────────────────────────────────────────────────────────

def _unique_doc_id(base: str) -> str:
    """Return base if unused as a document ID, else base-2, base-3, …"""
    if not document_id_exists(base):
        return base
    n = 2
    while document_id_exists(f"{base}-{n}"):
        n += 1
    return f"{base}-{n}"


def _unique_task_id(base: str) -> str:
    """Return base if unused as a task ID, else base-2, base-3, …"""
    if not task_id_exists(base):
        return base
    n = 2
    while task_id_exists(f"{base}-{n}"):
        n += 1
    return f"{base}-{n}"


def _bundle_gem_to_user_task(
    bg: BundleGem,
    doc_renames: dict[str, str],
    new_id: str,
) -> UserTask:
    """Convert a BundleGem to a UserTask, applying doc_id renames.

    Args:
        bg:          The BundleGem from the manifest.
        doc_renames: Mapping of original doc ID → new ID from Add-mode renaming.
        new_id:      The (possibly renamed) task ID to assign.

    Returns:
        A fully-constructed UserTask ready for save_task().
    """
    args = tuple(_arg_adapter.validate_python(a) for a in bg.args)
    new_doc_ids = tuple(doc_renames.get(did, did) for did in bg.doc_ids)
    return UserTask(
        id=new_id,
        name=bg.name,
        description=bg.description,
        hue=GemHue(bg.hue),
        template=bg.template,
        args=args,
        has_image=bg.has_image,
        has_audio=bg.has_audio,
        output_mode=OutputMode(bg.output_mode),
        doc_folder_ids=tuple(bg.doc_folder_ids),
        doc_ids=new_doc_ids,
    )


def _wipe_all(data_dir: Path) -> None:
    """Delete all gems, document .md files, document DB rows, and folder DB rows.

    Processes gems first, then documents+folders so foreign key order is respected.
    """
    for task in list_tasks():
        delete_task(task.id)

    for folder in list_folders():
        folder_dir = data_dir / "documents" / folder.id
        for doc in list_documents(folder.id):
            (folder_dir / f"{doc.id}.md").unlink(missing_ok=True)
        try:
            folder_dir.rmdir()
        except OSError:
            pass
        # delete_folder() removes all document rows then the folder row
        delete_folder(folder.id)


def _write_document(
    bd: BundleDocument,
    new_id: str,
    content: str,
    data_dir: Path,
) -> None:
    """Write a document's .md file and save its DB row."""
    doc_dir = data_dir / "documents" / bd.folder_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / f"{new_id}.md").write_text(content, encoding="utf-8")
    save_document(Document(
        id=new_id,
        folder_id=bd.folder_id,
        name=bd.name,
        description=bd.description,
        mime_type=bd.mime_type,
        created_at=datetime.fromisoformat(bd.created_at),
    ))


# ── Import ────────────────────────────────────────────────────────────────────

def import_bundle(zip_bytes: bytes, mode: ImportMode) -> ImportResult:
    """Parse and import a bundle ZIP produced by export_bundle().

    Args:
        zip_bytes: Raw bytes of the ZIP file.
        mode:      REPLACE wipes existing data first; ADD merges with renaming.

    Returns:
        ImportResult with counts and rename maps.

    Raises:
        zipfile.BadZipFile: If zip_bytes is not a valid ZIP.
        KeyError:           If manifest.json is missing from the archive.
    """
    data_dir = get_data_dir()
    buf = io.BytesIO(zip_bytes)

    with zipfile.ZipFile(buf, "r") as zf:
        manifest = BundleManifest.model_validate_json(zf.read("manifest.json"))
        namelist = set(zf.namelist())

        if mode == ImportMode.REPLACE:
            _wipe_all(data_dir)

            for bf in manifest.folders:
                save_folder(Folder(id=bf.id, name=bf.name))

            for bd in manifest.documents:
                md_key = f"documents/{bd.folder_id}/{bd.id}.md"
                content = zf.read(md_key).decode("utf-8") if md_key in namelist else ""
                _write_document(bd, bd.id, content, data_dir)

            for bg in manifest.gems:
                save_task(_bundle_gem_to_user_task(bg, {}, bg.id))

            return ImportResult(
                folders_created=len(manifest.folders),
                documents_imported=len(manifest.documents),
                documents_renamed={},
                gems_imported=len(manifest.gems),
                gems_renamed={},
            )

        else:  # ADD
            return _import_add(manifest, zf, namelist, data_dir)


def _import_add(
    manifest: BundleManifest,
    zf: zipfile.ZipFile,
    namelist: set[str],
    data_dir: Path,
) -> ImportResult:
    """Import bundle in Add mode: merge with existing data, rename on collision."""
    folders_created = 0
    doc_renames: dict[str, str] = {}
    gem_renames: dict[str, str] = {}

    # Step 1: Folders — create if absent; skip (keep existing) if ID taken
    for bf in manifest.folders:
        try:
            get_folder(bf.id)
        except KeyError:
            save_folder(Folder(id=bf.id, name=bf.name))
            folders_created += 1

    # Step 2: Documents — import with rename on collision
    for bd in manifest.documents:
        new_id = _unique_doc_id(bd.id)
        if new_id != bd.id:
            doc_renames[bd.id] = new_id
        md_key = f"documents/{bd.folder_id}/{bd.id}.md"
        content = zf.read(md_key).decode("utf-8") if md_key in namelist else ""
        _write_document(bd, new_id, content, data_dir)

    # Step 3: Gems — rewrite doc_ids using renames, rename gem ID on collision
    for bg in manifest.gems:
        new_id = _unique_task_id(bg.id)
        if new_id != bg.id:
            gem_renames[bg.id] = new_id
        save_task(_bundle_gem_to_user_task(bg, doc_renames, new_id))

    return ImportResult(
        folders_created=folders_created,
        documents_imported=len(manifest.documents),
        documents_renamed=doc_renames,
        gems_imported=len(manifest.gems),
        gems_renamed=gem_renames,
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_bundle.py -k "replace" -v
```

Expected: all four Replace-mode tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/bundle/service.py tests/test_bundle.py
git commit -m "feat: implement import_bundle() replace mode"
```

---

## Task 6: `import_bundle()` — Add mode with collision handling

**Files:**
- Modify: `tests/test_bundle.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_bundle.py`:

```python
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
```

- [ ] **Step 2: Run all bundle tests**

The `_import_add` function was fully implemented in Task 5's service code. These tests
exercise its collision-handling paths, so they should pass immediately.

```bash
pytest tests/test_bundle.py -v
```

Expected: all tests pass, including the new Add-mode collision tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_bundle.py
git commit -m "test: add import_bundle Add-mode tests"
```

---

## Task 7: `bundle/router.py` and router tests

**Files:**
- Create: `backend/bundle/router.py`
- Modify: `tests/test_bundle.py`

- [ ] **Step 1: Write the failing router tests**

Append to `tests/test_bundle.py`:

```python
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_bundle.py -k "endpoint" -v
```

Expected: `FAILED` — routes not found (router not yet created or wired).

- [ ] **Step 3: Create `backend/bundle/router.py`**

```python
"""FastAPI router for bundle export/import.

Mounted at /api/app via backend.app.router. All endpoints require
the admin cookie set by POST /api/app/admin/login.
"""
import io
import zipfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from backend.app.auth import require_admin_cookie
from backend.bundle.models import ImportMode, ImportResult
from backend.bundle.service import export_bundle, import_bundle

router = APIRouter(tags=["bundle"])


@router.get("/admin/bundle/export", dependencies=[Depends(require_admin_cookie)])
def bundle_export() -> Response:
    """Export all gems and documents as a downloadable ZIP bundle.

    The archive contains manifest.json and one .md file per document.
    Requires admin cookie.
    """
    zip_bytes = export_bundle()
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="trove-bundle.zip"'},
    )


@router.post("/admin/bundle/import", dependencies=[Depends(require_admin_cookie)])
async def bundle_import(
    file: UploadFile = File(...),
    mode: str = Form("add"),
) -> ImportResult:
    """Import a bundle ZIP, merging or replacing existing data.

    Args:
        file: The ZIP bundle produced by the export endpoint.
        mode: 'add' (default) or 'replace'. Invalid values return 422.

    Returns:
        ImportResult with counts and rename maps.

    Requires admin cookie.
    """
    try:
        import_mode = ImportMode(mode)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid mode '{mode}'. Must be 'add' or 'replace'.",
        )
    zip_bytes = await file.read()
    try:
        return import_bundle(zip_bytes, import_mode)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=422, detail="Uploaded file is not a valid ZIP archive.")
    except KeyError as e:
        raise HTTPException(status_code=422, detail=f"Bundle is missing required entry: {e}")
```

- [ ] **Step 4: Run tests — they will still fail (router not wired yet)**

```bash
pytest tests/test_bundle.py -k "endpoint" -v
```

Expected: still `FAILED` — routes return 404 because the router isn't mounted yet.

---

## Task 8: Wire bundle router into `backend/app/router.py`

**Files:**
- Modify: `backend/app/router.py`

- [ ] **Step 1: Add the import and include_router call**

In `backend/app/router.py`, add after the existing sub-router imports at the top:

```python
from backend.bundle.router import router as bundle_router          # noqa: E402
```

And at the bottom, after `router.include_router(documents_router)`:

```python
router.include_router(bundle_router)
```

- [ ] **Step 2: Run all bundle tests**

```bash
pytest tests/test_bundle.py -v
```

Expected: all tests pass.

- [ ] **Step 3: Run the full test suite to check for regressions**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/bundle/router.py backend/app/router.py tests/test_bundle.py
git commit -m "feat: add bundle export/import router and wire into app"
```

---

## Task 9: Document download endpoints

**Files:**
- Modify: `backend/documents/router.py`
- Modify: `tests/test_documents.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_documents.py`:

```python
# ── Download endpoints (Task 9) ───────────────────────────────────────────────

def test_download_folder_returns_zip(doc_client, data_dir):
    doc_client.post("/api/app/admin/folders", json={"name": "My Folder"})
    # Insert a document and its .md file
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="my-folder", name="My Folder"))
    save_document(Document(id="d1", folder_id="my-folder", name="d1.txt",
                           description="", mime_type="text/plain", created_at=now))
    md_dir = data_dir / "documents" / "my-folder"
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


def test_download_document_returns_markdown(doc_client, data_dir):
    now = datetime.now(timezone.utc)
    save_folder(Folder(id="f1", name="F1"))
    save_document(Document(id="d1", folder_id="f1", name="d1.txt",
                           description="", mime_type="text/plain", created_at=now))
    md_dir = data_dir / "documents" / "f1"
    md_dir.mkdir(parents=True, exist_ok=True)
    (md_dir / "d1.md").write_text("# Document")

    res = doc_client.get("/api/app/admin/documents/d1/download")
    assert res.status_code == 200
    assert "text/markdown" in res.headers["content-type"]
    assert res.content == b"# Document"


def test_download_document_not_found(doc_client):
    res = doc_client.get("/api/app/admin/documents/missing/download")
    assert res.status_code == 404
```

Also add `import zipfile` and `import io` at the top of `tests/test_documents.py` if not already present. The file already imports `import io` — add `import zipfile`:

```python
import zipfile  # add after `import io`
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_documents.py -k "download" -v
```

Expected: `FAILED` — routes return 404.

- [ ] **Step 3: Add the download endpoints to `backend/documents/router.py`**

Add `import io` and `import zipfile` at the top of `backend/documents/router.py` (after `import tempfile`):

```python
import io
import zipfile
```

Add `Response` to the FastAPI import line:

```python
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
```

Add these two endpoints after the `remove_folder` endpoint (before the Documents section):

```python
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
```

Add this endpoint after the `remove_document` endpoint (before `UpdateDocumentRequest`):

```python
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
```

- [ ] **Step 4: Run the download tests**

```bash
pytest tests/test_documents.py -k "download" -v
```

Expected: all four download tests pass.

- [ ] **Step 5: Run the full test suite**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/documents/router.py tests/test_documents.py
git commit -m "feat: add per-folder and per-document download endpoints"
```

---

## Task 10: Frontend — `client.ts` helpers and `bundle.ts` API client

**Files:**
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/api/bundle.ts`

- [ ] **Step 1: Add `getBlob` and `postFormData` to `client.ts`**

In `frontend/src/api/client.ts`, append after the `del` function:

```typescript
/**
 * Make a GET request and return the response as a Blob (for file downloads).
 * Handles session injection and 401 retry identically to get().
 * @param path API path (e.g. "/app/admin/bundle/export")
 */
export async function getBlob(path: string): Promise<Blob> {
  const res = await apiRequest(`${BASE}${path}`, {})
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.blob()
}

/**
 * Make a POST request with a FormData body (for multipart file uploads).
 * Does NOT set Content-Type — the browser sets it automatically with the boundary.
 * @param path API path
 * @param form FormData to send
 */
export async function postFormData(path: string, form: FormData): Promise<Response> {
  const res = await apiRequest(`${BASE}${path}`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
  return res
}
```

- [ ] **Step 2: Create `frontend/src/api/bundle.ts`**

```typescript
/**
 * API client for bundle export/import.
 *
 * exportBundle()  — downloads all gems and documents as a ZIP blob.
 * importBundle()  — POSTs a ZIP file to the import endpoint.
 */
import { getBlob, postFormData } from './client'

/** Summary returned by the backend after a bundle import. */
export interface ImportResult {
  folders_created: number
  documents_imported: number
  /** Map of original doc ID → renamed ID (only populated in Add mode). */
  documents_renamed: Record<string, string>
  gems_imported: number
  /** Map of original gem ID → renamed ID (only populated in Add mode). */
  gems_renamed: Record<string, string>
}

export type ImportMode = 'add' | 'replace'

export const bundleApi = {
  /**
   * Fetch the full bundle ZIP from the server.
   * Returns a Blob; the caller is responsible for triggering the download.
   */
  exportBundle: (): Promise<Blob> =>
    getBlob('/app/admin/bundle/export'),

  /**
   * Upload a bundle ZIP for import.
   *
   * @param file The ZIP file chosen by the admin.
   * @param mode 'add' merges with existing data (renaming on collision);
   *             'replace' wipes existing data first.
   */
  importBundle: async (file: File, mode: ImportMode): Promise<ImportResult> => {
    const form = new FormData()
    form.append('file', file)
    form.append('mode', mode)
    const res = await postFormData('/app/admin/bundle/import', form)
    return res.json()
  },
}
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && bun run build 2>&1 | grep -i error || echo "OK"
```

Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/bundle.ts
git commit -m "feat: add bundle API client and getBlob/postFormData helpers"
```

---

## Task 11: Frontend — `documents.ts` download methods + mock stubs

**Files:**
- Modify: `frontend/src/api/documents.ts`
- Modify: `frontend/src/api/mock/documents.ts`

- [ ] **Step 1: Add helper and download methods to `documents.ts`**

In `frontend/src/api/documents.ts`, add the import for `getBlob` at the top:

```typescript
import { del, get, getBlob, patch, post } from './client'
```

Add a module-level helper before `_realDocumentsApi`:

```typescript
/**
 * Trigger a browser file download from a Blob without navigating away.
 * Creates a temporary <a> element, clicks it, then revokes the object URL.
 */
function _triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
```

Add two methods inside `_realDocumentsApi` after `deleteDocument`:

```typescript
  /** Download all documents in a folder as a ZIP of .md files. */
  downloadFolder: async (folderId: string): Promise<void> => {
    const blob = await getBlob(`/app/admin/folders/${folderId}/download`)
    _triggerDownload(blob, `${folderId}.zip`)
  },

  /** Download a single document as its converted markdown file. */
  downloadDocument: async (docId: string): Promise<void> => {
    const blob = await getBlob(`/app/admin/documents/${docId}/download`)
    _triggerDownload(blob, `${docId}.md`)
  },
```

- [ ] **Step 2: Add no-op stubs to `mock/documents.ts`**

In `frontend/src/api/mock/documents.ts`, append after `deleteDocument`:

```typescript
  downloadFolder: async (_folderId: string): Promise<void> => {
    await delay()
    // No-op in mock mode — no real files to download.
  },

  downloadDocument: async (_docId: string): Promise<void> => {
    await delay()
    // No-op in mock mode — no real files to download.
  },
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && bun run build 2>&1 | grep -i error || echo "OK"
```

Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/documents.ts frontend/src/api/mock/documents.ts
git commit -m "feat: add folder and document download methods to documents API client"
```

---

## Task 12: Frontend — AdminPanel Settings tab Data section

**Files:**
- Modify: `frontend/src/pages/AdminPanel.tsx`

- [ ] **Step 1: Add imports**

In `AdminPanel.tsx`, add to the flowbite-react import line:

```typescript
import { Alert, Button, Label, Modal, ModalBody, ModalFooter, ModalHeader, Select, Spinner, TabItem, Tabs, RangeSlider } from 'flowbite-react'
```

Add the bundle API import after the existing API imports:

```typescript
import { bundleApi, type ImportResult } from '../api/bundle'
```

- [ ] **Step 2: Add state variables**

Inside the `AdminPanel` component, after the existing state declarations, add:

```typescript
// Bundle export/import state
const [exporting, setExporting] = useState(false)
const [showImportModal, setShowImportModal] = useState(false)
const [importFile, setImportFile] = useState<File | null>(null)
const [importMode, setImportMode] = useState<'add' | 'replace'>('add')
const [importing, setImporting] = useState(false)
const [importResult, setImportResult] = useState<ImportResult | null>(null)
const [importError, setImportError] = useState<string | null>(null)
```

- [ ] **Step 3: Add handler functions**

Inside the component, after `handleSave`, add:

```typescript
/** Fetch the bundle ZIP from the server and trigger a browser download. */
async function handleExport() {
  setExporting(true)
  try {
    const blob = await bundleApi.exportBundle()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'trove-bundle.zip'
    a.click()
    URL.revokeObjectURL(url)
  } finally {
    setExporting(false)
  }
}

/** POST the chosen ZIP file to the import endpoint. */
async function handleImport() {
  if (!importFile) return
  setImporting(true)
  setImportError(null)
  setImportResult(null)
  try {
    const result = await bundleApi.importBundle(importFile, importMode)
    setImportResult(result)
  } catch (e) {
    setImportError(String(e))
  } finally {
    setImporting(false)
  }
}
```

- [ ] **Step 4: Add the Data section JSX inside the Settings tab**

In the Settings tab JSX, after the closing `</div>` of the build log block and before the closing `</div>` of the Settings tab content, add:

```tsx
{/* Data section — export and import bundle */}
<div className="border-t border-gray-200 pt-6 flex flex-col gap-4">
  <Label className="text-base font-semibold text-gray-800">Data</Label>
  <div className="flex gap-3">
    <Button color="light" disabled={exporting} onClick={handleExport}>
      {exporting ? <><Spinner size="sm" className="mr-2" />Exporting…</> : 'Export bundle'}
    </Button>
    <Button color="light" onClick={() => {
      setImportFile(null)
      setImportMode('add')
      setImportResult(null)
      setImportError(null)
      setShowImportModal(true)
    }}>
      Import bundle
    </Button>
  </div>
</div>
```

- [ ] **Step 5: Add the Import modal JSX**

After the closing `</div>` of the outer admin panel wrapper (just before the final `return`'s closing tag), add:

```tsx
{/* Import bundle modal */}
<Modal show={showImportModal} onClose={() => setShowImportModal(false)} size="md">
  <ModalHeader>Import bundle</ModalHeader>
  <ModalBody>
    <div className="flex flex-col gap-4">
      {/* Mode selector */}
      <div className="flex flex-col gap-2">
        <Label>Import mode</Label>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="import-mode"
              value="add"
              checked={importMode === 'add'}
              onChange={() => setImportMode('add')}
            />
            <span className="text-sm text-gray-700">Add — merge with existing data</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="import-mode"
              value="replace"
              checked={importMode === 'replace'}
              onChange={() => setImportMode('replace')}
            />
            <span className="text-sm text-gray-700">Replace — wipe and reimport</span>
          </label>
        </div>
        {importMode === 'replace' && (
          <Alert color="warning">
            This will permanently delete all current gems and documents before importing.
          </Alert>
        )}
      </div>

      {/* File picker */}
      <div>
        <Label htmlFor="bundle-file">Bundle ZIP file</Label>
        <input
          id="bundle-file"
          type="file"
          accept=".zip"
          className="mt-1 block w-full text-sm text-gray-500"
          onChange={e => setImportFile(e.target.files?.[0] ?? null)}
        />
      </div>

      {/* Result feedback */}
      {importResult && (
        <Alert color="success">
          Import complete: {importResult.gems_imported} gem{importResult.gems_imported !== 1 ? 's' : ''} and{' '}
          {importResult.documents_imported} document{importResult.documents_imported !== 1 ? 's' : ''} imported.
          {Object.keys(importResult.documents_renamed).length > 0 && (
            <> {Object.keys(importResult.documents_renamed).length} document{Object.keys(importResult.documents_renamed).length !== 1 ? 's' : ''} renamed.</>
          )}
          {Object.keys(importResult.gems_renamed).length > 0 && (
            <> {Object.keys(importResult.gems_renamed).length} gem{Object.keys(importResult.gems_renamed).length !== 1 ? 's' : ''} renamed.</>
          )}
        </Alert>
      )}
      {importError && <Alert color="failure">{importError}</Alert>}
    </div>
  </ModalBody>
  <ModalFooter>
    <Button
      color="blue"
      disabled={!importFile || importing}
      onClick={handleImport}
    >
      {importing ? <><Spinner size="sm" className="mr-2" />Importing…</> : 'Import'}
    </Button>
    <Button color="light" onClick={() => setShowImportModal(false)}>
      Cancel
    </Button>
  </ModalFooter>
</Modal>
```

- [ ] **Step 6: Verify build**

```bash
cd frontend && bun run build 2>&1 | grep -i error || echo "OK"
```

Expected: `OK`.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/AdminPanel.tsx
git commit -m "feat: add export/import bundle UI to Settings tab"
```

---

## Task 13: Frontend — DocumentsPanel download buttons

**Files:**
- Modify: `frontend/src/pages/DocumentsPanel.tsx`

- [ ] **Step 1: Add download handlers**

In `DocumentsPanel.tsx`, after the existing handler functions (e.g., after `handleDeleteFolder`), add:

```typescript
async function handleDownloadFolder(folder: Folder) {
  try {
    await documentsApi.downloadFolder(folder.id)
  } catch (e) {
    setFolderError(String(e))
  }
}

async function handleDownloadDocument(doc: Document) {
  try {
    await documentsApi.downloadDocument(doc.id)
  } catch (e) {
    setDocError(String(e))
  }
}
```

- [ ] **Step 2: Add download button to each folder row**

Find the folder row JSX. Each folder is rendered inside the folders column. Locate where the pencil/delete buttons for folders are rendered (look for `renamingFolderId` and the delete button). Add a download button alongside them:

```tsx
<button
  onClick={() => handleDownloadFolder(folder)}
  title="Download folder as ZIP"
  className="text-gray-400 hover:text-gray-600 p-1"
>
  {/* Download icon */}
  <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
    <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
  </svg>
</button>
```

Place this button in the same row as the existing folder action buttons (pencil/delete icons), before or after the existing controls, matching the visual style.

- [ ] **Step 3: Add download button to each document row**

Find the document row JSX. Each document appears in the centre column as a clickable row. Add a small download button at the end of the row (right side), similar to the folder button:

```tsx
<button
  onClick={e => { e.stopPropagation(); handleDownloadDocument(doc) }}
  title="Download as markdown"
  className="text-gray-400 hover:text-gray-600 p-1 shrink-0"
>
  <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
    <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
  </svg>
</button>
```

The `e.stopPropagation()` prevents the document row click (which selects the doc) from firing at the same time as the download.

- [ ] **Step 4: Verify build**

```bash
cd frontend && bun run build 2>&1 | grep -i error || echo "OK"
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/DocumentsPanel.tsx
git commit -m "feat: add download buttons to folder and document rows in DocumentsPanel"
```

---

## Task 14: Frontend — GemForm `react-checkbox-tree` replacement

**Files:**
- Modify: `frontend/src/pages/GemForm.tsx`

- [ ] **Step 1: Add imports**

In `GemForm.tsx`, replace the existing import block top section with the addition of:

```typescript
import CheckboxTree from 'react-checkbox-tree'
import 'react-checkbox-tree/lib/react-checkbox-tree.css'
```

Add this after the existing React import, before the flowbite-react imports.

- [ ] **Step 2: Remove the old tree state variables**

Remove these state declarations (they are replaced by gem state directly):

```typescript
const [checkedFolderIds, setCheckedFolderIds] = useState<Set<string>>(new Set())
const [checkedDocIds, setCheckedDocIds] = useState<Set<string>>(new Set())
```

Add in their place the `expanded` state for the tree:

```typescript
const [expanded, setExpanded] = useState<string[]>([])
```

- [ ] **Step 3: Remove the old helpers**

Delete these five functions entirely:
- `docsInFolder`
- `isFolderFullyChecked`
- `isFolderIndeterminate`
- `isDocChecked`
- `toggleFolder`
- `toggleDocument`

- [ ] **Step 4: Update the gem-loading useEffect**

In the useEffect that loads the gem (edit mode), replace the lines that seed `checkedFolderIds` and `checkedDocIds`:

```typescript
// Replace this:
setCheckedFolderIds(new Set(g.doc_folder_ids))
setCheckedDocIds(new Set(g.doc_ids))

// With this (gem state holds doc_folder_ids and doc_ids directly):
// — nothing needed: the gem object itself is the source of truth —
```

So just remove the two `setChecked*` lines; `setGem(g)` already brings in `doc_folder_ids` and `doc_ids`.

- [ ] **Step 5: Add `expanded` initialisation effect**

Add this useEffect after the documents load useEffect:

```typescript
// Expand all folders by default when folder list loads
useEffect(() => {
  setExpanded(allFolders.map(f => `folder:${f.id}`))
}, [allFolders])
```

- [ ] **Step 6: Update `handleSave`**

In `handleSave`, replace:

```typescript
const cleanGem: UserTask = {
  ...gem,
  args: deriveArgs(gem.template),
  doc_folder_ids: Array.from(checkedFolderIds),
  doc_ids: Array.from(checkedDocIds),
}
```

With:

```typescript
const cleanGem: UserTask = {
  ...gem,
  args: deriveArgs(gem.template),
  // doc_folder_ids and doc_ids are kept current in gem state by handleCheckedChange
}
```

- [ ] **Step 7: Add `handleCheckedChange` and tree nodes computation**

Add these before the `return` statement:

```typescript
/**
 * Derive node values from gem state for the tree's controlled checked prop.
 * Folder values use 'folder:<id>' prefix; doc values use 'doc:<id>' prefix.
 * Only includes individual doc grants for docs whose folder is NOT already granted.
 */
const checkedValues: string[] = [
  ...gem.doc_folder_ids.map(id => `folder:${id}`),
  ...gem.doc_ids.map(id => `doc:${id}`),
]

/**
 * Handle checkbox changes from react-checkbox-tree.
 * Maps prefixed values back to doc_folder_ids and doc_ids in gem state.
 * When a folder is checked, its children are covered by the folder grant
 * and should not also appear as individual doc_ids.
 */
function handleCheckedChange(newChecked: string[]) {
  const newFolderIds = newChecked
    .filter(v => v.startsWith('folder:'))
    .map(v => v.slice(7))
  const checkedFolderSet = new Set(newFolderIds)
  const newDocIds = newChecked
    .filter(v => v.startsWith('doc:'))
    .map(v => v.slice(4))
    .filter(docId => {
      const doc = allDocuments.find(d => d.id === docId)
      return doc ? !checkedFolderSet.has(doc.folder_id) : true
    })
  setGem(g => ({ ...g, doc_folder_ids: newFolderIds, doc_ids: newDocIds }))
}

/** Build the node tree for react-checkbox-tree. */
const treeNodes = allFolders.map(folder => ({
  value: `folder:${folder.id}`,
  label: folder.name,
  children: allDocuments
    .filter(d => d.folder_id === folder.id)
    .map(doc => ({
      value: `doc:${doc.id}`,
      label: doc.name,
      title: doc.description || undefined,
    })),
}))

/** Minimal inline SVG icons — avoids pulling in Font Awesome. */
const TREE_ICONS = {
  check: (
    <svg className="w-4 h-4 text-blue-600 inline" viewBox="0 0 20 20" fill="currentColor">
      <rect x="2" y="2" width="16" height="16" rx="3" fill="currentColor" opacity="0.15" />
      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
    </svg>
  ),
  uncheck: (
    <svg className="w-4 h-4 text-gray-300 inline" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="2.75" y="2.75" width="14.5" height="14.5" rx="2.25" />
    </svg>
  ),
  halfCheck: (
    <svg className="w-4 h-4 text-blue-400 inline" viewBox="0 0 20 20" fill="currentColor">
      <rect x="2" y="2" width="16" height="16" rx="3" fill="currentColor" opacity="0.15" />
      <path d="M5 10h10" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  expandClose: <span className="text-gray-400 text-xs select-none">›</span>,
  expandOpen: <span className="text-gray-400 text-xs select-none">⌄</span>,
  expandAll: <span />,
  collapseAll: <span />,
  parentClose: <span />,
  parentOpen: <span />,
  leaf: <span />,
}
```

- [ ] **Step 8: Replace the manual tree JSX**

Find the "Document access" section in the JSX (starts with `{/* Document access */}`). Replace the entire inner div (the `allFolders.length === 0 ? ... : (...)` block) with:

```tsx
{allFolders.length === 0 ? (
  <p className="text-xs text-gray-400 italic">{t('gem.documents.no_folders')}</p>
) : (
  <div className="border border-gray-200 rounded-lg p-3">
    <CheckboxTree
      nodes={treeNodes}
      checked={checkedValues}
      expanded={expanded}
      onCheck={handleCheckedChange}
      onExpand={setExpanded}
      icons={TREE_ICONS}
    />
  </div>
)}
```

- [ ] **Step 9: Verify build**

```bash
cd frontend && bun run build 2>&1 | grep -i error || echo "OK"
```

Expected: `OK`.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/pages/GemForm.tsx
git commit -m "feat: replace manual checkbox tree with react-checkbox-tree in GemForm"
```

---

## Final verification

- [ ] **Run the full backend test suite**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Run a frontend build**

```bash
cd frontend && bun run build
```

Expected: no errors (chunk size warning is pre-existing and acceptable).

- [ ] **Manual smoke test checklist**
  - Settings tab: Export bundle → ZIP downloads. Import bundle (Add) → success message with counts. Import bundle (Replace) → warning shown, wipes and reimports.
  - Documents tab: Download icon on folder row → `<folder_id>.zip` downloads. Download icon on document row → `<doc_id>.md` downloads.
  - Gem create/edit form: Folder/document tree renders. Checking a folder visually checks its children. Unchecking one child makes folder indeterminate. Saving persists `doc_folder_ids` and `doc_ids` correctly.
