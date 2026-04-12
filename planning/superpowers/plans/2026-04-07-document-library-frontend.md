# Document Library Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the frontend for the document library — a typed API client, mock data, a `DocumentsPanel` admin component (folder list + document upload), and document access controls in `GemForm` (nested checkbox tree).

**Architecture:** Follows the existing real/mock API pattern from `frontend/src/api/tasks.ts`. `DocumentsPanel` replaces the existing placeholder in `AdminPanel`. `GemForm` gains a collapsible document access section. All UI uses Flowbite React components. The `UserTask` TypeScript type gains `doc_folder_ids` and `doc_ids` fields.

**Prerequisites:** The document library backend plan (`2026-04-07-document-library-backend.md`) must be complete before testing against a real backend. Mock mode (`VITE_MOCK_API=1`) can be used for frontend-only development.

**Tech Stack:** TypeScript, React, Flowbite React, Vite, Bun. No new npm packages needed.

---

## File Map

**Create:**
- `frontend/src/api/documents.ts`
- `frontend/src/api/mock/documents.ts`
- `frontend/src/pages/DocumentsPanel.tsx`

**Modify:**
- `frontend/src/api/tasks.ts` — add `doc_folder_ids`, `doc_ids` to `UserTask`
- `frontend/src/pages/AdminPanel.tsx` — replace Documents tab placeholder
- `frontend/src/pages/GemForm.tsx` — add document access section
- `locales/en.json` — add document library strings
- `locales/it.json` — add Italian translations

---

## Task 1: UserTask type + documents API client

**Files:**
- Modify: `frontend/src/api/tasks.ts`
- Create: `frontend/src/api/documents.ts`

- [ ] **Step 1: Add doc fields to `UserTask` in `frontend/src/api/tasks.ts`**

In `frontend/src/api/tasks.ts`, add two fields to the `UserTask` interface (after `output_mode`):

```typescript
/** IDs of folders whose entire contents are accessible to this gem. */
doc_folder_ids: string[]
/** IDs of individually accessible documents outside of folder grants. */
doc_ids: string[]
```

In `_realGemsApi.create` and `_realGemsApi.update`, no change is needed — the full `UserTask` object is already serialised and sent.

In the mock data (if any default `UserTask` objects exist in `frontend/src/api/mock/tasks.ts`), add `doc_folder_ids: []` and `doc_ids: []` to each sample task so TypeScript is happy.

- [ ] **Step 2: Open `frontend/src/api/mock/tasks.ts` and add the two fields to every sample UserTask**

Each sample gem in that file must have:
```typescript
doc_folder_ids: [],
doc_ids: [],
```

Run:
```bash
cd frontend && bun run build 2>&1 | head -30
```

Expected: no TypeScript errors related to `UserTask`.

- [ ] **Step 3: Create `frontend/src/api/documents.ts`**

