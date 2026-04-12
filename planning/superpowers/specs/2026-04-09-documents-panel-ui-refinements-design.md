# DocumentsPanel UI Refinements — Design

Date: 2026-04-09

## Overview

Refine the admin document library UI (DocumentsPanel) with a three-column layout, inline folder rename, a selected-document properties card, and modal-based upload flows. Backend gains two PATCH endpoints to support rename and move operations.

## Layout

Three columns inside the existing right-panel area of AdminPanel (Documents tab):

```
┌─────────────────┬────────────────────────┬──────────────────────┐
│  Folders        │  Documents             │  Properties          │
│  (200px fixed)  │  (flex-1)              │  (280px fixed)       │
│                 │                        │                      │
│ [New folder…][+]│ [Upload File][From URL]│ (empty until select) │
│ ─────────────── │ ───────────────────────│                      │
│ > My Folder  ✎×│  Document Name A       │                      │
│   Other      ✎×│  Document Name B  ←sel │ Name: [_________]   │
│                 │  Document Name C       │ Desc: [_________]   │
│                 │                        │ Move: [Folder ▼][Move]│
│                 │                        │       [Delete]      │
└─────────────────┴────────────────────────┴──────────────────────┘
```

All three columns are always rendered when a folder is selected. The properties column shows a grey placeholder when no document is selected.

## Folder Column

- New folder: text input + "+" button at the top (unchanged behaviour).
- Each folder row shows the folder name. On hover, a pencil icon (✎) and a delete icon (×) appear.
- **Rename (inline):** clicking ✎ replaces the name with a text input pre-filled with the current name. Enter or blur commits the rename (PATCH `/admin/folders/{id}`). Escape cancels.
- **Delete:** clicking × opens the existing confirmation modal (unchanged).
- Folder selection works by clicking the name area (not the icons).

## Document List Column

- Two buttons above the list: **Upload File** and **Add from URL**. Both are disabled when no folder is selected.
- Document rows show the document name only (no description).
- Clicking a row selects it (highlighted) and populates the properties card.
- No per-row delete button — deletion is handled in the properties card.

## Properties Card

Displayed on the right when a document is selected. All fields are independently auto-saving (no global Save button).

| Field | Behaviour |
|---|---|
| **Name** | Text input, pre-filled. Saves on blur via PATCH `/admin/documents/{id}`. |
| **Description** | Textarea (4 rows), pre-filled. Saves on blur via PATCH `/admin/documents/{id}`. |
| **Move to folder** | Dropdown listing all folders, current folder pre-selected. Changing the selection enables a **Move** button next to the dropdown. |
| **Delete** | Red button. First click changes label to "Sure?". Second click sends DELETE, clears the card, removes the document from the list. |

**Move behaviour:** clicking Move sends PATCH `/admin/documents/{id}` with the new `folder_id`. On success:
1. The left panel switches to the destination folder.
2. The document list reloads that folder's documents.
3. The moved document is auto-selected in the new list.
4. The properties card remains open.
5. The Move to folder dropdown resets to the now-current folder (Move button hides again).

Unsaved edits (name/description mid-type) are lost if the user selects a different document without blurring — no warning is shown (admin context, low risk).

Empty state: grey italic text "Select a document to view its properties."

## Upload File Modal

Triggered by the **Upload File** button (requires a folder to be selected).

Fields:
1. **File** — file picker, same allowed extensions as today (`.pdf .docx .pptx .xlsx .txt .md .html .htm`).
2. **Name** — optional text input. Placeholder shows the filename. If left blank, the filename is used as the display name.
3. **Description** — optional text input. Hint: "Leave blank to auto-generate."
4. **Upload** button — disabled until a file is chosen.

`needs_description` flow (document too long for AI summary): the modal stays open, the upload controls are replaced by a warning showing word count and context limit, and a required description field with a Retry button. Cancel closes the modal and discards the pending upload.

## Add from URL Modal

Triggered by the **Add from URL** button (requires a folder to be selected).

Fields:
1. **URL** — text input.
2. **Name** — optional text input. Placeholder: "Last part of URL if blank." The frontend fills in `url.split('/').filter(Boolean).pop()` before posting if the field is empty.
3. **Description** — optional text input. Same hint as above.
4. **Add** button — disabled until URL is non-empty.

Same `needs_description` inline flow as the file upload modal.

## Backend Changes

### New endpoints

**PATCH `/admin/folders/{folder_id}`**
```
Body: { "name": "New Name" }
Returns: Folder
```
Updates the folder name. Returns 404 if the folder does not exist.

**PATCH `/admin/documents/{doc_id}`**
```
Body: { "name"?: string, "description"?: string, "folder_id"?: string }
Returns: Document
```
Updates any subset of name, description, folder_id. If `folder_id` changes, the markdown file is moved on disk from `documents/<old_folder>/<doc_id>.md` to `documents/<new_folder>/<doc_id>.md` (creating the target directory if needed). Returns 404 if the document does not exist, 400 if the new folder does not exist.

### Repository additions

- `update_folder(folder_id, name) -> Folder` — UPDATE query, returns updated row.
- `update_document(doc_id, **kwargs) -> Document` — UPDATE query for provided fields, returns updated row. Handles `folder_id` change in DB only (file move is router responsibility).

## Frontend Changes

### `src/api/client.ts`
Add a `patch<T>(path, body)` helper matching the existing `post` pattern.

### `src/api/documents.ts`
Add:
- `renameFolder(id, name) -> Folder`
- `updateDocument(id, patch: Partial<{name, description, folder_id}>) -> Document`

### `src/api/mock/documents.ts`
Implement the same two methods on the mock.

### `src/pages/DocumentsPanel.tsx`
Full rewrite. Key state:
- `folders`, `selectedFolder` — unchanged
- `documents`, `selectedDoc` — replaces old document list state
- `uploadModalOpen`, `urlModalOpen` — controls modals
- `needsDescription` — moved inside each modal's local state

### Locale keys (additions)

```
admin.documents.upload_file_modal_title
admin.documents.from_url_modal_title
admin.documents.name_label
admin.documents.name_placeholder_file
admin.documents.name_placeholder_url
admin.documents.description_hint
admin.documents.move_button
admin.documents.delete_confirm
admin.documents.properties_empty
admin.documents.folder_rename_placeholder
```

## Testing

Backend:
- `test_rename_folder` — PATCH /admin/folders/{id}, verifies updated name returned and persisted.
- `test_rename_folder_not_found` — 404 for unknown id.
- `test_update_document_name` — PATCH updates name only.
- `test_update_document_description` — PATCH updates description only.
- `test_update_document_move` — PATCH with new folder_id, verify file moved on disk.
- `test_update_document_not_found` — 404.
- `test_update_document_bad_folder` — 400 when target folder doesn't exist.

Frontend: existing mock-based manual testing is sufficient given the complexity of the component rewrite.
