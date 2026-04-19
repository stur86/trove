# Import / Export Design

**Date:** 2026-04-19
**Status:** Approved

## Overview

Admins can export the full Trove configuration — all gems and all documents — as a portable ZIP bundle, and import a previously exported bundle onto any Trove instance. Separately, individual folders and documents can be downloaded directly from the Documents tab. The gem edit form's document access tree is replaced with `react-checkbox-tree`.

---

## 1. Bundle ZIP Format

```
trove-bundle.zip
├── manifest.json
└── documents/
    └── <folder_id>/
        └── <doc_id>.md
```

### manifest.json

```json
{
  "version": 1,
  "exported_at": "2026-04-19T10:00:00Z",
  "folders": [
    { "id": "hr-policies", "name": "HR Policies" }
  ],
  "documents": [
    {
      "id": "leave-policy-2024",
      "folder_id": "hr-policies",
      "name": "Leave Policy 2024.docx",
      "description": "One-sentence AI summary or admin-supplied description.",
      "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "gems": [
    {
      "id": "summarise-text",
      "name": "Summarise Text",
      "description": "Summarises a block of text.",
      "template": "Summarise the following in {{ language }}: {{ text }}",
      "args": [
        { "type": "string", "name": "language", "description": "", "default": "English" },
        { "type": "string", "name": "text", "description": "", "default": "" }
      ],
      "hue": "indigo",
      "has_image": false,
      "has_audio": false,
      "output_mode": "text",
      "doc_folder_ids": ["hr-policies"],
      "doc_ids": []
    }
  ]
}
```

The manifest is authoritative — the raw SQLite file is not included. The manifest contains every field from the `folders`, `documents`, and `gems` tables in a portable, version-stable form. The `.md` files under `documents/` hold the converted markdown content. `created_at` timestamps are preserved verbatim from the original.

---

## 2. Backend

### New domain: `backend/bundle/`

**`models.py`**

- `BundleFolder` — mirrors `Folder` for serialisation
- `BundleDocument` — mirrors `Document` for serialisation
- `BundleGem` — mirrors `UserTask` for serialisation
- `BundleManifest` — top-level model: `version`, `exported_at`, `folders`, `documents`, `gems`
- `ImportMode` — enum: `replace | add`
- `ImportResult` — counts + rename map returned to the caller: `folders_created`, `documents_imported`, `documents_renamed` (dict old→new), `gems_imported`, `gems_renamed` (dict old→new)

**`service.py`**

`export_bundle() → bytes`
1. Query all folders, documents, and gems from the DB.
2. For each document, read `~/.local/share/trove/documents/<folder_id>/<doc_id>.md` from disk.
3. Build a `BundleManifest` and write it as `manifest.json` into an in-memory `zipfile.ZipFile`.
4. Write each `.md` file at `documents/<folder_id>/<doc_id>.md`.
5. Return the ZIP bytes.

`import_bundle(zip_bytes: bytes, mode: ImportMode) → ImportResult`

*Replace mode:*
1. Delete all gems from the DB.
2. Delete all document rows and their `.md` files from disk.
3. Delete all folder rows.
4. Import all folders, documents (with `.md` files written to disk), and gems from the manifest verbatim.

*Add mode:*
1. For each folder: create it if the ID is absent; skip (keep existing name) if it already exists. Folder IDs are never renamed — documents reference them and renaming would require cascading updates across all document rows.
2. For each document: if the ID is free, import verbatim. If the ID already exists, find the next free suffix (`-2`, `-3`, …) and record the rename in `doc_renames`.
3. Write each `.md` file to disk under the (possibly renamed) doc ID.
4. For each gem: rewrite any `doc_ids` entries using `doc_renames`. If the gem ID already exists, find the next free suffix and record in `gem_renames`. Save the gem.
5. Return `ImportResult` with all counts and rename maps.

**`router.py`**

Both endpoints require `require_admin_cookie`.

- `GET /api/bundle/export` — calls `export_bundle()`, returns `StreamingResponse` with `Content-Type: application/zip` and `Content-Disposition: attachment; filename="trove-bundle.zip"`.
- `POST /api/bundle/import` — accepts `file: UploadFile` and `mode: str` as form fields. Reads the file bytes, calls `import_bundle()`, returns `ImportResult` as JSON.

### Additions to `backend/documents/router.py`

Both endpoints require `require_admin_cookie`.

- `GET /api/documents/folders/{folder_id}/download` — builds an in-memory ZIP of all `.md` files in the folder (flat, not nested), streams as `application/zip` with filename `<folder_id>.zip`.
- `GET /api/documents/{doc_id}/download` — reads the `.md` file, streams as `text/markdown` with `Content-Disposition: attachment; filename="<doc_id>.md"`.

---

## 3. Frontend

### Settings tab — Data section

A new "Data" card appended below the existing model/language controls.

**Export:** A single "Export bundle" button. On click, the browser fetches `GET /api/bundle/export` and triggers a file download (using a temporary `<a>` element with `download` attribute). A spinner replaces the button label while the request is in flight.

**Import:** An "Import bundle" button opens a modal containing:
- A file picker (`accept=".zip"`).
- A two-option radio/toggle: **Add** (default) / **Replace**.
- When Replace is selected, a red warning alert: *"This will permanently delete all current gems and documents."*
- An **Import** button (disabled until a file is chosen). On click, POSTs the file and mode to `/api/bundle/import` as `multipart/form-data`.
- On success: shows a green summary — e.g. *"3 gems and 12 documents imported. 2 documents renamed."*
- On error: shows a red alert with the server error message.

### Documents tab — per-item downloads

Each folder row in `DocumentsPanel` gets a small download icon button alongside the existing rename/delete controls, triggering `GET /api/documents/folders/{id}/download`.

Each document row gets the same for `GET /api/documents/{id}/download`.

### GemForm — `react-checkbox-tree` replacement

**Package:** `react-checkbox-tree` (already has TypeScript types via `@types/react-checkbox-tree`).

**Node structure:** each folder becomes a parent node with value `folder:<id>`; each document within it becomes a child node with value `doc:<id>`.

**Checked state mapping:**

*From gem → tree:*
- Add `folder:<id>` for each id in `doc_folder_ids`.
- Add `doc:<id>` for each id in `doc_ids` whose folder is not already in `doc_folder_ids` (the library cascades visually, so individually-granted docs under an un-granted folder are enough).

*From tree → gem (onChange):*
- Values prefixed `folder:` → `doc_folder_ids`.
- Values prefixed `doc:` whose parent folder value is **not** in the checked set → `doc_ids`.
- Values prefixed `doc:` whose parent folder **is** checked → discarded (the folder grant covers them).

The manual helper functions `isFolderFullyChecked`, `isFolderIndeterminate`, `toggleFolder`, `toggleDocument`, and `isDocChecked` are deleted; the library handles all visual cascade and indeterminate rendering.

**Expanded state:** controlled locally, initialised with all folder IDs expanded.

---

## 4. Testing

- `tests/test_bundle.py` — unit tests for `export_bundle` and `import_bundle` (both modes), covering: round-trip fidelity, Add-mode rename on collision, gem `doc_ids` reference rewrite after document rename, Replace-mode wipe.
- `tests/test_documents.py` — add tests for the two new download endpoints (folder ZIP contents, single `.md` response).
- Frontend: no automated tests; manual verification of export download, both import modes (including conflict rename feedback), and the checkbox-tree behaviour (folder cascade, individual doc toggle, mixed state).