```typescript
/**
 * Typed API client for the document library domain.
 *
 * Exports documentsApi — switches to the mock implementation when
 * VITE_MOCK_API=1 is set in the environment.
 */
import { del, get, post } from './client'

// ── Types ────────────────────────────────────────────────────────────────────

/** A folder grouping related documents in the library. */
export interface Folder {
  id: string
  name: string
}

/** A processed document stored in the library. */
export interface Document {
  id: string
  folder_id: string
  name: string
  description: string
  mime_type: string
  created_at: string
}

/**
 * Result of an upload request.
 * status='ok'                → document is ready; `document` is set.
 * status='needs_description' → document is too long for AI summary;
 *                              `word_count` and `num_ctx` are set.
 */
export type UploadResult =
  | { status: 'ok'; document: Document }
  | { status: 'needs_description'; word_count: number; num_ctx: number }

// ── Real API implementation ───────────────────────────────────────────────────

const _realDocumentsApi = {
  /** List all folders. */
  listFolders: (): Promise<Folder[]> =>
    get<Folder[]>('/app/admin/folders'),

  /** Create a folder from a human-readable name. Returns the created Folder. */
  createFolder: (name: string): Promise<Folder> =>
    post('/app/admin/folders', { name }).then(r => r.json()),

  /** Delete a folder and all its documents. */
  deleteFolder: (id: string): Promise<void> =>
    del(`/app/admin/folders/${id}`),

  /** List documents, optionally filtered by folder_id. */
  listDocuments: (folder_id?: string): Promise<Document[]> =>
    get<Document[]>(
      folder_id
        ? `/app/admin/documents?folder_id=${encodeURIComponent(folder_id)}`
        : '/app/admin/documents'
    ),

  /**
   * Upload a file to the document library.
   * Uses multipart/form-data. An optional description bypasses AI summary.
   */
  uploadFile: async (
    file: File,
    folder_id: string,
    description: string = '',
  ): Promise<UploadResult> => {
    const form = new FormData()
    form.append('file', file)
    form.append('folder_id', folder_id)
    if (description) form.append('description', description)
    const res = await fetch('/api/app/admin/documents/upload', {
      method: 'POST',
      body: form,
      credentials: 'include',
    })
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
    return res.json()
  },

  /**
   * Fetch a URL and add it to the document library.
   * An optional description bypasses AI summary.
   */
  uploadUrl: async (
    url: string,
    folder_id: string,
    name: string,
    description: string = '',
  ): Promise<UploadResult> => {
    const res = await post('/app/admin/documents/from-url', {
      url,
      folder_id,
      name,
      description,
    })
    return res.json()
  },

  /** Delete a document and its markdown file. */
  deleteDocument: (id: string): Promise<void> =>
    del(`/app/admin/documents/${id}`),
}

// ── Mock selector ─────────────────────────────────────────────────────────────

import { documentsApi as _mockDocumentsApi } from './mock/documents'
export const documentsApi =
  import.meta.env.VITE_MOCK_API ? _mockDocumentsApi : _realDocumentsApi
```

- [ ] **Step 4: Verify the build passes**

```bash
cd frontend && bun run build 2>&1 | head -40
```

Expected: build succeeds (mock import will fail until Task 2 — that is fine for now; fix any TypeScript errors in `tasks.ts` first).

---

## Task 2: Mock documents API

**Files:**
- Create: `frontend/src/api/mock/documents.ts`

- [ ] **Step 1: Create `frontend/src/api/mock/documents.ts`**

```typescript
/**
 * Mock implementation of the document library API.
 * Used when VITE_MOCK_API=1. Returns sample data after a short delay.
 */
import type { Document, Folder, UploadResult } from '../documents'

const delay = (ms = 300) => new Promise(r => setTimeout(r, ms))

const FOLDERS: Folder[] = [
  { id: 'hr-policies', name: 'HR Policies' },
  { id: 'general-reference', name: 'General Reference' },
]

const DOCUMENTS: Document[] = [
  {
    id: 'leave-policy-2024',
    folder_id: 'hr-policies',
    name: 'leave-policy-2024.pdf',
    description: 'Sets out employee leave entitlements and procedures.',
    mime_type: 'application/pdf',
    created_at: '2024-09-01T09:00:00Z',
  },
  {
    id: 'health-safety-guide',
    folder_id: 'hr-policies',
    name: 'health-safety-guide.docx',
    description: 'Covers on-site safety rules and emergency contacts.',
    mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    created_at: '2024-10-15T14:30:00Z',
  },
  {
    id: 'staff-handbook',
    folder_id: 'general-reference',
    name: 'staff-handbook.pdf',
    description: 'Complete onboarding guide for new staff members.',
    mime_type: 'application/pdf',
    created_at: '2024-07-20T10:00:00Z',
  },
  {
    id: 'it-acceptable-use',
    folder_id: 'general-reference',
    name: 'it-acceptable-use.txt',
    description: 'Acceptable use policy for IT equipment and internet access.',
    mime_type: 'text/plain',
    created_at: '2024-11-05T08:45:00Z',
  },
]

// In-memory mutable copies so create/delete work during a session
let folders = [...FOLDERS]
let documents = [...DOCUMENTS]

export const documentsApi = {
  listFolders: async (): Promise<Folder[]> => {
    await delay()
    return [...folders]
  },

  createFolder: async (name: string): Promise<Folder> => {
    await delay(500)
    const id = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
    const folder: Folder = { id, name }
    folders.push(folder)
    return folder
  },

  deleteFolder: async (id: string): Promise<void> => {
    await delay()
    folders = folders.filter(f => f.id !== id)
    documents = documents.filter(d => d.folder_id !== id)
  },

  listDocuments: async (folder_id?: string): Promise<Document[]> => {
    await delay()
    return folder_id ? documents.filter(d => d.folder_id === folder_id) : [...documents]
  },

  uploadFile: async (
    file: File,
    folder_id: string,
    description: string = '',
  ): Promise<UploadResult> => {
    await delay(800) // Simulate markitdown + AI summary
    const id = file.name
      .replace(/\.[^.]+$/, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
    const doc: Document = {
      id,
      folder_id,
      name: file.name,
      description: description || `Mock summary for ${file.name}.`,
      mime_type: file.type,
      created_at: new Date().toISOString(),
    }
    documents.push(doc)
    return { status: 'ok', document: doc }
  },

  uploadUrl: async (
    url: string,
    folder_id: string,
    name: string,
    description: string = '',
  ): Promise<UploadResult> => {
    await delay(800)
    const id = name.toLowerCase().replace(/[^a-z0-9]+/g, '-')
    const doc: Document = {
      id,
      folder_id,
      name,
      description: description || `Mock summary for ${name}.`,
      mime_type: 'text/html',
      created_at: new Date().toISOString(),
    }
    documents.push(doc)
    return { status: 'ok', document: doc }
  },

  deleteDocument: async (id: string): Promise<void> => {
    await delay()
    documents = documents.filter(d => d.id !== id)
  },
}
```

