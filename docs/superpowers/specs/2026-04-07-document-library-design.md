# Document Library Design

**Date:** 2026-04-07

## Overview

A document library that lets admins upload files or scrape URLs, converts them to markdown via Markitdown, generates a one-line AI summary per document, and organises them into flat folders. Gems can be granted access to specific folders and/or individual documents. When a gem run has any document access, the Pydantic AI agent receives two injected tools — a table of contents and a document fetcher — so the model can retrieve content on demand without bloating every prompt.

---

## Data Models

### `Folder`

```python
class Folder(BaseModel, frozen=True):
    id: str    # slug, e.g. "hr-policies"
    name: str  # "HR Policies"
```

Folders are flat — no nesting. The tree UI in GemForm is nested only in the sense that documents appear under their folder.

### `Document`

```python
class Document(BaseModel, frozen=True):
    id: str              # slug derived from filename, e.g. "leave-policy-2024"
    folder_id: str
    name: str            # original filename (display only)
    description: str     # AI-generated one-liner; falls back to filename on failure
    mime_type: str       # original upload MIME type
    created_at: datetime
```

### `UserTask` additions

Two new fields on `UserTask`:

```python
doc_folder_ids: tuple[str, ...] = ()  # whole folders granted access
doc_ids: tuple[str, ...] = ()         # individually granted documents
```

Effective document set at run time = all documents in allowed folders ∪ individually allowed documents.

Stored as JSON columns (`'[]'` default) in the existing `tasks` table in `trove.db`. No migration needed.

---

## Storage

### SQLite — `trove.db`

Two new tables owned by `backend/documents/repository.py`:

```sql
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
    created_at  TEXT NOT NULL   -- ISO-8601
);
```

The `tasks` table gains two columns:

```sql
doc_folder_ids  TEXT NOT NULL DEFAULT '[]',
doc_ids         TEXT NOT NULL DEFAULT '[]'
```

### Filesystem

Processed markdown lives at:

```
~/.local/share/trove/
├── trove.db
└── documents/
    └── <folder_id>/
        └── <doc_id>.md
```

Raw uploads are discarded after conversion. Re-uploading is the path to update a document's content.

For future export/import, the whole `~/.local/share/trove/` directory (DB + markdown files) is treated as one portable unit.

---

## File Structure

```
backend/
└── documents/
    ├── __init__.py
    ├── models.py       # Folder, Document
    ├── repository.py   # CRUD for folders and documents
    ├── service.py      # upload pipeline: markitdown + AI summary + persist
    └── router.py       # admin API endpoints
```

---

## Upload Processing Pipeline

Both upload paths (file and URL) funnel into a shared service function after content is retrieved:

```python
async def process_document(
    content: str,
    name: str,
    folder_id: str,
    mime_type: str,
    description: str = "",
) -> Document:
    """Slugify, summarise, write markdown, insert DB row. Returns the new Document."""
```

### File upload flow

1. Receive `multipart/form-data` with `file` + `folder_id` + optional `description`
2. Check file extension against whitelist (422 if not allowed)
3. Write to a temp path; pass to markitdown for conversion to markdown string
4. Delete temp file
5. Call `process_document()`

### URL upload flow

1. Receive `application/json` with `{ url, folder_id, name }` + optional `description`
2. Pass URL directly to markitdown (handles fetching + conversion)
3. Call `process_document()`

### `process_document` steps

1. **Slugify** — derive `id` from `name` (lowercase, hyphens); append numeric suffix on collision
2. **Summarise** — choose strategy based on document length:
   - Estimate token count as `word_count × 2` (where `word_count = len(content.split())`)
   - Read `num_ctx` from the active Trove config
   - If `word_count × 2 > num_ctx` **and** no `description` was supplied: return a special sentinel instead of a `Document` (see below — the router surfaces this to the frontend)
   - If `description` was supplied (either because admin provided it, or because the document is large and the frontend re-submitted with one): use it directly
   - Otherwise: run an internal hardcoded `Task` via `run_task()` with template `"In one sentence, describe what this document is about:\n\n{{ content }}"`. On any failure (Ollama unavailable, timeout, error): fall back to `name`
3. **Persist** — write markdown to `~/.local/share/trove/documents/<folder_id>/<doc_id>.md`; insert row into `documents` table

Processing is synchronous within the upload request.

### Too-long document flow

When a document exceeds the context window and no description is provided, neither the endpoint nor `process_document` persists anything. The endpoint returns HTTP 200 with:

```json
{ "status": "needs_description", "word_count": 42000 }
```

The frontend detects this, shows an inline description field (pre-filled with the filename as a prompt), and re-submits the same request with the `description` field populated. For file uploads the browser's `File` object is still in memory; for URL uploads the URL string is simply re-sent. On the second submission `description` is non-empty so the length check is bypassed and processing completes normally.

The word-count estimate and `num_ctx` value are included in the response so the frontend can show a helpful message: e.g. *"This document is too long to summarise automatically (≈42,000 tokens, context window is 32,768). Please enter a short description."*

### Supported file formats (whitelist)