- [ ] **Step 2: Verify the build passes**

```bash
cd frontend && bun run build 2>&1 | head -40
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/documents.ts frontend/src/api/mock/documents.ts frontend/src/api/tasks.ts frontend/src/api/mock/tasks.ts
git commit -m "feat: add document library API client and mock"
```

---

## Task 3: Add locale strings

**Files:**
- Modify: `locales/en.json`
- Modify: `locales/it.json`

- [ ] **Step 1: Add English strings to `locales/en.json`**

Add the following keys to `locales/en.json` (after the existing `admin.documents.placeholder` key):

```json
  "admin.documents.new_folder": "New Folder",
  "admin.documents.folder_name_placeholder": "Folder name",
  "admin.documents.delete_folder": "Delete folder",
  "admin.documents.delete_folder_confirm": "Delete this folder and all its documents? This cannot be undone.",
  "admin.documents.no_folder_selected": "Select a folder to view its documents.",
  "admin.documents.no_documents": "No documents in this folder.",
  "admin.documents.upload_file": "Upload file",
  "admin.documents.add_from_url": "Add from URL",
  "admin.documents.url_placeholder": "https://...",
  "admin.documents.url_name_placeholder": "Display name",
  "admin.documents.processing": "Processing…",
  "admin.documents.delete_document": "Delete",
  "admin.documents.too_long_title": "Document too long for automatic summary",
  "admin.documents.too_long_body": "This document has approximately {{words}} words (~{{tokens}} estimated tokens), which exceeds the model's context window of {{ctx}} tokens. Please enter a short description.",
  "admin.documents.description_label": "Description",
  "admin.documents.description_placeholder": "Brief description of what this document contains",
  "admin.documents.submit_with_description": "Add with description",
  "gem.documents.section_title": "Document access",
  "gem.documents.section_hint": "Select the folders or individual documents this gem can read.",
  "gem.documents.no_folders": "No folders in the document library yet. Add documents in the Documents tab."
```

- [ ] **Step 2: Add Italian strings to `locales/it.json`**

Add the following keys to `locales/it.json` at the same position:

```json
  "admin.documents.new_folder": "Nuova cartella",
  "admin.documents.folder_name_placeholder": "Nome cartella",
  "admin.documents.delete_folder": "Elimina cartella",
  "admin.documents.delete_folder_confirm": "Eliminare questa cartella e tutti i suoi documenti? Questa azione è irreversibile.",
  "admin.documents.no_folder_selected": "Seleziona una cartella per visualizzarne i documenti.",
  "admin.documents.no_documents": "Nessun documento in questa cartella.",
  "admin.documents.upload_file": "Carica file",
  "admin.documents.add_from_url": "Aggiungi da URL",
  "admin.documents.url_placeholder": "https://...",
  "admin.documents.url_name_placeholder": "Nome visualizzato",
  "admin.documents.processing": "Elaborazione…",
  "admin.documents.delete_document": "Elimina",
  "admin.documents.too_long_title": "Documento troppo lungo per il riassunto automatico",
  "admin.documents.too_long_body": "Questo documento ha circa {{words}} parole (~{{tokens}} token stimati), che supera la finestra di contesto del modello di {{ctx}} token. Inserisci una breve descrizione.",
  "admin.documents.description_label": "Descrizione",
  "admin.documents.description_placeholder": "Breve descrizione del contenuto del documento",
  "admin.documents.submit_with_description": "Aggiungi con descrizione",
  "gem.documents.section_title": "Accesso ai documenti",
  "gem.documents.section_hint": "Seleziona le cartelle o i singoli documenti che questo gem può leggere.",
  "gem.documents.no_folders": "Nessuna cartella nella libreria documenti. Aggiungi documenti nella scheda Documenti."
```

- [ ] **Step 3: Commit**

```bash
git add locales/en.json locales/it.json
git commit -m "feat: add document library locale strings"
```

---

## Task 4: DocumentsPanel component

**Files:**
- Create: `frontend/src/pages/DocumentsPanel.tsx`

- [ ] **Step 1: Create `frontend/src/pages/DocumentsPanel.tsx`**