| Extension | MIME type |
|-----------|-----------|
| `.pdf` | `application/pdf` |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| `.pptx` | `application/vnd.openxmlformats-officedocument.presentationml.presentation` |
| `.xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| `.txt` | `text/plain` |
| `.md` | `text/markdown` |
| `.html` / `.htm` | `text/html` |

Markitdown supports additional formats; these can be added to the whitelist as needed. See [Markitdown documentation](https://github.com/microsoft/markitdown) for the full list.

---

## Runner Integration

### Signature changes

Both runner functions gain a `documents` parameter:

```python
async def stream_task(
    task: Task,
    values: dict[str, str],
    *,
    media: MediaInput | None = None,
    documents: list[Document] | None = None,
    _agent: Agent | None = None,
) -> AsyncIterator[str]:

async def run_task(
    task: Task,
    values: dict[str, str],
    *,
    media: MediaInput | None = None,
    documents: list[Document] | None = None,
    _agent: Agent | None = None,
) -> str:
```

### Tool injection

When `documents` is non-empty, the agent is constructed with two tools and a system prompt addendum.

**`get_table_of_contents() → str`**

Returns a formatted list of all accessible documents:

```
[leave-policy-2024] Leave Policy 2024 — Sets out employee leave entitlements and procedures.
[health-safety-guide] Health & Safety Guide — Covers on-site safety rules and emergency contacts.
```

**`get_document(doc_id: str) → str`**

Returns the full markdown content of one document. If `doc_id` is not in the permitted set, returns a descriptive error string (not a Python exception) so the model receives a clean message.

Markdown files are read from disk at call time — not pre-loaded — so large document libraries don't bloat the agent context unnecessarily.

**System prompt addendum** (appended only when documents are present):

> "You have access to a document library. Call get_table_of_contents() to see what is available, then get_document(id) to read a specific document."

### Router responsibility

The run endpoint resolves the document set before calling the runner:

1. Load `UserTask.doc_folder_ids` and `UserTask.doc_ids`
2. Query the repository for the union of documents in scope
3. Pass the list to `stream_task` / `run_task`

---

## API Endpoints

All endpoints require admin credentials.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/app/admin/folders` | List all folders |
| `POST` | `/api/app/admin/folders` | Create folder (`{ name }`) |
| `DELETE` | `/api/app/admin/folders/{id}` | Delete folder + all its documents + markdown files |
| `GET` | `/api/app/admin/documents` | List documents; optional `?folder_id=` filter |
| `POST` | `/api/app/admin/documents/upload` | Multipart: `file` + `folder_id` + optional `description` |
| `POST` | `/api/app/admin/documents/from-url` | JSON: `{ url, folder_id, name, description? }` |
| `DELETE` | `/api/app/admin/documents/{id}` | Delete document + its markdown file |

---

## Frontend

### New files

```
frontend/src/
├── api/
│   ├── documents.ts          # typed API client for folders + documents
│   └── mock/documents.ts     # mock with sample folders + documents
└── pages/
    └── DocumentsPanel.tsx    # folder/document admin UI
```

### AdminPanel.tsx — Documents Tab

The existing placeholder `TabItem` (line 274) is replaced with `<DocumentsPanel />`.

`DocumentsPanel` uses a two-panel layout built from Flowbite components:

- **Left panel** — folder list (`ListGroup` or `List`). "New Folder" button at top. Each folder row has a delete button (with confirmation modal). Clicking a folder selects it.
- **Right panel** — document list for the selected folder. "Upload file" button opens a file picker (whitelist enforced by `accept` attribute). "Add from URL" shows an inline text input + submit. Both show a Flowbite `Spinner` while processing. On success, the new document appears in the list. Each document row shows name, description, and a delete button.

### GemForm.tsx — Document Access Section

A collapsible section below the template/args fields, using Flowbite's `Accordion` or a plain expandable `div`.

Shows a nested tree built from Flowbite `Checkbox` and layout primitives:

```
☐ HR Policies
    ☐ Leave Policy 2024 — Sets out employee leave...
    ☐ Health & Safety Guide — Covers on-site...
☐ General Reference
    ☑ Staff Handbook — Complete onboarding guide...
```

- Checking a folder checks all its documents
- Unchecking a folder unchecks all its documents
- Individual documents can be checked/unchecked independently
- Folder shows an indeterminate checkbox state when partially checked

On save, `doc_folder_ids` contains IDs of fully-checked folders; `doc_ids` contains IDs of individually-checked documents not covered by a fully-checked folder.

### mock/documents.ts

Sample data: 2–3 folders, 4–6 documents covering a mix of descriptions. Used when `VITE_MOCK_API=1`.

---

## Testing

- **`models.py`**: `Folder` and `Document` round-trip through DB. `UserTask` with `doc_folder_ids`/`doc_ids` persists and loads correctly.
- **`service.py`**: slug derivation and collision handling. Fallback description when AI summary raises. Markitdown called with correct args for file vs URL paths. Length check: document exceeding `num_ctx` with no description supplied returns sentinel (not a `Document`). Document within limit uses AI summary. Supplied `description` bypasses length check and AI summary.
- **`repository.py`**: folder CRUD, document CRUD, delete cascade (folder delete removes documents and markdown files).
- **`router.py`**: `TestClient` tests. File whitelist enforcement (422 on bad extension). URL upload path. Delete cascade.
- **`runner.py`**: tool injection present when `documents` is non-empty; absent when empty/None. `get_document` returns error string for out-of-scope ID. `get_table_of_contents` format.

---

## Out of Scope

- Always-visible tier (full document injected into every prompt unconditionally)
- Re-generating AI summaries for existing documents
- Document search or filtering in the runner
- Per-user document access (access is per-gem, not per-user)
- Nested folders