```tsx
/**
 * DocumentsPanel — admin UI for the document library.
 *
 * Two-panel layout: folder list on the left, document list on the right.
 * Supports creating/deleting folders, uploading files, adding from URL,
 * and deleting documents. Handles the needs_description flow inline.
 */
import { useEffect, useRef, useState } from 'react'
import {
  Alert,
  Button,
  Label,
  ListGroup,
  Modal,
  Spinner,
  TextInput,
} from 'flowbite-react'
import { documentsApi, type Document, type Folder } from '../api/documents'
import { useTranslation } from '../i18n/useTranslation'

export default function DocumentsPanel() {
  const { t } = useTranslation()
  const [folders, setFolders] = useState<Folder[]>([])
  const [selectedFolder, setSelectedFolder] = useState<Folder | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [loadingFolders, setLoadingFolders] = useState(true)
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // New folder creation
  const [newFolderName, setNewFolderName] = useState('')
  const [creatingFolder, setCreatingFolder] = useState(false)

  // URL upload
  const [urlInput, setUrlInput] = useState('')
  const [urlName, setUrlName] = useState('')

  // Delete folder confirmation
  const [folderToDelete, setFolderToDelete] = useState<Folder | null>(null)

  // Too-long document flow
  const [needsDescription, setNeedsDescription] = useState<{
    pendingFile?: File
    pendingUrl?: { url: string; name: string }
    wordCount: number
    numCtx: number
  } | null>(null)
  const [manualDescription, setManualDescription] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    documentsApi.listFolders().then(setFolders).finally(() => setLoadingFolders(false))
  }, [])

  useEffect(() => {
    if (!selectedFolder) { setDocuments([]); return }
    setLoadingDocs(true)
    documentsApi.listDocuments(selectedFolder.id)
      .then(setDocuments)
      .finally(() => setLoadingDocs(false))
  }, [selectedFolder])

  async function handleCreateFolder() {
    if (!newFolderName.trim()) return
    setCreatingFolder(true)
    setError(null)
    try {
      const folder = await documentsApi.createFolder(newFolderName.trim())
      setFolders(prev => [...prev, folder].sort((a, b) => a.name.localeCompare(b.name)))
      setNewFolderName('')
    } catch (e) {
      setError(String(e))
    } finally {
      setCreatingFolder(false)
    }
  }

  async function handleDeleteFolder(folder: Folder) {
    setFolderToDelete(null)
    setError(null)
    try {
      await documentsApi.deleteFolder(folder.id)
      setFolders(prev => prev.filter(f => f.id !== folder.id))
      if (selectedFolder?.id === folder.id) setSelectedFolder(null)
    } catch (e) {
      setError(String(e))
    }
  }

  async function processUploadResult(
    result: Awaited<ReturnType<typeof documentsApi.uploadFile>>,
    pendingFile?: File,
    pendingUrl?: { url: string; name: string },
  ) {
    if (result.status === 'ok') {
      setDocuments(prev => [...prev, result.document].sort((a, b) => a.name.localeCompare(b.name)))
      setNeedsDescription(null)
      setManualDescription('')
    } else {
      // Too long — prompt for description
      setNeedsDescription({ pendingFile, pendingUrl, wordCount: result.word_count, numCtx: result.num_ctx })
    }
  }

  async function handleFileUpload(file: File) {
    if (!selectedFolder) return
    setUploading(true)
    setError(null)
    try {
      const result = await documentsApi.uploadFile(file, selectedFolder.id)
      await processUploadResult(result, file)
    } catch (e) {
      setError(String(e))
    } finally {
      setUploading(false)
    }
  }

  async function handleUrlUpload() {
    if (!selectedFolder || !urlInput.trim() || !urlName.trim()) return
    setUploading(true)
    setError(null)
    try {
      const result = await documentsApi.uploadUrl(urlInput.trim(), selectedFolder.id, urlName.trim())
      await processUploadResult(result, undefined, { url: urlInput.trim(), name: urlName.trim() })
      setUrlInput('')
      setUrlName('')
    } catch (e) {
      setError(String(e))
    } finally {
      setUploading(false)
    }
  }

  async function handleSubmitWithDescription() {
    if (!needsDescription || !selectedFolder || !manualDescription.trim()) return
    setUploading(true)
    setError(null)
    try {
      let result: Awaited<ReturnType<typeof documentsApi.uploadFile>>
      if (needsDescription.pendingFile) {
        result = await documentsApi.uploadFile(
          needsDescription.pendingFile, selectedFolder.id, manualDescription.trim()
        )
      } else if (needsDescription.pendingUrl) {
        result = await documentsApi.uploadUrl(
          needsDescription.pendingUrl.url, selectedFolder.id,
          needsDescription.pendingUrl.name, manualDescription.trim()
        )
      } else {
        return
      }
      await processUploadResult(result)
    } catch (e) {
      setError(String(e))
    } finally {
      setUploading(false)
    }
  }

  async function handleDeleteDocument(doc: Document) {
    setError(null)
    try {
      await documentsApi.deleteDocument(doc.id)
      setDocuments(prev => prev.filter(d => d.id !== doc.id))
    } catch (e) {
      setError(String(e))
    }
  }

  return (
    <div className="pt-4 flex gap-6">
      {/* Left panel — folder list */}
      <div className="w-64 flex-shrink-0 flex flex-col gap-3">
        <div className="flex gap-2">
          <TextInput
            sizing="sm"
            placeholder={t('admin.documents.folder_name_placeholder')}
            value={newFolderName}
            onChange={e => setNewFolderName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleCreateFolder()}
            className="flex-1"
          />
          <Button size="sm" onClick={handleCreateFolder} disabled={creatingFolder || !newFolderName.trim()}>
            {creatingFolder ? <Spinner size="sm" /> : '+'}
          </Button>
        </div>
        {loadingFolders ? (
          <Spinner />
        ) : (
          <ListGroup>
            {folders.map(folder => (
              <ListGroup.Item
                key={folder.id}
                active={selectedFolder?.id === folder.id}
                onClick={() => setSelectedFolder(folder)}
                className="flex justify-between items-center cursor-pointer"
              >
                <span className="truncate flex-1">{folder.name}</span>
                <button
                  className="ml-2 text-gray-400 hover:text-red-500"
                  onClick={e => { e.stopPropagation(); setFolderToDelete(folder) }}
                  title={t('admin.documents.delete_folder')}
                >
                  ×
                </button>
              </ListGroup.Item>
            ))}
          </ListGroup>
        )}
      </div>

      {/* Right panel — document list */}
      <div className="flex-1 flex flex-col gap-4">
        {error && <Alert color="failure">{error}</Alert>}

        {!selectedFolder ? (
          <p className="text-gray-500">{t('admin.documents.no_folder_selected')}</p>
        ) : (
          <>
            {/* Upload controls */}
            <div className="flex flex-wrap gap-2 items-start">
              {/* File upload */}
              <div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.pptx,.xlsx,.txt,.md,.html,.htm"
                  className="hidden"
                  onChange={e => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
                />
                <Button size="sm" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
                  {t('admin.documents.upload_file')}
                </Button>
              </div>

              {/* URL upload */}
              <TextInput
                sizing="sm"
                placeholder={t('admin.documents.url_placeholder')}
                value={urlInput}
                onChange={e => setUrlInput(e.target.value)}
                className="w-56"
              />
              <TextInput
                sizing="sm"
                placeholder={t('admin.documents.url_name_placeholder')}
                value={urlName}
                onChange={e => setUrlName(e.target.value)}
                className="w-40"
              />
              <Button
                size="sm"
                onClick={handleUrlUpload}
                disabled={uploading || !urlInput.trim() || !urlName.trim()}
              >
                {uploading ? <Spinner size="sm" /> : t('admin.documents.add_from_url')}
              </Button>
            </div>

            {/* Too-long document — description prompt */}
            {needsDescription && (
              <Alert color="warning">
                <p className="font-semibold">{t('admin.documents.too_long_title')}</p>
                <p className="text-sm mt-1">
                  {t('admin.documents.too_long_body')
                    .replace('{{words}}', needsDescription.wordCount.toLocaleString())
                    .replace('{{tokens}}', (needsDescription.wordCount * 2).toLocaleString())
                    .replace('{{ctx}}', needsDescription.numCtx.toLocaleString())}
                </p>
                <div className="mt-2 flex gap-2">
                  <TextInput
                    sizing="sm"
                    placeholder={t('admin.documents.description_placeholder')}
                    value={manualDescription}
                    onChange={e => setManualDescription(e.target.value)}
                    className="flex-1"
                  />
                  <Button
                    size="sm"
                    onClick={handleSubmitWithDescription}
                    disabled={!manualDescription.trim() || uploading}
                  >
                    {uploading ? <Spinner size="sm" /> : t('admin.documents.submit_with_description')}
                  </Button>
                </div>
              </Alert>
            )}

            {/* Document list */}
            {loadingDocs ? (
              <Spinner />
            ) : documents.length === 0 ? (
              <p className="text-gray-500">{t('admin.documents.no_documents')}</p>
            ) : (
              <div className="flex flex-col gap-2">
                {documents.map(doc => (
                  <div
                    key={doc.id}
                    className="flex items-start justify-between p-3 bg-white border border-gray-200 rounded-lg"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{doc.name}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{doc.description}</p>
                    </div>
                    <Button
                      size="xs"
                      color="failure"
                      className="ml-3 flex-shrink-0"
                      onClick={() => handleDeleteDocument(doc)}
                    >
                      {t('admin.documents.delete_document')}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* Delete folder confirmation modal */}
      <Modal show={!!folderToDelete} onClose={() => setFolderToDelete(null)} size="sm">
        <Modal.Header>{t('admin.documents.delete_folder')}</Modal.Header>
        <Modal.Body>
          <p>{t('admin.documents.delete_folder_confirm')}</p>
        </Modal.Body>
        <Modal.Footer>
          <Button color="failure" onClick={() => folderToDelete && handleDeleteFolder(folderToDelete)}>
            {t('admin.documents.delete_folder')}
          </Button>
          <Button color="gray" onClick={() => setFolderToDelete(null)}>Cancel</Button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}
```

- [ ] **Step 2: Verify the build passes**

```bash
cd frontend && bun run build 2>&1 | head -50
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/DocumentsPanel.tsx
git commit -m "feat: add DocumentsPanel admin component"
```

---

## Task 5: AdminPanel — replace placeholder

**Files:**
- Modify: `frontend/src/pages/AdminPanel.tsx`

- [ ] **Step 1: Add the import at the top of `frontend/src/pages/AdminPanel.tsx`**

After the existing page imports, add:

```tsx
import DocumentsPanel from './DocumentsPanel'
```

- [ ] **Step 2: Replace the placeholder TabItem content**

Find the Documents `TabItem` (currently around line 274):

```tsx
          <TabItem title={t('admin.tab.documents')}>
            <p className="pt-4 text-gray-500">{t('admin.documents.placeholder')}</p>
          </TabItem>
```

Replace it with:

```tsx
          <TabItem title={t('admin.tab.documents')}>
            <DocumentsPanel />
          </TabItem>
```

- [ ] **Step 3: Verify the build passes**

```bash
cd frontend && bun run build 2>&1 | head -40
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/AdminPanel.tsx
git commit -m "feat: replace Documents tab placeholder with DocumentsPanel"
```

---

## Task 6: GemForm — document access section

**Files:**
- Modify: `frontend/src/pages/GemForm.tsx`

- [ ] **Step 1: Read the current bottom of `GemForm.tsx` to locate the save/cancel buttons**

The section to add goes above the save/cancel button row. Identify the exact JSX structure before adding.

- [ ] **Step 2: Add the import for documents API at the top of `GemForm.tsx`**

After existing imports:

```tsx
import { documentsApi, type Folder, type Document } from '../api/documents'
```

- [ ] **Step 3: Add state variables for the document tree**

Inside the `GemForm` component, after existing `useState` calls, add:

```tsx
  // Document access
  const [allFolders, setAllFolders] = useState<Folder[]>([])
  const [allDocuments, setAllDocuments] = useState<Document[]>([])
  const [checkedFolderIds, setCheckedFolderIds] = useState<Set<string>>(new Set(task?.doc_folder_ids ?? []))
  const [checkedDocIds, setCheckedDocIds] = useState<Set<string>>(new Set(task?.doc_ids ?? []))
```

In the `useEffect` that loads the gem on edit, also seed these sets from the loaded task:

```tsx
    if (task) {
      setCheckedFolderIds(new Set(task.doc_folder_ids))
      setCheckedDocIds(new Set(task.doc_ids))
    }
```

Add a separate `useEffect` to load folders and all documents on mount:

```tsx
  useEffect(() => {
    documentsApi.listFolders().then(setAllFolders)
    documentsApi.listDocuments().then(setAllDocuments)
  }, [])
```

- [ ] **Step 4: Add helper functions for the checkbox tree**

Inside the component, before the return:

```tsx
  /** All document IDs that belong to a folder. */
  function docsInFolder(folderId: string): Document[] {
    return allDocuments.filter(d => d.folder_id === folderId)
  }

  /** True when every document in the folder is individually checked. */
  function isFolderFullyChecked(folderId: string): boolean {
    const docs = docsInFolder(folderId)
    return docs.length > 0 && docs.every(d => checkedDocIds.has(d.id))
  }

  /** True when some (but not all) documents in the folder are individually checked. */
  function isFolderIndeterminate(folderId: string): boolean {
    if (checkedFolderIds.has(folderId)) return false
    const docs = docsInFolder(folderId)
    return docs.some(d => checkedDocIds.has(d.id)) && !isFolderFullyChecked(folderId)
  }

  /** True when a document is accessible (either via folder or individual grant). */
  function isDocChecked(doc: Document): boolean {
    return checkedFolderIds.has(doc.folder_id) || checkedDocIds.has(doc.id)
  }

  function toggleFolder(folderId: string, checked: boolean) {
    const docs = docsInFolder(folderId)
    setCheckedFolderIds(prev => {
      const next = new Set(prev)
      if (checked) next.add(folderId)
      else next.delete(folderId)
      return next
    })
    // Remove individual doc grants for docs in this folder (folder grant covers them)
    setCheckedDocIds(prev => {
      const next = new Set(prev)
      docs.forEach(d => next.delete(d.id))
      return next
    })
  }

  function toggleDocument(doc: Document, checked: boolean) {
    // If the folder is currently granted, switching to individual control:
    // uncheck the folder, then check all OTHER docs individually
    if (checkedFolderIds.has(doc.folder_id)) {
      const siblings = docsInFolder(doc.folder_id)
      setCheckedFolderIds(prev => { const n = new Set(prev); n.delete(doc.folder_id); return n })
      setCheckedDocIds(prev => {
        const n = new Set(prev)
        siblings.forEach(d => { if (d.id !== doc.id) n.add(d.id) })
        if (checked) n.add(doc.id)
        return n
      })
    } else {
      setCheckedDocIds(prev => {
        const n = new Set(prev)
        if (checked) n.add(doc.id)
        else n.delete(doc.id)
        return n
      })
    }
  }
```

- [ ] **Step 5: Collect doc access values when building the save payload**

Find where the `UserTask` object is constructed for save (the `handleSave` or similar function). Add `doc_folder_ids` and `doc_ids` to the payload:

```tsx
    const payload: UserTask = {
      // ... existing fields ...
      doc_folder_ids: Array.from(checkedFolderIds),
      doc_ids: Array.from(checkedDocIds),
    }
```

- [ ] **Step 6: Add the document access section to the JSX**

Locate the position just above the save/cancel button row in the return JSX. Insert the following section:

```tsx
        {/* Document access */}
        <div className="flex flex-col gap-2">
          <Label>{t('gem.documents.section_title')}</Label>
          <p className="text-xs text-gray-500">{t('gem.documents.section_hint')}</p>
          {allFolders.length === 0 ? (
            <p className="text-xs text-gray-400 italic">{t('gem.documents.no_folders')}</p>
          ) : (
            <div className="flex flex-col gap-1 border border-gray-200 rounded-lg p-3">
              {allFolders.map(folder => {
                const folderChecked = checkedFolderIds.has(folder.id)
                const indeterminate = isFolderIndeterminate(folder.id)
                const docs = docsInFolder(folder.id)
                return (
                  <div key={folder.id}>
                    {/* Folder row */}
                    <div className="flex items-center gap-2 py-1">
                      <input
                        type="checkbox"
                        checked={folderChecked}
                        ref={el => { if (el) el.indeterminate = indeterminate }}
                        onChange={e => toggleFolder(folder.id, e.target.checked)}
                        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        id={`folder-${folder.id}`}
                      />
                      <label htmlFor={`folder-${folder.id}`} className="text-sm font-medium text-gray-800 cursor-pointer">
                        {folder.name}
                      </label>
                    </div>
                    {/* Document rows */}
                    {docs.map(doc => (
                      <div key={doc.id} className="flex items-start gap-2 pl-6 py-0.5">
                        <input
                          type="checkbox"
                          checked={isDocChecked(doc)}
                          onChange={e => toggleDocument(doc, e.target.checked)}
                          className="mt-0.5 w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          id={`doc-${doc.id}`}
                        />
                        <label htmlFor={`doc-${doc.id}`} className="text-xs text-gray-700 cursor-pointer">
                          <span className="font-medium">{doc.name}</span>
                          {doc.description && (
                            <span className="text-gray-400"> — {doc.description}</span>
                          )}
                        </label>
                      </div>
                    ))}
                  </div>
                )
              })}
            </div>
          )}
        </div>
```

- [ ] **Step 7: Verify the build passes**

```bash
cd frontend && bun run build 2>&1 | head -50
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 8: Run in mock mode and verify the UI**

```bash
cd frontend && VITE_MOCK_API=1 bun run dev
```

Navigate to `/admin/gems/new`. Scroll to the bottom of the form. Verify:
- The "Document access" section shows the two mock folders (HR Policies, General Reference)
- Checking a folder checks its documents
- Unchecking individual documents shows the folder in indeterminate state
- Unchecking the folder unchecks all its documents

Navigate to the Documents tab in the admin panel. Verify:
- Folder list appears on the left
- Selecting a folder shows its documents on the right
- "Upload file" opens a file picker
- "Add from URL" fields appear and submit correctly (mock returns ok)

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/GemForm.tsx locales/en.json locales/it.json
git commit -m "feat: add document access tree to GemForm and locale strings"
```
